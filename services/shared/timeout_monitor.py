"""
Job Timeout Monitoring Service

A standalone service for monitoring and enforcing job processing timeouts
across the PDF accessibility platform. Can be run as a background service
or integrated into existing services.
"""

import asyncio
import os
import signal
import sys
from datetime import datetime
from typing import Optional

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from aws_lambda_powertools import Logger
from timeout_enforcement import TimeoutEvent, TimeoutReason, global_timeout_enforcer

logger = Logger()


class TimeoutMonitorService:
    """
    Standalone timeout monitoring service

    Provides continuous monitoring of job timeouts with configurable
    intervals and automatic cleanup of timed-out jobs.
    """

    def __init__(self, check_interval: int = 300):
        self.check_interval = check_interval
        self.enforcer = global_timeout_enforcer
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None

        # Register timeout callbacks
        self._register_callbacks()

    def _register_callbacks(self):
        """Register callbacks for different timeout events"""

        async def log_execution_timeout(event: TimeoutEvent):
            """Handle execution timeout events"""
            logger.error(
                f"Job execution timeout: {event.job_id}",
                extra={
                    "job_id": event.job_id,
                    "step": event.step,
                    "doc_id": event.doc_id,
                    "execution_duration": event.execution_duration,
                    "timeout_reason": "execution_timeout",
                },
            )

        async def log_heartbeat_timeout(event: TimeoutEvent):
            """Handle heartbeat timeout events"""
            logger.error(
                f"Job heartbeat timeout: {event.job_id}",
                extra={
                    "job_id": event.job_id,
                    "step": event.step,
                    "doc_id": event.doc_id,
                    "worker_instance": event.worker_instance,
                    "last_heartbeat": (
                        event.last_heartbeat.isoformat()
                        if event.last_heartbeat
                        else None
                    ),
                    "timeout_reason": "heartbeat_timeout",
                },
            )

        async def log_global_timeout(event: TimeoutEvent):
            """Handle global timeout events"""
            logger.error(
                f"Job global timeout: {event.job_id}",
                extra={
                    "job_id": event.job_id,
                    "step": event.step,
                    "doc_id": event.doc_id,
                    "execution_duration": event.execution_duration,
                    "timeout_reason": "global_timeout",
                },
            )

        # Register the callbacks
        self.enforcer.register_timeout_callback(
            TimeoutReason.EXECUTION_TIMEOUT, log_execution_timeout
        )
        self.enforcer.register_timeout_callback(
            TimeoutReason.HEARTBEAT_TIMEOUT, log_heartbeat_timeout
        )
        self.enforcer.register_timeout_callback(
            TimeoutReason.GLOBAL_TIMEOUT, log_global_timeout
        )

    async def start(self):
        """Start the timeout monitoring service"""
        if self.running:
            logger.warning("Timeout monitor service is already running")
            return

        self.running = True

        logger.info(
            f"Starting timeout monitor service with {self.check_interval}s intervals",
            extra={"check_interval": self.check_interval, "service": "timeout_monitor"},
        )

        # Start the monitoring loop
        self.monitor_task = asyncio.create_task(self._monitor_loop())

        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()

        # Wait for the monitoring task to complete
        try:
            await self.monitor_task
        except asyncio.CancelledError:
            logger.info("Timeout monitor service was cancelled")
        except Exception as e:
            logger.error(f"Timeout monitor service error: {e}")
            raise

    async def stop(self):
        """Stop the timeout monitoring service"""
        if not self.running:
            return

        logger.info("Stopping timeout monitor service")

        self.running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Timeout monitor service stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                start_time = datetime.utcnow()

                # Check for job timeouts
                timeout_events = await self.enforcer.check_job_timeouts()

                check_duration = (datetime.utcnow() - start_time).total_seconds()

                if timeout_events:
                    logger.info(
                        f"Timeout check completed: {len(timeout_events)} timeouts found",
                        extra={
                            "timeout_count": len(timeout_events),
                            "check_duration": check_duration,
                            "service": "timeout_monitor",
                        },
                    )
                else:
                    logger.debug(
                        "Timeout check completed: no timeouts found",
                        extra={
                            "check_duration": check_duration,
                            "service": "timeout_monitor",
                        },
                    )

                # Sleep until next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error in timeout monitoring loop: {e}",
                    extra={"service": "timeout_monitor", "error": str(e)},
                )
                # Sleep before retrying
                await asyncio.sleep(min(self.check_interval, 60))

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            if self.running:
                asyncio.create_task(self.stop())

        # Set up signal handlers (Unix-like systems)
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except AttributeError:
            # Windows doesn't have these signals
            pass

    async def get_service_status(self) -> dict:
        """Get current service status and statistics"""
        try:
            stats = await self.enforcer.get_timeout_statistics()

            return {
                "service_running": self.running,
                "check_interval": self.check_interval,
                "timeout_statistics": stats,
                "enforcer_monitoring": self.enforcer.monitoring_active,
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "service_running": self.running,
                "check_interval": self.check_interval,
                "error": str(e),
            }


async def main():
    """Main entry point for the timeout monitor service"""
    import argparse

    parser = argparse.ArgumentParser(description="Job Timeout Monitor Service")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Check interval in seconds (default: 300)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    # Create and start the service
    service = TimeoutMonitorService(check_interval=args.interval)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
        await service.stop()
    except Exception as e:
        logger.error(f"Service error: {e}")
        await service.stop()
        raise


if __name__ == "__main__":
    # Run the timeout monitor service
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# Export for use as a module
__all__ = ["TimeoutMonitorService"]

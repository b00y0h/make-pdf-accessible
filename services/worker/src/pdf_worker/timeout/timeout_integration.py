"""
Timeout Integration for PDF Worker Service

Integrates job timeout enforcement directly into the worker service
to ensure processing jobs respect timeout limits and provide heartbeat monitoring.
"""

import asyncio
import os
import sys
from collections.abc import Callable
from datetime import datetime
from typing import Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../shared"))

try:
    from mongo.jobs import get_job_repository
    from timeout_enforcement import (
        JobTimeoutEnforcer,
        TimeoutConfig,
        TimeoutEvent,
        TimeoutReason,
        get_timeout_enforcer,
    )
except ImportError:
    # Fallback if shared modules not available
    JobTimeoutEnforcer = None
    TimeoutConfig = None
    def get_timeout_enforcer(x):
        return None
    def get_job_repository():
        return None

from aws_lambda_powertools import Logger

logger = Logger()


class WorkerTimeoutManager:
    """
    Timeout management for PDF worker operations

    Provides worker-side timeout monitoring including:
    - Job execution time tracking
    - Heartbeat management
    - Timeout prevention and recovery
    - Resource cleanup on timeout
    """

    def __init__(self, service_name: str = "worker"):
        self.service_name = service_name
        self.enforcer = (
            get_timeout_enforcer(service_name) if get_timeout_enforcer else None
        )
        self.job_repo = get_job_repository() if get_job_repository else None
        self.active_jobs: dict[str, dict[str, Any]] = {}
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}
        self.timeout_tasks: dict[str, asyncio.Task] = {}

    async def start_job_with_timeout(
        self, job_id: str, step: str, job_function: Callable, *args, **kwargs
    ) -> Any:
        """
        Start a job with timeout monitoring

        Args:
            job_id: Job identifier
            step: Processing step name
            job_function: The function to execute
            *args, **kwargs: Arguments for the job function

        Returns:
            Job result or raises timeout exception
        """
        if not self.enforcer or not self.job_repo:
            logger.warning(
                "Timeout enforcement not available, running job without timeout"
            )
            return await job_function(*args, **kwargs)

        try:
            # Get timeout configuration for this step
            timeout_config = self.enforcer.get_timeout_config(step)

            logger.info(
                f"Starting job {job_id} with timeout monitoring",
                extra={
                    "job_id": job_id,
                    "step": step,
                    "execution_timeout": timeout_config.execution_timeout_seconds,
                    "heartbeat_interval": timeout_config.heartbeat_interval_seconds,
                },
            )

            # Start heartbeat monitoring
            await self._start_heartbeat_monitoring(job_id, timeout_config)

            # Start timeout monitoring
            timeout_task = asyncio.create_task(
                self._timeout_job_after_delay(
                    job_id, timeout_config.execution_timeout_seconds
                )
            )
            self.timeout_tasks[job_id] = timeout_task

            # Track job start
            self.active_jobs[job_id] = {
                "step": step,
                "start_time": datetime.utcnow(),
                "timeout_config": timeout_config,
            }

            try:
                # Execute the job with timeout
                result = await asyncio.wait_for(
                    job_function(*args, **kwargs),
                    timeout=timeout_config.execution_timeout_seconds,
                )

                logger.info(
                    f"Job {job_id} completed successfully",
                    extra={
                        "job_id": job_id,
                        "step": step,
                        "execution_time": (
                            datetime.utcnow() - self.active_jobs[job_id]["start_time"]
                        ).total_seconds(),
                    },
                )

                return result

            except TimeoutError:
                logger.error(
                    f"Job {job_id} timed out during execution",
                    extra={
                        "job_id": job_id,
                        "step": step,
                        "timeout_seconds": timeout_config.execution_timeout_seconds,
                    },
                )
                raise

        finally:
            # Clean up monitoring tasks
            await self._cleanup_job_monitoring(job_id)

    async def _start_heartbeat_monitoring(self, job_id: str, config: TimeoutConfig):
        """Start heartbeat monitoring for a job"""
        try:

            async def heartbeat_loop():
                while job_id in self.active_jobs:
                    try:
                        # Send heartbeat
                        worker_instance_id = f"{self.service_name}-{os.getpid()}"
                        success = self.job_repo.set_job_heartbeat(
                            job_id, worker_instance_id
                        )

                        if success:
                            logger.debug(
                                f"Heartbeat sent for job {job_id}",
                                extra={
                                    "job_id": job_id,
                                    "worker_instance": worker_instance_id,
                                },
                            )
                        else:
                            logger.warning(f"Failed to send heartbeat for job {job_id}")

                        # Wait for next heartbeat
                        await asyncio.sleep(config.heartbeat_interval_seconds)

                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error in heartbeat loop for job {job_id}: {e}")
                        await asyncio.sleep(config.heartbeat_interval_seconds)

            # Start heartbeat task
            self.heartbeat_tasks[job_id] = asyncio.create_task(heartbeat_loop())

        except Exception as e:
            logger.error(f"Error starting heartbeat monitoring for job {job_id}: {e}")

    async def _timeout_job_after_delay(self, job_id: str, timeout_seconds: int):
        """Timeout a job after specified delay"""
        try:
            await asyncio.sleep(timeout_seconds)

            # If we reach here, the job has timed out
            if job_id in self.active_jobs:
                logger.error(
                    f"Job {job_id} execution timeout after {timeout_seconds} seconds",
                    extra={
                        "job_id": job_id,
                        "timeout_seconds": timeout_seconds,
                        "step": self.active_jobs[job_id]["step"],
                    },
                )

                # Mark job as timed out in database
                if self.job_repo:
                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status="timeout",
                        error={
                            "type": "timeout",
                            "reason": "execution_timeout",
                            "timeout_seconds": timeout_seconds,
                        },
                    )

        except asyncio.CancelledError:
            # Normal cancellation when job completes
            pass
        except Exception as e:
            logger.error(f"Error in timeout monitoring for job {job_id}: {e}")

    async def _cleanup_job_monitoring(self, job_id: str):
        """Clean up monitoring tasks for a job"""
        try:
            # Cancel heartbeat task
            if job_id in self.heartbeat_tasks:
                self.heartbeat_tasks[job_id].cancel()
                try:
                    await self.heartbeat_tasks[job_id]
                except asyncio.CancelledError:
                    pass
                del self.heartbeat_tasks[job_id]

            # Cancel timeout task
            if job_id in self.timeout_tasks:
                self.timeout_tasks[job_id].cancel()
                try:
                    await self.timeout_tasks[job_id]
                except asyncio.CancelledError:
                    pass
                del self.timeout_tasks[job_id]

            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

        except Exception as e:
            logger.error(f"Error cleaning up monitoring for job {job_id}: {e}")

    async def send_heartbeat(self, job_id: str) -> bool:
        """Manually send a heartbeat for a job"""
        try:
            if not self.job_repo:
                return False

            worker_instance_id = f"{self.service_name}-{os.getpid()}"
            return self.job_repo.set_job_heartbeat(job_id, worker_instance_id)

        except Exception as e:
            logger.error(f"Error sending heartbeat for job {job_id}: {e}")
            return False

    async def check_job_timeout_status(self, job_id: str) -> dict[str, Any]:
        """Check timeout status for a specific job"""
        try:
            if job_id not in self.active_jobs:
                return {"active": False, "reason": "Job not found in active jobs"}

            job_info = self.active_jobs[job_id]
            elapsed_time = (datetime.utcnow() - job_info["start_time"]).total_seconds()
            timeout_config = job_info["timeout_config"]

            return {
                "active": True,
                "job_id": job_id,
                "step": job_info["step"],
                "elapsed_time": elapsed_time,
                "execution_timeout": timeout_config.execution_timeout_seconds,
                "heartbeat_interval": timeout_config.heartbeat_interval_seconds,
                "time_remaining": max(
                    0, timeout_config.execution_timeout_seconds - elapsed_time
                ),
                "heartbeat_active": job_id in self.heartbeat_tasks,
                "timeout_monitoring_active": job_id in self.timeout_tasks,
            }

        except Exception as e:
            logger.error(f"Error checking timeout status for job {job_id}: {e}")
            return {"active": False, "error": str(e)}

    async def get_active_jobs_status(self) -> dict[str, dict[str, Any]]:
        """Get timeout status for all active jobs"""
        status = {}

        for job_id in list(self.active_jobs.keys()):
            status[job_id] = await self.check_job_timeout_status(job_id)

        return status

    async def emergency_stop_job(
        self, job_id: str, reason: str = "emergency_stop"
    ) -> bool:
        """Emergency stop a job and clean up resources"""
        try:
            logger.warning(
                f"Emergency stop requested for job {job_id}",
                extra={"job_id": job_id, "reason": reason},
            )

            # Update job status
            if self.job_repo:
                self.job_repo.update_job_status(
                    job_id=job_id,
                    status="cancelled",
                    error={
                        "type": "emergency_stop",
                        "reason": reason,
                        "stopped_at": datetime.utcnow().isoformat(),
                    },
                )

            # Clean up monitoring
            await self._cleanup_job_monitoring(job_id)

            return True

        except Exception as e:
            logger.error(f"Error during emergency stop for job {job_id}: {e}")
            return False


# Global worker timeout manager
worker_timeout_manager = WorkerTimeoutManager()


# Convenience functions
async def run_job_with_timeout(
    job_id: str, step: str, job_function: Callable, *args, **kwargs
):
    """Run a job with timeout monitoring"""
    return await worker_timeout_manager.start_job_with_timeout(
        job_id, step, job_function, *args, **kwargs
    )


async def send_job_heartbeat(job_id: str) -> bool:
    """Send heartbeat for a job"""
    return await worker_timeout_manager.send_heartbeat(job_id)


async def stop_job(job_id: str, reason: str = "manual_stop") -> bool:
    """Emergency stop a job"""
    return await worker_timeout_manager.emergency_stop_job(job_id, reason)


async def get_job_timeout_status(job_id: str) -> dict[str, Any]:
    """Get timeout status for a job"""
    return await worker_timeout_manager.check_job_timeout_status(job_id)


# Export commonly used items
__all__ = [
    "WorkerTimeoutManager",
    "worker_timeout_manager",
    "run_job_with_timeout",
    "send_job_heartbeat",
    "stop_job",
    "get_job_timeout_status",
]

"""
Job Processing Timeout Enforcement

This module provides comprehensive timeout management for PDF processing jobs
to prevent jobs from running indefinitely and consuming excessive resources.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

try:
    from services.shared.mongo.jobs import JobRepository, get_job_repository
except ImportError:
    get_job_repository = None
    JobRepository = None

from aws_lambda_powertools import Logger

logger = Logger()


class JobStatus(str, Enum):
    """Job status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"
    CANCELLED = "cancelled"


class TimeoutReason(str, Enum):
    """Reasons for job timeout"""

    EXECUTION_TIMEOUT = "execution_timeout"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    RESOURCE_TIMEOUT = "resource_timeout"
    GLOBAL_TIMEOUT = "global_timeout"


@dataclass
class TimeoutConfig:
    """Configuration for job timeouts"""

    execution_timeout_seconds: int = 900  # 15 minutes default
    heartbeat_timeout_seconds: int = 120  # 2 minutes default
    global_timeout_seconds: int = 3600  # 1 hour absolute maximum
    heartbeat_interval_seconds: int = 30  # Expected heartbeat frequency
    max_retries_on_timeout: int = 2  # Max retries for timed out jobs
    cleanup_interval_seconds: int = 300  # How often to check for timeouts


@dataclass
class TimeoutEvent:
    """Represents a timeout event"""

    job_id: str
    timeout_reason: TimeoutReason
    timeout_at: datetime
    execution_duration: float
    last_heartbeat: Optional[datetime]
    worker_instance: Optional[str]
    step: str
    doc_id: str
    retry_count: int


class JobTimeoutEnforcer:
    """
    Enforces job processing timeouts across the PDF processing pipeline

    Monitors running jobs and automatically times them out based on:
    - Execution time limits
    - Heartbeat monitoring
    - Global timeout policies
    - Resource consumption limits
    """

    # Default timeout configurations by processing step
    STEP_TIMEOUTS = {
        "router": TimeoutConfig(
            execution_timeout_seconds=300,  # 5 minutes
            heartbeat_timeout_seconds=60,
            global_timeout_seconds=600,  # 10 minutes
        ),
        "ocr": TimeoutConfig(
            execution_timeout_seconds=1800,  # 30 minutes for OCR
            heartbeat_timeout_seconds=120,
            global_timeout_seconds=3600,  # 1 hour
        ),
        "structure": TimeoutConfig(
            execution_timeout_seconds=600,  # 10 minutes
            heartbeat_timeout_seconds=90,
            global_timeout_seconds=1200,  # 20 minutes
        ),
        "tagger": TimeoutConfig(
            execution_timeout_seconds=900,  # 15 minutes
            heartbeat_timeout_seconds=90,
            global_timeout_seconds=1800,  # 30 minutes
        ),
        "exporter": TimeoutConfig(
            execution_timeout_seconds=600,  # 10 minutes
            heartbeat_timeout_seconds=60,
            global_timeout_seconds=1200,  # 20 minutes
        ),
        "validator": TimeoutConfig(
            execution_timeout_seconds=300,  # 5 minutes
            heartbeat_timeout_seconds=60,
            global_timeout_seconds=600,  # 10 minutes
        ),
        "notifier": TimeoutConfig(
            execution_timeout_seconds=120,  # 2 minutes
            heartbeat_timeout_seconds=30,
            global_timeout_seconds=300,  # 5 minutes
        ),
        "alt_text": TimeoutConfig(
            execution_timeout_seconds=1200,  # 20 minutes for AI processing
            heartbeat_timeout_seconds=120,
            global_timeout_seconds=2400,  # 40 minutes
        ),
    }

    def __init__(self, service_name: str = "timeout_enforcer"):
        self.service_name = service_name
        self.job_repo = get_job_repository() if get_job_repository else None
        self.timeout_callbacks: Dict[TimeoutReason, List[Callable]] = {
            TimeoutReason.EXECUTION_TIMEOUT: [],
            TimeoutReason.HEARTBEAT_TIMEOUT: [],
            TimeoutReason.RESOURCE_TIMEOUT: [],
            TimeoutReason.GLOBAL_TIMEOUT: [],
        }
        self.monitoring_active = False
        self.cleanup_task: Optional[asyncio.Task] = None

    def get_timeout_config(self, step: str) -> TimeoutConfig:
        """Get timeout configuration for a processing step"""
        return self.STEP_TIMEOUTS.get(step, TimeoutConfig())

    async def check_job_timeouts(self) -> List[TimeoutEvent]:
        """
        Check all running jobs for timeout conditions

        Returns:
            List of timeout events that occurred
        """
        if not self.job_repo:
            logger.warning("Job repository not available, cannot check timeouts")
            return []

        timeout_events = []

        try:
            # Get all running jobs
            running_jobs = await self._get_running_jobs()

            for job in running_jobs:
                timeout_event = await self._check_single_job_timeout(job)
                if timeout_event:
                    timeout_events.append(timeout_event)
                    await self._handle_timeout_event(timeout_event)

            if timeout_events:
                logger.info(
                    f"Processed {len(timeout_events)} job timeouts",
                    extra={
                        "timeout_count": len(timeout_events),
                        "service": self.service_name,
                    },
                )

            return timeout_events

        except Exception as e:
            logger.error(f"Error checking job timeouts: {e}")
            return []

    async def _get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get all currently running jobs"""
        try:
            running_jobs = self.job_repo.get_jobs_by_status("running", limit=None)
            return running_jobs
        except Exception as e:
            logger.error(f"Error getting running jobs: {e}")
            return []

    async def _check_single_job_timeout(
        self, job: Dict[str, Any]
    ) -> Optional[TimeoutEvent]:
        """Check a single job for timeout conditions"""
        try:
            job_id = job.get("jobId")
            step = job.get("step", "unknown")
            doc_id = job.get("docId", "unknown")
            started_at = job.get("startedAt")
            last_heartbeat = job.get("worker", {}).get("lastHeartbeat")
            worker_instance = job.get("worker", {}).get("instanceId")
            retry_count = job.get("attempts", 0)

            if not started_at:
                # Job marked as running but no start time - assume started now
                logger.warning(
                    f"Running job {job_id} has no start time, assuming started now"
                )
                started_at = datetime.utcnow()

            # Get timeout configuration for this step
            timeout_config = self.get_timeout_config(step)

            now = datetime.utcnow()
            execution_duration = (now - started_at).total_seconds()

            # Check execution timeout
            if execution_duration > timeout_config.execution_timeout_seconds:
                return TimeoutEvent(
                    job_id=job_id,
                    timeout_reason=TimeoutReason.EXECUTION_TIMEOUT,
                    timeout_at=now,
                    execution_duration=execution_duration,
                    last_heartbeat=last_heartbeat,
                    worker_instance=worker_instance,
                    step=step,
                    doc_id=doc_id,
                    retry_count=retry_count,
                )

            # Check global timeout
            if execution_duration > timeout_config.global_timeout_seconds:
                return TimeoutEvent(
                    job_id=job_id,
                    timeout_reason=TimeoutReason.GLOBAL_TIMEOUT,
                    timeout_at=now,
                    execution_duration=execution_duration,
                    last_heartbeat=last_heartbeat,
                    worker_instance=worker_instance,
                    step=step,
                    doc_id=doc_id,
                    retry_count=retry_count,
                )

            # Check heartbeat timeout
            if last_heartbeat:
                heartbeat_age = (now - last_heartbeat).total_seconds()
                if heartbeat_age > timeout_config.heartbeat_timeout_seconds:
                    return TimeoutEvent(
                        job_id=job_id,
                        timeout_reason=TimeoutReason.HEARTBEAT_TIMEOUT,
                        timeout_at=now,
                        execution_duration=execution_duration,
                        last_heartbeat=last_heartbeat,
                        worker_instance=worker_instance,
                        step=step,
                        doc_id=doc_id,
                        retry_count=retry_count,
                    )

            # If no last heartbeat but job has been running for more than heartbeat timeout
            elif execution_duration > timeout_config.heartbeat_timeout_seconds:
                return TimeoutEvent(
                    job_id=job_id,
                    timeout_reason=TimeoutReason.HEARTBEAT_TIMEOUT,
                    timeout_at=now,
                    execution_duration=execution_duration,
                    last_heartbeat=None,
                    worker_instance=worker_instance,
                    step=step,
                    doc_id=doc_id,
                    retry_count=retry_count,
                )

            return None

        except Exception as e:
            logger.error(
                f"Error checking timeout for job {job.get('jobId', 'unknown')}: {e}"
            )
            return None

    async def _handle_timeout_event(self, event: TimeoutEvent):
        """Handle a timeout event by updating job status and triggering callbacks"""
        try:
            timeout_config = self.get_timeout_config(event.step)

            # Determine if job should be retried or failed
            should_retry = (
                event.retry_count < timeout_config.max_retries_on_timeout
                and event.timeout_reason
                in [TimeoutReason.EXECUTION_TIMEOUT, TimeoutReason.HEARTBEAT_TIMEOUT]
            )

            new_status = JobStatus.RETRY if should_retry else JobStatus.TIMEOUT

            # Update job status
            error_info = {
                "type": "timeout",
                "reason": event.timeout_reason.value,
                "execution_duration": event.execution_duration,
                "timeout_at": event.timeout_at.isoformat(),
                "last_heartbeat": (
                    event.last_heartbeat.isoformat() if event.last_heartbeat else None
                ),
                "worker_instance": event.worker_instance,
                "retry_count": event.retry_count,
                "will_retry": should_retry,
            }

            success = self.job_repo.update_job_status(
                job_id=event.job_id,
                status=new_status.value,
                completed_at=event.timeout_at,
                execution_time_seconds=event.execution_duration,
                error=error_info,
            )

            if success:
                logger.warning(
                    f"Job {event.job_id} timed out: {event.timeout_reason.value}",
                    extra={
                        "job_id": event.job_id,
                        "step": event.step,
                        "doc_id": event.doc_id,
                        "timeout_reason": event.timeout_reason.value,
                        "execution_duration": event.execution_duration,
                        "retry_count": event.retry_count,
                        "will_retry": should_retry,
                        "worker_instance": event.worker_instance,
                    },
                )

                # Add timeout log entry
                await self._add_timeout_log(event, should_retry)

                # Trigger timeout callbacks
                await self._trigger_timeout_callbacks(event)
            else:
                logger.error(f"Failed to update job status for timeout: {event.job_id}")

        except Exception as e:
            logger.error(f"Error handling timeout event for job {event.job_id}: {e}")

    async def _add_timeout_log(self, event: TimeoutEvent, will_retry: bool):
        """Add a log entry for the timeout event"""
        try:
            log_entry = {
                "level": "ERROR",
                "message": f"Job timed out: {event.timeout_reason.value}",
                "details": {
                    "timeout_reason": event.timeout_reason.value,
                    "execution_duration": event.execution_duration,
                    "last_heartbeat": (
                        event.last_heartbeat.isoformat()
                        if event.last_heartbeat
                        else None
                    ),
                    "worker_instance": event.worker_instance,
                    "will_retry": will_retry,
                },
                "timestamp": event.timeout_at,
                "source": "timeout_enforcer",
            }

            self.job_repo.add_job_log(event.job_id, log_entry)

        except Exception as e:
            logger.error(f"Error adding timeout log for job {event.job_id}: {e}")

    async def _trigger_timeout_callbacks(self, event: TimeoutEvent):
        """Trigger registered callbacks for timeout events"""
        try:
            callbacks = self.timeout_callbacks.get(event.timeout_reason, [])
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in timeout callback: {e}")

        except Exception as e:
            logger.error(f"Error triggering timeout callbacks: {e}")

    def register_timeout_callback(
        self, timeout_reason: TimeoutReason, callback: Callable
    ):
        """Register a callback to be triggered on specific timeout events"""
        if timeout_reason not in self.timeout_callbacks:
            self.timeout_callbacks[timeout_reason] = []
        self.timeout_callbacks[timeout_reason].append(callback)

    async def start_monitoring(self, check_interval_seconds: int = 300):
        """Start continuous timeout monitoring"""
        if self.monitoring_active:
            logger.warning("Timeout monitoring is already active")
            return

        self.monitoring_active = True

        async def monitor_loop():
            while self.monitoring_active:
                try:
                    await self.check_job_timeouts()
                    await asyncio.sleep(check_interval_seconds)
                except Exception as e:
                    logger.error(f"Error in timeout monitoring loop: {e}")
                    await asyncio.sleep(check_interval_seconds)

        self.cleanup_task = asyncio.create_task(monitor_loop())

        logger.info(
            f"Started job timeout monitoring with {check_interval_seconds}s intervals",
            extra={
                "check_interval": check_interval_seconds,
                "service": self.service_name,
            },
        )

    async def stop_monitoring(self):
        """Stop timeout monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped job timeout monitoring")

    async def force_timeout_job(
        self, job_id: str, reason: str = "manual_timeout"
    ) -> bool:
        """Manually timeout a specific job"""
        try:
            if not self.job_repo:
                return False

            job = self.job_repo.get_job(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return False

            if job.get("status") != "running":
                logger.error(
                    f"Job {job_id} is not running (status: {job.get('status')})"
                )
                return False

            # Create timeout event
            started_at = job.get("startedAt", datetime.utcnow())
            now = datetime.utcnow()
            execution_duration = (now - started_at).total_seconds()

            event = TimeoutEvent(
                job_id=job_id,
                timeout_reason=TimeoutReason.GLOBAL_TIMEOUT,
                timeout_at=now,
                execution_duration=execution_duration,
                last_heartbeat=job.get("worker", {}).get("lastHeartbeat"),
                worker_instance=job.get("worker", {}).get("instanceId"),
                step=job.get("step", "unknown"),
                doc_id=job.get("docId", "unknown"),
                retry_count=job.get("attempts", 0),
            )

            await self._handle_timeout_event(event)

            logger.info(
                f"Manually timed out job {job_id}",
                extra={
                    "job_id": job_id,
                    "reason": reason,
                    "execution_duration": execution_duration,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error forcing timeout for job {job_id}: {e}")
            return False

    async def get_timeout_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get timeout statistics for the specified period"""
        try:
            if not self.job_repo:
                return {"available": False, "reason": "Job repository not available"}

            start_date = datetime.utcnow() - timedelta(days=days)

            # Get timeout jobs
            timeout_jobs = self.job_repo.find(
                {
                    "status": {"$in": ["timeout", "failed"]},
                    "error.type": "timeout",
                    "completedAt": {"$gte": start_date},
                }
            )

            # Analyze timeout patterns
            timeout_by_step = {}
            timeout_by_reason = {}
            total_timeouts = 0

            for job in timeout_jobs:
                total_timeouts += 1
                step = job.get("step", "unknown")
                timeout_reason = job.get("error", {}).get("reason", "unknown")

                timeout_by_step[step] = timeout_by_step.get(step, 0) + 1
                timeout_by_reason[timeout_reason] = (
                    timeout_by_reason.get(timeout_reason, 0) + 1
                )

            # Get total jobs for comparison
            total_jobs = self.job_repo.count({"createdAt": {"$gte": start_date}})

            timeout_rate = (total_timeouts / total_jobs) if total_jobs > 0 else 0

            return {
                "available": True,
                "period_days": days,
                "total_timeouts": total_timeouts,
                "total_jobs": total_jobs,
                "timeout_rate": timeout_rate,
                "timeouts_by_step": timeout_by_step,
                "timeouts_by_reason": timeout_by_reason,
                "monitoring_active": self.monitoring_active,
            }

        except Exception as e:
            logger.error(f"Error getting timeout statistics: {e}")
            return {"available": False, "reason": f"Error: {str(e)}"}


# Global timeout enforcer instance
global_timeout_enforcer = JobTimeoutEnforcer("global")


# Service-specific timeout enforcers
def get_timeout_enforcer(service_name: str) -> JobTimeoutEnforcer:
    """Get timeout enforcer instance for a service"""
    return JobTimeoutEnforcer(service_name)


# Convenience functions
async def check_timeouts() -> List[TimeoutEvent]:
    """Quick check for job timeouts"""
    return await global_timeout_enforcer.check_job_timeouts()


async def timeout_job(job_id: str, reason: str = "manual") -> bool:
    """Manually timeout a specific job"""
    return await global_timeout_enforcer.force_timeout_job(job_id, reason)


async def get_timeout_stats(days: int = 7) -> Dict[str, Any]:
    """Get timeout statistics"""
    return await global_timeout_enforcer.get_timeout_statistics(days)


def configure_step_timeout(step: str, config: TimeoutConfig):
    """Configure timeout settings for a processing step"""
    JobTimeoutEnforcer.STEP_TIMEOUTS[step] = config


# Export commonly used items
__all__ = [
    "JobStatus",
    "TimeoutReason",
    "TimeoutConfig",
    "TimeoutEvent",
    "JobTimeoutEnforcer",
    "global_timeout_enforcer",
    "get_timeout_enforcer",
    "check_timeouts",
    "timeout_job",
    "get_timeout_stats",
    "configure_step_timeout",
]

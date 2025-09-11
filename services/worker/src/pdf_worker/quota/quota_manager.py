"""
Quota management for PDF worker service

Integrates with the shared quota enforcement system to ensure
worker operations respect organizational limits and track usage.
"""

import os
import sys
from dataclasses import dataclass
from typing import Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../shared"))

try:
    from quota_enforcement import (
        QuotaEnforcer,
        QuotaStatus,
        QuotaType,
        check_processing_quota,
        check_storage_quota,
        increment_processing_usage,
        increment_storage_usage,
        worker_quota_enforcer,
    )
except ImportError:
    # Fallback if shared modules not available
    QuotaEnforcer = None
    QuotaType = None
    QuotaStatus = None
    worker_quota_enforcer = None

from aws_lambda_powertools import Logger

logger = Logger()


@dataclass
class WorkerQuotaCheck:
    """Result of worker quota check"""

    can_proceed: bool
    quota_type: str
    current_usage: int
    limit: int
    reason: str | None = None


class WorkerQuotaManager:
    """
    Quota management specific to PDF worker operations

    Handles quota enforcement for document processing, storage usage,
    and concurrent job limits within the worker service.
    """

    def __init__(self):
        self.quota_enforcer = worker_quota_enforcer if worker_quota_enforcer else None
        self.fallback_limits = {
            "processing_monthly": 100,
            "storage_total": 5 * 1024 * 1024 * 1024,  # 5GB
            "concurrent_jobs": 5,
            "file_count_total": 1000,
        }

    async def check_processing_quota(self, org_id: str) -> WorkerQuotaCheck:
        """
        Check if organization can process another document

        Args:
            org_id: Organization ID

        Returns:
            WorkerQuotaCheck with result
        """
        try:
            if not self.quota_enforcer:
                return WorkerQuotaCheck(
                    can_proceed=True,
                    quota_type="processing_monthly",
                    current_usage=0,
                    limit=self.fallback_limits["processing_monthly"],
                    reason="Quota enforcement not available",
                )

            can_proceed = await check_processing_quota(org_id, "worker")
            status = await self.quota_enforcer.get_quota_status(
                org_id, QuotaType.PROCESSING_MONTHLY
            )

            if status:
                return WorkerQuotaCheck(
                    can_proceed=can_proceed,
                    quota_type="processing_monthly",
                    current_usage=status.current_usage,
                    limit=status.limit,
                    reason=(
                        None
                        if can_proceed
                        else f"Monthly processing limit exceeded ({status.current_usage}/{status.limit})"
                    ),
                )
            else:
                return WorkerQuotaCheck(
                    can_proceed=True,
                    quota_type="processing_monthly",
                    current_usage=0,
                    limit=self.fallback_limits["processing_monthly"],
                    reason="No quota status available",
                )

        except Exception as e:
            logger.error(f"Error checking processing quota for {org_id}: {e}")
            return WorkerQuotaCheck(
                can_proceed=True,  # Allow on error
                quota_type="processing_monthly",
                current_usage=0,
                limit=self.fallback_limits["processing_monthly"],
                reason=f"Quota check failed: {str(e)}",
            )

    async def check_storage_quota(
        self, org_id: str, file_size: int
    ) -> WorkerQuotaCheck:
        """
        Check if organization can store additional file data

        Args:
            org_id: Organization ID
            file_size: Size of file to be stored in bytes

        Returns:
            WorkerQuotaCheck with result
        """
        try:
            if not self.quota_enforcer:
                return WorkerQuotaCheck(
                    can_proceed=True,
                    quota_type="storage_total",
                    current_usage=0,
                    limit=self.fallback_limits["storage_total"],
                    reason="Quota enforcement not available",
                )

            can_proceed = await check_storage_quota(org_id, file_size, "worker")
            status = await self.quota_enforcer.get_quota_status(
                org_id, QuotaType.STORAGE_TOTAL
            )

            if status:
                return WorkerQuotaCheck(
                    can_proceed=can_proceed,
                    quota_type="storage_total",
                    current_usage=status.current_usage,
                    limit=status.limit,
                    reason=(
                        None
                        if can_proceed
                        else f"Storage limit exceeded (would use {status.current_usage + file_size}/{status.limit} bytes)"
                    ),
                )
            else:
                return WorkerQuotaCheck(
                    can_proceed=True,
                    quota_type="storage_total",
                    current_usage=0,
                    limit=self.fallback_limits["storage_total"],
                    reason="No quota status available",
                )

        except Exception as e:
            logger.error(f"Error checking storage quota for {org_id}: {e}")
            return WorkerQuotaCheck(
                can_proceed=True,  # Allow on error
                quota_type="storage_total",
                current_usage=0,
                limit=self.fallback_limits["storage_total"],
                reason=f"Quota check failed: {str(e)}",
            )

    async def check_concurrent_jobs_quota(self, org_id: str) -> WorkerQuotaCheck:
        """
        Check if organization can start another concurrent job

        Args:
            org_id: Organization ID

        Returns:
            WorkerQuotaCheck with result
        """
        try:
            if not self.quota_enforcer:
                return WorkerQuotaCheck(
                    can_proceed=True,
                    quota_type="concurrent_jobs",
                    current_usage=0,
                    limit=self.fallback_limits["concurrent_jobs"],
                    reason="Quota enforcement not available",
                )

            can_proceed = await self.quota_enforcer.enforce_quota(
                org_id, QuotaType.CONCURRENT_JOBS, 1
            )
            status = await self.quota_enforcer.get_quota_status(
                org_id, QuotaType.CONCURRENT_JOBS
            )

            if status:
                return WorkerQuotaCheck(
                    can_proceed=can_proceed,
                    quota_type="concurrent_jobs",
                    current_usage=status.current_usage,
                    limit=status.limit,
                    reason=(
                        None
                        if can_proceed
                        else f"Concurrent job limit exceeded ({status.current_usage}/{status.limit})"
                    ),
                )
            else:
                return WorkerQuotaCheck(
                    can_proceed=True,
                    quota_type="concurrent_jobs",
                    current_usage=0,
                    limit=self.fallback_limits["concurrent_jobs"],
                    reason="No quota status available",
                )

        except Exception as e:
            logger.error(f"Error checking concurrent jobs quota for {org_id}: {e}")
            return WorkerQuotaCheck(
                can_proceed=True,  # Allow on error
                quota_type="concurrent_jobs",
                current_usage=0,
                limit=self.fallback_limits["concurrent_jobs"],
                reason=f"Quota check failed: {str(e)}",
            )

    async def validate_job_quotas(
        self, org_id: str, file_size: int = 0
    ) -> dict[str, WorkerQuotaCheck]:
        """
        Validate all relevant quotas for a processing job

        Args:
            org_id: Organization ID
            file_size: Size of file being processed (optional)

        Returns:
            Dictionary of quota check results by quota type
        """
        results = {}

        # Check processing quota
        results["processing"] = await self.check_processing_quota(org_id)

        # Check storage quota if file size provided
        if file_size > 0:
            results["storage"] = await self.check_storage_quota(org_id, file_size)

        # Check concurrent jobs quota
        results["concurrent_jobs"] = await self.check_concurrent_jobs_quota(org_id)

        return results

    async def can_start_job(self, org_id: str, file_size: int = 0) -> bool:
        """
        Check if a job can be started based on all quota constraints

        Args:
            org_id: Organization ID
            file_size: Size of file being processed (optional)

        Returns:
            True if job can be started, False otherwise
        """
        quota_results = await self.validate_job_quotas(org_id, file_size)

        # All quota checks must pass
        for quota_type, result in quota_results.items():
            if not result.can_proceed:
                logger.warning(
                    f"Job blocked by {quota_type} quota for {org_id}: {result.reason}",
                    extra={
                        "org_id": org_id,
                        "quota_type": quota_type,
                        "reason": result.reason,
                        "current_usage": result.current_usage,
                        "limit": result.limit,
                    },
                )
                return False

        return True

    async def record_job_completion(
        self,
        org_id: str,
        file_size: int = 0,
        output_files: dict[str, int] | None = None,
    ) -> bool:
        """
        Record quota usage after job completion

        Args:
            org_id: Organization ID
            file_size: Size of original file processed
            output_files: Dictionary of output file names to sizes

        Returns:
            True if usage recorded successfully
        """
        try:
            success = True

            if not self.quota_enforcer:
                logger.warning("Quota enforcer not available, cannot record usage")
                return False

            # Record processing usage
            processing_success = await increment_processing_usage(org_id, "worker")
            if not processing_success:
                logger.error(f"Failed to record processing usage for {org_id}")
                success = False

            # Record storage usage for output files
            if output_files:
                total_output_size = sum(output_files.values())
                storage_success = await increment_storage_usage(
                    org_id, total_output_size, "worker"
                )
                if not storage_success:
                    logger.error(f"Failed to record storage usage for {org_id}")
                    success = False

                logger.info(
                    f"Recorded storage usage for {org_id}: {total_output_size} bytes from {len(output_files)} files",
                    extra={
                        "org_id": org_id,
                        "output_size": total_output_size,
                        "file_count": len(output_files),
                        "files": list(output_files.keys()),
                    },
                )

            # Record file count usage
            if output_files:
                file_count_success = await self.quota_enforcer.increment_usage(
                    org_id, QuotaType.FILE_COUNT_TOTAL, len(output_files)
                )
                if not file_count_success:
                    logger.error(f"Failed to record file count usage for {org_id}")
                    success = False

            logger.info(
                f"Job completion quota recording for {org_id}: {'success' if success else 'partial failure'}",
                extra={
                    "org_id": org_id,
                    "processing_recorded": processing_success,
                    "storage_recorded": storage_success if output_files else True,
                    "file_count_recorded": file_count_success if output_files else True,
                },
            )

            return success

        except Exception as e:
            logger.error(f"Error recording job completion usage for {org_id}: {e}")
            return False

    async def get_quota_summary(self, org_id: str) -> dict[str, Any]:
        """
        Get comprehensive quota status summary for an organization

        Args:
            org_id: Organization ID

        Returns:
            Dictionary with quota status information
        """
        try:
            if not self.quota_enforcer:
                return {
                    "available": False,
                    "reason": "Quota enforcement not available",
                    "quotas": {},
                }

            all_status = await self.quota_enforcer.get_all_quota_status(org_id)

            summary = {
                "available": True,
                "org_id": org_id,
                "quotas": {},
                "recommendations": [],
            }

            for quota_type, status in all_status.items():
                summary["quotas"][quota_type] = {
                    "current_usage": status.current_usage,
                    "limit": status.limit,
                    "remaining": status.remaining,
                    "percentage_used": status.percentage_used,
                    "is_exceeded": status.is_exceeded,
                    "period_start": status.period_start.isoformat(),
                    "period_end": status.period_end.isoformat(),
                }

                # Add recommendations based on usage
                if status.percentage_used > 90:
                    summary["recommendations"].append(
                        f"{quota_type} quota is nearly exhausted ({status.percentage_used:.1f}% used)"
                    )
                elif status.is_exceeded:
                    summary["recommendations"].append(
                        f"{quota_type} quota has been exceeded ({status.current_usage}/{status.limit})"
                    )

            return summary

        except Exception as e:
            logger.error(f"Error getting quota summary for {org_id}: {e}")
            return {
                "available": False,
                "reason": f"Error retrieving quota status: {str(e)}",
                "quotas": {},
            }


# Global worker quota manager instance
worker_quota_manager = WorkerQuotaManager()


# Convenience functions for worker operations
async def can_start_processing_job(org_id: str, file_size: int = 0) -> bool:
    """Check if organization can start a processing job"""
    return await worker_quota_manager.can_start_job(org_id, file_size)


async def record_processing_completion(
    org_id: str, file_size: int = 0, output_files: dict[str, int] | None = None
) -> bool:
    """Record quota usage after processing completion"""
    return await worker_quota_manager.record_job_completion(
        org_id, file_size, output_files
    )


async def get_worker_quota_status(org_id: str) -> dict[str, Any]:
    """Get worker-specific quota status"""
    return await worker_quota_manager.get_quota_summary(org_id)


# Export commonly used items
__all__ = [
    "WorkerQuotaCheck",
    "WorkerQuotaManager",
    "worker_quota_manager",
    "can_start_processing_job",
    "record_processing_completion",
    "get_worker_quota_status",
]

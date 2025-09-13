"""
Shared quota enforcement utilities for microservices

This module provides consistent quota enforcement across all services
in the PDF accessibility platform, including real-time monitoring
and automatic quota management.
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

try:
    from services.shared.mongo.repository import BaseRepository
except ImportError:
    # Fallback for services that don't have direct access to shared modules
    BaseRepository = None

from aws_lambda_powertools import Logger

logger = Logger()


class QuotaType(str, Enum):
    """Types of quotas that can be enforced"""

    PROCESSING_MONTHLY = "processing_monthly"
    STORAGE_TOTAL = "storage_total"
    API_CALLS_MONTHLY = "api_calls_monthly"
    CONCURRENT_JOBS = "concurrent_jobs"
    BANDWIDTH_MONTHLY = "bandwidth_monthly"
    FILE_COUNT_TOTAL = "file_count_total"


@dataclass
class QuotaViolation:
    """Represents a quota violation"""

    quota_type: QuotaType
    current_usage: int
    limit: int
    org_id: str
    exceeded_by: int
    timestamp: datetime
    service_name: str


@dataclass
class QuotaStatus:
    """Current quota status for an organization"""

    org_id: str
    quota_type: QuotaType
    current_usage: int
    limit: int
    percentage_used: float
    remaining: int
    is_exceeded: bool
    period_start: datetime
    period_end: datetime
    last_updated: datetime


class QuotaEnforcer:
    """
    Centralized quota enforcement for all services

    Provides real-time quota checking, usage tracking, and violation handling
    across the entire PDF accessibility platform.
    """

    # Default quota limits for different service tiers
    DEFAULT_QUOTAS = {
        "free": {
            QuotaType.PROCESSING_MONTHLY: 10,  # 10 documents/month
            QuotaType.STORAGE_TOTAL: 1024 * 1024 * 1024,  # 1GB
            QuotaType.API_CALLS_MONTHLY: 1000,  # 1k API calls/month
            QuotaType.CONCURRENT_JOBS: 1,  # 1 concurrent job
            QuotaType.BANDWIDTH_MONTHLY: 5 * 1024 * 1024 * 1024,  # 5GB bandwidth
            QuotaType.FILE_COUNT_TOTAL: 100,  # 100 files total
        },
        "basic": {
            QuotaType.PROCESSING_MONTHLY: 100,  # 100 documents/month
            QuotaType.STORAGE_TOTAL: 5 * 1024 * 1024 * 1024,  # 5GB
            QuotaType.API_CALLS_MONTHLY: 10000,  # 10k API calls/month
            QuotaType.CONCURRENT_JOBS: 3,  # 3 concurrent jobs
            QuotaType.BANDWIDTH_MONTHLY: 50 * 1024 * 1024 * 1024,  # 50GB bandwidth
            QuotaType.FILE_COUNT_TOTAL: 1000,  # 1k files total
        },
        "pro": {
            QuotaType.PROCESSING_MONTHLY: 1000,  # 1k documents/month
            QuotaType.STORAGE_TOTAL: 50 * 1024 * 1024 * 1024,  # 50GB
            QuotaType.API_CALLS_MONTHLY: 100000,  # 100k API calls/month
            QuotaType.CONCURRENT_JOBS: 10,  # 10 concurrent jobs
            QuotaType.BANDWIDTH_MONTHLY: 500 * 1024 * 1024 * 1024,  # 500GB bandwidth
            QuotaType.FILE_COUNT_TOTAL: 10000,  # 10k files total
        },
        "enterprise": {
            QuotaType.PROCESSING_MONTHLY: -1,  # Unlimited
            QuotaType.STORAGE_TOTAL: -1,  # Unlimited
            QuotaType.API_CALLS_MONTHLY: -1,  # Unlimited
            QuotaType.CONCURRENT_JOBS: 50,  # 50 concurrent jobs
            QuotaType.BANDWIDTH_MONTHLY: -1,  # Unlimited
            QuotaType.FILE_COUNT_TOTAL: -1,  # Unlimited
        },
    }

    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self.quota_cache: dict[str, dict] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update: dict[str, datetime] = {}

        # Initialize repositories if available
        self.quota_limits_repo = (
            BaseRepository("quota_limits") if BaseRepository else None
        )
        self.quota_usage_repo = (
            BaseRepository("quota_usage") if BaseRepository else None
        )
        self.violations_repo = (
            BaseRepository("quota_violations") if BaseRepository else None
        )

    async def check_quota_limit(
        self,
        org_id: str,
        quota_type: QuotaType,
        additional_usage: int = 1,
        file_size: Optional[int] = None,
    ) -> tuple[bool, Optional[QuotaViolation]]:
        """
        Check if adding usage would exceed quota limit

        Args:
            org_id: Organization ID
            quota_type: Type of quota to check
            additional_usage: Amount of usage to add
            file_size: File size for storage quotas (optional)

        Returns:
            Tuple of (can_proceed, violation_info)
        """
        try:
            # Use file size for storage quotas
            if quota_type == QuotaType.STORAGE_TOTAL and file_size is not None:
                additional_usage = file_size

            # Get current quota status
            status = await self._get_quota_status(org_id, quota_type)
            if not status:
                logger.warning(f"No quota status found for {org_id}, {quota_type}")
                return True, None

            # Check for unlimited quotas
            if status.limit == -1:
                return True, None

            # Check if adding usage would exceed limit
            new_usage = status.current_usage + additional_usage
            if new_usage > status.limit:
                violation = QuotaViolation(
                    quota_type=quota_type,
                    current_usage=status.current_usage,
                    limit=status.limit,
                    org_id=org_id,
                    exceeded_by=new_usage - status.limit,
                    timestamp=datetime.utcnow(),
                    service_name=self.service_name,
                )

                # Log violation
                await self._record_violation(violation)

                logger.warning(
                    f"Quota violation for {org_id}, {quota_type}: "
                    f"{new_usage} > {status.limit} (exceeded by {violation.exceeded_by})",
                    extra={
                        "org_id": org_id,
                        "quota_type": quota_type.value,
                        "current_usage": status.current_usage,
                        "additional_usage": additional_usage,
                        "limit": status.limit,
                        "service": self.service_name,
                    },
                )

                return False, violation

            return True, None

        except Exception as e:
            logger.error(f"Error checking quota limit for {org_id}, {quota_type}: {e}")
            # Allow on error to avoid blocking operations
            return True, None

    async def enforce_quota(
        self,
        org_id: str,
        quota_type: QuotaType,
        additional_usage: int = 1,
        file_size: Optional[int] = None,
    ) -> bool:
        """
        Enforce quota check and return result

        Args:
            org_id: Organization ID
            quota_type: Type of quota to check
            additional_usage: Amount of usage to add
            file_size: File size for storage quotas (optional)

        Returns:
            True if quota allows the operation, False if exceeded
        """
        can_proceed, violation = await self.check_quota_limit(
            org_id, quota_type, additional_usage, file_size
        )

        if not can_proceed and violation:
            # Additional enforcement actions could go here
            # e.g., sending alerts, blocking API calls, etc.
            await self._handle_quota_violation(violation)

        return can_proceed

    async def increment_usage(
        self,
        org_id: str,
        quota_type: QuotaType,
        amount: int = 1,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Increment usage for a quota type

        Args:
            org_id: Organization ID
            quota_type: Type of quota to increment
            amount: Amount to increment by
            metadata: Additional metadata to store

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.quota_usage_repo:
                logger.warning("Quota usage repository not available")
                return False

            now = datetime.utcnow()

            # Calculate period dates based on quota type
            period_start, period_end = self._calculate_period_dates(quota_type, now)

            # Prepare update document
            update_doc = {
                "$inc": {"current_usage": amount},
                "$set": {
                    "last_updated": now.isoformat(),
                    "service_name": self.service_name,
                },
                "$setOnInsert": {
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "created_at": now.isoformat(),
                },
            }

            # Add metadata if provided
            if metadata:
                update_doc["$set"]["metadata"] = metadata

            # Update usage record
            result = await self.quota_usage_repo.collection.update_one(
                {
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                },
                update_doc,
                upsert=True,
            )

            # Clear cache for this org
            cache_key = f"{org_id}:{quota_type.value}"
            if cache_key in self.quota_cache:
                del self.quota_cache[cache_key]

            logger.info(
                f"Incremented quota usage for {org_id}, {quota_type}: +{amount}",
                extra={
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "amount": amount,
                    "service": self.service_name,
                    "modified_count": result.modified_count,
                    "upserted_id": (
                        str(result.upserted_id) if result.upserted_id else None
                    ),
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error incrementing usage for {org_id}, {quota_type}: {e}")
            return False

    async def get_quota_status(
        self, org_id: str, quota_type: QuotaType
    ) -> Optional[QuotaStatus]:
        """Get current quota status for an organization and quota type"""
        return await self._get_quota_status(org_id, quota_type)

    async def get_all_quota_status(self, org_id: str) -> dict[str, QuotaStatus]:
        """Get quota status for all quota types for an organization"""
        status_dict = {}

        for quota_type in QuotaType:
            status = await self._get_quota_status(org_id, quota_type)
            if status:
                status_dict[quota_type.value] = status

        return status_dict

    async def _get_quota_status(
        self, org_id: str, quota_type: QuotaType
    ) -> Optional[QuotaStatus]:
        """Internal method to get quota status with caching"""
        try:
            cache_key = f"{org_id}:{quota_type.value}"
            now = datetime.utcnow()

            # Check cache first
            if (
                cache_key in self.quota_cache
                and cache_key in self.last_cache_update
                and (now - self.last_cache_update[cache_key]).seconds < self.cache_ttl
            ):
                cached_data = self.quota_cache[cache_key]
                return QuotaStatus(**cached_data)

            # Get quota limits
            limit = await self._get_quota_limit(org_id, quota_type)
            if limit is None:
                return None

            # Get current usage
            current_usage = await self._get_current_usage(org_id, quota_type)

            # Calculate period dates
            period_start, period_end = self._calculate_period_dates(quota_type, now)

            # Calculate status
            if limit == -1:  # Unlimited
                percentage_used = 0.0
                remaining = -1
                is_exceeded = False
            else:
                percentage_used = (current_usage / limit) * 100 if limit > 0 else 0
                remaining = max(0, limit - current_usage)
                is_exceeded = current_usage > limit

            status = QuotaStatus(
                org_id=org_id,
                quota_type=quota_type,
                current_usage=current_usage,
                limit=limit,
                percentage_used=percentage_used,
                remaining=remaining,
                is_exceeded=is_exceeded,
                period_start=period_start,
                period_end=period_end,
                last_updated=now,
            )

            # Cache the result
            self.quota_cache[cache_key] = {
                "org_id": org_id,
                "quota_type": quota_type,
                "current_usage": current_usage,
                "limit": limit,
                "percentage_used": percentage_used,
                "remaining": remaining,
                "is_exceeded": is_exceeded,
                "period_start": period_start,
                "period_end": period_end,
                "last_updated": now,
            }
            self.last_cache_update[cache_key] = now

            return status

        except Exception as e:
            logger.error(f"Error getting quota status for {org_id}, {quota_type}: {e}")
            return None

    async def _get_quota_limit(
        self, org_id: str, quota_type: QuotaType
    ) -> Optional[int]:
        """Get quota limit for an organization and quota type"""
        try:
            if not self.quota_limits_repo:
                # Fallback to default quotas
                return self.DEFAULT_QUOTAS.get("basic", {}).get(quota_type, 0)

            limit_doc = await self.quota_limits_repo.find_one(
                {"org_id": org_id, "quota_type": quota_type.value}
            )

            if limit_doc:
                return limit_doc.get("limit", 0)
            else:
                # Return default limit for basic tier
                return self.DEFAULT_QUOTAS.get("basic", {}).get(quota_type, 0)

        except Exception as e:
            logger.error(f"Error getting quota limit for {org_id}, {quota_type}: {e}")
            return None

    async def _get_current_usage(self, org_id: str, quota_type: QuotaType) -> int:
        """Get current usage for an organization and quota type"""
        try:
            if not self.quota_usage_repo:
                return 0

            now = datetime.utcnow()
            period_start, period_end = self._calculate_period_dates(quota_type, now)

            # For concurrent jobs, count active jobs
            if quota_type == QuotaType.CONCURRENT_JOBS:
                jobs_repo = BaseRepository("jobs")
                if jobs_repo:
                    active_jobs = await jobs_repo.count(
                        {
                            "org_id": org_id,
                            "status": {"$in": ["pending", "in_progress", "running"]},
                        }
                    )
                    return active_jobs
                return 0

            # Get usage record for the current period
            usage_doc = await self.quota_usage_repo.find_one(
                {
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "period_start": {"$lte": period_end.isoformat()},
                    "period_end": {"$gte": period_start.isoformat()},
                }
            )

            if usage_doc:
                return usage_doc.get("current_usage", 0)
            else:
                return 0

        except Exception as e:
            logger.error(f"Error getting current usage for {org_id}, {quota_type}: {e}")
            return 0

    def _calculate_period_dates(
        self, quota_type: QuotaType, now: datetime
    ) -> tuple[datetime, datetime]:
        """Calculate period start and end dates based on quota type"""
        if quota_type.value.endswith("_monthly"):
            # Monthly period - start of current month to end of current month
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(
                    year=period_start.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                period_end = period_start.replace(
                    month=period_start.month + 1, day=1
                ) - timedelta(days=1)
            period_end = period_end.replace(hour=23, minute=59, second=59)
        else:
            # Total/lifetime quotas - use a wide range
            period_start = datetime(2020, 1, 1)
            period_end = datetime(2030, 12, 31)

        return period_start, period_end

    async def _record_violation(self, violation: QuotaViolation) -> bool:
        """Record a quota violation"""
        try:
            if not self.violations_repo:
                return False

            violation_doc = {
                "org_id": violation.org_id,
                "quota_type": violation.quota_type.value,
                "current_usage": violation.current_usage,
                "limit": violation.limit,
                "exceeded_by": violation.exceeded_by,
                "timestamp": violation.timestamp.isoformat(),
                "service_name": violation.service_name,
                "created_at": datetime.utcnow().isoformat(),
            }

            await self.violations_repo.create(violation_doc)
            return True

        except Exception as e:
            logger.error(f"Error recording quota violation: {e}")
            return False

    async def _handle_quota_violation(self, violation: QuotaViolation):
        """Handle quota violation with appropriate actions"""
        try:
            # Log the violation
            logger.error(
                f"Quota violation handled for {violation.org_id}",
                extra={
                    "org_id": violation.org_id,
                    "quota_type": violation.quota_type.value,
                    "exceeded_by": violation.exceeded_by,
                    "service": violation.service_name,
                },
            )

            # Additional actions could include:
            # - Sending notifications
            # - Triggering alerts
            # - Updating billing systems
            # - Temporarily blocking operations

        except Exception as e:
            logger.error(f"Error handling quota violation: {e}")


# Global quota enforcer instances for common services
api_quota_enforcer = QuotaEnforcer("api")
worker_quota_enforcer = QuotaEnforcer("worker")
router_quota_enforcer = QuotaEnforcer("router")
ocr_quota_enforcer = QuotaEnforcer("ocr")
structure_quota_enforcer = QuotaEnforcer("structure")
tagger_quota_enforcer = QuotaEnforcer("tagger")
exporter_quota_enforcer = QuotaEnforcer("exporter")
validator_quota_enforcer = QuotaEnforcer("validator")
notifier_quota_enforcer = QuotaEnforcer("notifier")


def get_quota_enforcer(service_name: str) -> QuotaEnforcer:
    """Get quota enforcer instance for a service"""
    enforcers = {
        "api": api_quota_enforcer,
        "worker": worker_quota_enforcer,
        "router": router_quota_enforcer,
        "ocr": ocr_quota_enforcer,
        "structure": structure_quota_enforcer,
        "tagger": tagger_quota_enforcer,
        "exporter": exporter_quota_enforcer,
        "validator": validator_quota_enforcer,
        "notifier": notifier_quota_enforcer,
    }

    return enforcers.get(service_name, QuotaEnforcer(service_name))


# Convenience functions for common quota operations
async def check_storage_quota(
    org_id: str, file_size: int, service_name: str = "api"
) -> bool:
    """Quick check for storage quota"""
    enforcer = get_quota_enforcer(service_name)
    return await enforcer.enforce_quota(
        org_id, QuotaType.STORAGE_TOTAL, file_size=file_size
    )


async def check_processing_quota(org_id: str, service_name: str = "api") -> bool:
    """Quick check for processing quota"""
    enforcer = get_quota_enforcer(service_name)
    return await enforcer.enforce_quota(org_id, QuotaType.PROCESSING_MONTHLY, 1)


async def check_api_quota(org_id: str, service_name: str = "api") -> bool:
    """Quick check for API call quota"""
    enforcer = get_quota_enforcer(service_name)
    return await enforcer.enforce_quota(org_id, QuotaType.API_CALLS_MONTHLY, 1)


async def increment_storage_usage(
    org_id: str, file_size: int, service_name: str = "api"
) -> bool:
    """Increment storage usage"""
    enforcer = get_quota_enforcer(service_name)
    return await enforcer.increment_usage(org_id, QuotaType.STORAGE_TOTAL, file_size)


async def increment_processing_usage(org_id: str, service_name: str = "api") -> bool:
    """Increment processing usage"""
    enforcer = get_quota_enforcer(service_name)
    return await enforcer.increment_usage(org_id, QuotaType.PROCESSING_MONTHLY, 1)


async def increment_api_usage(org_id: str, service_name: str = "api") -> bool:
    """Increment API call usage"""
    enforcer = get_quota_enforcer(service_name)
    return await enforcer.increment_usage(org_id, QuotaType.API_CALLS_MONTHLY, 1)


# Export commonly used items
__all__ = [
    "QuotaType",
    "QuotaViolation",
    "QuotaStatus",
    "QuotaEnforcer",
    "get_quota_enforcer",
    "check_storage_quota",
    "check_processing_quota",
    "check_api_quota",
    "increment_storage_usage",
    "increment_processing_usage",
    "increment_api_usage",
]

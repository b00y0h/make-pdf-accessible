"""
Tenant quota management system
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

from services.shared.mongo.repository import BaseRepository

logger = Logger()


class QuotaType(str, Enum):
    """Types of quotas that can be enforced"""

    PROCESSING_MONTHLY = "processing_monthly"
    STORAGE_TOTAL = "storage_total"
    API_CALLS_MONTHLY = "api_calls_monthly"
    CONCURRENT_JOBS = "concurrent_jobs"


@dataclass
class QuotaLimit:
    """Quota limit definition"""

    quota_type: QuotaType
    limit: int  # Limit value (documents, bytes, calls, etc.)
    period: str = "monthly"  # monthly, daily, total
    name: str = ""
    description: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "QuotaLimit":
        return cls(**data)


@dataclass
class QuotaUsage:
    """Current quota usage"""

    org_id: str
    quota_type: QuotaType
    current_usage: int
    period_start: datetime
    period_end: datetime
    last_updated: datetime

    def to_dict(self) -> Dict:
        data = asdict(self)
        # Convert datetime objects to ISO strings for MongoDB
        for key in ["period_start", "period_end", "last_updated"]:
            if isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "QuotaUsage":
        # Convert ISO strings back to datetime objects
        for key in ["period_start", "period_end", "last_updated"]:
            if isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class QuotaService:
    """Service for managing tenant quotas"""

    def __init__(self):
        self.quota_limits_repo = BaseRepository("quota_limits")
        self.quota_usage_repo = BaseRepository("quota_usage")

        # Default quota limits for new tenants
        self.default_quotas = {
            QuotaType.PROCESSING_MONTHLY: QuotaLimit(
                quota_type=QuotaType.PROCESSING_MONTHLY,
                limit=100,  # 100 documents per month
                period="monthly",
                name="Monthly Document Processing",
                description="Maximum number of documents that can be processed per month",
            ),
            QuotaType.STORAGE_TOTAL: QuotaLimit(
                quota_type=QuotaType.STORAGE_TOTAL,
                limit=5 * 1024 * 1024 * 1024,  # 5GB
                period="total",
                name="Total Storage",
                description="Maximum total storage for all files",
            ),
            QuotaType.API_CALLS_MONTHLY: QuotaLimit(
                quota_type=QuotaType.API_CALLS_MONTHLY,
                limit=10000,  # 10k API calls per month
                period="monthly",
                name="Monthly API Calls",
                description="Maximum number of API calls per month",
            ),
            QuotaType.CONCURRENT_JOBS: QuotaLimit(
                quota_type=QuotaType.CONCURRENT_JOBS,
                limit=5,  # 5 concurrent jobs
                period="concurrent",
                name="Concurrent Jobs",
                description="Maximum number of concurrent processing jobs",
            ),
        }

    async def initialize_tenant_quotas(self, org_id: str) -> bool:
        """Initialize default quotas for a new tenant"""
        try:
            # Check if quotas already exist
            existing_limits = await self.quota_limits_repo.find({"org_id": org_id})

            if existing_limits:
                logger.info(f"Quotas already exist for tenant {org_id}")
                return True

            # Create default quota limits
            for quota_type, limit in self.default_quotas.items():
                limit_doc = limit.to_dict()
                limit_doc["org_id"] = org_id
                limit_doc["created_at"] = datetime.utcnow().isoformat()

                await self.quota_limits_repo.create(limit_doc)

            logger.info(f"Initialized default quotas for tenant {org_id}")
            return True

        except Exception as e:
            logger.error(f"Error initializing quotas for tenant {org_id}: {e}")
            return False

    async def get_quota_limits(self, org_id: str) -> Dict[QuotaType, QuotaLimit]:
        """Get all quota limits for a tenant"""
        try:
            limits_docs = await self.quota_limits_repo.find({"org_id": org_id})

            limits = {}
            for doc in limits_docs:
                quota_type = QuotaType(doc["quota_type"])
                limits[quota_type] = QuotaLimit.from_dict(doc)

            # If no limits exist, initialize with defaults
            if not limits:
                await self.initialize_tenant_quotas(org_id)
                return self.default_quotas.copy()

            return limits

        except Exception as e:
            logger.error(f"Error getting quota limits for {org_id}: {e}")
            return {}

    async def get_current_usage(self, org_id: str, quota_type: QuotaType) -> int:
        """Get current usage for a specific quota type"""
        try:
            now = datetime.utcnow()

            # Calculate period start based on quota type
            if quota_type.value.endswith("_monthly"):
                period_start = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            elif quota_type == QuotaType.CONCURRENT_JOBS:
                # For concurrent jobs, count current active jobs
                jobs_repo = BaseRepository("jobs")
                active_jobs = await jobs_repo.count(
                    {"org_id": org_id, "status": {"$in": ["pending", "in_progress"]}}
                )
                return active_jobs
            else:
                # For total quotas, use all-time usage
                period_start = datetime(2020, 1, 1)  # Beginning of time

            period_end = now

            # Get or create usage record
            usage_doc = await self.quota_usage_repo.find_one(
                {
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "period_start": {"$lte": period_start.isoformat()},
                    "period_end": {"$gte": period_end.isoformat()},
                }
            )

            if usage_doc:
                usage = QuotaUsage.from_dict(usage_doc)
                return usage.current_usage
            else:
                # Create new usage record
                usage = QuotaUsage(
                    org_id=org_id,
                    quota_type=quota_type,
                    current_usage=0,
                    period_start=period_start,
                    period_end=period_end,
                    last_updated=now,
                )
                await self.quota_usage_repo.create(usage.to_dict())
                return 0

        except Exception as e:
            logger.error(f"Error getting current usage for {org_id}, {quota_type}: {e}")
            return 0

    async def check_quota_limit(
        self, org_id: str, quota_type: QuotaType, additional_usage: int = 1
    ) -> bool:
        """Check if adding usage would exceed quota limit"""
        try:
            limits = await self.get_quota_limits(org_id)
            current_usage = await self.get_current_usage(org_id, quota_type)

            if quota_type not in limits:
                logger.warning(f"No quota limit found for {org_id}, {quota_type}")
                return True  # Allow if no limit set

            limit = limits[quota_type].limit
            would_exceed = (current_usage + additional_usage) > limit

            if would_exceed:
                logger.warning(
                    f"Quota would be exceeded for {org_id}, {quota_type}: "
                    f"{current_usage + additional_usage} > {limit}"
                )

            return not would_exceed

        except Exception as e:
            logger.error(f"Error checking quota limit for {org_id}, {quota_type}: {e}")
            return True  # Allow on error to avoid blocking operations

    async def increment_usage(
        self, org_id: str, quota_type: QuotaType, amount: int = 1
    ) -> bool:
        """Increment usage for a quota type"""
        try:
            now = datetime.utcnow()

            # Calculate period dates
            if quota_type.value.endswith("_monthly"):
                period_start = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                next_month = period_start.replace(month=period_start.month % 12 + 1)
                period_end = next_month - timedelta(days=1)
            else:
                period_start = datetime(2020, 1, 1)
                period_end = datetime(2030, 12, 31)

            # Update or create usage record
            result = await self.quota_usage_repo.collection.update_one(
                {
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                },
                {
                    "$inc": {"current_usage": amount},
                    "$set": {"last_updated": now.isoformat()},
                    "$setOnInsert": {
                        "org_id": org_id,
                        "quota_type": quota_type.value,
                        "period_start": period_start.isoformat(),
                        "period_end": period_end.isoformat(),
                    },
                },
                upsert=True,
            )

            logger.info(
                f"Incremented quota usage for {org_id}, {quota_type}: +{amount}",
                extra={
                    "org_id": org_id,
                    "quota_type": quota_type.value,
                    "amount": amount,
                    "modified_count": result.modified_count,
                    "upserted_id": result.upserted_id,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error incrementing usage for {org_id}, {quota_type}: {e}")
            return False

    async def get_quota_status(self, org_id: str) -> Dict[str, Dict]:
        """Get comprehensive quota status for a tenant"""
        try:
            limits = await self.get_quota_limits(org_id)
            status = {}

            for quota_type, limit in limits.items():
                current_usage = await self.get_current_usage(org_id, quota_type)
                percentage_used = (
                    (current_usage / limit.limit) * 100 if limit.limit > 0 else 0
                )

                status[quota_type.value] = {
                    "name": limit.name,
                    "description": limit.description,
                    "limit": limit.limit,
                    "current_usage": current_usage,
                    "remaining": max(0, limit.limit - current_usage),
                    "percentage_used": round(percentage_used, 2),
                    "period": limit.period,
                    "is_exceeded": current_usage > limit.limit,
                }

            return status

        except Exception as e:
            logger.error(f"Error getting quota status for {org_id}: {e}")
            return {}

    async def enforce_quota(
        self, org_id: str, quota_type: QuotaType, additional_usage: int = 1
    ):
        """Enforce quota check and raise HTTPException if exceeded"""
        can_proceed = await self.check_quota_limit(org_id, quota_type, additional_usage)

        if not can_proceed:
            limits = await self.get_quota_limits(org_id)
            current_usage = await self.get_current_usage(org_id, quota_type)

            if quota_type in limits:
                limit_info = limits[quota_type]
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Quota exceeded for {limit_info.name}. "
                    f"Current usage: {current_usage}/{limit_info.limit}. "
                    f"Please upgrade your plan or wait for quota reset.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Quota exceeded for {quota_type.value}",
                )


# Global quota service instance
quota_service = QuotaService()

"""
Quota management API routes
"""
from typing import Dict, Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import User, get_current_user, require_roles
from ..models import UserRole
from ..quota import quota_service, QuotaType

logger = Logger()
tracer = Tracer()
metrics = Metrics()

router = APIRouter(prefix="/quotas", tags=["quotas"])


@router.get(
    "/status",
    summary="Get quota status",
    description="Get current quota usage and limits for the authenticated user's organization."
)
@tracer.capture_method
async def get_quota_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get quota status for current user's organization"""
    
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )
    
    try:
        quota_status = await quota_service.get_quota_status(current_user.org_id)
        
        metrics.add_metric(name="QuotaStatusRequests", unit="Count", value=1)
        
        logger.info(
            "Quota status retrieved",
            extra={
                "org_id": current_user.org_id,
                "user_id": current_user.sub
            }
        )
        
        return {
            "org_id": current_user.org_id,
            "quotas": quota_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get quota status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota status"
        )


@router.post(
    "/initialize/{org_id}",
    summary="Initialize quotas for organization",
    description="Initialize default quotas for an organization (admin only)."
)
@tracer.capture_method
async def initialize_org_quotas(
    org_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
) -> Dict[str, Any]:
    """Initialize quotas for an organization (admin only)"""
    
    try:
        success = await quota_service.initialize_tenant_quotas(org_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize quotas"
            )
        
        quota_status = await quota_service.get_quota_status(org_id)
        
        metrics.add_metric(name="QuotaInitializations", unit="Count", value=1)
        
        logger.info(
            "Quotas initialized for organization",
            extra={
                "org_id": org_id,
                "admin_user": current_user.sub
            }
        )
        
        return {
            "message": f"Quotas initialized for organization {org_id}",
            "org_id": org_id,
            "quotas": quota_status
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize quotas for {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize quotas"
        )


@router.get(
    "/admin/{org_id}",
    summary="Get quota status for any organization",
    description="Get quota status for any organization (admin only)."
)
@tracer.capture_method
async def get_org_quota_status(
    org_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
) -> Dict[str, Any]:
    """Get quota status for any organization (admin only)"""
    
    try:
        quota_status = await quota_service.get_quota_status(org_id)
        
        metrics.add_metric(name="AdminQuotaRequests", unit="Count", value=1)
        
        logger.info(
            "Admin quota status retrieved",
            extra={
                "target_org_id": org_id,
                "admin_user": current_user.sub
            }
        )
        
        return {
            "org_id": org_id,
            "quotas": quota_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get quota status for {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota status"
        )


@router.get(
    "/health",
    summary="Check quota service health",
    description="Health check endpoint for quota service."
)
async def quota_health() -> Dict[str, str]:
    """Health check for quota service"""
    return {"status": "healthy", "service": "quota_service"}
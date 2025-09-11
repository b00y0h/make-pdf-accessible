import os
import sys
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, status

# Add shared services to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../shared"))

from auth import UserInfo, get_admin_user, get_current_user, require_admin
from quota_enforcement import (
    QuotaType,
    check_processing_quota,
    increment_processing_usage,
    validator_quota_enforcer,
)
from timeout_enforcement import check_timeouts, get_timeout_stats

app = FastAPI(
    title="PDF Validator Service",
    description="Microservice for PDF validation functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF validator service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/validate")
async def validate_document(
    document_data: Dict[str, Any], current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate a PDF document
    Requires authentication and respects processing quotas
    """
    # Check processing quota before starting validation
    if current_user.org_id:
        can_proceed = await check_processing_quota(current_user.org_id, "validator")
        if not can_proceed:
            # Get quota status for detailed error
            if validator_quota_enforcer:
                status_info = await validator_quota_enforcer.get_quota_status(
                    current_user.org_id, QuotaType.PROCESSING_MONTHLY
                )
                if status_info:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Monthly processing quota exceeded ({status_info.current_usage}/{status_info.limit}). Please upgrade your plan or wait for quota reset.",
                    )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Processing quota exceeded. Please try again later.",
            )

    # Perform validation logic here
    # This is where actual PDF validation would occur
    doc_id = document_data.get("doc_id")

    # Simulate validation processing
    validation_result = {
        "message": "Document validation initiated",
        "user_id": current_user.sub,
        "user_role": current_user.role,
        "org_id": current_user.org_id,
        "document_id": doc_id,
        "validation_status": "in_progress",
        "estimated_completion": "2-5 minutes",
    }

    # Record quota usage after successful validation start
    if current_user.org_id:
        await increment_processing_usage(current_user.org_id, "validator")

    return validation_result


@app.get("/validate/{doc_id}/status")
def get_validation_status(
    doc_id: str, current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get validation status for a document
    Requires authentication
    """
    return {
        "doc_id": doc_id,
        "status": "completed",
        "validation_result": "passed",
        "user_id": current_user.sub,
    }


@app.get("/validate/{doc_id}/report")
def get_validation_report(
    doc_id: str, current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed validation report for a document
    Requires authentication - user can only access their own documents unless admin
    """
    # In a real implementation, you'd check document ownership here
    # For now, we'll just return the report
    return {
        "doc_id": doc_id,
        "validation_report": {
            "file_format": "valid_pdf",
            "accessibility_score": 95,
            "issues_found": 2,
            "recommendations": ["Add alt text to images", "Improve heading structure"],
        },
        "requested_by": current_user.sub,
        "user_role": current_user.role,
    }


@app.delete("/validate/{doc_id}")
def delete_validation_data(
    doc_id: str, current_user: UserInfo = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Delete validation data for a document
    Requires admin role
    """
    return {
        "message": f"Validation data for document {doc_id} has been deleted",
        "deleted_by": current_user.sub,
        "admin_action": True,
    }


@app.get("/quota/status")
async def get_quota_status(
    current_user: UserInfo = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get quota status for the current user's organization
    """
    if not current_user.org_id:
        return {
            "available": False,
            "reason": "User not associated with an organization",
        }

    if validator_quota_enforcer:
        all_status = await validator_quota_enforcer.get_all_quota_status(
            current_user.org_id
        )
        return {
            "available": True,
            "org_id": current_user.org_id,
            "quotas": {
                quota_type: {
                    "current_usage": status.current_usage,
                    "limit": status.limit,
                    "remaining": status.remaining,
                    "percentage_used": status.percentage_used,
                    "is_exceeded": status.is_exceeded,
                }
                for quota_type, status in all_status.items()
            },
        }
    else:
        return {"available": False, "reason": "Quota enforcement not available"}


@app.get("/timeout/check")
async def check_job_timeouts(
    current_user: UserInfo = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Check for job timeouts and return timeout events
    Admin only endpoint
    """
    try:
        timeout_events = await check_timeouts()

        return {
            "timeout_events_found": len(timeout_events),
            "events": [
                {
                    "job_id": event.job_id,
                    "timeout_reason": event.timeout_reason.value,
                    "execution_duration": event.execution_duration,
                    "step": event.step,
                    "doc_id": event.doc_id,
                    "timeout_at": event.timeout_at.isoformat(),
                    "retry_count": event.retry_count,
                }
                for event in timeout_events
            ],
            "checked_by": current_user.sub,
        }

    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/timeout/stats")
async def get_timeout_statistics(
    days: int = 7, current_user: UserInfo = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get timeout statistics for the specified period
    Admin only endpoint
    """
    try:
        stats = await get_timeout_stats(days)
        stats["requested_by"] = current_user.sub
        return stats

    except Exception as e:
        return {"available": False, "error": str(e), "requested_by": current_user.sub}


@app.get("/admin/stats")
async def get_validation_stats(
    current_user: UserInfo = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get validation statistics
    Admin only endpoint
    """
    stats = {
        "total_validations": 1250,
        "validations_today": 47,
        "average_score": 87.3,
        "admin_user": current_user.sub,
    }

    # Add quota overview for admin
    if validator_quota_enforcer:
        # Get quota statistics across all organizations
        # This would require additional implementation in the quota system
        stats["quota_overview"] = {
            "organizations_monitored": "Available in quota system",
            "quota_violations_today": "Available in quota system",
            "average_quota_usage": "Available in quota system",
        }

    # Add timeout statistics
    try:
        timeout_stats = await get_timeout_stats(1)  # Last 24 hours
        stats["timeout_overview"] = {
            "total_timeouts_24h": timeout_stats.get("total_timeouts", 0),
            "timeout_rate_24h": timeout_stats.get("timeout_rate", 0),
            "monitoring_active": timeout_stats.get("monitoring_active", False),
        }
    except Exception as e:
        stats["timeout_overview"] = {"error": f"Failed to get timeout stats: {str(e)}"}

    return stats

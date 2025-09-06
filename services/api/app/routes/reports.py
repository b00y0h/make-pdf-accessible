from fastapi import APIRouter, Depends, HTTPException, status
from aws_lambda_powertools import Logger, Metrics, Tracer

from ..auth import User, require_roles
from ..models import ReportsSummaryResponse, UserRole
from ..services import AWSServiceError, reports_service


logger = Logger()
tracer = Tracer()
metrics = Metrics()

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/summary",
    response_model=ReportsSummaryResponse,
    summary="Get reports summary",
    description="Get summary statistics including document counts, averages by week, and success rates (admin only)."
)
@tracer.capture_method
async def get_summary_report(
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
) -> ReportsSummaryResponse:
    """Get summary report with statistics"""
    
    try:
        report = await reports_service.get_summary_report()
        
        metrics.add_metric(name="ReportRequests", unit="Count", value=1)
        
        logger.info(
            "Summary report generated",
            extra={
                "admin_user": current_user.sub,
                "total_documents": report.total_documents,
                "success_rate": report.success_rate
            }
        )
        
        return report
        
    except AWSServiceError as e:
        logger.error(f"Failed to generate summary report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary report"
        )


@router.get(
    "/health",
    summary="Reports health check",
    description="Health check for reports service."
)
async def reports_health() -> dict:
    """Reports service health check"""
    return {
        "status": "healthy",
        "service": "reports",
        "features": ["summary", "analytics"]
    }
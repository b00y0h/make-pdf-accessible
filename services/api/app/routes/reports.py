import csv
import io
from datetime import datetime
from typing import Optional

from aws_lambda_powertools import Logger, Metrics, Tracer
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

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
    description="Get summary statistics including document counts, averages by week, and success rates (admin only).",
)
@tracer.capture_method
async def get_summary_report(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
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
                "success_rate": report.success_rate,
            },
        )

        return report

    except AWSServiceError as e:
        logger.error(f"Failed to generate summary report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary report",
        )


@router.get(
    "/export.csv",
    summary="Export documents to CSV",
    description="Stream CSV export of documents with filtering support (admin only).",
)
@tracer.capture_method
async def export_documents_csv(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    start_date: Optional[datetime] = Query(
        None, description="Start date filter (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date filter (ISO format)"
    ),
    owner_filter: Optional[str] = Query(None, description="Filter by owner ID"),
    status_filter: Optional[str] = Query(None, description="Filter by document status"),
) -> StreamingResponse:
    """Export documents as CSV with streaming response"""

    try:
        # Get CSV data from service
        csv_data = await reports_service.export_documents_csv(
            start_date=start_date,
            end_date=end_date,
            owner_filter=owner_filter,
            status_filter=status_filter,
        )

        # Generate CSV in memory
        output = io.StringIO()

        if csv_data:
            writer = csv.DictWriter(output, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        else:
            # Write headers even for empty data
            headers = [
                "Document ID",
                "Filename",
                "Owner ID",
                "Status",
                "Created At",
                "Updated At",
                "Completed At",
                "File Size (bytes)",
                "Content Type",
                "Source",
                "Error Message",
                "Accessibility Score",
                "WCAG Level",
                "Total Issues",
                "Processing Time (seconds)",
                "AI Cost (USD)",
                "Priority",
            ]
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()

        csv_content = output.getvalue()
        output.close()

        # Generate filename with timestamp and filters
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename_parts = [f"documents_export_{timestamp}"]

        if start_date:
            filename_parts.append(f"from_{start_date.strftime('%Y%m%d')}")
        if end_date:
            filename_parts.append(f"to_{end_date.strftime('%Y%m%d')}")
        if status_filter:
            filename_parts.append(f"status_{status_filter}")
        if owner_filter:
            filename_parts.append(f"owner_{owner_filter[:8]}")

        filename = "_".join(filename_parts) + ".csv"

        # Log export activity
        metrics.add_metric(name="CSVExports", unit="Count", value=1)
        logger.info(
            "CSV export generated",
            extra={
                "admin_user": current_user.sub,
                "record_count": len(csv_data),
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "owner_filter": owner_filter,
                    "status_filter": status_filter,
                },
                "filename": filename,
            },
        )

        # Create streaming response with proper headers for Excel/Sheets compatibility
        def iter_csv():
            yield csv_content.encode(
                "utf-8-sig"
            )  # UTF-8 with BOM for Excel compatibility

        return StreamingResponse(
            iter_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    except AWSServiceError as e:
        logger.error(f"Failed to export CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export CSV",
        )


@router.get(
    "/health",
    summary="Reports health check",
    description="Health check for reports service.",
)
async def reports_health() -> dict:
    """Reports service health check"""
    return {
        "status": "healthy",
        "service": "reports",
        "features": ["summary", "export", "analytics"],
    }

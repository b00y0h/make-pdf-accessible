"""
Reports service: summary statistics and CSV export over the MongoDB documents
collection
"""

import logging
from datetime import datetime
from typing import Any, Optional

from services.shared.mongo.documents import get_document_repository

from ..models import ReportsSummaryResponse
from .errors import AWSServiceError

logger = logging.getLogger(__name__)


def _isoformat(value: Any) -> str:
    """Format a stored timestamp for CSV output"""
    if isinstance(value, datetime):
        return value.isoformat()
    return value or ""


class ReportsService:
    """Service for generating reports and analytics"""

    async def get_summary_report(self) -> ReportsSummaryResponse:
        """Generate summary report with MongoDB aggregations"""
        try:
            doc_repo = get_document_repository()
            summary = doc_repo.get_processing_summary()
            weekly_stats = doc_repo.get_weekly_stats(weeks=4)

            formatted_weekly_stats = [
                {
                    "week": week_data["week"],
                    "total_documents": week_data["documents"],
                    "completed_documents": week_data["completed"],
                    "failed_documents": week_data["failed"],
                    "success_rate": week_data["success_rate"] * 100,
                }
                for week_data in weekly_stats
            ]

            return ReportsSummaryResponse(
                total_documents=summary.get("total_documents", 0),
                completed_documents=summary.get("completed_documents", 0),
                processing_documents=summary.get("processing_documents", 0),
                failed_documents=summary.get("failed_documents", 0),
                pending_documents=summary.get("pending_documents", 0),
                completion_rate=summary.get("completion_rate", 0) * 100,
                avg_processing_time_hours=summary.get("avg_processing_time_hours", 0),
                weekly_stats=formatted_weekly_stats,
            )

        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            raise AWSServiceError(f"Failed to generate report: {e}") from e

    async def export_documents_csv(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        owner_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """Export documents as CSV rows with filtering"""
        try:
            pipeline = []

            match_stage: dict[str, Any] = {}
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                match_stage["createdAt"] = date_filter

            if owner_filter:
                match_stage["ownerId"] = owner_filter

            if status_filter:
                match_stage["status"] = status_filter

            if match_stage:
                pipeline.append({"$match": match_stage})

            pipeline.append(
                {
                    "$project": {
                        "docId": 1,
                        "filename": 1,
                        "ownerId": 1,
                        "status": 1,
                        "createdAt": 1,
                        "updatedAt": 1,
                        "completedAt": 1,
                        "fileSize": 1,
                        "contentType": 1,
                        "source": 1,
                        "errorMessage": 1,
                        "accessibilityScore": {
                            "$ifNull": ["$scores.accessibility", None]
                        },
                        "wcagLevel": {"$ifNull": ["$scores.wcagLevel", None]},
                        "totalIssues": {"$size": {"$ifNull": ["$issues", []]}},
                        "processingTimeSeconds": {
                            "$ifNull": ["$ai.totalProcessingTimeSeconds", None]
                        },
                        "aiCostUsd": {"$ifNull": ["$ai.totalCostUSD", None]},
                        "priority": {"$ifNull": ["$metadata.priority", False]},
                    }
                }
            )

            # Newest first
            pipeline.append({"$sort": {"createdAt": -1}})

            results = get_document_repository().aggregate(pipeline)

            csv_data = [
                {
                    "Document ID": doc.get("docId", ""),
                    "Filename": doc.get("filename", ""),
                    "Owner ID": doc.get("ownerId", ""),
                    "Status": doc.get("status", ""),
                    "Created At": _isoformat(doc.get("createdAt")),
                    "Updated At": _isoformat(doc.get("updatedAt")),
                    "Completed At": _isoformat(doc.get("completedAt")),
                    "File Size (bytes)": doc.get("fileSize", ""),
                    "Content Type": doc.get("contentType", ""),
                    "Source": doc.get("source", ""),
                    "Error Message": doc.get("errorMessage", ""),
                    "Accessibility Score": doc.get("accessibilityScore", ""),
                    "WCAG Level": doc.get("wcagLevel", ""),
                    "Total Issues": doc.get("totalIssues", 0),
                    "Processing Time (seconds)": doc.get("processingTimeSeconds", ""),
                    "AI Cost (USD)": doc.get("aiCostUsd", ""),
                    "Priority": doc.get("priority", False),
                }
                for doc in results
            ]

            logger.info(f"Exported {len(csv_data)} documents to CSV")
            return csv_data

        except Exception as e:
            logger.error(f"Failed to export documents to CSV: {e}")
            raise AWSServiceError(f"Failed to export CSV: {e}") from e


reports_service = ReportsService()

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from botocore.exceptions import ClientError

from services.shared.mongo.alt_text import get_alt_text_repository
from services.shared.persistence import get_persistence_manager

from .config import settings
from .models import (
    AltTextDocumentResponse,
    AltTextEditResponse,
    AltTextFigure,
    AltTextHistoryResponse,
    AltTextStatus,
    AltTextVersion,
    DocumentResponse,
    DocumentStatus,
    DocumentType,
    PreSignedUploadResponse,
    ReportsSummaryResponse,
)

logger = Logger()
tracer = Tracer()
metrics = Metrics()


class AWSServiceError(Exception):
    """Base exception for AWS service errors"""

    pass


class DocumentService:
    """Service for document operations with MongoDB/DynamoDB and S3"""

    def __init__(self):
        self.persistence_manager = get_persistence_manager()
        self.s3_client = boto3.client("s3", region_name=settings.aws_region)
        self.sqs_client = boto3.client("sqs", region_name=settings.aws_region)

    @tracer.capture_method
    async def create_document(
        self,
        user_id: str,
        filename: Optional[str] = None,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: bool = False,
        webhook_url: Optional[str] = None,
    ) -> DocumentResponse:
        """Create a new document record"""
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow()

        document_data = {
            "docId": doc_id,
            "ownerId": user_id,  # Use ownerId for MongoDB schema compatibility
            "status": DocumentStatus.PENDING.value,
            "createdAt": now,
            "updatedAt": now,
            "metadata": metadata or {},
            "artifacts": {},
        }

        if filename:
            document_data["filename"] = filename
        if source_url:
            document_data["sourceUrl"] = source_url
        if webhook_url:
            document_data["webhookUrl"] = webhook_url

        try:
            # Store document record using persistence layer
            created_document = self.persistence_manager.create_document(document_data)

            # Create job record
            job_data = {
                "jobId": str(uuid.uuid4()),
                "docId": doc_id,
                "ownerId": user_id,  # Use ownerId for consistency
                "step": "structure",  # Initial step
                "status": "pending",
                "priority": priority,
                "createdAt": now,
                "updatedAt": now,
                "queuedAt": now,
            }

            self.persistence_manager.create_job(job_data)

            # Send to appropriate queue
            queue_url = (
                settings.priority_process_queue_url
                if priority
                else settings.ingest_queue_url
            )

            message_body = {
                "docId": doc_id,
                "userId": user_id,
                "filename": filename,
                "sourceUrl": source_url,
                "priority": priority,
                "webhookUrl": webhook_url,
                "metadata": metadata or {},
            }

            self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    "docId": {"StringValue": doc_id, "DataType": "String"},
                    "priority": {"StringValue": str(priority), "DataType": "String"},
                },
            )

            metrics.add_metric(name="DocumentsCreated", unit="Count", value=1)
            logger.info(f"Created document {doc_id} for user {user_id}")

            return DocumentResponse(
                doc_id=uuid.UUID(doc_id),
                status=DocumentStatus.PENDING,
                filename=filename,
                created_at=now,
                updated_at=now,
                user_id=user_id,
                metadata=metadata or {},
                artifacts={},
            )

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise AWSServiceError(f"Failed to create document: {e}")

    @tracer.capture_method
    async def get_document(
        self, doc_id: str, user_id: Optional[str] = None
    ) -> Optional[DocumentResponse]:
        """Get document by ID"""
        try:
            document = self.persistence_manager.document_repository.get_document(doc_id)

            if not document:
                return None

            # Check access permissions - handle both userId (DynamoDB) and ownerId (MongoDB)
            document_owner = document.get("ownerId") or document.get("userId")
            if user_id and document_owner != user_id:
                return None

            # Handle both datetime objects and ISO strings for compatibility
            created_at = document["createdAt"]
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            updated_at = document["updatedAt"]
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)

            completed_at = document.get("completedAt")
            if completed_at and isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)

            return DocumentResponse(
                doc_id=uuid.UUID(document["docId"]),
                status=DocumentStatus(document["status"]),
                filename=document.get("filename"),
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at,
                user_id=document_owner,  # Use the appropriate field
                metadata=document.get("metadata", {}),
                error_message=document.get("errorMessage"),
                artifacts=document.get("artifacts", {}),
            )

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            raise AWSServiceError(f"Failed to get document: {e}")

    @tracer.capture_method
    async def generate_presigned_upload_url(
        self, user_id: str, filename: str, content_type: str, file_size: int
    ) -> PreSignedUploadResponse:
        """Generate a pre-signed S3 upload URL for direct client upload"""

        # Generate document ID and S3 key
        doc_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = quote(filename, safe=".-_")
        s3_key = f"uploads/{user_id}/{timestamp}_{doc_id}_{safe_filename}"

        try:
            # Generate pre-signed POST for S3 upload
            bucket_name = settings.get_bucket_name("originals")

            # Set up conditions for the upload
            conditions = [
                ["content-length-range", 1, settings.max_file_size],
                {"bucket": bucket_name},
                {"key": s3_key},
                {"Content-Type": content_type},
                {"x-amz-meta-user-id": user_id},
                {"x-amz-meta-doc-id": doc_id},
                {"x-amz-meta-original-filename": filename},
            ]

            # Generate pre-signed POST
            post_data = self.s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key=s3_key,
                Fields={
                    "Content-Type": content_type,
                    "x-amz-meta-user-id": user_id,
                    "x-amz-meta-doc-id": doc_id,
                    "x-amz-meta-original-filename": filename,
                },
                Conditions=conditions,
                ExpiresIn=settings.presigned_url_expiration,
            )

            expires_at = datetime.utcnow() + timedelta(
                seconds=settings.presigned_url_expiration
            )

            logger.info(
                f"Generated pre-signed upload URL for document {doc_id}",
                extra={
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "s3_key": s3_key,
                    "file_size": file_size,
                },
            )

            return PreSignedUploadResponse(
                upload_url=post_data["url"],
                fields=post_data["fields"],
                expires_at=expires_at,
                s3_key=s3_key,
                doc_id=uuid.UUID(doc_id),
            )

        except ClientError as e:
            logger.error(f"Failed to generate pre-signed upload URL: {e}")
            raise AWSServiceError(f"Failed to generate upload URL: {e}")

    @tracer.capture_method
    async def create_document_from_s3(
        self,
        doc_id: str,
        user_id: str,
        s3_key: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: bool = False,
        webhook_url: Optional[str] = None,
    ) -> DocumentResponse:
        """Create document record after successful S3 upload and enqueue for processing"""

        try:
            # Verify the file exists in S3
            bucket_name = settings.get_bucket_name("originals")

            try:
                response = self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                file_size = response.get("ContentLength", 0)
                content_type = response.get("ContentType", "application/octet-stream")

                # Extract filename from metadata or S3 key
                filename = response.get("Metadata", {}).get("original-filename")
                if not filename:
                    filename = s3_key.split("/")[-1]
                    # Remove timestamp and doc_id prefix if present
                    parts = filename.split("_")
                    if len(parts) >= 3:
                        filename = "_".join(parts[2:])

            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    logger.error(f"S3 object not found: {s3_key}")
                    raise AWSServiceError("Uploaded file not found in S3")
                raise

            now = datetime.utcnow()

            document_data = {
                "docId": doc_id,
                "ownerId": user_id,
                "status": DocumentStatus.PENDING.value,
                "filename": filename,
                "s3Key": s3_key,
                "source": source,
                "fileSize": file_size,
                "contentType": content_type,
                "createdAt": now,
                "updatedAt": now,
                "metadata": metadata or {},
                "artifacts": {},
            }

            if webhook_url:
                document_data["webhookUrl"] = webhook_url

            # Store document record using persistence layer
            created_document = self.persistence_manager.create_document(document_data)

            # Create job record
            job_data = {
                "jobId": str(uuid.uuid4()),
                "docId": doc_id,
                "ownerId": user_id,
                "step": "router",  # Start with router step
                "status": "pending",
                "priority": priority,
                "createdAt": now,
                "updatedAt": now,
                "queuedAt": now,
            }

            self.persistence_manager.create_job(job_data)

            # Send to appropriate queue
            queue_url = (
                settings.priority_process_queue_url
                if priority
                else settings.ingest_queue_url
            )

            message_body = {
                "docId": doc_id,
                "userId": user_id,
                "filename": filename,
                "s3Key": s3_key,
                "source": source,
                "priority": priority,
                "webhookUrl": webhook_url,
                "metadata": metadata or {},
            }

            self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    "docId": {"StringValue": doc_id, "DataType": "String"},
                    "priority": {"StringValue": str(priority), "DataType": "String"},
                    "source": {"StringValue": source, "DataType": "String"},
                },
            )

            metrics.add_metric(name="DocumentsFromS3", unit="Count", value=1)
            logger.info(f"Created document {doc_id} from S3 upload for user {user_id}")

            return DocumentResponse(
                doc_id=uuid.UUID(doc_id),
                status=DocumentStatus.PENDING,
                filename=filename,
                created_at=now,
                updated_at=now,
                user_id=user_id,
                metadata=metadata or {},
                artifacts={},
            )

        except Exception as e:
            logger.error(f"Failed to create document from S3: {e}")
            raise AWSServiceError(f"Failed to create document from S3: {e}")

    @tracer.capture_method
    async def list_user_documents(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        status_filter: Optional[DocumentStatus] = None,
    ) -> Tuple[List[DocumentResponse], int]:
        """List documents for a user with pagination"""
        try:
            # Prepare status filter for persistence layer
            status_list = [status_filter.value] if status_filter else None

            # Use the persistence layer's document repository
            result = (
                self.persistence_manager.document_repository.get_documents_by_owner(
                    owner_id=user_id,
                    status_filter=status_list,
                    page=(offset // limit) + 1,  # Convert offset to page number
                    limit=limit,
                )
            )

            documents = []
            for item in result["documents"]:
                # Handle both datetime objects and ISO strings for compatibility
                created_at = item["createdAt"]
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)

                updated_at = item["updatedAt"]
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at)

                completed_at = item.get("completedAt")
                if completed_at and isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at)

                # Handle both userId (DynamoDB) and ownerId (MongoDB) fields
                document_owner = item.get("ownerId") or item.get("userId")

                documents.append(
                    DocumentResponse(
                        doc_id=uuid.UUID(item["docId"]),
                        status=DocumentStatus(item["status"]),
                        filename=item.get("filename"),
                        created_at=created_at,
                        updated_at=updated_at,
                        completed_at=completed_at,
                        user_id=document_owner,
                        metadata=item.get("metadata", {}),
                        error_message=item.get("errorMessage"),
                        artifacts=item.get("artifacts", {}),
                    )
                )

            return documents, result["total"]

        except Exception as e:
            logger.error(f"Failed to list documents for user {user_id}: {e}")
            raise AWSServiceError(f"Failed to list documents: {e}")

    @tracer.capture_method
    async def generate_presigned_url(
        self, doc_id: str, document_type: DocumentType, expires_in: int = 3600
    ) -> Tuple[str, str, str]:
        """Generate pre-signed URL for document download"""
        try:
            # Determine bucket and key based on document type
            if document_type == DocumentType.PDF:
                bucket = settings.get_bucket_name("derivatives")
                key = f"processed/{doc_id}/{doc_id}.pdf"
                content_type = "application/pdf"
                filename = f"{doc_id}.pdf"
            elif document_type == DocumentType.HTML:
                bucket = settings.get_bucket_name("derivatives")
                key = f"processed/{doc_id}/{doc_id}.html"
                content_type = "text/html"
                filename = f"{doc_id}.html"
            elif document_type == DocumentType.JSON:
                bucket = settings.get_bucket_name("reports")
                key = f"reports/{doc_id}/accessibility_report.json"
                content_type = "application/json"
                filename = f"{doc_id}_report.json"
            elif document_type == DocumentType.CSV_ZIP:
                bucket = settings.get_bucket_name("reports")
                key = f"reports/{doc_id}/data_export.zip"
                content_type = "application/zip"
                filename = f"{doc_id}_data.zip"
            else:
                raise AWSServiceError(f"Unsupported document type: {document_type}")

            # Check if file exists
            try:
                self.s3_client.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise AWSServiceError(
                        f"Document {document_type.value} not available"
                    )
                raise

            # Generate pre-signed URL
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentDisposition": f'attachment; filename="{quote(filename)}"',
                },
                ExpiresIn=expires_in,
            )

            return presigned_url, content_type, filename

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {doc_id}: {e}")
            raise AWSServiceError(f"Failed to generate download URL: {e}")


class WebhookService:
    """Service for webhook operations"""

    def __init__(self):
        self.sqs_client = boto3.client("sqs", region_name=settings.aws_region)

    @tracer.capture_method
    def verify_webhook_signature(
        self, payload: str, signature: str, secret: str
    ) -> bool:
        """Verify HMAC signature for webhook"""
        try:
            expected_signature = hmac.new(
                secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # Compare signatures safely
            return hmac.compare_digest(f"sha256={expected_signature}", signature)

        except Exception as e:
            logger.error(f"Failed to verify webhook signature: {e}")
            return False

    @tracer.capture_method
    async def process_webhook(self, payload: Dict[str, Any]) -> bool:
        """Process incoming webhook"""
        try:
            # Send to callback queue for processing
            message_body = json.dumps(payload)

            self.sqs_client.send_message(
                QueueUrl=settings.callback_queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    "eventType": {
                        "StringValue": payload.get("event_type", "unknown"),
                        "DataType": "String",
                    }
                },
            )

            metrics.add_metric(name="WebhooksReceived", unit="Count", value=1)
            logger.info(f"Processed webhook for doc_id: {payload.get('doc_id')}")

            return True

        except ClientError as e:
            logger.error(f"Failed to process webhook: {e}")
            return False


class ReportsService:
    """Service for generating reports and analytics"""

    def __init__(self):
        self.persistence_manager = get_persistence_manager()

    @tracer.capture_method
    async def get_summary_report(self) -> ReportsSummaryResponse:
        """Generate summary report with MongoDB aggregations"""
        try:
            # Get processing summary with proper aggregation
            summary = (
                self.persistence_manager.document_repository.get_processing_summary()
            )

            # Get weekly stats using aggregation
            weekly_stats = (
                self.persistence_manager.document_repository.get_weekly_stats(weeks=4)
            )

            # Calculate metrics
            total_documents = summary.get("total_documents", 0)
            completed_count = summary.get("completed_documents", 0)
            failed_count = summary.get("failed_documents", 0)
            processing_count = summary.get("processing_documents", 0)
            pending_count = summary.get("pending_documents", 0)

            success_rate = summary.get("completion_rate", 0) * 100
            avg_processing_time = summary.get("avg_processing_time_hours", 0)

            # Format weekly stats for response
            formatted_weekly_stats = []
            for week_data in weekly_stats:
                formatted_weekly_stats.append(
                    {
                        "week": week_data["week"],
                        "total_documents": week_data["documents"],
                        "completed_documents": week_data["completed"],
                        "failed_documents": week_data["failed"],
                        "success_rate": week_data["success_rate"] * 100,
                    }
                )

            return ReportsSummaryResponse(
                total_documents=total_documents,
                completed_documents=completed_count,
                processing_documents=processing_count,
                failed_documents=failed_count,
                pending_documents=pending_count,
                completion_rate=success_rate,
                avg_processing_time_hours=avg_processing_time,
                weekly_stats=formatted_weekly_stats,
            )

        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            raise AWSServiceError(f"Failed to generate report: {e}")

    @tracer.capture_method
    async def export_documents_csv(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        owner_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[dict]:
        """Export documents as CSV data with filtering"""
        try:
            # Build aggregation pipeline for CSV export
            pipeline = []

            # Match stage with filters
            match_stage = {}
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

            # Project fields for CSV export
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

            # Sort by creation date (newest first)
            pipeline.append({"$sort": {"createdAt": -1}})

            # Execute aggregation
            results = self.persistence_manager.document_repository.aggregate(pipeline)

            # Convert MongoDB results to CSV-friendly format
            csv_data = []
            for doc in results:
                row = {
                    "Document ID": doc.get("docId", ""),
                    "Filename": doc.get("filename", ""),
                    "Owner ID": doc.get("ownerId", ""),
                    "Status": doc.get("status", ""),
                    "Created At": (
                        doc.get("createdAt", "").isoformat()
                        if doc.get("createdAt")
                        else ""
                    ),
                    "Updated At": (
                        doc.get("updatedAt", "").isoformat()
                        if doc.get("updatedAt")
                        else ""
                    ),
                    "Completed At": (
                        doc.get("completedAt", "").isoformat()
                        if doc.get("completedAt")
                        else ""
                    ),
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
                csv_data.append(row)

            logger.info(f"Exported {len(csv_data)} documents to CSV")
            return csv_data

        except Exception as e:
            logger.error(f"Failed to export documents to CSV: {e}")
            raise AWSServiceError(f"Failed to export CSV: {e}")


class AltTextService:
    """Service for alt-text operations with versioning and audit history"""

    def __init__(self):
        self.persistence_manager = get_persistence_manager()
        self.alt_text_repository = get_alt_text_repository()

    @tracer.capture_method
    async def get_document_alt_text(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
        status_filter: Optional[AltTextStatus] = None,
    ) -> Optional[AltTextDocumentResponse]:
        """Get alt text data for a document with optional status filtering"""
        try:
            # Verify document access if not admin
            if user_id:
                has_access = await self.verify_document_access(doc_id, user_id)
                if not has_access:
                    return None

            # Get alt text data from MongoDB
            alt_text_doc = self.alt_text_repository.get_document_alt_text(doc_id)

            if not alt_text_doc:
                return None

            # Convert MongoDB document to response model
            figures = []
            for figure_data in alt_text_doc.get("figures", []):
                # Apply status filter if specified
                if status_filter and figure_data.get("status") != status_filter.value:
                    continue

                # Convert versions to model objects
                versions = []
                for version_data in figure_data.get("versions", []):
                    versions.append(
                        AltTextVersion(
                            version=version_data.get("version", 1),
                            text=version_data.get("text", ""),
                            editor_id=version_data.get("editor_id", ""),
                            editor_name=version_data.get("editor_name"),
                            timestamp=version_data.get("timestamp"),
                            comment=version_data.get("comment"),
                            is_ai_generated=version_data.get("is_ai_generated", False),
                            confidence=version_data.get("confidence"),
                        )
                    )

                figure = AltTextFigure(
                    figure_id=figure_data.get("figure_id", ""),
                    status=AltTextStatus(figure_data.get("status", "pending")),
                    current_version=figure_data.get("current_version", 1),
                    ai_text=figure_data.get("ai_text"),
                    approved_text=figure_data.get("approved_text"),
                    confidence=figure_data.get("confidence"),
                    generation_method=figure_data.get("generation_method"),
                    versions=versions,
                    context=figure_data.get("context", {}),
                    bounding_box=figure_data.get("bounding_box"),
                    page_number=figure_data.get("page_number"),
                )
                figures.append(figure)

            return AltTextDocumentResponse(
                doc_id=uuid.UUID(doc_id),
                figures=figures,
                total_figures=alt_text_doc.get("total_figures", 0),
                pending_review=alt_text_doc.get("pending_review", 0),
                approved=alt_text_doc.get("approved", 0),
                edited=alt_text_doc.get("edited", 0),
                last_updated=alt_text_doc.get("updated_at", datetime.utcnow()),
            )

        except Exception as e:
            logger.error(f"Failed to get alt text for document {doc_id}: {e}")
            raise AWSServiceError(f"Failed to get alt text: {e}")

    @tracer.capture_method
    async def edit_figure_alt_text(
        self,
        doc_id: str,
        figure_id: str,
        new_text: str,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Optional[AltTextEditResponse]:
        """Edit alt text for a figure, creating a new version"""
        try:
            # Edit the figure alt text in repository
            success = self.alt_text_repository.edit_figure_alt_text(
                doc_id=doc_id,
                figure_id=figure_id,
                new_text=new_text,
                editor_id=editor_id,
                editor_name=editor_name,
                comment=comment,
            )

            if not success:
                return None

            # Get the updated figure to return current version info
            alt_text_doc = self.alt_text_repository.get_document_alt_text(doc_id)
            if not alt_text_doc:
                return None

            # Find the figure that was edited
            for figure_data in alt_text_doc.get("figures", []):
                if figure_data.get("figure_id") == figure_id:
                    return AltTextEditResponse(
                        figure_id=figure_id,
                        version=figure_data.get("current_version", 1),
                        text=new_text,
                        status=AltTextStatus(figure_data.get("status", "edited")),
                        timestamp=datetime.utcnow(),
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to edit alt text for figure {figure_id}: {e}")
            raise AWSServiceError(f"Failed to edit alt text: {e}")

    @tracer.capture_method
    async def bulk_update_status(
        self,
        doc_id: str,
        figure_ids: List[str],
        status: AltTextStatus,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> int:
        """Update status for multiple figures"""
        try:
            return self.alt_text_repository.bulk_update_status(
                doc_id=doc_id,
                figure_ids=figure_ids,
                status=status.value,
                editor_id=editor_id,
                editor_name=editor_name,
                comment=comment,
            )

        except Exception as e:
            logger.error(f"Failed to bulk update status: {e}")
            raise AWSServiceError(f"Failed to bulk update status: {e}")

    @tracer.capture_method
    async def get_figure_history(
        self, doc_id: str, figure_id: str
    ) -> Optional[AltTextHistoryResponse]:
        """Get complete history for a specific figure"""
        try:
            history_data = self.alt_text_repository.get_figure_history(
                doc_id, figure_id
            )

            if not history_data:
                return None

            # Convert versions to model objects
            versions = []
            for version_data in history_data.get("versions", []):
                versions.append(
                    AltTextVersion(
                        version=version_data.get("version", 1),
                        text=version_data.get("text", ""),
                        editor_id=version_data.get("editor_id", ""),
                        editor_name=version_data.get("editor_name"),
                        timestamp=version_data.get("timestamp"),
                        comment=version_data.get("comment"),
                        is_ai_generated=version_data.get("is_ai_generated", False),
                        confidence=version_data.get("confidence"),
                    )
                )

            return AltTextHistoryResponse(
                figure_id=figure_id,
                versions=versions,
                current_version=history_data.get("current_version", 1),
                status=AltTextStatus(history_data.get("status", "pending")),
            )

        except Exception as e:
            logger.error(f"Failed to get history for figure {figure_id}: {e}")
            raise AWSServiceError(f"Failed to get figure history: {e}")

    @tracer.capture_method
    async def revert_to_version(
        self,
        doc_id: str,
        figure_id: str,
        version: int,
        editor_id: str,
        editor_name: Optional[str] = None,
    ) -> Optional[AltTextEditResponse]:
        """Revert a figure to a specific version"""
        try:
            success = self.alt_text_repository.revert_to_version(
                doc_id=doc_id,
                figure_id=figure_id,
                version=version,
                editor_id=editor_id,
                editor_name=editor_name,
            )

            if not success:
                return None

            # Get the updated figure to return version info
            alt_text_doc = self.alt_text_repository.get_document_alt_text(doc_id)
            if not alt_text_doc:
                return None

            # Find the figure that was reverted
            for figure_data in alt_text_doc.get("figures", []):
                if figure_data.get("figure_id") == figure_id:
                    # Get the text from the reverted-to version
                    reverted_text = ""
                    for version_data in figure_data.get("versions", []):
                        if version_data.get("version") == version:
                            reverted_text = version_data.get("text", "")
                            break

                    return AltTextEditResponse(
                        figure_id=figure_id,
                        version=figure_data.get("current_version", 1),
                        text=reverted_text,
                        status=AltTextStatus(figure_data.get("status", "edited")),
                        timestamp=datetime.utcnow(),
                    )

            return None

        except Exception as e:
            logger.error(
                f"Failed to revert figure {figure_id} to version {version}: {e}"
            )
            raise AWSServiceError(f"Failed to revert to version: {e}")

    @tracer.capture_method
    async def verify_document_access(self, doc_id: str, user_id: str) -> bool:
        """Verify that a user has access to a document"""
        try:
            document = self.persistence_manager.document_repository.get_document(doc_id)
            if not document:
                return False

            # Check if user is the owner (handle both userId and ownerId fields)
            document_owner = document.get("ownerId") or document.get("userId")
            return document_owner == user_id

        except Exception as e:
            logger.error(f"Failed to verify document access for {doc_id}: {e}")
            return False

    @tracer.capture_method
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get alt text dashboard statistics"""
        try:
            # Get documents that need review
            documents_needing_review = (
                self.alt_text_repository.get_documents_needing_review(limit=100)
            )

            # Calculate summary statistics
            total_documents_with_alt_text = len(documents_needing_review)
            total_figures = sum(
                doc.get("total_figures", 0) for doc in documents_needing_review
            )
            pending_review = sum(
                doc.get("pending_review", 0) for doc in documents_needing_review
            )
            approved = sum(doc.get("approved", 0) for doc in documents_needing_review)
            edited = sum(doc.get("edited", 0) for doc in documents_needing_review)

            return {
                "summary": {
                    "total_documents": total_documents_with_alt_text,
                    "total_figures": total_figures,
                    "pending_review": pending_review,
                    "approved": approved,
                    "edited": edited,
                    "completion_rate": (
                        (approved / total_figures * 100) if total_figures > 0 else 0
                    ),
                },
                "recent_documents": documents_needing_review[:10],  # Most recent 10
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            raise AWSServiceError(f"Failed to get dashboard stats: {e}")


# Global service instances
document_service = DocumentService()
webhook_service = WebhookService()
reports_service = ReportsService()
alt_text_service = AltTextService()

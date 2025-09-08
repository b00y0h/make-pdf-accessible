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

from .config import settings
from .models import (
    DocumentResponse,
    DocumentStatus,
    DocumentType,
    ReportsSummaryResponse,
)
from services.shared.persistence import get_persistence_manager

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
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.sqs_client = boto3.client('sqs', region_name=settings.aws_region)

    @tracer.capture_method
    async def create_document(
        self,
        user_id: str,
        filename: Optional[str] = None,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: bool = False,
        webhook_url: Optional[str] = None
    ) -> DocumentResponse:
        """Create a new document record"""
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow()

        document_data = {
            'docId': doc_id,
            'ownerId': user_id,  # Use ownerId for MongoDB schema compatibility
            'status': DocumentStatus.PENDING.value,
            'createdAt': now,
            'updatedAt': now,
            'metadata': metadata or {},
            'artifacts': {}
        }

        if filename:
            document_data['filename'] = filename
        if source_url:
            document_data['sourceUrl'] = source_url
        if webhook_url:
            document_data['webhookUrl'] = webhook_url

        try:
            # Store document record using persistence layer
            created_document = self.persistence_manager.create_document(document_data)

            # Create job record
            job_data = {
                'jobId': str(uuid.uuid4()),
                'docId': doc_id,
                'ownerId': user_id,  # Use ownerId for consistency
                'step': 'structure',  # Initial step
                'status': 'pending',
                'priority': priority,
                'createdAt': now,
                'updatedAt': now,
                'queuedAt': now
            }

            self.persistence_manager.create_job(job_data)

            # Send to appropriate queue
            queue_url = settings.priority_process_queue_url if priority else settings.ingest_queue_url

            message_body = {
                'docId': doc_id,
                'userId': user_id,
                'filename': filename,
                'sourceUrl': source_url,
                'priority': priority,
                'webhookUrl': webhook_url,
                'metadata': metadata or {}
            }

            self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    'docId': {'StringValue': doc_id, 'DataType': 'String'},
                    'priority': {'StringValue': str(priority), 'DataType': 'String'}
                }
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
                artifacts={}
            )

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise AWSServiceError(f"Failed to create document: {e}")

    @tracer.capture_method
    async def get_document(self, doc_id: str, user_id: Optional[str] = None) -> Optional[DocumentResponse]:
        """Get document by ID"""
        try:
            document = self.persistence_manager.document_repository.get_document(doc_id)

            if not document:
                return None

            # Check access permissions - handle both userId (DynamoDB) and ownerId (MongoDB)
            document_owner = document.get('ownerId') or document.get('userId')
            if user_id and document_owner != user_id:
                return None

            # Handle both datetime objects and ISO strings for compatibility
            created_at = document['createdAt']
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            updated_at = document['updatedAt']
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)

            completed_at = document.get('completedAt')
            if completed_at and isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)

            return DocumentResponse(
                doc_id=uuid.UUID(document['docId']),
                status=DocumentStatus(document['status']),
                filename=document.get('filename'),
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at,
                user_id=document_owner,  # Use the appropriate field
                metadata=document.get('metadata', {}),
                error_message=document.get('errorMessage'),
                artifacts=document.get('artifacts', {})
            )

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            raise AWSServiceError(f"Failed to get document: {e}")

    @tracer.capture_method
    async def list_user_documents(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        status_filter: Optional[DocumentStatus] = None
    ) -> Tuple[List[DocumentResponse], int]:
        """List documents for a user with pagination"""
        try:
            # Prepare status filter for persistence layer
            status_list = [status_filter.value] if status_filter else None

            # Use the persistence layer's document repository
            result = self.persistence_manager.document_repository.get_documents_by_owner(
                owner_id=user_id,
                status_filter=status_list,
                page=(offset // limit) + 1,  # Convert offset to page number
                limit=limit
            )

            documents = []
            for item in result['documents']:
                # Handle both datetime objects and ISO strings for compatibility
                created_at = item['createdAt']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                updated_at = item['updatedAt']
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at)

                completed_at = item.get('completedAt')
                if completed_at and isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at)

                # Handle both userId (DynamoDB) and ownerId (MongoDB) fields
                document_owner = item.get('ownerId') or item.get('userId')

                documents.append(DocumentResponse(
                    doc_id=uuid.UUID(item['docId']),
                    status=DocumentStatus(item['status']),
                    filename=item.get('filename'),
                    created_at=created_at,
                    updated_at=updated_at,
                    completed_at=completed_at,
                    user_id=document_owner,
                    metadata=item.get('metadata', {}),
                    error_message=item.get('errorMessage'),
                    artifacts=item.get('artifacts', {})
                ))

            return documents, result['total']

        except Exception as e:
            logger.error(f"Failed to list documents for user {user_id}: {e}")
            raise AWSServiceError(f"Failed to list documents: {e}")

    @tracer.capture_method
    async def generate_presigned_url(
        self,
        doc_id: str,
        document_type: DocumentType,
        expires_in: int = 3600
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
                if e.response['Error']['Code'] == '404':
                    raise AWSServiceError(f"Document {document_type.value} not available")
                raise

            # Generate pre-signed URL
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket,
                    'Key': key,
                    'ResponseContentDisposition': f'attachment; filename="{quote(filename)}"'
                },
                ExpiresIn=expires_in
            )

            return presigned_url, content_type, filename

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {doc_id}: {e}")
            raise AWSServiceError(f"Failed to generate download URL: {e}")


class WebhookService:
    """Service for webhook operations"""

    def __init__(self):
        self.sqs_client = boto3.client('sqs', region_name=settings.aws_region)

    @tracer.capture_method
    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature for webhook"""
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
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
                    'eventType': {'StringValue': payload.get('event_type', 'unknown'), 'DataType': 'String'}
                }
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
        """Generate summary report with statistics"""
        try:
            # Get processing summary from the document repository
            summary = self.persistence_manager.document_repository.get_processing_summary()

            # Calculate metrics
            total_documents = summary.get('total_documents', 0)
            status_counts = summary.get('documents_by_status', {})
            completed_count = status_counts.get('completed', 0)
            success_rate = (completed_count / total_documents * 100) if total_documents > 0 else 0
            avg_processing_time = summary.get('average_processing_time', 0)

            # Generate weekly stats (last 4 weeks) - simplified for now
            # In a production system, this would be optimized with aggregation queries
            weekly_stats = []
            current_week = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            for i in range(4):
                week_start = current_week - timedelta(weeks=i+1)
                week_end = current_week - timedelta(weeks=i)

                # For now, use placeholder data - this would need proper aggregation
                weekly_stats.append({
                    'week_start': week_start.isoformat(),
                    'week_end': week_end.isoformat(),
                    'total_documents': 0,  # Would need aggregation query
                    'completed_documents': 0,  # Would need aggregation query
                    'failed_documents': 0  # Would need aggregation query
                })

            return ReportsSummaryResponse(
                total_documents=total_documents,
                documents_by_status=status_counts,
                weekly_stats=weekly_stats,
                average_processing_time=avg_processing_time,
                success_rate=success_rate
            )

        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            raise AWSServiceError(f"Failed to generate report: {e}")


# Global service instances
document_service = DocumentService()
webhook_service = WebhookService()
reports_service = ReportsService()

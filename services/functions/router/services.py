"""AWS services for the router function."""

import json
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import boto3
import httpx
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError
from models import DocumentRecord, JobRecord, ProcessMessage

logger = Logger()
tracer = Tracer()


class AWSServiceError(Exception):
    """Custom exception for AWS service errors."""

    pass


class RouterService:
    """Service for router function operations."""

    def __init__(
        self,
        documents_table: str,
        jobs_table: str,
        pdf_originals_bucket: str,
        process_queue_url: str,
        priority_process_queue_url: str,
        region: str = "us-east-1",
    ):
        self.documents_table = documents_table
        self.jobs_table = jobs_table
        self.pdf_originals_bucket = pdf_originals_bucket
        self.process_queue_url = process_queue_url
        self.priority_process_queue_url = priority_process_queue_url

        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.s3_client = boto3.client("s3", region_name=region)
        self.sqs_client = boto3.client("sqs", region_name=region)

        self.documents_table_resource = self.dynamodb.Table(self.documents_table)
        self.jobs_table_resource = self.dynamodb.Table(self.jobs_table)

    @tracer.capture_method
    def check_document_exists(self, doc_id: str) -> bool:
        """Check if document already exists (idempotency check)."""
        try:
            response = self.documents_table_resource.get_item(Key={"docId": doc_id})
            exists = "Item" in response

            if exists:
                logger.info(f"Document {doc_id} already exists - skipping processing")

            return exists

        except ClientError as e:
            logger.error(f"Failed to check document existence for {doc_id}: {e}")
            raise AWSServiceError(f"Database error: {e}")

    @tracer.capture_method
    async def download_and_store_from_url(
        self, doc_id: str, source_url: str, filename: Optional[str] = None
    ) -> str:
        """Download file from URL and store in S3."""
        logger.info(f"Downloading file from URL for {doc_id}: {source_url}")

        try:
            # Generate S3 key
            parsed_url = urlparse(source_url)
            if filename:
                s3_key = f"originals/{doc_id}/{filename}"
            else:
                # Extract filename from URL or use a default
                url_filename = parsed_url.path.split("/")[-1] or "document"
                s3_key = f"originals/{doc_id}/{url_filename}"

            # Download file
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(source_url)
                response.raise_for_status()

                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.pdf_originals_bucket,
                    Key=s3_key,
                    Body=response.content,
                    ContentType=response.headers.get(
                        "content-type", "application/octet-stream"
                    ),
                    Metadata={
                        "source_url": source_url,
                        "doc_id": doc_id,
                        "downloaded_at": datetime.utcnow().isoformat(),
                    },
                )

            logger.info(
                f"Successfully downloaded and stored file for {doc_id} at {s3_key}"
            )
            return s3_key

        except httpx.HTTPError as e:
            logger.error(f"Failed to download from URL {source_url}: {e}")
            raise AWSServiceError(f"Failed to download file: {e}")
        except ClientError as e:
            logger.error(f"Failed to upload to S3 for {doc_id}: {e}")
            raise AWSServiceError(f"S3 upload failed: {e}")

    @tracer.capture_method
    def copy_uploaded_file(
        self, doc_id: str, source_s3_key: str, filename: Optional[str] = None
    ) -> str:
        """Copy uploaded file to pdf-originals bucket."""
        logger.info(f"Copying uploaded file for {doc_id}: {source_s3_key}")

        try:
            # Parse the source key to extract bucket and key
            # Assume source_s3_key is in format "bucket/key" or just "key"
            if "/" in source_s3_key:
                source_bucket, source_key = source_s3_key.split("/", 1)
            else:
                # Assume it's from a temp bucket
                source_bucket = self.pdf_originals_bucket.replace("-originals", "-temp")
                source_key = source_s3_key

            # Generate destination key
            dest_key = f"originals/{doc_id}/{filename or 'document'}"

            # Copy file
            copy_source = {"Bucket": source_bucket, "Key": source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.pdf_originals_bucket,
                Key=dest_key,
                MetadataDirective="REPLACE",
                Metadata={"doc_id": doc_id, "copied_at": datetime.utcnow().isoformat()},
            )

            logger.info(f"Successfully copied file for {doc_id} to {dest_key}")
            return dest_key

        except ClientError as e:
            logger.error(f"Failed to copy file for {doc_id}: {e}")
            raise AWSServiceError(f"S3 copy failed: {e}")

    @tracer.capture_method
    def save_document_record(self, document: DocumentRecord) -> None:
        """Save document record to DynamoDB."""
        logger.info(f"Saving document record: {document.doc_id}")

        try:
            # Convert to DynamoDB item format
            item = {
                "docId": document.doc_id,
                "userId": document.user_id,
                "status": document.status.value,
                "source": document.source.value,
                "filename": document.filename,
                "s3KeyOriginal": document.s3_key_original,
                "sourceUrl": document.source_url,
                "webhookUrl": document.webhook_url,
                "metadata": document.metadata or {},
                "createdAt": document.created_at.isoformat(),
                "updatedAt": document.updated_at.isoformat(),
                "errorMessage": document.error_message,
                "artifacts": document.artifacts or {},
                "processingStats": document.processing_stats or {},
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.documents_table_resource.put_item(Item=item)
            logger.info(f"Successfully saved document record: {document.doc_id}")

        except ClientError as e:
            logger.error(f"Failed to save document record {document.doc_id}: {e}")
            raise AWSServiceError(f"Database save failed: {e}")

    @tracer.capture_method
    def create_job_record(self, job: JobRecord) -> None:
        """Create job record in DynamoDB."""
        logger.info(f"Creating job record: {job.job_id} for document {job.doc_id}")

        try:
            # Convert to DynamoDB item format
            item = {
                "jobId": job.job_id,
                "docId": job.doc_id,
                "step": job.step.value,
                "status": job.status.value,
                "priority": job.priority,
                "inputData": job.input_data or {},
                "outputData": job.output_data or {},
                "createdAt": job.created_at.isoformat(),
                "updatedAt": job.updated_at.isoformat(),
                "startedAt": job.started_at.isoformat() if job.started_at else None,
                "completedAt": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
                "errorMessage": job.error_message,
                "retryCount": job.retry_count,
                "maxRetries": job.max_retries,
                "processingTimeMs": job.processing_time_ms,
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.jobs_table_resource.put_item(Item=item)
            logger.info(f"Successfully created job record: {job.job_id}")

        except ClientError as e:
            logger.error(f"Failed to create job record {job.job_id}: {e}")
            raise AWSServiceError(f"Database save failed: {e}")

    @tracer.capture_method
    def enqueue_process_message(self, message: ProcessMessage) -> None:
        """Send message to process queue."""
        queue_url = (
            self.priority_process_queue_url
            if message.priority
            else self.process_queue_url
        )
        logger.info(
            f"Enqueuing process message for job {message.job_id} to {'priority' if message.priority else 'standard'} queue"
        )

        try:
            message_body = json.dumps(
                {
                    "jobId": message.job_id,
                    "docId": message.doc_id,
                    "step": message.step.value,
                    "priority": message.priority,
                    "inputData": message.input_data,
                    "retryCount": message.retry_count,
                }
            )

            # Add message attributes for filtering
            message_attributes = {
                "step": {"StringValue": message.step.value, "DataType": "String"},
                "priority": {
                    "StringValue": str(message.priority).lower(),
                    "DataType": "String",
                },
                "docId": {"StringValue": message.doc_id, "DataType": "String"},
            }

            self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageAttributes=message_attributes,
                MessageGroupId=message.doc_id if queue_url.endswith(".fifo") else None,
                MessageDeduplicationId=(
                    f"{message.job_id}-{message.retry_count}"
                    if queue_url.endswith(".fifo")
                    else None
                ),
            )

            logger.info(
                f"Successfully enqueued process message for job {message.job_id}"
            )

        except ClientError as e:
            logger.error(
                f"Failed to enqueue process message for job {message.job_id}: {e}"
            )
            raise AWSServiceError(f"Queue send failed: {e}")

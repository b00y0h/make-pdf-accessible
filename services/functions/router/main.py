"""
Router function: Normalize inputs and create jobs.

Input: SQS message from ingest-queue containing docId, source (upload or URL), S3 key.
Actions: Save Documents record, store original to pdf-originals, create Jobs row with step OCR, enqueue process-queue.
Features: Idempotency (dedupe by docId), structured logs, X-Ray tracing.
"""

import json
import os
from typing import Any, Dict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.data_classes import SQSEvent, event_source
from aws_lambda_powertools.utilities.typing import LambdaContext
from models import (
    DocumentRecord,
    DocumentSource,
    DocumentStatus,
    IngestMessage,
    JobRecord,
    JobStatus,
    JobStep,
    ProcessMessage,
)
from pydantic import ValidationError

from services import AWSServiceError, RouterService

# Initialize Powertools
logger = Logger(service="pdf-router")
tracer = Tracer(service="pdf-router")
metrics = Metrics(namespace="PDF-Accessibility", service="pdf-router")

# Environment variables
DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "pdf-accessibility-documents")
JOBS_TABLE = os.environ.get("JOBS_TABLE", "pdf-accessibility-jobs")
PDF_ORIGINALS_BUCKET = os.environ.get(
    "PDF_ORIGINALS_BUCKET", "pdf-accessibility-pdf-originals"
)
PROCESS_QUEUE_URL = os.environ.get("PROCESS_QUEUE_URL", "")
PRIORITY_PROCESS_QUEUE_URL = os.environ.get("PRIORITY_PROCESS_QUEUE_URL", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize service
router_service = RouterService(
    documents_table=DOCUMENTS_TABLE,
    jobs_table=JOBS_TABLE,
    pdf_originals_bucket=PDF_ORIGINALS_BUCKET,
    process_queue_url=PROCESS_QUEUE_URL,
    priority_process_queue_url=PRIORITY_PROCESS_QUEUE_URL,
    region=AWS_REGION,
)


@tracer.capture_method
async def process_document(ingest_message: IngestMessage) -> Dict[str, Any]:
    """
    Process a single document from ingest queue.

    Returns:
        Dict containing processing results and metrics
    """
    doc_id = ingest_message.doc_id
    logger.info(f"Processing document {doc_id}", extra={"doc_id": doc_id})

    processing_start = tracer.provider.get_start_time()
    result = {
        "doc_id": doc_id,
        "status": "success",
        "actions_performed": [],
        "error": None,
    }

    try:
        # 1. Idempotency check - skip if document already exists
        if router_service.check_document_exists(doc_id):
            result["status"] = "skipped"
            result["reason"] = "document already exists"
            metrics.add_metric(name="DocumentsSkipped", unit="Count", value=1)
            logger.info(f"Document {doc_id} already exists, skipping processing")
            return result

        result["actions_performed"].append("idempotency_check_passed")

        # 2. Store original file to pdf-originals bucket
        s3_key_original = None

        if ingest_message.source == DocumentSource.UPLOAD:
            # Copy from temp/uploaded location to originals
            s3_key_original = router_service.copy_uploaded_file(
                doc_id=doc_id,
                source_s3_key=ingest_message.s3_key,
                filename=ingest_message.filename,
            )
            result["actions_performed"].append("file_copied_to_originals")

        elif ingest_message.source == DocumentSource.URL:
            # Download from URL and store
            s3_key_original = await router_service.download_and_store_from_url(
                doc_id=doc_id,
                source_url=ingest_message.source_url,
                filename=ingest_message.filename,
            )
            result["actions_performed"].append("file_downloaded_from_url")

        # 3. Create document record
        document_record = DocumentRecord(
            doc_id=doc_id,
            user_id=ingest_message.user_id,
            status=DocumentStatus.PENDING,
            source=ingest_message.source,
            filename=ingest_message.filename,
            s3_key_original=s3_key_original,
            source_url=ingest_message.source_url,
            webhook_url=ingest_message.webhook_url,
            metadata=ingest_message.metadata or {},
        )

        router_service.save_document_record(document_record)
        result["actions_performed"].append("document_record_saved")

        # 4. Create OCR job record
        ocr_job = JobRecord(
            doc_id=doc_id,
            step=JobStep.OCR,
            status=JobStatus.PENDING,
            priority=ingest_message.priority,
            input_data={
                "s3_bucket": PDF_ORIGINALS_BUCKET,
                "s3_key": s3_key_original,
                "filename": ingest_message.filename,
                "source": ingest_message.source.value,
            },
        )

        router_service.create_job_record(ocr_job)
        result["actions_performed"].append("ocr_job_created")

        # 5. Enqueue to process queue
        process_message = ProcessMessage(
            job_id=ocr_job.job_id,
            doc_id=doc_id,
            step=JobStep.OCR,
            priority=ingest_message.priority,
            input_data=ocr_job.input_data,
        )

        router_service.enqueue_process_message(process_message)
        result["actions_performed"].append("process_message_enqueued")

        # Add processing metrics
        processing_time = tracer.provider.get_elapsed_time_ms(processing_start)
        result["processing_time_ms"] = processing_time
        result["job_id"] = ocr_job.job_id
        result["s3_key_original"] = s3_key_original

        metrics.add_metric(name="DocumentsProcessed", unit="Count", value=1)
        metrics.add_metric(
            name="ProcessingTime", unit="Milliseconds", value=processing_time
        )

        if ingest_message.priority:
            metrics.add_metric(name="PriorityDocumentsProcessed", unit="Count", value=1)

        logger.info(
            f"Successfully processed document {doc_id}",
            extra={
                "doc_id": doc_id,
                "job_id": ocr_job.job_id,
                "processing_time_ms": processing_time,
                "actions": result["actions_performed"],
            },
        )

        return result

    except ValidationError as e:
        error_msg = f"Validation error for document {doc_id}: {e}"
        logger.error(
            error_msg, extra={"doc_id": doc_id, "validation_errors": e.errors()}
        )
        result["status"] = "failed"
        result["error"] = error_msg
        metrics.add_metric(name="ValidationErrors", unit="Count", value=1)
        return result

    except AWSServiceError as e:
        error_msg = f"AWS service error for document {doc_id}: {e}"
        logger.error(error_msg, extra={"doc_id": doc_id})
        result["status"] = "failed"
        result["error"] = error_msg
        metrics.add_metric(name="AWSServiceErrors", unit="Count", value=1)
        return result

    except Exception as e:
        error_msg = f"Unexpected error for document {doc_id}: {e}"
        logger.exception(error_msg, extra={"doc_id": doc_id})
        result["status"] = "failed"
        result["error"] = error_msg
        metrics.add_metric(name="UnexpectedErrors", unit="Count", value=1)
        return result


@event_source(data_class=SQSEvent)
@logger.inject_lambda_context(correlation_id_path=correlation_paths.SQS)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: SQSEvent, context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for processing SQS messages from ingest-queue.

    Processes documents with idempotency, stores originals, creates jobs,
    and enqueues to process-queue.
    """
    logger.info(f"Processing {len(event.records)} messages from ingest queue")

    results = {"processed": 0, "skipped": 0, "failed": 0, "results": []}

    for record in event.records:
        try:
            # Parse SQS message
            message_body = json.loads(record.body)
            logger.debug(f"Processing message: {message_body}")

            # Validate and create ingest message
            ingest_message = IngestMessage.model_validate(message_body)

            # Process the document
            result = await process_document(ingest_message)
            results["results"].append(result)

            # Update counters
            if result["status"] == "success":
                results["processed"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            error_msg = f"Failed to process SQS record: {e}"
            logger.exception(error_msg)
            results["failed"] += 1
            results["results"].append(
                {
                    "status": "failed",
                    "error": error_msg,
                    "message_id": record.message_id,
                }
            )
            metrics.add_metric(name="RecordProcessingErrors", unit="Count", value=1)

    # Log final results
    logger.info(
        "Batch processing complete",
        extra={
            "total_records": len(event.records),
            "processed": results["processed"],
            "skipped": results["skipped"],
            "failed": results["failed"],
        },
    )

    # Add batch metrics
    metrics.add_metric(name="BatchesProcessed", unit="Count", value=1)
    metrics.add_metric(name="RecordsPerBatch", unit="Count", value=len(event.records))

    return results


# For local testing
if __name__ == "__main__":
    # Sample test message
    test_event = {
        "Records": [
            {
                "messageId": "test-message-1",
                "body": json.dumps(
                    {
                        "doc_id": "test-doc-123",
                        "source": "upload",
                        "s3_key": "temp/test-doc-123/document.pdf",
                        "filename": "test-document.pdf",
                        "user_id": "user-123",
                        "priority": False,
                        "metadata": {"test": True},
                    }
                ),
            }
        ]
    }

    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "test-router"
            self.function_version = "1"
            self.aws_request_id = "test-request-id"

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))

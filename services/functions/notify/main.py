import json
import time
from typing import Any, Dict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="pdf-notifier")
tracer = Tracer(service="pdf-notifier")
metrics = Metrics(namespace="PDF-Accessibility", service="pdf-notifier")


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Update DynamoDB and send notifications via SNS/webhook."""
    start_time = time.time()

    try:
        doc_id = event.get("docId") or event.get("doc_id")
        status = event.get("status", "unknown")
        user_id = event.get("userId") or event.get("user_id")

        logger.info(f"Sending notifications for document {doc_id} with status {status}")

        # Mock notification - in real implementation:
        # 1. Update DynamoDB Documents table with final status
        # 2. Create completion record with all S3 keys and results
        # 3. Send SNS notification to configured topics
        # 4. Send webhook notification if webhook_url provided
        # 5. Update job status in Jobs table
        # 6. Log completion metrics

        notifications_sent = 2  # SNS + webhook (mock)
        processing_time = time.time() - start_time

        if status == "completed":
            results = event.get("results", {})
            logger.info(f"Document {doc_id} processing completed successfully")
            logger.info(f"Results: {json.dumps(results, indent=2)}")

            # Mock DynamoDB update
            document_update = {
                "docId": doc_id,
                "status": "completed",
                "completedAt": int(time.time()),
                "accessibilityScore": results.get("validationScore", 0),
                "taggedPdfUrl": results.get("taggedPdfS3Key"),
                "htmlUrl": results.get("htmlS3Key"),
                "epubUrl": results.get("epubS3Key"),
                "csvZipUrl": results.get("csvZipS3Key"),
            }

            metrics.add_metric(name="DocumentsCompleted", unit="Count", value=1)

        else:
            # Handle failure case
            error = event.get("error", {})
            step = event.get("step", "unknown")

            logger.error(f"Document {doc_id} processing failed at step {step}")
            logger.error(f"Error: {json.dumps(error, indent=2)}")

            # Mock DynamoDB update for failure
            document_update = {
                "docId": doc_id,
                "status": "failed",
                "failedAt": int(time.time()),
                "failedStep": step,
                "errorMessage": error.get("Error", "Unknown error"),
            }

            metrics.add_metric(name="DocumentsFailed", unit="Count", value=1)

        # Mock webhook notification
        if status == "completed":
            webhook_payload = {
                "event": "document_processing_completed",
                "doc_id": doc_id,
                "user_id": user_id,
                "timestamp": int(time.time()),
                "results": event.get("results", {}),
            }
        else:
            webhook_payload = {
                "event": "document_processing_failed",
                "doc_id": doc_id,
                "user_id": user_id,
                "timestamp": int(time.time()),
                "error": event.get("error", {}),
            }

        logger.info(f"Sent {notifications_sent} notifications for document {doc_id}")

        return {
            "doc_id": doc_id,
            "status": "completed",
            "notifications_sent": notifications_sent,
            "processing_time_seconds": processing_time,
        }

    except Exception as e:
        logger.error(f"Notification failed: {str(e)}")
        return {
            "doc_id": event.get("docId", "unknown"),
            "status": "failed",
            "error_message": str(e),
        }

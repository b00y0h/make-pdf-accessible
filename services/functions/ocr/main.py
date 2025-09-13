import time
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from models import OCRRequest, OCRResult, OCRStatus

from services import OCRService, OCRServiceError

# Initialize AWS Lambda Powertools
logger = Logger(service="pdf-ocr")
tracer = Tracer(service="pdf-ocr")
metrics = Metrics(namespace="PDF-Accessibility", service="pdf-ocr")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda handler for OCR processing using AWS Textract.

    Processes PDF documents to extract text using Textract for image-based PDFs.
    For text-based PDFs, validates content and marks as not requiring OCR.
    """
    start_time = time.time()

    try:
        # Parse input
        ocr_request = OCRRequest(**event)
        logger.info(f"Starting OCR processing for document {ocr_request.doc_id}")

        # Initialize service
        ocr_service = OCRService()

        # Check if PDF is image-based
        logger.info("Analyzing PDF content type")
        is_image_based, page_count = ocr_service.check_if_image_based(
            ocr_request.s3_key
        )

        if not is_image_based:
            # Text-based PDF - no OCR needed
            logger.info(f"PDF is text-based with {page_count} pages - skipping OCR")
            processing_time = time.time() - start_time

            metrics.add_metric(name="TextBasedPDFs", unit="Count", value=1)
            metrics.add_metric(
                name="ProcessingTime", unit="Seconds", value=processing_time
            )

            return OCRResult(
                doc_id=ocr_request.doc_id,
                status=OCRStatus.COMPLETED,
                textract_s3_key=None,  # No Textract output needed
                is_image_based=False,
                page_count=page_count,
                processing_time_seconds=processing_time,
            ).dict()

        # Image-based PDF - run Textract
        logger.info(f"PDF is image-based with {page_count} pages - running Textract")
        metrics.add_metric(name="ImageBasedPDFs", unit="Count", value=1)

        # Start Textract job
        job_id = ocr_service.start_textract_job(ocr_request.s3_key, ocr_request.doc_id)
        logger.info(f"Started Textract job {job_id}")

        # Poll for completion
        job_status = ocr_service.poll_textract_job(job_id)

        if job_status.status != OCRStatus.COMPLETED:
            error_msg = job_status.error_message or "Textract job failed"
            logger.error(f"Textract job failed: {error_msg}")
            metrics.add_metric(name="OCRFailures", unit="Count", value=1)

            return OCRResult(
                doc_id=ocr_request.doc_id,
                status=OCRStatus.FAILED,
                textract_s3_key=None,
                is_image_based=True,
                page_count=page_count,
                error_message=error_msg,
            ).dict()

        # Get results and save to S3
        textract_response = ocr_service.get_textract_results(job_id)
        textract_s3_key = ocr_service.save_textract_results(
            ocr_request.doc_id, textract_response
        )

        processing_time = time.time() - start_time

        logger.info(
            f"OCR processing completed for {ocr_request.doc_id} in {processing_time:.2f} seconds"
        )
        metrics.add_metric(name="OCRSuccess", unit="Count", value=1)
        metrics.add_metric(name="ProcessingTime", unit="Seconds", value=processing_time)
        metrics.add_metric(name="PagesProcessed", unit="Count", value=page_count)

        return OCRResult(
            doc_id=ocr_request.doc_id,
            status=OCRStatus.COMPLETED,
            textract_s3_key=textract_s3_key,
            is_image_based=True,
            page_count=page_count,
            processing_time_seconds=processing_time,
        ).dict()

    except OCRServiceError as e:
        logger.error(f"OCR service error: {str(e)}")
        metrics.add_metric(name="ServiceErrors", unit="Count", value=1)

        return OCRResult(
            doc_id=event.get("doc_id", "unknown"),
            status=OCRStatus.FAILED,
            textract_s3_key=None,
            is_image_based=False,
            page_count=0,
            error_message=str(e),
        ).dict()

    except Exception as e:
        logger.error(f"Unexpected error in OCR processing: {str(e)}")
        metrics.add_metric(name="UnexpectedErrors", unit="Count", value=1)

        return OCRResult(
            doc_id=event.get("doc_id", "unknown"),
            status=OCRStatus.FAILED,
            textract_s3_key=None,
            is_image_based=False,
            page_count=0,
            error_message=f"Unexpected error: {str(e)}",
        ).dict()

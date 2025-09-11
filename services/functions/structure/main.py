import time
from typing import Any, Dict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from models import StructureRequest, StructureResult

from services import StructureService, StructureServiceError

# Initialize AWS Lambda Powertools
logger = Logger(service="pdf-structure")
tracer = Tracer(service="pdf-structure")
metrics = Metrics(namespace="PDF-Accessibility", service="pdf-structure")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for document structure analysis.

    Combines Textract OCR results with PDF text extraction and uses Bedrock Claude
    to analyze document structure and create a logical document model.
    """
    start_time = time.time()

    try:
        # Parse input
        request = StructureRequest(**event)
        logger.info(f"Starting structure analysis for document {request.doc_id}")

        # Initialize service
        structure_service = StructureService()

        # Extract PDF text using pdfminer.six
        logger.info("Extracting PDF text content")
        pdf_text = structure_service.extract_pdf_text(request.original_s3_key)

        # Load Textract results if available
        textract_data = None
        if request.textract_s3_key:
            logger.info("Loading Textract OCR results")
            textract_data = structure_service.load_textract_results(
                request.textract_s3_key
            )

        # Analyze document structure with Bedrock
        logger.info("Analyzing document structure with Bedrock Claude")
        document_structure = structure_service.analyze_document_structure(
            pdf_text, textract_data
        )

        # Set doc_id in structure
        document_structure.doc_id = request.doc_id

        # Save structured document to S3
        document_json_s3_key = structure_service.save_document_structure(
            request.doc_id, document_structure
        )

        processing_time = time.time() - start_time

        logger.info(
            f"Structure analysis completed for {request.doc_id} in {processing_time:.2f} seconds"
        )
        logger.info(f"Detected {len(document_structure.elements)} structural elements")

        metrics.add_metric(name="StructureAnalysisSuccess", unit="Count", value=1)
        metrics.add_metric(name="ProcessingTime", unit="Seconds", value=processing_time)
        metrics.add_metric(
            name="ElementsDetected",
            unit="Count",
            value=len(document_structure.elements),
        )

        # Evaluate confidence scores for structure analysis
        confidence_scores = {
            "structureExtraction": sum(elem.confidence for elem in document_structure.elements) / len(document_structure.elements) if document_structure.elements else 0.8,
            "headingLevels": 0.85,  # Mock confidence for heading analysis
            "readingOrder": 0.9,    # Mock confidence for reading order
        }
        
        # Check if review is needed
        review_assessment = None
        try:
            from src.review_service import get_review_service
            review_service = get_review_service()
            review_assessment = review_service.evaluate_confidence_scores(doc_id, confidence_scores)
            
            if review_assessment.get("needsReview"):
                logger.info(f"Document {doc_id} structure needs human review")
                
        except Exception as e:
            logger.warning(f"Review service evaluation failed: {e}")

        return StructureResult(
            doc_id=request.doc_id,
            status="completed",
            document_json_s3_key=document_json_s3_key,
            processing_time_seconds=processing_time,
            elements_count=len(document_structure.elements),
            confidence_scores=confidence_scores,
            review_assessment=review_assessment,
        ).dict()

    except StructureServiceError as e:
        logger.error(f"Structure service error: {str(e)}")
        metrics.add_metric(name="ServiceErrors", unit="Count", value=1)

        return StructureResult(
            doc_id=event.get("doc_id", "unknown"), status="failed", error_message=str(e)
        ).dict()

    except Exception as e:
        logger.error(f"Unexpected error in structure analysis: {str(e)}")
        metrics.add_metric(name="UnexpectedErrors", unit="Count", value=1)

        return StructureResult(
            doc_id=event.get("doc_id", "unknown"),
            status="failed",
            error_message=f"Unexpected error: {str(e)}",
        ).dict()

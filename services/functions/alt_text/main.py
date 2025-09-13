import time
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import the alt text repository for MongoDB storage
try:
    from services.shared.mongo.alt_text import get_alt_text_repository
except ImportError:
    # Fallback for lambda environment
    get_alt_text_repository = None

logger = Logger(service="pdf-alt-text")
tracer = Tracer(service="pdf-alt-text")
metrics = Metrics(namespace="PDF-Accessibility", service="pdf-alt-text")


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Generate alt text for figures using Bedrock Vision and Rekognition."""
    start_time = time.time()

    try:
        doc_id = event.get("docId") or event.get("doc_id")
        logger.info(f"Starting alt text generation for document {doc_id}")

        # Mock alt text generation - in real implementation:
        # 1. Load document structure from S3
        # 2. Extract figure locations and images
        # 3. Call Bedrock Vision for detailed descriptions
        # 4. Use Rekognition for object/text detection hints
        # 5. Generate contextual alt text based on document content

        figures_processed = 0  # Will be set based on actual processing
        processing_time = time.time() - start_time

        alt_text_s3_key = f"pdf-derivatives/{doc_id}/alt-text/alt.json"

        # Mock alt text generation with more realistic data
        figures_data = [
            {
                "figure_id": "figure-1",
                "alt_text": "Bar chart displaying accessibility compliance scores across different product areas. Web products show 94% compliance, mobile apps show 87% compliance, and desktop applications show 91% compliance.",
                "confidence": 0.92,
                "generation_method": "bedrock_vision",
                "context": {"page": 5, "section": "Compliance Overview"},
                "bounding_box": {"left": 0.1, "top": 0.3, "width": 0.8, "height": 0.4},
                "page_number": 5,
            },
            {
                "figure_id": "figure-2",
                "alt_text": "Line graph showing improvement in accessibility metrics over the past year, with scores rising from 78% in January to 94% in December.",
                "confidence": 0.87,
                "generation_method": "bedrock_vision",
                "context": {"page": 8, "section": "Yearly Progress"},
                "bounding_box": {
                    "left": 0.15,
                    "top": 0.2,
                    "width": 0.7,
                    "height": 0.35,
                },
                "page_number": 8,
            },
            {
                "figure_id": "figure-3",
                "alt_text": "Pie chart breaking down accessibility issues by category: Color contrast (45%), Missing alt text (30%), Keyboard navigation (15%), Focus indicators (10%).",
                "confidence": 0.94,
                "generation_method": "bedrock_vision",
                "context": {"page": 12, "section": "Issue Analysis"},
                "bounding_box": {"left": 0.2, "top": 0.25, "width": 0.6, "height": 0.5},
                "page_number": 12,
            },
        ]

        # Store alt text data in MongoDB if repository is available
        if get_alt_text_repository:
            try:
                alt_text_repository = get_alt_text_repository()
                alt_text_repository.create_document_alt_text(doc_id, figures_data)
                logger.info(f"Created alt text document in MongoDB for {doc_id}")
                figures_processed = len(figures_data)
            except Exception as e:
                logger.error(f"Failed to store alt text in MongoDB: {e}")
                # Continue with S3 fallback

        # Save to S3 (mocked)
        logger.info(f"Saved alt text data to {alt_text_s3_key}")

        # Evaluate confidence scores and route to A2I if needed
        confidence_scores = {
            "altTextGeneration": sum(fig["confidence"] for fig in figures_data) / len(figures_data) if figures_data else 0.8,
            "overall": 0.85  # Mock overall confidence
        }

        # Import and use review service
        try:
            from src.review_service import get_review_service
            review_service = get_review_service()

            # Evaluate if human review is needed
            review_assessment = review_service.evaluate_confidence_scores(doc_id, confidence_scores)

            if review_assessment.get("needsReview"):
                logger.info(f"Document {doc_id} alt-text needs human review (confidence: {confidence_scores['altTextGeneration']:.2f})")
                # In production, would trigger A2I workflow here

        except Exception as e:
            logger.warning(f"Review service evaluation failed: {e}")

        return {
            "doc_id": doc_id,
            "status": "completed",
            "alt_text_json_s3_key": alt_text_s3_key,
            "figures_processed": figures_processed,
            "processing_time_seconds": processing_time,
            "confidence_scores": confidence_scores,
            "review_assessment": review_assessment if 'review_assessment' in locals() else None,
        }

    except Exception as e:
        logger.error(f"Alt text generation failed: {str(e)}")
        return {
            "doc_id": event.get("docId", "unknown"),
            "status": "failed",
            "error_message": str(e),
        }

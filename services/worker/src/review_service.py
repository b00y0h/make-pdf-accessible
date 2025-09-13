"""
A2I Review Service - Routes low-confidence AI results for human review
"""

import json
import logging
from datetime import datetime
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for routing low-confidence AI results to Amazon A2I for human review."""

    def __init__(self):
        self.sagemaker = boto3.client("sagemaker")
        self.s3 = boto3.client("s3")
        self.confidence_threshold = 0.8  # Default threshold for auto-approval

    def evaluate_confidence_scores(
        self,
        doc_id: str,
        ai_confidence_scores: dict[str, float]
    ) -> dict[str, Any]:
        """
        Evaluate AI confidence scores and determine if human review is needed.

        Args:
            doc_id: Document identifier
            ai_confidence_scores: Dictionary of confidence scores by category

        Returns:
            Review assessment with recommendations
        """
        try:
            review_assessment = {
                "docId": doc_id,
                "needsReview": False,
                "reviewPriority": "low",
                "lowConfidenceAreas": [],
                "overallConfidence": 0.0,
                "reviewRecommendations": [],
                "assessedAt": datetime.utcnow(),
            }

            # Calculate overall confidence (weighted average)
            weights = {
                "structureExtraction": 0.25,
                "altTextGeneration": 0.20,
                "headingLevels": 0.15,
                "tableStructure": 0.15,
                "contentClassification": 0.10,
                "metadataExtraction": 0.10,
                "readingOrder": 0.05,
            }

            total_weighted_score = 0.0
            total_weight = 0.0
            low_confidence_areas = []

            for area, score in ai_confidence_scores.items():
                if area in weights:
                    weight = weights[area]
                    total_weighted_score += score * weight
                    total_weight += weight

                    # Check if below threshold
                    if score < self.confidence_threshold:
                        low_confidence_areas.append({
                            "area": area,
                            "score": score,
                            "threshold": self.confidence_threshold,
                            "weight": weight
                        })

            # Calculate overall confidence
            overall_confidence = total_weighted_score / total_weight if total_weight > 0 else 0.0
            review_assessment["overallConfidence"] = overall_confidence
            review_assessment["lowConfidenceAreas"] = low_confidence_areas

            # Determine if review is needed
            if overall_confidence < self.confidence_threshold or low_confidence_areas:
                review_assessment["needsReview"] = True

                # Determine priority based on how low the confidence is
                if overall_confidence < 0.6:
                    review_assessment["reviewPriority"] = "high"
                elif overall_confidence < 0.7:
                    review_assessment["reviewPriority"] = "medium"
                else:
                    review_assessment["reviewPriority"] = "low"

                # Generate recommendations
                review_assessment["reviewRecommendations"] = self._generate_review_recommendations(
                    low_confidence_areas
                )

            logger.info(
                f"Confidence assessment for {doc_id}: overall={overall_confidence:.3f}, "
                f"needs_review={review_assessment['needsReview']}, "
                f"priority={review_assessment['reviewPriority']}"
            )

            return review_assessment

        except Exception as e:
            logger.error(f"Failed to evaluate confidence scores for {doc_id}: {e}")
            raise

    def _generate_review_recommendations(
        self,
        low_confidence_areas: list[dict[str, Any]]
    ) -> list[str]:
        """Generate specific review recommendations based on low confidence areas."""

        recommendations = []

        for area_data in low_confidence_areas:
            area = area_data["area"]
            score = area_data["score"]

            if area == "structureExtraction":
                recommendations.append(
                    f"Review document structure detection (confidence: {score:.2f}) - "
                    "Check heading hierarchy and reading order"
                )
            elif area == "altTextGeneration":
                recommendations.append(
                    f"Review generated alt-text (confidence: {score:.2f}) - "
                    "Verify accuracy of image descriptions"
                )
            elif area == "headingLevels":
                recommendations.append(
                    f"Review heading level assignments (confidence: {score:.2f}) - "
                    "Verify logical heading hierarchy"
                )
            elif area == "tableStructure":
                recommendations.append(
                    f"Review table structure detection (confidence: {score:.2f}) - "
                    "Check table headers and cell relationships"
                )
            elif area == "contentClassification":
                recommendations.append(
                    f"Review content type classification (confidence: {score:.2f}) - "
                    "Verify identification of figures, tables, and text"
                )
            elif area == "metadataExtraction":
                recommendations.append(
                    f"Review extracted metadata (confidence: {score:.2f}) - "
                    "Verify title, author, and topic identification"
                )
            elif area == "readingOrder":
                recommendations.append(
                    f"Review reading order (confidence: {score:.2f}) - "
                    "Check logical flow of content"
                )

        return recommendations

    def create_a2i_review_job(
        self,
        doc_id: str,
        review_assessment: dict[str, Any],
        document_data: dict[str, Any],
        flow_definition_arn: str,
        review_team_arn: str
    ) -> str | None:
        """
        Create an Amazon A2I human review job for low-confidence results.

        Args:
            doc_id: Document identifier
            review_assessment: Confidence assessment results
            document_data: Document content and metadata for review
            flow_definition_arn: A2I flow definition ARN
            review_team_arn: A2I private workforce team ARN

        Returns:
            Human review job ARN or None if creation failed
        """
        try:
            # Prepare review data
            review_data = {
                "docId": doc_id,
                "reviewAssessment": review_assessment,
                "documentPreview": {
                    "title": document_data.get("metadata", {}).get("title", "Untitled Document"),
                    "pageCount": document_data.get("metadata", {}).get("pageCount", 0),
                    "author": document_data.get("metadata", {}).get("author"),
                    "subject": document_data.get("metadata", {}).get("subject"),
                },
                "reviewInstructions": self._generate_review_instructions(review_assessment),
                "priority": review_assessment.get("reviewPriority", "low"),
            }

            # Save review data to S3 for A2I access
            review_s3_key = f"review/{doc_id}/review_data_{int(datetime.utcnow().timestamp())}.json"

            bucket_name = "pdf-derivatives"  # Use appropriate bucket
            self.s3.put_object(
                Bucket=bucket_name,
                Key=review_s3_key,
                Body=json.dumps(review_data, default=str),
                ContentType="application/json"
            )

            # Create A2I human review job
            job_name = f"pdf-accessibility-review-{doc_id}-{int(datetime.utcnow().timestamp())}"

            response = self.sagemaker.start_human_loop(
                HumanLoopName=job_name,
                FlowDefinitionArn=flow_definition_arn,
                HumanLoopInput={
                    "InputContent": json.dumps(review_data)
                },
                DataAttributes={
                    "ContentClassifiers": ["FreeOfPersonallyIdentifiableInformation"]
                }
            )

            review_job_arn = response.get("HumanLoopArn")

            logger.info(
                f"Created A2I review job for document {doc_id}: {review_job_arn}"
            )

            return review_job_arn

        except Exception as e:
            logger.error(f"Failed to create A2I review job for {doc_id}: {e}")
            return None

    def _generate_review_instructions(
        self,
        review_assessment: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate specific instructions for human reviewers."""

        instructions = {
            "overview": "Please review the AI-generated accessibility improvements for this PDF document.",
            "priority": review_assessment.get("reviewPriority", "low"),
            "overallConfidence": review_assessment.get("overallConfidence", 0.0),
            "specificAreas": [],
            "tasks": [],
        }

        # Add specific review areas
        for area_data in review_assessment.get("lowConfidenceAreas", []):
            area = area_data["area"]
            score = area_data["score"]

            instructions["specificAreas"].append({
                "area": area,
                "confidence": score,
                "description": self._get_area_description(area)
            })

        # Add recommended tasks
        instructions["tasks"] = review_assessment.get("reviewRecommendations", [])

        return instructions

    def _get_area_description(self, area: str) -> str:
        """Get human-readable description for review areas."""

        descriptions = {
            "structureExtraction": "Document structure and organization",
            "altTextGeneration": "Alternative text for images and figures",
            "headingLevels": "Heading hierarchy and levels",
            "tableStructure": "Table structure and accessibility",
            "contentClassification": "Content type identification",
            "metadataExtraction": "Document metadata extraction",
            "readingOrder": "Logical reading order"
        }

        return descriptions.get(area, area.replace("_", " ").title())

    def check_review_status(self, review_job_arn: str) -> dict[str, Any]:
        """
        Check the status of an A2I human review job.

        Args:
            review_job_arn: ARN of the review job

        Returns:
            Review status information
        """
        try:
            # Extract job name from ARN
            job_name = review_job_arn.split("/")[-1]

            response = self.sagemaker.describe_human_loop(
                HumanLoopName=job_name
            )

            status_info = {
                "status": response.get("HumanLoopStatus"),
                "createdAt": response.get("CreationTime"),
                "failureReason": response.get("FailureReason"),
            }

            # Get output if completed
            if response.get("HumanLoopStatus") == "Completed":
                output_location = response.get("HumanLoopOutput", {}).get("OutputS3Uri")
                if output_location:
                    status_info["outputLocation"] = output_location
                    status_info["reviewResults"] = self._load_review_results(output_location)

            return status_info

        except Exception as e:
            logger.error(f"Failed to check review status for {review_job_arn}: {e}")
            return {"status": "unknown", "error": str(e)}

    def _load_review_results(self, output_s3_uri: str) -> dict[str, Any] | None:
        """Load review results from S3."""

        try:
            # Parse S3 URI to get bucket and key
            if output_s3_uri.startswith("s3://"):
                parts = output_s3_uri[5:].split("/", 1)
                bucket = parts[0]
                key = parts[1]

                response = self.s3.get_object(Bucket=bucket, Key=key)
                return json.loads(response["Body"].read())

        except Exception as e:
            logger.error(f"Failed to load review results from {output_s3_uri}: {e}")

        return None

    def process_review_completion(
        self,
        doc_id: str,
        review_results: dict[str, Any]
    ) -> bool:
        """
        Process completed human review and update document accordingly.

        Args:
            doc_id: Document identifier
            review_results: Results from human review

        Returns:
            True if processing successful
        """
        try:
            # Extract review decisions
            approved_changes = []
            rejected_changes = []

            for result in review_results.get("answerContent", {}).values():
                if result.get("approved", False):
                    approved_changes.append(result)
                else:
                    rejected_changes.append(result)

            logger.info(
                f"Review completed for {doc_id}: "
                f"{len(approved_changes)} approved, {len(rejected_changes)} rejected"
            )

            # Update document with review results
            # This would integrate with the document repository
            # to apply approved changes and log review decisions

            return True

        except Exception as e:
            logger.error(f"Failed to process review completion for {doc_id}: {e}")
            return False


# Global service instance
_review_service = None


def get_review_service() -> ReviewService:
    """Get global review service instance."""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service

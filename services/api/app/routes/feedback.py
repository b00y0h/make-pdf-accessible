"""
AI Learning Feedback API - Improves AI accuracy over time based on user corrections
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ..auth import User as UserInfo, get_current_user

router = APIRouter(prefix="/v1/feedback", tags=["ai_learning"])


class FeedbackItem(BaseModel):
    """Individual feedback item for AI improvement."""
    
    item_type: str = Field(..., description="Type of feedback: alt_text, structure, heading_level")
    item_id: str = Field(..., description="Unique identifier for the item")
    ai_prediction: str = Field(..., description="What the AI predicted/generated")
    user_correction: str = Field(..., description="User's correction/preferred value")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI's original confidence")
    feedback_quality: str = Field(..., description="User rating: excellent, good, fair, poor")


class DocumentFeedback(BaseModel):
    """Feedback for a complete document processing."""
    
    doc_id: str = Field(..., description="Document identifier")
    overall_rating: str = Field(..., description="Overall processing quality: excellent, good, fair, poor")
    feedback_items: List[FeedbackItem] = Field(default=[], description="Specific feedback items")
    general_comments: Optional[str] = Field(None, description="General feedback comments")
    processing_time_acceptable: bool = Field(True, description="Was processing time reasonable?")


class AILearningMetrics(BaseModel):
    """AI learning progress metrics."""
    
    total_feedback_items: int
    improvement_areas: Dict[str, Dict[str, Any]]
    confidence_trends: Dict[str, List[float]]
    user_satisfaction_trends: List[Dict[str, Any]]


@router.post("/document/{doc_id}")
async def submit_document_feedback(
    doc_id: str,
    feedback: DocumentFeedback,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Submit feedback for AI learning and improvement.
    
    This endpoint collects user feedback on AI processing quality to improve
    future predictions and accuracy over time.
    """
    try:
        # Validate document access
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()
        
        document = doc_repo.get_document(doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check ownership (user can only give feedback on their docs unless admin)
        if document.get("ownerId") != current_user.sub and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Store feedback for AI learning
        feedback_data = {
            "feedbackId": f"feedback_{doc_id}_{int(datetime.utcnow().timestamp())}",
            "docId": doc_id,
            "userId": current_user.sub,
            "submittedAt": datetime.utcnow(),
            "overallRating": feedback.overall_rating,
            "feedbackItems": [item.dict() for item in feedback.feedback_items],
            "generalComments": feedback.general_comments,
            "processingTimeAcceptable": feedback.processing_time_acceptable,
            "documentMetadata": {
                "title": document.get("metadata", {}).get("title"),
                "pageCount": document.get("metadata", {}).get("pageCount"),
                "fileSize": document.get("metadata", {}).get("originalSize"),
            }
        }
        
        # Store in feedback collection for ML training
        from services.shared.mongo.connection import get_database
        db = get_database()
        feedback_collection = db["ai_feedback"]
        result = feedback_collection.insert_one(feedback_data)
        
        # Analyze feedback patterns for immediate improvements
        improvement_suggestions = await _analyze_feedback_patterns(feedback.feedback_items, doc_id)
        
        # Update AI confidence calibration based on feedback
        await _update_confidence_calibration(feedback.feedback_items, current_user.sub)
        
        return {
            "success": True,
            "feedback_id": str(result.inserted_id),
            "message": "Feedback submitted successfully for AI learning",
            "immediate_improvements": improvement_suggestions,
            "ai_learning_impact": {
                "confidence_adjustments": len(feedback.feedback_items),
                "training_data_points": 1,
                "user_satisfaction_recorded": True,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/metrics", response_model=AILearningMetrics)
async def get_ai_learning_metrics(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get AI learning progress metrics.
    
    Shows how the AI is improving over time based on user feedback.
    Requires authentication to view metrics.
    """
    try:
        from services.shared.mongo.connection import get_database
        db = get_database()
        feedback_collection = db["ai_feedback"]
        
        # Calculate improvement metrics
        total_feedback = feedback_collection.count_documents({})
        
        # Analyze improvement areas
        improvement_pipeline = [
            {"$unwind": "$feedbackItems"},
            {"$group": {
                "_id": "$feedbackItems.item_type",
                "avg_confidence": {"$avg": "$feedbackItems.confidence_score"},
                "feedback_count": {"$sum": 1},
                "improvement_rate": {"$avg": {"$cond": [
                    {"$in": ["$overallRating", ["excellent", "good"]]}, 
                    1, 0
                ]}}
            }}
        ]
        
        improvement_areas = {}
        for result in feedback_collection.aggregate(improvement_pipeline):
            improvement_areas[result["_id"]] = {
                "average_confidence": result["avg_confidence"],
                "feedback_count": result["feedback_count"], 
                "improvement_rate": result["improvement_rate"],
                "trend": "improving" if result["improvement_rate"] > 0.7 else "needs_attention"
            }
        
        # Get satisfaction trends
        satisfaction_pipeline = [
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$submittedAt"}},
                "excellent": {"$sum": {"$cond": [{"$eq": ["$overallRating", "excellent"]}, 1, 0]}},
                "good": {"$sum": {"$cond": [{"$eq": ["$overallRating", "good"]}, 1, 0]}},
                "fair": {"$sum": {"$cond": [{"$eq": ["$overallRating", "fair"]}, 1, 0]}},
                "poor": {"$sum": {"$cond": [{"$eq": ["$overallRating", "poor"]}, 1, 0]}},
                "total": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        satisfaction_trends = []
        for result in feedback_collection.aggregate(satisfaction_pipeline):
            satisfaction_trends.append({
                "date": result["_id"],
                "ratings": {
                    "excellent": result["excellent"],
                    "good": result["good"], 
                    "fair": result["fair"],
                    "poor": result["poor"]
                },
                "total_feedback": result["total"],
                "satisfaction_score": (result["excellent"] * 4 + result["good"] * 3 + result["fair"] * 2 + result["poor"] * 1) / (result["total"] * 4) if result["total"] > 0 else 0
            })
        
        return AILearningMetrics(
            total_feedback_items=total_feedback,
            improvement_areas=improvement_areas,
            confidence_trends={},  # Would calculate confidence trends over time
            user_satisfaction_trends=satisfaction_trends
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get AI learning metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI learning metrics"
        )


async def _analyze_feedback_patterns(feedback_items: List[FeedbackItem], doc_id: str) -> List[str]:
    """Analyze feedback patterns to generate immediate improvement suggestions."""
    
    suggestions = []
    
    # Analyze alt-text feedback
    alt_text_feedback = [item for item in feedback_items if item.item_type == "alt_text"]
    if alt_text_feedback:
        low_confidence_count = len([item for item in alt_text_feedback if item.confidence_score < 0.7])
        if low_confidence_count > 0:
            suggestions.append(f"Consider lowering confidence threshold for alt-text generation ({low_confidence_count} items had low confidence)")
    
    # Analyze structure feedback
    structure_feedback = [item for item in feedback_items if item.item_type == "structure"]
    if structure_feedback:
        heading_issues = len([item for item in structure_feedback if "heading" in item.ai_prediction.lower()])
        if heading_issues > 0:
            suggestions.append(f"Heading detection needs improvement ({heading_issues} heading-related corrections)")
    
    return suggestions


async def _update_confidence_calibration(feedback_items: List[FeedbackItem], user_id: str):
    """Update AI confidence calibration based on user feedback."""
    
    try:
        from services.shared.mongo.connection import get_database
        db = get_database()
        calibration_collection = db["ai_calibration"]
        
        # Store calibration data for each feedback item
        for item in feedback_items:
            calibration_data = {
                "userId": user_id,
                "itemType": item.item_type,
                "originalConfidence": item.confidence_score,
                "userAcceptance": item.feedback_quality in ["excellent", "good"],
                "correctionMagnitude": len(item.user_correction) - len(item.ai_prediction) if item.ai_prediction else 0,
                "timestamp": datetime.utcnow(),
                "itemId": item.item_id,
            }
            
            calibration_collection.insert_one(calibration_data)
        
        # Calculate updated confidence thresholds (simplified)
        # In production, would use more sophisticated ML algorithms
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to update confidence calibration: {e}")


@router.get("/suggestions/{doc_id}")
async def get_improvement_suggestions(
    doc_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get AI improvement suggestions for a specific document.
    """
    try:
        from services.shared.mongo.connection import get_database
        db = get_database()
        
        # Get feedback history for this document
        feedback_collection = db["ai_feedback"]
        feedback_history = list(feedback_collection.find({"docId": doc_id}))
        
        suggestions = []
        
        if feedback_history:
            # Analyze patterns from feedback
            all_items = []
            for feedback_doc in feedback_history:
                all_items.extend(feedback_doc.get("feedbackItems", []))
            
            # Generate suggestions based on patterns
            suggestions = await _analyze_feedback_patterns(all_items, doc_id)
        else:
            suggestions = [
                "No feedback available yet for this document",
                "Submit feedback to help improve AI accuracy",
                "High-quality feedback helps train better models"
            ]
        
        return {
            "doc_id": doc_id,
            "suggestions": suggestions,
            "feedback_count": len(feedback_history),
            "last_feedback": feedback_history[-1]["submittedAt"] if feedback_history else None
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get improvement suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve improvement suggestions"
        )
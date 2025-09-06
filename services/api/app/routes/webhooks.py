import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from aws_lambda_powertools import Logger, Metrics, Tracer

from ..config import settings
from ..models import ErrorResponse
from ..services import AWSServiceError, webhook_service


logger = Logger()
tracer = Tracer()
metrics = Metrics()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Receive webhook callbacks",
    description="Endpoint for receiving HMAC-signed webhook callbacks from external services."
)
@tracer.capture_method
async def receive_webhook(request: Request) -> Dict[str, str]:
    """Receive and process webhook callbacks"""
    
    try:
        # Get raw body for signature verification
        raw_body = await request.body()
        body_str = raw_body.decode('utf-8')
        
        # Get signature from headers
        signature = request.headers.get('X-Hub-Signature-256') or request.headers.get('X-Signature-256')
        
        if not signature:
            logger.warning("Webhook received without signature")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing webhook signature"
            )
        
        # Verify signature if webhook secret is configured
        if settings.webhook_secret_key:
            is_valid = webhook_service.verify_webhook_signature(
                payload=body_str,
                signature=signature,
                secret=settings.webhook_secret_key
            )
            
            if not is_valid:
                logger.warning(
                    "Invalid webhook signature",
                    extra={
                        "signature": signature,
                        "remote_addr": request.client.host if request.client else "unknown"
                    }
                )
                metrics.add_metric(name="WebhookAuthFailures", unit="Count", value=1)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )
        else:
            logger.warning("Webhook secret not configured - signature verification skipped")
        
        # Parse JSON payload
        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Validate required fields
        required_fields = ['event_type', 'doc_id', 'status', 'timestamp']
        missing_fields = [field for field in required_fields if field not in payload]
        
        if missing_fields:
            logger.error(f"Missing required fields in webhook: {missing_fields}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {missing_fields}"
            )
        
        # Log webhook details
        logger.info(
            "Webhook received",
            extra={
                "event_type": payload.get('event_type'),
                "doc_id": payload.get('doc_id'),
                "status": payload.get('status'),
                "remote_addr": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get('User-Agent', 'unknown')
            }
        )
        
        # Process webhook
        success = await webhook_service.process_webhook(payload)
        
        if success:
            metrics.add_metric(name="WebhooksProcessed", unit="Count", value=1)
            metrics.add_metric(
                name=f"Webhooks{payload.get('event_type', 'Unknown').title()}", 
                unit="Count", 
                value=1
            )
            
            return {"status": "received", "message": "Webhook processed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process webhook"
            )
        
    except HTTPException:
        raise
    except AWSServiceError as e:
        logger.error(f"AWS service error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal service error"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error processing webhook"
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Webhook endpoint health check",
    description="Simple health check for webhook endpoint availability."
)
async def webhook_health() -> Dict[str, str]:
    """Webhook endpoint health check"""
    return {"status": "healthy", "service": "webhooks"}


@router.post(
    "/test",
    status_code=status.HTTP_200_OK,
    summary="Test webhook endpoint",
    description="Test endpoint for webhook functionality (development only)."
)
@tracer.capture_method
async def test_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Test webhook endpoint for development"""
    
    if settings.environment.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test endpoint not available in production"
        )
    
    logger.info("Test webhook received", extra={"payload": payload})
    
    # Echo back the payload with additional metadata
    return {
        "status": "test_received",
        "received_payload": payload,
        "timestamp": "2023-01-01T00:00:00Z",
        "environment": settings.environment
    }
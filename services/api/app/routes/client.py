"""
Client Integration API - For WordPress plugins and other client-side integrations
"""

import uuid
from datetime import datetime
from typing import Any, Optional

import boto3
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import User as UserInfo
from ..auth import get_current_user

router = APIRouter(prefix="/v1/client", tags=["client_integration"])


class ClientUploadRequest(BaseModel):
    """Request model for client-side PDF upload."""

    file_url: str = Field(..., description="URL where the PDF can be downloaded")
    filename: str = Field(..., description="Original filename")
    client_metadata: dict[str, Any] = Field(..., description="Client site metadata")
    callback_url: Optional[str] = Field(None, description="Webhook URL for completion notification")
    public_discovery: bool = Field(True, description="Allow public LLM discovery")


class ClientUploadResponse(BaseModel):
    """Response model for client upload."""

    accesspdf_id: str = Field(..., description="AccessPDF document ID for client tracking")
    status: str = Field(..., description="Initial processing status")
    estimated_completion: str = Field(..., description="Estimated completion time")
    discovery_endpoints: dict[str, str] = Field(..., description="Endpoints for LLM discovery")


@router.post("/upload", response_model=ClientUploadResponse)
async def upload_from_client(
    request: ClientUploadRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Process PDF upload from client websites (WordPress, etc.).

    This endpoint allows client sites to send PDFs for processing while
    keeping the original files on their own infrastructure.
    """
    try:
        # Generate unique AccessPDF ID
        accesspdf_id = str(uuid.uuid4())

        # Download PDF from client URL
        async with httpx.AsyncClient() as client:
            response = await client.get(request.file_url, timeout=30.0)
            response.raise_for_status()
            pdf_content = response.content

        # Validate PDF
        if not pdf_content.startswith(b'%PDF'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a valid PDF"
            )

        # Extract client domain for organization
        from urllib.parse import urlparse
        client_domain = urlparse(request.client_metadata.get("site_url", "")).hostname

        # Store PDF in your S3 with client metadata
        s3_client = boto3.client("s3")
        bucket_name = "pdf-originals"
        s3_key = f"clients/{client_domain}/{accesspdf_id}/{request.filename}"

        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=pdf_content,
            ContentType="application/pdf",
            Metadata={
                "client-domain": client_domain or "unknown",
                "client-site-name": str(request.client_metadata.get("site_name", "")),
                "original-url": request.file_url,
                "accesspdf-id": accesspdf_id,
                "public-discovery": str(request.public_discovery).lower(),
                "callback-url": request.callback_url or "",
                "upload-source": "client-integration",
            }
        )

        # Create document record with client metadata
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()

        document_data = {
            "docId": accesspdf_id,
            "ownerId": current_user.sub,
            "status": "pending",
            "filename": request.filename,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "metadata": {
                "originalSize": len(pdf_content),
                "clientDomain": client_domain,
                "clientSiteName": request.client_metadata.get("site_name"),
                "clientMetadata": request.client_metadata,
                "originalUrl": request.file_url,
                "callbackUrl": request.callback_url,
                "publicDiscovery": request.public_discovery,
                "uploadSource": "client-integration",
            }
        }

        doc_repo.create_document(document_data)

        # Trigger processing pipeline
        from services.worker.worker import process_pdf
        process_pdf.delay(
            doc_id=accesspdf_id,
            s3_key=s3_key,
            user_id=current_user.sub
        )

        # Prepare response with discovery endpoints
        discovery_endpoints = {
            "document_info": f"{request.client_metadata.get('site_url')}/wp-json/accesspdf/v1/documents/{accesspdf_id}",
            "search_api": f"/public/embeddings/search?doc_ids={accesspdf_id}",
            "direct_access": f"/public/embeddings/documents/{accesspdf_id}",
        }

        return ClientUploadResponse(
            accesspdf_id=accesspdf_id,
            status="processing",
            estimated_completion="2-5 minutes",
            discovery_endpoints=discovery_endpoints
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Client upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failed: {str(e)}"
        )


@router.get("/status/{accesspdf_id}")
async def get_client_document_status(
    accesspdf_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get processing status for client-uploaded document.

    Allows client sites to check processing progress and retrieve results.
    """
    try:
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()

        document = doc_repo.get_document(accesspdf_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check access (document owner or admin)
        if document.get("ownerId") != current_user.sub and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        response_data = {
            "accesspdf_id": accesspdf_id,
            "status": document.get("status"),
            "processing_progress": {
                "started_at": document.get("createdAt"),
                "updated_at": document.get("updatedAt"),
                "completed_at": document.get("completedAt"),
            },
            "accessibility_results": {
                "overall_score": document.get("scores", {}).get("overall"),
                "wcag_level": "AA" if document.get("scores", {}).get("overall", 0) >= 85 else "A",
                "pdf_ua_compliant": document.get("scores", {}).get("overall", 0) >= 90,
            },
            "available_formats": {},
        }

        # Add download URLs for completed documents
        if document.get("status") == "completed" and document.get("artifacts"):
            document.get("artifacts", {})
            response_data["available_formats"] = {
                "accessible_pdf": f"/v1/documents/{accesspdf_id}/downloads?document_type=pdf",
                "html": f"/v1/documents/{accesspdf_id}/downloads?document_type=html",
                "text": f"/v1/documents/{accesspdf_id}/downloads?document_type=text",
                "analysis_report": f"/v1/documents/{accesspdf_id}/downloads?document_type=analysis",
            }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get client document status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document status"
        )


@router.post("/webhook/notify/{accesspdf_id}")
async def send_client_webhook(
    accesspdf_id: str,
    webhook_data: dict[str, Any]
):
    """
    Send webhook notification to client when processing completes.

    This is called internally by the processing pipeline to notify
    client sites when their PDFs are ready.
    """
    try:
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()

        document = doc_repo.get_document(accesspdf_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        callback_url = document.get("metadata", {}).get("callbackUrl")
        if not callback_url:
            return {"message": "No callback URL configured, skipping notification"}

        # Prepare webhook payload
        webhook_payload = {
            "accesspdf_id": accesspdf_id,
            "status": webhook_data.get("status"),
            "accessibility_score": document.get("scores", {}).get("overall"),
            "completed_at": webhook_data.get("completed_at"),
            "available_formats": {
                "accessible_pdf": f"/v1/documents/{accesspdf_id}/downloads?document_type=pdf",
                "html": f"/v1/documents/{accesspdf_id}/downloads?document_type=html",
                "text": f"/v1/documents/{accesspdf_id}/downloads?document_type=text",
            },
            "discovery_metadata": {
                "search_endpoint": f"/public/embeddings/search?doc_ids={accesspdf_id}",
                "document_info": f"/public/embeddings/documents/{accesspdf_id}",
            }
        }

        # Send webhook to client
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    callback_url,
                    json=webhook_payload,
                    timeout=10.0,
                    headers={"User-Agent": "AccessPDF-Webhook/1.0"}
                )
                response.raise_for_status()

                return {
                    "success": True,
                    "webhook_sent": True,
                    "callback_url": callback_url,
                    "status_code": response.status_code
                }

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Webhook delivery failed: {e}")

                return {
                    "success": False,
                    "webhook_sent": False,
                    "error": str(e)
                }

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )

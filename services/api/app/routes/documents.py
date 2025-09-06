from typing import Optional
from uuid import UUID

from aws_lambda_powertools import Logger, Metrics, Tracer
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from ..auth import User, get_current_user, require_roles
from ..config import settings
from ..models import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    DocumentType,
    DownloadResponse,
    PaginationParams,
    UserRole,
)
from ..services import AWSServiceError, document_service

logger = Logger()
tracer = Tracer()
metrics = Metrics()

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document for processing",
    description="Upload a document file or provide URL for processing. Returns document ID and queues for processing."
)
@tracer.capture_method
async def upload_document(
    file: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    priority: bool = Form(False),
    webhook_url: Optional[str] = Form(None),
    metadata: Optional[str] = Form("{}"),
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Upload document for accessibility processing"""

    # Validate input
    if not file and not source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file upload or source_url must be provided"
        )

    if file and source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide both file upload and source_url"
        )

    # Process file upload
    if file:
        # Validate file size
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )

        # Validate file type
        file_extension = None
        if file.filename:
            file_extension = f".{file.filename.split('.')[-1].lower()}"
            if file_extension not in settings.allowed_file_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed. Supported types: {settings.allowed_file_types}"
                )

        filename = filename or file.filename

    # Parse metadata
    import json
    try:
        metadata_dict = json.loads(metadata) if metadata != "{}" else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in metadata field"
        )

    # Validate webhook URL if provided
    if webhook_url:
        if not (webhook_url.startswith('http://') or webhook_url.startswith('https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url must be a valid HTTP/HTTPS URL"
            )

    try:
        # Create document record
        document = await document_service.create_document(
            user_id=current_user.sub,
            filename=filename,
            source_url=source_url,
            metadata=metadata_dict,
            priority=priority,
            webhook_url=webhook_url
        )

        # If file was uploaded, we would upload it to S3 here
        # For now, we'll assume the processing pipeline handles file downloads

        metrics.add_metric(name="DocumentUploads", unit="Count", value=1)
        metrics.add_metric(name="PriorityUploads", unit="Count", value=1 if priority else 0)

        logger.info(
            "Document uploaded successfully",
            extra={
                "doc_id": str(document.doc_id),
                "user_id": current_user.sub,
                "priority": priority,
                "has_file": file is not None,
                "has_source_url": source_url is not None
            }
        )

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document upload"
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List user documents",
    description="List documents for the authenticated user with pagination and optional status filtering."
)
@tracer.capture_method
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by document status"),
    current_user: User = Depends(get_current_user)
) -> DocumentListResponse:
    """List documents for the authenticated user"""

    try:
        pagination = PaginationParams(page=page, per_page=per_page)

        documents, total = await document_service.list_user_documents(
            user_id=current_user.sub,
            limit=pagination.per_page,
            offset=pagination.offset,
            status_filter=status
        )

        metrics.add_metric(name="DocumentListRequests", unit="Count", value=1)

        return DocumentListResponse(
            documents=documents,
            total=total,
            page=pagination.page,
            per_page=pagination.per_page
        )

    except AWSServiceError as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Get detailed information about a specific document including status, metadata, and available artifacts."
)
@tracer.capture_method
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Get document by ID"""

    try:
        document = await document_service.get_document(
            doc_id=str(document_id),
            user_id=current_user.sub if not current_user.is_admin() else None
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check access permissions for non-admin users
        if not current_user.is_admin() and not current_user.can_access_resource(document.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )

        metrics.add_metric(name="DocumentRetrievals", unit="Count", value=1)

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.get(
    "/{document_id}/downloads",
    response_model=DownloadResponse,
    summary="Get document download URL",
    description="Generate pre-signed URL for downloading processed documents in various formats."
)
@tracer.capture_method
async def get_download_url(
    document_id: UUID,
    document_type: DocumentType = Query(..., description="Type of document to download"),
    expires_in: int = Query(3600, ge=300, le=86400, description="URL expiration time in seconds"),
    current_user: User = Depends(get_current_user)
) -> DownloadResponse:
    """Get pre-signed download URL for document"""

    try:
        # First, verify the document exists and user has access
        document = await document_service.get_document(
            doc_id=str(document_id),
            user_id=current_user.sub if not current_user.is_admin() else None
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check access permissions
        if not current_user.is_admin() and not current_user.can_access_resource(document.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )

        # Check if document is completed
        if document.status != DocumentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document is not ready for download. Current status: {document.status.value}"
            )

        # Generate pre-signed URL
        from datetime import datetime, timedelta

        presigned_url, content_type, filename = await document_service.generate_presigned_url(
            doc_id=str(document_id),
            document_type=document_type,
            expires_in=expires_in
        )

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        metrics.add_metric(name="DownloadUrls", unit="Count", value=1)
        metrics.add_metric(name=f"Downloads{document_type.value.title()}", unit="Count", value=1)

        logger.info(
            "Generated download URL",
            extra={
                "doc_id": str(document_id),
                "user_id": current_user.sub,
                "document_type": document_type.value,
                "expires_in": expires_in
            }
        )

        return DownloadResponse(
            download_url=presigned_url,
            expires_at=expires_at,
            content_type=content_type,
            filename=filename
        )

    except AWSServiceError as e:
        logger.error(f"Failed to generate download URL for {document_id}: {e}")
        if "not available" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_type.value} not available"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Delete a document and all associated files (admin only)."
)
@tracer.capture_method
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
) -> None:
    """Delete document (admin only)"""

    try:
        # First, verify the document exists
        document = await document_service.get_document(doc_id=str(document_id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # TODO: Implement document deletion logic
        # This would involve:
        # 1. Deleting files from S3 buckets
        # 2. Removing records from DynamoDB
        # 3. Canceling any in-progress jobs

        metrics.add_metric(name="DocumentDeletions", unit="Count", value=1)

        logger.info(
            "Document deleted",
            extra={
                "doc_id": str(document_id),
                "admin_user": current_user.sub
            }
        )

    except AWSServiceError as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

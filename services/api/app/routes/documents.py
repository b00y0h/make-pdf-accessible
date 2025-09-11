from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

from aws_lambda_powertools import Logger, Metrics, Tracer
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from services.shared.mongo.demo_sessions import get_demo_session_repository

from ..auth import User, get_current_user, get_dashboard_user, require_roles
from ..config import settings
from ..models import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    DocumentType,
    DownloadResponse,
    PaginationParams,
    PreSignedUploadRequest,
    PreSignedUploadResponse,
    UserRole,
)
from ..quota import QuotaType, quota_service
from ..security import VirusDetectedError, VirusScanError, security_service
from ..services import AWSServiceError, document_service

logger = Logger()
tracer = Tracer()
metrics = Metrics()

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload/presigned",
    response_model=PreSignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Get pre-signed upload URL",
    description="Generate a pre-signed S3 upload URL for direct client-side file upload with progress tracking.",
)
@tracer.capture_method
async def get_presigned_upload_url(
    request: PreSignedUploadRequest, 
    current_user: User = Depends(get_dashboard_user)
) -> PreSignedUploadResponse:
    """Get pre-signed S3 upload URL for direct client upload"""
    
    logger.info(f"Presigned upload request received", extra={"file_name": request.filename, "content_type": request.content_type, "file_size": request.file_size})
    logger.info(f"Current user: {current_user.sub}, org_id={current_user.org_id}")

    # Enforce quota limits
    if current_user.org_id:
        await quota_service.enforce_quota(
            current_user.org_id, QuotaType.PROCESSING_MONTHLY, 1
        )
        await quota_service.enforce_quota(
            current_user.org_id, QuotaType.STORAGE_TOTAL, request.file_size
        )

    # Validate file size
    if request.file_size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes",
        )

    # Enhanced file metadata validation
    security_service.validate_file_metadata(
        filename=request.filename,
        content_type=request.content_type,
        metadata={"size": request.file_size},
    )

    # Validate file extension
    filename_lower = request.filename.lower()
    file_extension = f".{filename_lower.split('.')[-1]}"
    if file_extension not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported types: {settings.allowed_file_types}",
        )

    # Security audit logging
    security_service.audit_security_event(
        "PRESIGNED_UPLOAD_REQUEST",
        current_user.sub,
        {
            "filename": request.filename,
            "file_size": request.file_size,
            "org_id": current_user.org_id,
        },
    )

    try:
        # Generate pre-signed upload URL
        upload_response = await document_service.generate_presigned_upload_url(
            user_id=current_user.sub,
            filename=request.filename,
            content_type=request.content_type,
            file_size=request.file_size,
        )

        metrics.add_metric(name="PreSignedUploadRequests", unit="Count", value=1)

        logger.info(
            "Pre-signed upload URL generated",
            extra={
                "doc_id": str(upload_response.doc_id),
                "user_id": current_user.sub,
                "file_name": request.filename,  # Changed from "filename" to avoid logging conflict
                "file_size": request.file_size,
            },
        )

        return upload_response

    except AWSServiceError as e:
        logger.error(f"Failed to generate pre-signed upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post(
    "/demo/upload",
    response_model=PreSignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Demo upload - Get pre-signed upload URL without authentication",
    description="Public demo endpoint for testing PDF upload without authentication.",
)
@tracer.capture_method
async def demo_presigned_upload(
    request_obj: PreSignedUploadRequest,
    request: Request,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
) -> PreSignedUploadResponse:
    """Demo endpoint - Get pre-signed S3 upload URL without authentication"""

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Get or create session
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID required in X-Session-ID header",
        )

    demo_repo = get_demo_session_repository()
    demo_repo.get_or_create_session(
        session_id=x_session_id,
        ip_address=client_ip,
        user_agent=user_agent or "unknown"
    )

    # Check rate limits
    allowed, reason = demo_repo.check_rate_limit(
        session_id=x_session_id,
        ip_address=client_ip,
        max_per_hour=5  # 5 uploads per hour for demo
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
        )

    # Validate file size (basic limits for demo)
    MAX_DEMO_FILE_SIZE = 10 * 1024 * 1024  # 10MB for demo
    if request_obj.file_size > MAX_DEMO_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Demo file size limit is 10MB",
        )

    # Validate file extension
    filename_lower = request_obj.filename.lower()
    if not filename_lower.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo only supports PDF files",
        )

    try:
        # Generate pre-signed upload URL using document_service
        # Use session ID as the user ID for tracking
        upload_response = await document_service.generate_presigned_upload_url(
            user_id=f"demo-{x_session_id}",
            filename=request_obj.filename,
            content_type=request_obj.content_type or "application/pdf",
            file_size=request_obj.file_size,
        )

        # Record the upload in the session
        demo_repo.record_upload(
            session_id=x_session_id,
            document_id=str(upload_response.doc_id)
        )

        logger.info(
            "Demo pre-signed upload URL generated",
            extra={
                "doc_id": str(upload_response.doc_id),
                "file_name": request_obj.filename,
                "file_size": request_obj.file_size,
                "session_id": x_session_id,
            },
        )

        return upload_response

    except AWSServiceError as e:
        logger.error(f"Failed to generate demo pre-signed upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post(
    "/demo/create",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Demo - Create document after successful upload",
    description="Demo endpoint to create document record without authentication.",
)
@tracer.capture_method
async def demo_create_document(
    request_obj: DocumentCreateRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> DocumentResponse:
    """Demo endpoint - Create document record after S3 upload without authentication"""

    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID required in X-Session-ID header",
        )

    try:
        # Create document record with session-specific user ID
        document = await document_service.create_document_from_upload(
            user_id=f"demo-{x_session_id}",
            doc_id=request_obj.doc_id,
            s3_key=request_obj.s3_key,
            filename=request_obj.filename,
            content_type=request_obj.content_type,
            file_size=request_obj.file_size,
            metadata={**(request_obj.metadata or {}), "session_id": x_session_id},
        )

        logger.info(
            "Demo document created successfully",
            extra={
                "doc_id": str(document.doc_id),
                "file_name": request_obj.filename,
            },
        )

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to create demo document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document",
        )


@router.post(
    "/create",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create document after successful upload",
    description="Create document record and enqueue for processing after successful S3 upload.",
)
@tracer.capture_method
async def create_document_after_upload(
    request: DocumentCreateRequest, current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Create document record and enqueue for processing after S3 upload"""

    # Validate webhook URL if provided
    if request.webhook_url:
        if not (
            request.webhook_url.startswith("http://")
            or request.webhook_url.startswith("https://")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url must be a valid HTTP/HTTPS URL",
            )

    try:
        # Validate processing request for security
        file_info = {
            "filename": request.s3_key.split("/")[-1],
            "s3_key": request.s3_key,
            "size": 0,  # Will be determined from S3 file
        }

        await security_service.validate_processing_request(
            current_user.sub, current_user.org_id or "default", file_info
        )

        # First validate the uploaded file for security
        try:
            # Create S3 client for validation
            import boto3
            from botocore.config import Config
            
            s3_config = Config(signature_version='s3v4')
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1',
                config=s3_config
            )
            
            await security_service.validate_s3_file(
                s3_client=s3_client,
                bucket=settings.s3_bucket,
                key=request.s3_key,
            )

            logger.info(
                "S3 file security validation passed",
                extra={
                    "doc_id": str(request.doc_id),
                    "s3_key": request.s3_key,
                    "user_id": current_user.sub,
                },
            )
        except VirusDetectedError as e:
            logger.error(
                f"Virus detected in S3 file: {e.virus_name}",
                extra={
                    "doc_id": str(request.doc_id),
                    "s3_key": request.s3_key,
                    "user_id": current_user.sub,
                    "virus_name": e.virus_name,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File rejected: virus detected ({e.virus_name})",
            )
        except VirusScanError as e:
            logger.error(
                f"S3 file security validation failed: {str(e)}",
                extra={
                    "doc_id": str(request.doc_id),
                    "s3_key": request.s3_key,
                    "user_id": current_user.sub,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File security validation failed. Please try again.",
            )

        # Create document record and enqueue for processing
        document = await document_service.create_document_from_upload(
            user_id=current_user.sub,
            doc_id=request.doc_id,
            s3_key=request.s3_key,
            filename=request.filename,
            content_type=request.content_type,
            file_size=request.file_size,
            metadata=request.metadata
        )

        # Increment quota usage after successful document creation
        if current_user.org_id:
            await quota_service.increment_usage(
                current_user.org_id, QuotaType.PROCESSING_MONTHLY, 1
            )
            # TODO: Get actual file size for storage quota
            # For now, we'll increment storage quota in the worker

        metrics.add_metric(name="DocumentsCreated", unit="Count", value=1)
        metrics.add_metric(
            name="PriorityDocuments", unit="Count", value=1 if request.priority else 0
        )

        logger.info(
            "Document created and enqueued for processing",
            extra={
                "doc_id": str(request.doc_id),
                "user_id": current_user.sub,
                "s3_key": request.s3_key,
                "source": request.source,
                "priority": request.priority,
            },
        )

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to create document: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uploaded file not found in S3",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document record",
        )


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document for processing",
    description="Upload a document file or provide URL for processing. Returns document ID and queues for processing.",
)
@tracer.capture_method
async def upload_document(
    file: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    priority: bool = Form(False),
    webhook_url: Optional[str] = Form(None),
    metadata: Optional[str] = Form("{}"),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload document for accessibility processing"""

    # Validate input
    if not file and not source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file upload or source_url must be provided",
        )

    if file and source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide both file upload and source_url",
        )

    # Process file upload
    if file:
        # Enforce quota limits before processing
        if current_user.org_id:
            await quota_service.enforce_quota(
                current_user.org_id, QuotaType.PROCESSING_MONTHLY, 1
            )
            # We'll check storage quota after reading the file

        # Perform comprehensive security validation
        try:
            file_content = await security_service.validate_upload_file(file)

            # Enforce storage quota after getting file size
            if current_user.org_id:
                await quota_service.enforce_quota(
                    current_user.org_id, QuotaType.STORAGE_TOTAL, len(file_content)
                )

            logger.info(
                "File security validation passed",
                extra={
                    "file_name": file.filename,
                    "size": len(file_content),
                    "user_id": current_user.sub,
                },
            )
        except VirusDetectedError as e:
            logger.error(
                f"Virus detected in uploaded file: {e.virus_name}",
                extra={
                    "file_name": file.filename,
                    "user_id": current_user.sub,
                    "virus_name": e.virus_name,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File rejected: virus detected ({e.virus_name})",
            )
        except VirusScanError as e:
            logger.error(
                f"Virus scanning failed: {str(e)}",
                extra={"file_name": file.filename, "user_id": current_user.sub},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File security validation failed. Please try again.",
            )

        filename = filename or file.filename

    # Parse metadata
    import json

    try:
        metadata_dict = json.loads(metadata) if metadata != "{}" else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in metadata field",
        )

    # Validate webhook URL if provided
    if webhook_url:
        if not (
            webhook_url.startswith("http://") or webhook_url.startswith("https://")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url must be a valid HTTP/HTTPS URL",
            )

    # Upload file to S3 if provided
    s3_key = None
    doc_id = None
    if file:
        import boto3
        from botocore.config import Config
        from uuid import uuid4
        from ..config import settings
        
        try:
            # Generate document ID and S3 key
            doc_id = uuid4()
            s3_key = f"uploads/{current_user.sub}/{doc_id}/{filename}"
            
            # Create S3 client 
            s3_config = Config(signature_version='s3v4')
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1',
                config=s3_config
            )
            
            # Upload file to S3
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=file.content_type or 'application/pdf'
            )
            
            logger.info(
                "File uploaded to S3 successfully",
                extra={
                    "s3_key": s3_key,
                    "file_name": filename,
                    "user_id": current_user.sub,
                    "doc_id": str(doc_id)
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to upload file to S3: {str(e)}",
                extra={
                    "file_name": filename,
                    "user_id": current_user.sub
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file. Please try again."
            )

    try:
        # Create document record
        if file and s3_key:
            # Use create_document_from_upload for files with S3 upload
            document = await document_service.create_document_from_upload(
                user_id=current_user.sub,
                doc_id=doc_id,
                s3_key=s3_key,
                filename=filename,
                content_type=file.content_type or 'application/pdf',
                file_size=len(file_content),
                metadata=metadata_dict
            )
        else:
            # Use regular create_document for URL-based processing
            document = await document_service.create_document(
                user_id=current_user.sub,
                filename=filename,
                source_url=source_url,
                metadata=metadata_dict,
                priority=priority,
                webhook_url=webhook_url,
            )

        # Increment quota usage after successful document creation
        if current_user.org_id:
            await quota_service.increment_usage(
                current_user.org_id, QuotaType.PROCESSING_MONTHLY, 1
            )
            if file:
                await quota_service.increment_usage(
                    current_user.org_id, QuotaType.STORAGE_TOTAL, len(file_content)
                )

        metrics.add_metric(name="DocumentUploads", unit="Count", value=1)
        metrics.add_metric(
            name="PriorityUploads", unit="Count", value=1 if priority else 0
        )

        logger.info(
            "Document uploaded successfully",
            extra={
                "doc_id": str(document.doc_id),
                "user_id": current_user.sub,
                "priority": priority,
                "has_file": file is not None,
                "has_source_url": source_url is not None,
            },
        )

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document upload",
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List user documents",
    description="List documents for the authenticated user with pagination and optional status filtering.",
)
@tracer.capture_method
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[DocumentStatus] = Query(
        None, description="Filter by document status"
    ),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """List documents for the authenticated user"""

    try:
        pagination = PaginationParams(page=page, per_page=per_page)

        documents, total = await document_service.list_user_documents(
            user_id=current_user.sub,
            limit=pagination.per_page,
            skip=pagination.offset,
            status_filter=status,
        )

        metrics.add_metric(name="DocumentListRequests", unit="Count", value=1)

        return DocumentListResponse(
            documents=documents,
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
        )

    except AWSServiceError as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        )


@router.get(
    "/demo/{document_id}",
    response_model=DocumentResponse,
    summary="Demo - Get document details without authentication",
    description="Demo endpoint to get document status without authentication.",
)
@tracer.capture_method
async def demo_get_document(
    document_id: UUID,
) -> DocumentResponse:
    """Demo endpoint - Get document by ID without authentication"""

    try:
        document = await document_service.get_document(
            doc_id=str(document_id),
            user_id="demo-user",
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        logger.info(
            "Demo document retrieved",
            extra={"doc_id": str(document_id)},
        )

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to get demo document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Get detailed information about a specific document including status, metadata, and available artifacts.",
)
@tracer.capture_method
async def get_document(
    document_id: UUID, current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Get document by ID"""

    try:
        document = await document_service.get_document(
            doc_id=str(document_id),
            user_id=current_user.sub if not current_user.is_admin() else None,
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Check access permissions for non-admin users
        if not current_user.is_admin() and not current_user.can_access_resource(
            document.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document",
            )

        metrics.add_metric(name="DocumentRetrievals", unit="Count", value=1)

        return document

    except AWSServiceError as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        )


# Commented out - using demo.py endpoint instead
# The demo downloads endpoint is now in demo.py
# @router.get(
#     "/demo/{document_id}/downloads",
#     response_model=DownloadResponse,
#     summary="Demo - Get document download URL without authentication",
#     description="Demo endpoint to download processed documents without authentication. Accessible PDF requires login.",
# )
# @tracer.capture_method
# async def demo_get_download_url_DISABLED(
#     document_id: UUID,
#     document_type: DocumentType = Query(
#         ..., description="Type of document to download"
#     ),
#     x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
#     expires_in: int = Query(
#         3600, ge=300, le=86400, description="URL expiration time in seconds"
#     ),
# ) -> DownloadResponse:
#     """Demo endpoint - Get pre-signed download URL without authentication"""
# 
#     if not x_session_id:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Session ID required in X-Session-ID header",
#         )
# 
#     # Restrict accessible PDF to authenticated users only
#     if document_type == DocumentType.ACCESSIBLE_PDF:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Please sign up or log in to download the accessible PDF. Other formats are available without login.",
#             headers={"X-Requires-Auth": "true"}
#         )
# 
#     # Allow preview and other formats (HTML, text, CSV, analysis)
#     allowed_demo_types = [
#         DocumentType.PREVIEW,  # PNG preview of first page
#         DocumentType.HTML,      # HTML version
#         DocumentType.TEXT,      # Plain text
#         DocumentType.CSV,       # Data extract
#         DocumentType.ANALYSIS,  # AI analysis report
#     ]
# 
#     if document_type not in allowed_demo_types:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail=f"Document type '{document_type.value}' requires authentication",
#         )
# 
#     try:
#         # Verify the document exists for this session
#         demo_repo = get_demo_session_repository()
#         session_docs = demo_repo.get_session_documents(x_session_id)
# 
#         if str(document_id) not in session_docs:
#             # Try with demo-user prefix for backwards compatibility
#             document = await document_service.get_document(
#                 doc_id=str(document_id),
#                 user_id=f"demo-{x_session_id}",
#             )
# 
#             if not document:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail="Document not found or not associated with this session"
#                 )
#         else:
#             document = await document_service.get_document(
#                 doc_id=str(document_id),
#                 user_id=f"demo-{x_session_id}",
#             )
# 
#         # Check if document is completed
#         if document.status != DocumentStatus.COMPLETED:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail=f"Document is not ready for download. Current status: {document.status.value}",
#             )
# 
#         # Generate pre-signed URL
#         from datetime import datetime, timedelta
# 
#         presigned_url, content_type, filename = (
#             await document_service.generate_presigned_url(
#                 doc_id=str(document_id),
#                 document_type=document_type,
#                 expires_in=expires_in,
#             )
#         )
# 
#         expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
# 
#         logger.info(
#             "Demo download URL generated",
#             extra={
#                 "doc_id": str(document_id),
#                 "document_type": document_type.value,
#                 "session_id": x_session_id,
#             },
#         )
# 
#         return DownloadResponse(
#             download_url=presigned_url,
#             expires_at=expires_at,
#             content_type=content_type,
#             filename=filename,
#         )
# 
#     except AWSServiceError as e:
#         logger.error(f"Failed to generate demo download URL: {e}")
#         if "not available" in str(e):
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Document {document_type.value} not available",
#             )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to generate download URL",
#         )


@router.get(
    "/demo/{doc_id}/downloads",
    summary="Demo - Get document download URL",
    description="Get download URL for demo document artifacts",
)
async def demo_get_download_url(
    doc_id: str,
    document_type: str = Query(..., description="Type of document to download"),
    request: Request = None
):
    """Get download URL for demo document artifacts"""
    logging.info(f"Demo download URL requested for {doc_id}, type: {document_type}")
    
    # Import boto3 for S3 operations
    import boto3
    from botocore.config import Config
    
    # S3 key mappings for different document types
    s3_keys = {
        "accessible_pdf": f"accessible/{doc_id}/accessible.pdf",
        "preview": f"previews/{doc_id}/preview.png",
        "html": f"exports/{doc_id}/document.html",
        "text": f"exports/{doc_id}/document.txt",
        "csv": f"exports/{doc_id}/data.csv",
        "analysis": f"reports/{doc_id}/analysis.json"
    }
    
    if document_type not in s3_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type: {document_type}"
        )
    
    # For accessible_pdf, require authentication
    if document_type == "accessible_pdf":
        # Check for authenticated user header from the frontend
        auth_header = request.headers.get("X-Authenticated-User") if request else None
        if not auth_header:
            raise HTTPException(
                status_code=403,
                detail="Sign in required to download accessible PDF"
            )
    
    try:
        # Create S3 client with browser-accessible endpoint
        s3_config = Config(signature_version='s3v4')
        s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',  # Browser-accessible endpoint
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1',
            config=s3_config
        )
        
        # Generate pre-signed URL for download
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': 'pdf-accessibility-dev-pdf-originals',
                'Key': s3_keys[document_type],
                'ResponseContentDisposition': f'attachment; filename="{document_type}_{doc_id[-8:]}.{s3_keys[document_type].split(".")[-1]}"'
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            "download_url": download_url,
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "document_type": document_type
        }
        
    except Exception as e:
        logging.error(f"Failed to generate download URL: {e}")
        # Fallback to direct URL if pre-signed URL generation fails
        base_url = "http://localhost:4566/pdf-accessibility-dev-pdf-originals"
        return {
            "download_url": f"{base_url}/{s3_keys[document_type]}",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "document_type": document_type
        }


@router.get(
    "/{document_id}/downloads",
    response_model=DownloadResponse,
    summary="Get document download URL",
    description="Generate pre-signed URL for downloading processed documents in various formats.",
)
@tracer.capture_method
async def get_download_url(
    document_id: UUID,
    document_type: DocumentType = Query(
        ..., description="Type of document to download"
    ),
    expires_in: int = Query(
        3600, ge=300, le=86400, description="URL expiration time in seconds"
    ),
    current_user: User = Depends(get_current_user),
) -> DownloadResponse:
    """Get pre-signed download URL for document"""

    try:
        # First, verify the document exists and user has access
        document = await document_service.get_document(
            doc_id=str(document_id),
            user_id=current_user.sub if not current_user.is_admin() else None,
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Check access permissions
        if not current_user.is_admin() and not current_user.can_access_resource(
            document.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document",
            )

        # Check if document is ready for download based on document type
        # Original PDF is always available, processed versions require completion
        if document_type != DocumentType.PDF and document.status != DocumentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document is not ready for download. Current status: {document.status.value}",
            )

        # Generate pre-signed URL
        from datetime import datetime, timedelta

        presigned_url, content_type, filename = (
            await document_service.generate_presigned_url(
                doc_id=str(document_id),
                document_type=document_type,
                expires_in=expires_in,
            )
        )

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        metrics.add_metric(name="DownloadUrls", unit="Count", value=1)
        metrics.add_metric(
            name=f"Downloads{document_type.value.title()}", unit="Count", value=1
        )

        logger.info(
            "Generated download URL",
            extra={
                "doc_id": str(document_id),
                "user_id": current_user.sub,
                "document_type": document_type.value,
                "expires_in": expires_in,
            },
        )

        return DownloadResponse(
            download_url=presigned_url,
            expires_at=expires_at,
            content_type=content_type,
            filename=filename,
        )

    except AWSServiceError as e:
        logger.error(f"Failed to generate download URL for {document_id}: {e}")
        if "not available" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_type.value} not available",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document and all artifacts",
    description="Permanently delete a document and all associated artifacts. Requires confirmation parameter.",
)
@tracer.capture_method
async def delete_document(
    document_id: UUID,
    confirm_deletion: bool = Query(False, description="Must be true to confirm deletion"),
    current_user: User = Depends(get_dashboard_user)
) -> Dict[str, Any]:
    """Delete document and all artifacts with confirmation"""

    if not confirm_deletion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be confirmed by setting confirm_deletion=true"
        )

    try:
        # First, verify the document exists
        document = await document_service.get_document(doc_id=str(document_id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Get document to verify it exists and get artifact info
        document = await document_service.get_document(doc_id=str(document_id))
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check ownership (user can only delete own docs unless admin)
        if document.user_id != current_user.sub and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own documents"
            )
        
        # Delete all S3 artifacts
        import boto3
        s3_client = boto3.client("s3")
        buckets_to_check = ["pdf-accessibility-dev-pdf-originals", "pdf-derivatives", "pdf-temp", "pdf-reports"]
        
        deleted_objects = []
        doc_id = str(document_id)
        
        # Delete from all possible S3 locations
        common_prefixes = [
            f"uploads/{current_user.sub}/{doc_id}/",
            f"pdf-derivatives/{doc_id}/",
            f"exports/{doc_id}/",
            f"reports/{doc_id}/", 
            f"previews/{doc_id}/",
            f"accessible/{doc_id}/",
            f"corpus/{doc_id}/",
            f"embeddings/{doc_id}/",
        ]
        
        for bucket in buckets_to_check:
            try:
                for prefix in common_prefixes:
                    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
                    
                    if 'Contents' in response:
                        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                        
                        if objects_to_delete:
                            delete_response = s3_client.delete_objects(
                                Bucket=bucket,
                                Delete={'Objects': objects_to_delete}
                            )
                            deleted_objects.extend(delete_response.get('Deleted', []))
                            
            except Exception as e:
                logger.warning(f"Could not delete from bucket {bucket}: {e}")
        
        # Delete from MongoDB
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()
        mongo_deleted = doc_repo.delete_by_id(doc_id)
        
        # Delete alt-text data
        try:
            from services.shared.mongo.alt_text import get_alt_text_repository
            alt_text_repo = get_alt_text_repository()
            alt_text_repo.delete_document_alt_text(doc_id)
        except Exception as e:
            logger.warning(f"Could not delete alt-text data: {e}")

        metrics.add_metric(name="DocumentDeletions", unit="Count", value=1)
        metrics.add_metric(name="ArtifactsDeleted", unit="Count", value=len(deleted_objects))

        logger.info(
            "Document and artifacts deleted successfully",
            extra={
                "doc_id": str(document_id), 
                "admin_user": current_user.sub,
                "deleted_objects": len(deleted_objects)
            },
        )
        
        return {
            "message": "Document and all artifacts deleted successfully",
            "doc_id": str(document_id),
            "deletion_summary": {
                "s3_objects_deleted": len(deleted_objects),
                "mongodb_record_deleted": mongo_deleted,
                "alt_text_deleted": True,
                "total_artifacts_removed": len(deleted_objects),
            }
        }

    except AWSServiceError as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.post(
    "/{document_id}/generate-preview",
    response_model=dict[str, str],
    summary="Generate preview for document",
    description="Generate a PNG preview of the first page of a PDF document",
)
@tracer.capture_method
async def generate_document_preview(
    document_id: UUID,
    page_number: int = 1,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Generate a preview image for a PDF document"""

    try:
        from ..services import preview_service
        from services.shared.mongo.documents import get_document_repository
        import boto3

        # Get document metadata from MongoDB
        doc_repo = get_document_repository()
        document = doc_repo.get_document(
            doc_id=str(document_id),
            user_id=current_user.id
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Generate preview from S3 PDF
        original_s3_key = f"original/{document_id}.pdf"
        preview_s3_key = preview_service.generate_preview_from_s3(
            s3_key=original_s3_key,
            page_number=page_number,
            dpi=150,
            format="PNG"
        )

        # Generate presigned URL for preview
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url,
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        preview_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": preview_s3_key},
            ExpiresIn=3600,
        )

        # Update document with preview info
        doc_repo.update_document(
            doc_id=str(document_id),
            user_id=current_user.id,
            update_data={
                "preview_url": preview_url,
                "preview_s3_key": preview_s3_key,
                "preview_generated_at": datetime.utcnow()
            }
        )

        logger.info(f"Generated preview for document {document_id}")

        return {
            "preview_url": preview_url,
            "s3_key": preview_s3_key,
            "page_number": str(page_number)
        }

    except Exception as e:
        logger.error(f"Failed to generate preview for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview"
        )


@router.get(
    "/processing-steps",
    summary="Get processing pipeline steps",
    description="Get the list of processing steps for the PDF accessibility pipeline",
)
async def get_processing_steps(current_user: User = Depends(get_current_user)):
    """Get the actual processing pipeline steps for authenticated users"""
    
    return {
        "steps": [
            {
                "step": 0,
                "title": "Document Upload",
                "description": "Securely uploading your PDF document...",
                "estimated_duration": "5-10 seconds"
            },
            {
                "step": 1,
                "title": "File Validation",
                "description": "Validating file format and security...",
                "estimated_duration": "2-5 seconds"
            },
            {
                "step": 2,
                "title": "Content Extraction",
                "description": "Extracting text, images, and structural elements...",
                "estimated_duration": "10-30 seconds"
            },
            {
                "step": 3,
                "title": "OCR Processing",
                "description": "Running OCR on images and scanned content...",
                "estimated_duration": "20-60 seconds"
            },
            {
                "step": 4,
                "title": "Structure Analysis",
                "description": "Analyzing document structure and layout...",
                "estimated_duration": "15-30 seconds"
            },
            {
                "step": 5,
                "title": "AI Content Tagging",
                "description": "Adding semantic tags using AI analysis...",
                "estimated_duration": "30-90 seconds"
            },
            {
                "step": 6,
                "title": "Alt Text Generation",
                "description": "Creating descriptive text for images with AI...",
                "estimated_duration": "20-60 seconds"
            },
            {
                "step": 7,
                "title": "Color & Contrast",
                "description": "Optimizing colors for accessibility compliance...",
                "estimated_duration": "10-20 seconds"
            },
            {
                "step": 8,
                "title": "Accessibility Validation",
                "description": "Verifying WCAG 2.1 AA compliance...",
                "estimated_duration": "15-30 seconds"
            },
            {
                "step": 9,
                "title": "Export Generation",
                "description": "Creating accessible formats (HTML, CSV, Text)...",
                "estimated_duration": "20-45 seconds"
            },
            {
                "step": 10,
                "title": "Processing Complete",
                "description": "Your accessible document is ready for download!",
                "estimated_duration": "Complete"
            }
        ],
        "total_estimated_time": "2-6 minutes",
        "pipeline_version": "v2.1.0"
    }

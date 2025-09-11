from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator


class DocumentStatus(str, Enum):
    """Document processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"
    NOTIFICATION_FAILED = "notification_failed"


class DocumentType(str, Enum):
    """Supported document types"""

    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV_ZIP = "csvzip"


class UserRole(str, Enum):
    """User roles for authorization"""

    VIEWER = "viewer"
    ADMIN = "admin"


class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""

    source_url: Optional[str] = Field(None, description="URL to download document from")
    filename: Optional[str] = Field(None, description="Original filename")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    priority: bool = Field(False, description="High priority processing")
    webhook_url: Optional[str] = Field(None, description="Callback webhook URL")

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v):
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must be a valid HTTP/HTTPS URL")
        return v


class DocumentResponse(BaseModel):
    """Response model for document operations"""

    doc_id: UUID = Field(..., description="Document ID")
    status: DocumentStatus = Field(..., description="Processing status")
    filename: Optional[str] = Field(None, description="Original filename")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    user_id: str = Field(..., description="User who uploaded the document")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    artifacts: Dict[str, str] = Field(
        default_factory=dict, description="Available artifacts"
    )

    @field_serializer("doc_id")
    def serialize_doc_id(self, value: UUID) -> str:
        return str(value)

    @field_serializer("created_at", "updated_at", "completed_at")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class DocumentListResponse(BaseModel):
    """Response model for document list"""

    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class DownloadRequest(BaseModel):
    """Request model for document downloads"""

    document_type: DocumentType = Field(..., description="Type of document to download")
    expires_in: int = Field(
        3600, ge=300, le=86400, description="URL expiration time in seconds"
    )


class DownloadResponse(BaseModel):
    """Response model for download URLs"""

    download_url: str = Field(..., description="Pre-signed download URL")
    expires_at: datetime = Field(..., description="URL expiration timestamp")
    content_type: str = Field(..., description="MIME content type")
    filename: str = Field(..., description="Suggested filename")

    @field_serializer("expires_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class WebhookPayload(BaseModel):
    """Webhook payload model"""

    event_type: str = Field(..., description="Type of webhook event")
    doc_id: UUID = Field(..., description="Document ID")
    status: DocumentStatus = Field(..., description="Document status")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event data"
    )

    @field_serializer("doc_id")
    def serialize_doc_id(self, value: UUID) -> str:
        return str(value)

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class WebhookRequest(BaseModel):
    """Webhook request model"""

    signature: str = Field(..., description="HMAC signature")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")


class ReportsSummaryResponse(BaseModel):
    """Response model for reports summary with enhanced MongoDB aggregations"""

    total_documents: int = Field(..., description="Total documents processed")
    completed_documents: int = Field(
        ..., description="Successfully completed documents"
    )
    processing_documents: int = Field(
        ..., description="Documents currently being processed"
    )
    failed_documents: int = Field(..., description="Documents that failed processing")
    pending_documents: int = Field(..., description="Documents pending processing")
    completion_rate: float = Field(..., description="Success rate percentage (0-100)")
    avg_processing_time_hours: float = Field(
        ..., description="Average processing time in hours"
    )
    weekly_stats: List[Dict[str, Any]] = Field(
        ..., description="Weekly statistics with aggregated data"
    )


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request ID for tracing")

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Dependency status"
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class PaginationParams(BaseModel):
    """Pagination parameters"""

    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PreSignedUploadRequest(BaseModel):
    """Request model for pre-signed upload URL"""

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    file_size: int = Field(..., ge=1, description="File size in bytes")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError("filename is required")
        # Extract file extension and validate
        parts = v.split(".")
        if len(parts) < 2:
            raise ValueError("filename must have an extension")
        return v.strip()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/html",
        ]
        if v not in allowed_types:
            raise ValueError(f"content_type must be one of: {allowed_types}")
        return v


class PreSignedUploadResponse(BaseModel):
    """Response model for pre-signed upload URL"""

    upload_url: str = Field(..., description="Pre-signed S3 upload URL")
    fields: Dict[str, str] = Field(..., description="Required form fields for upload")
    expires_at: datetime = Field(..., description="URL expiration timestamp")
    s3_key: str = Field(..., description="S3 key for the uploaded file")
    doc_id: UUID = Field(..., description="Generated document ID")

    @field_serializer("expires_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("doc_id")
    def serialize_doc_id(self, value: UUID) -> str:
        return str(value)


class DocumentCreateRequest(BaseModel):
    """Request model for creating document after upload"""

    doc_id: UUID = Field(..., description="Document ID from pre-signed upload")
    s3_key: str = Field(..., description="S3 key of uploaded file")
    source: str = Field("upload", description="Source of document")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    priority: bool = Field(False, description="High priority processing")
    webhook_url: Optional[str] = Field(None, description="Callback webhook URL")

    @field_serializer("doc_id")
    def serialize_doc_id(self, value: UUID) -> str:
        return str(value)

    @field_validator("source")
    @classmethod
    def validate_source(cls, v):
        allowed_sources = ["upload", "url", "api"]
        if v not in allowed_sources:
            raise ValueError(f"source must be one of: {allowed_sources}")
        return v


class AltTextStatus(str, Enum):
    """Alt text review status"""

    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"


class AltTextVersion(BaseModel):
    """Single version of alt text"""

    version: int = Field(..., description="Version number")
    text: str = Field(..., description="Alt text content")
    editor_id: str = Field(..., description="User ID who made this edit")
    editor_name: Optional[str] = Field(None, description="Display name of editor")
    timestamp: datetime = Field(..., description="When this version was created")
    comment: Optional[str] = Field(None, description="Editor comment for this change")
    is_ai_generated: bool = Field(False, description="Whether this was AI generated")
    confidence: Optional[float] = Field(
        None, ge=0, le=1, description="AI confidence score"
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class AltTextFigure(BaseModel):
    """Figure with alt text and history"""

    figure_id: str = Field(..., description="Unique figure identifier")
    status: AltTextStatus = Field(AltTextStatus.PENDING, description="Review status")
    current_version: int = Field(1, description="Current active version")
    ai_text: Optional[str] = Field(None, description="Original AI generated text")
    approved_text: Optional[str] = Field(None, description="Current approved text")
    confidence: Optional[float] = Field(
        None, ge=0, le=1, description="AI confidence score"
    )
    generation_method: Optional[str] = Field(
        None, description="How alt text was generated"
    )
    versions: List[AltTextVersion] = Field(
        default_factory=list, description="Version history"
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Figure context metadata"
    )
    bounding_box: Optional[Dict[str, float]] = Field(
        None, description="Figure location"
    )
    page_number: Optional[int] = Field(
        None, description="Page number where figure appears"
    )

    @field_validator("versions")
    @classmethod
    def validate_versions(cls, v):
        if not v:
            return v
        # Ensure versions are sorted by version number
        return sorted(v, key=lambda x: x.version)


class AltTextDocumentResponse(BaseModel):
    """Alt text data for a document"""

    doc_id: UUID = Field(..., description="Document ID")
    figures: List[AltTextFigure] = Field(
        default_factory=list, description="Figures with alt text"
    )
    total_figures: int = Field(0, description="Total number of figures")
    pending_review: int = Field(0, description="Figures needing review")
    approved: int = Field(0, description="Figures approved")
    edited: int = Field(0, description="Figures with edits")
    last_updated: datetime = Field(..., description="Last update timestamp")

    @field_serializer("doc_id")
    def serialize_doc_id(self, value: UUID) -> str:
        return str(value)

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class AltTextEditRequest(BaseModel):
    """Request to edit alt text"""

    figure_id: str = Field(..., description="Figure ID to edit")
    text: str = Field(..., min_length=1, max_length=500, description="New alt text")
    comment: Optional[str] = Field(
        None, max_length=200, description="Comment about the change"
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Alt text cannot be empty")
        return v.strip()


class AltTextEditResponse(BaseModel):
    """Response for alt text edit"""

    figure_id: str = Field(..., description="Figure ID that was edited")
    version: int = Field(..., description="New version number")
    text: str = Field(..., description="Updated alt text")
    status: AltTextStatus = Field(..., description="New status")
    timestamp: datetime = Field(..., description="Edit timestamp")

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class AltTextBulkStatusRequest(BaseModel):
    """Request to update status for multiple figures"""

    figure_ids: List[str] = Field(..., min_items=1, description="Figure IDs to update")
    status: AltTextStatus = Field(..., description="New status for all figures")
    comment: Optional[str] = Field(
        None, max_length=200, description="Comment for bulk action"
    )

    @field_validator("figure_ids")
    @classmethod
    def validate_figure_ids(cls, v):
        if not v:
            raise ValueError("At least one figure ID is required")
        return list(set(v))  # Remove duplicates


class AltTextHistoryResponse(BaseModel):
    """History for a specific figure"""

    figure_id: str = Field(..., description="Figure ID")
    versions: List[AltTextVersion] = Field(
        ..., description="All versions of this figure"
    )
    current_version: int = Field(..., description="Current active version")
    status: AltTextStatus = Field(..., description="Current status")


# Admin models
class UserSummary(BaseModel):
    """User summary for admin interface"""

    id: str = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="User display name")
    email: str = Field(..., description="User email address")
    role: Optional[str] = Field(None, description="User role")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )
    document_count: int = Field(default=0, description="Total documents")
    documents_completed: int = Field(default=0, description="Completed documents")
    documents_processing: int = Field(default=0, description="Processing documents")
    documents_failed: int = Field(default=0, description="Failed documents")

    @field_serializer("created_at", "updated_at", "last_activity")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class UserListParams(BaseModel):
    """Parameters for user list query"""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    search: Optional[str] = Field(None, description="Search term")
    role: Optional[str] = Field(None, description="Role filter")


class UserListResponse(BaseModel):
    """Response for user list"""

    users: List[UserSummary] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    total_pages: int = Field(..., description="Total number of pages")
    current_page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")

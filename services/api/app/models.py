from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


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
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    priority: bool = Field(False, description="High priority processing")
    webhook_url: Optional[str] = Field(None, description="Callback webhook URL")
    
    @validator('source_url')
    def validate_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('source_url must be a valid HTTP/HTTPS URL')
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
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="Available artifacts")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class DocumentListResponse(BaseModel):
    """Response model for document list"""
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class DownloadRequest(BaseModel):
    """Request model for document downloads"""
    document_type: DocumentType = Field(..., description="Type of document to download")
    expires_in: int = Field(3600, ge=300, le=86400, description="URL expiration time in seconds")


class DownloadResponse(BaseModel):
    """Response model for download URLs"""
    download_url: str = Field(..., description="Pre-signed download URL")
    expires_at: datetime = Field(..., description="URL expiration timestamp")
    content_type: str = Field(..., description="MIME content type")
    filename: str = Field(..., description="Suggested filename")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookPayload(BaseModel):
    """Webhook payload model"""
    event_type: str = Field(..., description="Type of webhook event")
    doc_id: UUID = Field(..., description="Document ID")
    status: DocumentStatus = Field(..., description="Document status")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class WebhookRequest(BaseModel):
    """Webhook request model"""
    signature: str = Field(..., description="HMAC signature")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")


class ReportsSummaryResponse(BaseModel):
    """Response model for reports summary"""
    total_documents: int = Field(..., description="Total documents processed")
    documents_by_status: Dict[str, int] = Field(..., description="Documents grouped by status")
    weekly_stats: List[Dict[str, Any]] = Field(..., description="Weekly statistics")
    average_processing_time: float = Field(..., description="Average processing time in seconds")
    success_rate: float = Field(..., description="Success rate percentage")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency status")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page
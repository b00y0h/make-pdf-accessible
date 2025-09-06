from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ProcessingStatus(str, Enum):
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ElementType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    FOOTER = "footer"
    HEADER = "header"


class ValidationLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0-1)."""
    left: float = Field(..., ge=0, le=1)
    top: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)


class AltTextRequest(BaseModel):
    """Request for alt text generation."""
    doc_id: str = Field(..., description="Document identifier")
    document_json_s3_key: str = Field(..., description="S3 key for document structure")
    original_s3_key: str = Field(..., description="S3 key for original PDF")
    user_id: str = Field(..., description="User identifier")


class AltTextResult(BaseModel):
    """Result of alt text generation."""
    doc_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    alt_text_json_s3_key: Optional[str] = Field(None, description="S3 key for alt text JSON")
    figures_processed: int = Field(default=0, description="Number of figures processed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class TagPDFRequest(BaseModel):
    """Request for PDF tagging."""
    doc_id: str = Field(..., description="Document identifier")
    original_s3_key: str = Field(..., description="S3 key for original PDF")
    document_json_s3_key: str = Field(..., description="S3 key for document structure")
    alt_text_json_s3_key: str = Field(..., description="S3 key for alt text data")
    user_id: str = Field(..., description="User identifier")


class TagPDFResult(BaseModel):
    """Result of PDF tagging."""
    doc_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    tagged_pdf_s3_key: Optional[str] = Field(None, description="S3 key for tagged PDF")
    tags_applied: int = Field(default=0, description="Number of accessibility tags applied")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class ExportsRequest(BaseModel):
    """Request for exports generation."""
    doc_id: str = Field(..., description="Document identifier")
    tagged_pdf_s3_key: str = Field(..., description="S3 key for tagged PDF")
    document_json_s3_key: str = Field(..., description="S3 key for document structure")
    alt_text_json_s3_key: str = Field(..., description="S3 key for alt text data")
    user_id: str = Field(..., description="User identifier")


class ExportsResult(BaseModel):
    """Result of exports generation."""
    doc_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    html_s3_key: Optional[str] = Field(None, description="S3 key for accessible HTML")
    epub_s3_key: Optional[str] = Field(None, description="S3 key for EPUB file")
    csv_zip_s3_key: Optional[str] = Field(None, description="S3 key for CSV tables ZIP")
    exports_generated: int = Field(default=0, description="Number of exports generated")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class ValidationRequest(BaseModel):
    """Request for accessibility validation."""
    doc_id: str = Field(..., description="Document identifier")
    tagged_pdf_s3_key: str = Field(..., description="S3 key for tagged PDF")
    html_s3_key: str = Field(..., description="S3 key for HTML file")
    user_id: str = Field(..., description="User identifier")


class ValidationIssue(BaseModel):
    """Individual validation issue."""
    type: str = Field(..., description="Issue type")
    level: ValidationLevel = Field(..., description="Issue severity level")
    message: str = Field(..., description="Human-readable issue description")
    location: Optional[str] = Field(None, description="Location in document")
    rule: Optional[str] = Field(None, description="Validation rule that triggered")


class ValidationResult(BaseModel):
    """Result of accessibility validation."""
    doc_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    validation_score: Optional[float] = Field(None, ge=0, le=100, description="Overall accessibility score")
    validation_issues: List[ValidationIssue] = Field(default_factory=list, description="List of issues found")
    pdf_ua_compliant: Optional[bool] = Field(None, description="PDF/UA compliance status")
    wcag_level: Optional[str] = Field(None, description="WCAG compliance level achieved")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class NotifyRequest(BaseModel):
    """Request for notification."""
    doc_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Final processing status")
    user_id: str = Field(..., description="User identifier")
    step: Optional[str] = Field(None, description="Step that failed (if status=failed)")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    results: Optional[Dict[str, Any]] = Field(None, description="Processing results")


class NotifyResult(BaseModel):
    """Result of notification."""
    doc_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Notification status")
    notifications_sent: int = Field(default=0, description="Number of notifications sent")
    error_message: Optional[str] = Field(None, description="Error message if failed")
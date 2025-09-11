"""Data models for the router function."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentSource(str, Enum):
    """Document source type."""

    UPLOAD = "upload"
    URL = "url"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStep(str, Enum):
    """Processing step types."""

    OCR = "ocr"
    STRUCTURE = "structure"
    TAGGER = "tagger"
    EXPORTER = "exporter"
    VALIDATOR = "validator"
    NOTIFIER = "notifier"


class JobStatus(str, Enum):
    """Job processing status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class IngestMessage(BaseModel):
    """SQS message from ingest-queue."""

    doc_id: str = Field(..., description="Unique document identifier")
    source: DocumentSource = Field(..., description="Document source type")
    s3_key: Optional[str] = Field(None, description="S3 key for uploaded files")
    source_url: Optional[str] = Field(
        None, description="Source URL for URL-based ingestion"
    )
    filename: Optional[str] = Field(None, description="Original filename")
    user_id: Optional[str] = Field(None, description="User who initiated the upload")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    webhook_url: Optional[str] = Field(
        None, description="Webhook URL for notifications"
    )
    priority: bool = Field(False, description="High priority processing")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v, values):
        source = values.data.get("source") if hasattr(values, "data") else None
        if source == DocumentSource.URL and not v:
            raise ValueError("source_url is required when source is URL")
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must be a valid HTTP/HTTPS URL")
        return v

    @field_validator("s3_key")
    @classmethod
    def validate_s3_key(cls, v, values):
        source = values.data.get("source") if hasattr(values, "data") else None
        if source == DocumentSource.UPLOAD and not v:
            raise ValueError("s3_key is required when source is upload")
        return v


class DocumentRecord(BaseModel):
    """DynamoDB document record."""

    doc_id: str = Field(..., description="Unique document identifier")
    user_id: Optional[str] = Field(None, description="User who uploaded the document")
    status: DocumentStatus = Field(
        DocumentStatus.PENDING, description="Processing status"
    )
    source: DocumentSource = Field(..., description="Document source type")
    filename: Optional[str] = Field(None, description="Original filename")
    s3_key_original: Optional[str] = Field(None, description="S3 key for original file")
    source_url: Optional[str] = Field(None, description="Source URL for URL-based docs")
    webhook_url: Optional[str] = Field(
        None, description="Webhook URL for notifications"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    artifacts: Dict[str, str] = Field(
        default_factory=dict, description="Generated artifacts"
    )
    processing_stats: Dict[str, Any] = Field(
        default_factory=dict, description="Processing statistics"
    )


class JobRecord(BaseModel):
    """DynamoDB job record."""

    job_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique job identifier"
    )
    doc_id: str = Field(..., description="Associated document ID")
    step: JobStep = Field(..., description="Processing step")
    status: JobStatus = Field(JobStatus.PENDING, description="Job status")
    priority: bool = Field(False, description="High priority job")
    input_data: Dict[str, Any] = Field(
        default_factory=dict, description="Input data for the job"
    )
    output_data: Dict[str, Any] = Field(
        default_factory=dict, description="Output data from the job"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Job completion timestamp"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    max_retries: int = Field(3, description="Maximum number of retries")
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )


class ProcessMessage(BaseModel):
    """SQS message for process-queue."""

    job_id: str = Field(..., description="Job identifier")
    doc_id: str = Field(..., description="Document identifier")
    step: JobStep = Field(..., description="Processing step")
    priority: bool = Field(False, description="High priority processing")
    input_data: Dict[str, Any] = Field(
        default_factory=dict, description="Input data for processing"
    )
    retry_count: int = Field(0, description="Current retry count")

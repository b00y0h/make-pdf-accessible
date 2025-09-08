from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OCRStatus(str, Enum):
    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OCRRequest(BaseModel):
    """Input model for OCR Lambda function."""
    doc_id: str = Field(..., description="Unique document identifier")
    s3_key: str = Field(..., description="S3 key of the PDF to process")
    user_id: str = Field(..., description="User identifier")
    priority: bool = Field(default=False, description="High priority processing flag")


class TextractJobStatus(BaseModel):
    """Textract job status tracking."""
    job_id: str = Field(..., description="Textract job ID")
    status: OCRStatus = Field(..., description="Current job status")
    completion_time: Optional[str] = Field(None, description="Job completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class OCRResult(BaseModel):
    """Output model for OCR Lambda function."""
    doc_id: str = Field(..., description="Document identifier")
    status: OCRStatus = Field(..., description="OCR processing status")
    textract_s3_key: Optional[str] = Field(None, description="S3 key for Textract JSON results")
    is_image_based: bool = Field(..., description="Whether PDF is image-based")
    page_count: int = Field(..., description="Total number of pages processed")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")


class TextractBlock(BaseModel):
    """Simplified Textract block model."""
    id: str = Field(..., description="Block ID")
    block_type: str = Field(..., description="Type of block (WORD, LINE, PAGE, etc.)")
    text: Optional[str] = Field(None, description="Extracted text content")
    confidence: Optional[float] = Field(None, description="Confidence score")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Bounding box coordinates")
    page: Optional[int] = Field(None, description="Page number")


class TextractResponse(BaseModel):
    """Structured Textract response."""
    job_id: str = Field(..., description="Textract job ID")
    document_metadata: Dict[str, Any] = Field(..., description="Document metadata")
    blocks: List[TextractBlock] = Field(..., description="Extracted text blocks")
    total_pages: int = Field(..., description="Total number of pages")

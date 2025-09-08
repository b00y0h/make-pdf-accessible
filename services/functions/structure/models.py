from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class HeadingLevel(int, Enum):
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    H6 = 6


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0-1)."""
    left: float = Field(..., ge=0, le=1, description="Left coordinate")
    top: float = Field(..., ge=0, le=1, description="Top coordinate")
    width: float = Field(..., ge=0, le=1, description="Width")
    height: float = Field(..., ge=0, le=1, description="Height")


class DocumentElement(BaseModel):
    """Base class for document structure elements."""
    id: str = Field(..., description="Unique element identifier")
    type: ElementType = Field(..., description="Type of document element")
    page_number: int = Field(..., ge=1, description="Page number (1-based)")
    bounding_box: Optional[BoundingBox] = Field(None, description="Element bounding box")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Detection confidence score")
    text: Optional[str] = Field(None, description="Text content")
    children: List["DocumentElement"] = Field(default_factory=list, description="Child elements")


class Heading(DocumentElement):
    """Heading element with level information."""
    type: ElementType = Field(default=ElementType.HEADING)
    level: HeadingLevel = Field(..., description="Heading level (1-6)")


class Paragraph(DocumentElement):
    """Paragraph text element."""
    type: ElementType = Field(default=ElementType.PARAGRAPH)


class ListElement(DocumentElement):
    """List container element."""
    type: ElementType = Field(default=ElementType.LIST)
    ordered: bool = Field(default=False, description="Whether list is ordered")


class ListItem(DocumentElement):
    """List item element."""
    type: ElementType = Field(default=ElementType.LIST_ITEM)
    marker: Optional[str] = Field(None, description="List marker (bullet, number, etc.)")


class TableElement(DocumentElement):
    """Table element with structure information."""
    type: ElementType = Field(default=ElementType.TABLE)
    rows: int = Field(..., ge=1, description="Number of rows")
    columns: int = Field(..., ge=1, description="Number of columns")
    cells: List[Dict[str, Any]] = Field(default_factory=list, description="Table cell data")


class Figure(DocumentElement):
    """Figure/image element."""
    type: ElementType = Field(default=ElementType.FIGURE)
    alt_text: Optional[str] = Field(None, description="Alternative text description")
    caption: Optional[str] = Field(None, description="Figure caption")


class StructureRequest(BaseModel):
    """Input model for structure analysis Lambda."""
    doc_id: str = Field(..., description="Document identifier")
    textract_s3_key: Optional[str] = Field(None, description="S3 key for Textract results")
    original_s3_key: str = Field(..., description="S3 key for original PDF")
    user_id: str = Field(..., description="User identifier")


class DocumentStructure(BaseModel):
    """Complete document structure model."""
    doc_id: str = Field(..., description="Document identifier")
    title: Optional[str] = Field(None, description="Document title")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    elements: List[DocumentElement] = Field(default_factory=list, description="All document elements")
    reading_order: List[str] = Field(default_factory=list, description="Reading order by element IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class StructureResult(BaseModel):
    """Output model for structure analysis Lambda."""
    doc_id: str = Field(..., description="Document identifier")
    status: str = Field(..., description="Processing status")
    document_json_s3_key: Optional[str] = Field(None, description="S3 key for structured document JSON")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    elements_count: int = Field(default=0, description="Number of elements detected")


class BedrockRequest(BaseModel):
    """Request model for Bedrock Claude analysis."""
    content: str = Field(..., description="Content to analyze")
    instructions: str = Field(..., description="Analysis instructions")
    max_tokens: int = Field(default=4000, description="Maximum response tokens")


class BedrockResponse(BaseModel):
    """Response model from Bedrock Claude."""
    content: str = Field(..., description="Analysis result")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")


# Update forward references
DocumentElement.model_rebuild()

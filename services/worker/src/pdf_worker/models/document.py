"""Document structure models with comprehensive type hints."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, root_validator, validator


class ElementType(str, Enum):
    """Types of document structure elements."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    FIGURE = "figure"
    CAPTION = "caption"
    FOOTER = "footer"
    HEADER = "header"
    SIDEBAR = "sidebar"
    QUOTE = "quote"
    CODE = "code"


class HeadingLevel(int, Enum):
    """Heading levels 1-6."""

    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    H6 = 6


class ListType(str, Enum):
    """Types of lists."""

    UNORDERED = "unordered"  # Bulleted
    ORDERED = "ordered"  # Numbered
    DEFINITION = "definition"  # Definition list


class FigureType(str, Enum):
    """Types of figures."""

    IMAGE = "image"
    CHART = "chart"
    DIAGRAM = "diagram"
    GRAPH = "graph"
    ILLUSTRATION = "illustration"
    PHOTO = "photo"
    SCREENSHOT = "screenshot"
    MAP = "map"
    OTHER = "other"


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0-1 scale)."""

    left: float = Field(..., ge=0.0, le=1.0, description="Left coordinate")
    top: float = Field(..., ge=0.0, le=1.0, description="Top coordinate")
    width: float = Field(..., ge=0.0, le=1.0, description="Width")
    height: float = Field(..., ge=0.0, le=1.0, description="Height")

    @validator("width", "height")
    def validate_dimensions(cls, v, values):
        """Validate that dimensions don't exceed bounds."""
        if "left" in values and v + values.get("left", 0) > 1.0:
            raise ValueError("Bounding box exceeds right boundary")
        if "top" in values and v + values.get("top", 0) > 1.0:
            raise ValueError("Bounding box exceeds bottom boundary")
        return v

    @property
    def right(self) -> float:
        """Right coordinate."""
        return self.left + self.width

    @property
    def bottom(self) -> float:
        """Bottom coordinate."""
        return self.top + self.height

    @property
    def center_x(self) -> float:
        """Center X coordinate."""
        return self.left + (self.width / 2)

    @property
    def center_y(self) -> float:
        """Center Y coordinate."""
        return self.top + (self.height / 2)

    def overlaps_with(self, other: "BoundingBox", threshold: float = 0.0) -> bool:
        """Check if this bounding box overlaps with another."""
        return not (
            self.right <= other.left + threshold
            or other.right <= self.left + threshold
            or self.bottom <= other.top + threshold
            or other.bottom <= self.top + threshold
        )


class DocumentElement(BaseModel):
    """Base class for document structure elements."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique element identifier",
    )
    type: ElementType = Field(..., description="Type of document element")
    page_number: int = Field(..., ge=1, description="Page number (1-based)")
    bounding_box: BoundingBox | None = Field(None, description="Element bounding box")
    confidence: float = Field(
        0.8, ge=0.0, le=1.0, description="Detection confidence score"
    )
    text: str = Field("", description="Text content of the element")
    children: list["DocumentElement"] = Field(
        default_factory=list, description="Child elements"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        validate_assignment = True

    def add_child(self, child: "DocumentElement") -> None:
        """Add a child element."""
        self.children.append(child)

    def get_all_text(self) -> str:
        """Get all text content including children."""
        texts = [self.text] if self.text else []
        for child in self.children:
            child_text = child.get_all_text()
            if child_text:
                texts.append(child_text)
        return " ".join(texts).strip()

    def find_elements_by_type(
        self, element_type: ElementType
    ) -> list["DocumentElement"]:
        """Find all elements of a specific type in this element and its children."""
        elements = []
        if self.type == element_type:
            elements.append(self)

        for child in self.children:
            elements.extend(child.find_elements_by_type(element_type))

        return elements


class Heading(DocumentElement):
    """Heading element with level information."""

    type: ElementType = Field(default=ElementType.HEADING, const=True)
    level: HeadingLevel = Field(..., description="Heading level (1-6)")

    @validator("text")
    def validate_heading_text(cls, v):
        """Validate heading has meaningful text."""
        if not v or not v.strip():
            raise ValueError("Heading must have text content")
        return v.strip()


class Paragraph(DocumentElement):
    """Paragraph text element."""

    type: ElementType = Field(default=ElementType.PARAGRAPH, const=True)


class ListElement(DocumentElement):
    """List container element."""

    type: ElementType = Field(default=ElementType.LIST, const=True)
    list_type: ListType = Field(ListType.UNORDERED, description="Type of list")
    start_number: int | None = Field(
        None, description="Starting number for ordered lists"
    )

    @validator("start_number")
    def validate_start_number(cls, v, values):
        """Validate start number for ordered lists."""
        list_type = values.get("list_type")
        if list_type == ListType.ORDERED and v is None:
            return 1  # Default start number
        elif list_type != ListType.ORDERED and v is not None:
            raise ValueError("start_number only valid for ordered lists")
        return v


class ListItem(DocumentElement):
    """List item element."""

    type: ElementType = Field(default=ElementType.LIST_ITEM, const=True)
    marker: str | None = Field(None, description="List marker (bullet, number, etc.)")
    item_number: int | None = Field(None, description="Item number in ordered lists")


class TableCell(DocumentElement):
    """Table cell element."""

    type: ElementType = Field(default=ElementType.TABLE_CELL, const=True)
    row_index: int = Field(..., ge=0, description="Row index (0-based)")
    column_index: int = Field(..., ge=0, description="Column index (0-based)")
    row_span: int = Field(1, ge=1, description="Number of rows this cell spans")
    column_span: int = Field(1, ge=1, description="Number of columns this cell spans")
    is_header: bool = Field(False, description="Whether this is a header cell")
    scope: str | None = Field(
        None, description="Header scope (row, col, rowgroup, colgroup)"
    )

    @validator("scope")
    def validate_scope(cls, v, values):
        """Validate scope is only set for header cells."""
        is_header = values.get("is_header", False)
        if v and not is_header:
            raise ValueError("scope can only be set for header cells")
        if v and v not in ["row", "col", "rowgroup", "colgroup"]:
            raise ValueError("scope must be one of: row, col, rowgroup, colgroup")
        return v


class TableElement(DocumentElement):
    """Table element with structure information."""

    type: ElementType = Field(default=ElementType.TABLE, const=True)
    rows: int = Field(..., ge=1, description="Number of rows")
    columns: int = Field(..., ge=1, description="Number of columns")
    has_header: bool = Field(False, description="Whether table has header row/column")
    caption: str | None = Field(None, description="Table caption")
    summary: str | None = Field(None, description="Table summary for accessibility")

    def get_cells(self) -> list[TableCell]:
        """Get all table cells."""
        return [child for child in self.children if isinstance(child, TableCell)]

    def get_cell(self, row: int, column: int) -> TableCell | None:
        """Get cell at specific row and column."""
        for child in self.children:
            if isinstance(child, TableCell):
                if child.row_index == row and child.column_index == column:
                    return child
        return None


class Figure(DocumentElement):
    """Figure/image element."""

    type: ElementType = Field(default=ElementType.FIGURE, const=True)
    figure_type: FigureType = Field(FigureType.OTHER, description="Type of figure")
    alt_text: str | None = Field(None, description="Alternative text description")
    caption: str | None = Field(None, description="Figure caption")
    title: str | None = Field(None, description="Figure title")
    long_description: str | None = Field(
        None, description="Long description for complex figures"
    )
    image_url: str | None = Field(None, description="Image URL or S3 key")

    @validator("alt_text")
    def validate_alt_text(cls, v):
        """Validate alt text length and content."""
        if v and len(v) > 250:
            raise ValueError("Alt text should be under 250 characters")
        return v


class Caption(DocumentElement):
    """Caption element for figures, tables, etc."""

    type: ElementType = Field(default=ElementType.CAPTION, const=True)
    caption_for: str | None = Field(
        None, description="ID of element this caption describes"
    )


class DocumentStructure(BaseModel):
    """Complete document structure model."""

    doc_id: str = Field(..., description="Document identifier")
    title: str | None = Field(None, description="Document title")
    language: str = Field("en", description="Primary document language")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    elements: list[DocumentElement] = Field(
        default_factory=list, description="All document elements"
    )
    reading_order: list[str] = Field(
        default_factory=list, description="Reading order by element IDs"
    )
    toc_elements: list[str] = Field(
        default_factory=list, description="Table of contents element IDs"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    @validator("reading_order")
    def validate_reading_order(cls, v, values):
        """Validate reading order references existing elements."""
        elements = values.get("elements", [])
        element_ids = {elem.id for elem in elements}

        invalid_ids = set(v) - element_ids
        if invalid_ids:
            raise ValueError(
                f"Reading order contains invalid element IDs: {invalid_ids}"
            )

        return v

    @root_validator
    def validate_structure(cls, values):
        """Validate overall document structure."""
        elements = values.get("elements", [])
        total_pages = values.get("total_pages", 1)

        # Validate page numbers don't exceed total
        invalid_pages = [
            elem.page_number for elem in elements if elem.page_number > total_pages
        ]
        if invalid_pages:
            raise ValueError(
                f"Elements reference pages beyond total_pages: {invalid_pages}"
            )

        # Update timestamp
        values["updated_at"] = datetime.utcnow()

        return values

    def add_element(self, element: DocumentElement) -> None:
        """Add an element to the document."""
        self.elements.append(element)
        # Add to reading order if not already present
        if element.id not in self.reading_order:
            self.reading_order.append(element.id)
        self.updated_at = datetime.utcnow()

    def get_element_by_id(self, element_id: str) -> DocumentElement | None:
        """Get element by ID."""
        for element in self.elements:
            if element.id == element_id:
                return element
        return None

    def get_elements_by_type(self, element_type: ElementType) -> list[DocumentElement]:
        """Get all elements of a specific type."""
        return [elem for elem in self.elements if elem.type == element_type]

    def get_elements_by_page(self, page_number: int) -> list[DocumentElement]:
        """Get all elements on a specific page."""
        return [elem for elem in self.elements if elem.page_number == page_number]

    def get_headings_hierarchy(self) -> list[Heading]:
        """Get headings in hierarchical order."""
        headings = [elem for elem in self.elements if isinstance(elem, Heading)]
        return sorted(headings, key=lambda h: (h.page_number, h.level.value))

    def generate_toc(self) -> list[dict[str, Any]]:
        """Generate table of contents from headings."""
        headings = self.get_headings_hierarchy()
        toc = []

        for heading in headings:
            toc_entry = {
                "id": heading.id,
                "title": heading.text,
                "level": heading.level.value,
                "page": heading.page_number,
                "children": [],
            }
            toc.append(toc_entry)

        return toc

    def validate_accessibility(self) -> dict[str, Any]:
        """Perform basic accessibility validation."""
        issues = []

        # Check for proper heading hierarchy
        headings = self.get_headings_hierarchy()
        if headings:
            prev_level = 0
            for heading in headings:
                if heading.level.value > prev_level + 1:
                    issues.append(
                        f"Heading level jump from H{prev_level} to H{heading.level.value}"
                    )
                prev_level = heading.level.value

        # Check for figures without alt text
        figures = [elem for elem in self.elements if isinstance(elem, Figure)]
        for figure in figures:
            if not figure.alt_text:
                issues.append(f"Figure {figure.id} missing alt text")

        # Check for tables without captions
        tables = [elem for elem in self.elements if isinstance(elem, TableElement)]
        for table in tables:
            if not table.caption and not table.summary:
                issues.append(f"Table {table.id} missing caption or summary")

        return {
            "issues": issues,
            "is_accessible": len(issues) == 0,
            "score": max(0, 100 - len(issues) * 10),  # Simple scoring
        }


# Update forward references
DocumentElement.model_rebuild()

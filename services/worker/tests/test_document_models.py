"""Tests for document structure models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from pdf_worker.models.document import (
    BoundingBox,
    DocumentElement,
    DocumentStructure,
    ElementType,
    Figure,
    FigureType,
    Heading,
    HeadingLevel,
    ListElement,
    ListType,
    Paragraph,
    TableCell,
    TableElement,
)


class TestBoundingBox:
    """Test BoundingBox model."""

    def test_valid_bounding_box(self):
        """Test creating valid bounding box."""
        bbox = BoundingBox(left=0.1, top=0.2, width=0.3, height=0.4)

        assert bbox.left == 0.1
        assert bbox.top == 0.2
        assert bbox.width == 0.3
        assert bbox.height == 0.4
        assert bbox.right == 0.4
        assert bbox.bottom == 0.6

    def test_bounding_box_validation(self):
        """Test bounding box coordinate validation."""
        # Invalid coordinates (negative)
        with pytest.raises(ValidationError):
            BoundingBox(left=-0.1, top=0.0, width=0.5, height=0.5)

        # Invalid coordinates (> 1.0)
        with pytest.raises(ValidationError):
            BoundingBox(left=0.0, top=0.0, width=1.5, height=0.5)

    def test_bounding_box_properties(self):
        """Test bounding box computed properties."""
        bbox = BoundingBox(left=0.2, top=0.3, width=0.4, height=0.2)

        assert bbox.center_x == 0.4
        assert bbox.center_y == 0.4
        assert bbox.right == 0.6
        assert bbox.bottom == 0.5

    def test_overlaps_with(self):
        """Test bounding box overlap detection."""
        bbox1 = BoundingBox(left=0.1, top=0.1, width=0.3, height=0.3)
        bbox2 = BoundingBox(left=0.2, top=0.2, width=0.3, height=0.3)  # Overlaps
        bbox3 = BoundingBox(left=0.6, top=0.6, width=0.2, height=0.2)  # No overlap

        assert bbox1.overlaps_with(bbox2) is True
        assert bbox1.overlaps_with(bbox3) is False
        assert bbox2.overlaps_with(bbox3) is False


class TestDocumentElement:
    """Test base DocumentElement model."""

    def test_create_basic_element(self):
        """Test creating basic document element."""
        element = DocumentElement(
            type=ElementType.PARAGRAPH, page_number=1, text="Test paragraph text"
        )

        assert element.type == ElementType.PARAGRAPH
        assert element.page_number == 1
        assert element.text == "Test paragraph text"
        assert element.confidence == 0.8  # default
        assert len(element.children) == 0

    def test_element_with_bounding_box(self):
        """Test element with bounding box."""
        bbox = BoundingBox(left=0.1, top=0.1, width=0.8, height=0.1)
        element = DocumentElement(
            type=ElementType.HEADING,
            page_number=1,
            text="Heading Text",
            bounding_box=bbox,
            confidence=0.95,
        )

        assert element.bounding_box == bbox
        assert element.confidence == 0.95

    def test_add_child(self):
        """Test adding child elements."""
        parent = DocumentElement(
            type=ElementType.LIST, page_number=1, text="List container"
        )

        child = DocumentElement(
            type=ElementType.LIST_ITEM, page_number=1, text="List item"
        )

        parent.add_child(child)

        assert len(parent.children) == 1
        assert parent.children[0] == child

    def test_get_all_text(self):
        """Test getting all text including children."""
        parent = DocumentElement(type=ElementType.LIST, page_number=1, text="List:")

        child1 = DocumentElement(
            type=ElementType.LIST_ITEM, page_number=1, text="Item 1"
        )

        child2 = DocumentElement(
            type=ElementType.LIST_ITEM, page_number=1, text="Item 2"
        )

        parent.add_child(child1)
        parent.add_child(child2)

        all_text = parent.get_all_text()
        assert "List:" in all_text
        assert "Item 1" in all_text
        assert "Item 2" in all_text

    def test_find_elements_by_type(self):
        """Test finding elements by type."""
        root = DocumentElement(type=ElementType.LIST, page_number=1, text="Root list")

        item1 = DocumentElement(
            type=ElementType.LIST_ITEM, page_number=1, text="Item 1"
        )

        item2 = DocumentElement(
            type=ElementType.LIST_ITEM, page_number=1, text="Item 2"
        )

        nested_para = DocumentElement(
            type=ElementType.PARAGRAPH, page_number=1, text="Nested paragraph"
        )

        root.add_child(item1)
        root.add_child(item2)
        item1.add_child(nested_para)

        list_items = root.find_elements_by_type(ElementType.LIST_ITEM)
        paragraphs = root.find_elements_by_type(ElementType.PARAGRAPH)

        assert len(list_items) == 2
        assert len(paragraphs) == 1


class TestHeading:
    """Test Heading model."""

    def test_create_heading(self):
        """Test creating heading element."""
        heading = Heading(
            page_number=1,
            text="Chapter 1: Introduction",
            level=HeadingLevel.H1,
            confidence=0.9,
        )

        assert heading.type == ElementType.HEADING
        assert heading.level == HeadingLevel.H1
        assert heading.text == "Chapter 1: Introduction"

    def test_heading_validation(self):
        """Test heading validation."""
        # Valid heading
        heading = Heading(page_number=1, text="Valid Heading", level=HeadingLevel.H2)
        assert heading.text == "Valid Heading"

        # Empty text should raise error
        with pytest.raises(ValidationError, match="Heading must have text content"):
            Heading(page_number=1, text="", level=HeadingLevel.H1)


class TestListElement:
    """Test ListElement model."""

    def test_create_unordered_list(self):
        """Test creating unordered list."""
        list_elem = ListElement(
            page_number=1, text="Bullet list", list_type=ListType.UNORDERED
        )

        assert list_elem.type == ElementType.LIST
        assert list_elem.list_type == ListType.UNORDERED
        assert list_elem.start_number is None

    def test_create_ordered_list(self):
        """Test creating ordered list."""
        list_elem = ListElement(
            page_number=1,
            text="Numbered list",
            list_type=ListType.ORDERED,
            start_number=5,
        )

        assert list_elem.list_type == ListType.ORDERED
        assert list_elem.start_number == 5

    def test_ordered_list_default_start(self):
        """Test ordered list with default start number."""
        list_elem = ListElement(
            page_number=1, text="Numbered list", list_type=ListType.ORDERED
        )

        # Should get default start number of 1
        assert list_elem.start_number == 1


class TestTableElement:
    """Test TableElement model."""

    def test_create_table(self):
        """Test creating table element."""
        table = TableElement(
            page_number=1,
            text="Data table",
            rows=3,
            columns=4,
            has_header=True,
            caption="Sample data table",
        )

        assert table.type == ElementType.TABLE
        assert table.rows == 3
        assert table.columns == 4
        assert table.has_header is True
        assert table.caption == "Sample data table"

    def test_table_with_cells(self):
        """Test table with cell children."""
        table = TableElement(page_number=1, text="Table with cells", rows=2, columns=2)

        # Add cells
        cell1 = TableCell(
            page_number=1,
            text="Cell 1,1",
            row_index=0,
            column_index=0,
            is_header=True,
            scope="col",
        )

        cell2 = TableCell(
            page_number=1,
            text="Cell 1,2",
            row_index=0,
            column_index=1,
            is_header=True,
            scope="col",
        )

        table.add_child(cell1)
        table.add_child(cell2)

        cells = table.get_cells()
        assert len(cells) == 2

        found_cell = table.get_cell(0, 1)
        assert found_cell == cell2


class TestTableCell:
    """Test TableCell model."""

    def test_create_regular_cell(self):
        """Test creating regular table cell."""
        cell = TableCell(
            page_number=1, text="Regular cell", row_index=1, column_index=2
        )

        assert cell.type == ElementType.TABLE_CELL
        assert cell.row_index == 1
        assert cell.column_index == 2
        assert cell.is_header is False
        assert cell.scope is None

    def test_create_header_cell(self):
        """Test creating header table cell."""
        cell = TableCell(
            page_number=1,
            text="Header cell",
            row_index=0,
            column_index=0,
            is_header=True,
            scope="row",
        )

        assert cell.is_header is True
        assert cell.scope == "row"

    def test_cell_validation(self):
        """Test table cell validation."""
        # Valid header cell with scope
        TableCell(
            page_number=1,
            text="Header",
            row_index=0,
            column_index=0,
            is_header=True,
            scope="col",
        )

        # Invalid: scope on non-header cell
        with pytest.raises(
            ValidationError, match="scope can only be set for header cells"
        ):
            TableCell(
                page_number=1,
                text="Regular cell",
                row_index=1,
                column_index=0,
                is_header=False,
                scope="row",
            )


class TestFigure:
    """Test Figure model."""

    def test_create_figure(self):
        """Test creating figure element."""
        figure = Figure(
            page_number=2,
            text="Chart showing sales data",
            figure_type=FigureType.CHART,
            alt_text="Bar chart showing quarterly sales increases",
            caption="Figure 1: Quarterly Sales Data",
        )

        assert figure.type == ElementType.FIGURE
        assert figure.figure_type == FigureType.CHART
        assert figure.alt_text == "Bar chart showing quarterly sales increases"
        assert figure.caption == "Figure 1: Quarterly Sales Data"

    def test_alt_text_validation(self):
        """Test alt text length validation."""
        # Valid alt text
        Figure(page_number=1, text="Figure", alt_text="Short alt text")

        # Alt text too long
        long_alt_text = "x" * 300  # Over 250 character limit
        with pytest.raises(
            ValidationError, match="Alt text should be under 250 characters"
        ):
            Figure(page_number=1, text="Figure", alt_text=long_alt_text)


class TestDocumentStructure:
    """Test DocumentStructure model."""

    def test_create_document_structure(self):
        """Test creating document structure."""
        doc = DocumentStructure(
            doc_id="test-doc-123", title="Test Document", language="en", total_pages=3
        )

        assert doc.doc_id == "test-doc-123"
        assert doc.title == "Test Document"
        assert doc.language == "en"
        assert doc.total_pages == 3
        assert len(doc.elements) == 0
        assert isinstance(doc.created_at, datetime)

    def test_add_element(self):
        """Test adding elements to document."""
        doc = DocumentStructure(doc_id="test-doc", total_pages=1)

        heading = Heading(page_number=1, text="Test Heading", level=HeadingLevel.H1)

        doc.add_element(heading)

        assert len(doc.elements) == 1
        assert doc.elements[0] == heading
        assert heading.id in doc.reading_order

    def test_get_elements_by_type(self):
        """Test getting elements by type."""
        doc = DocumentStructure(doc_id="test-doc", total_pages=1)

        heading = Heading(page_number=1, text="Heading", level=HeadingLevel.H1)

        paragraph = Paragraph(page_number=1, text="Paragraph text")

        doc.add_element(heading)
        doc.add_element(paragraph)

        headings = doc.get_elements_by_type(ElementType.HEADING)
        paragraphs = doc.get_elements_by_type(ElementType.PARAGRAPH)

        assert len(headings) == 1
        assert len(paragraphs) == 1
        assert headings[0] == heading

    def test_get_elements_by_page(self):
        """Test getting elements by page number."""
        doc = DocumentStructure(doc_id="test-doc", total_pages=2)

        elem1 = Paragraph(page_number=1, text="Page 1 content")
        elem2 = Paragraph(page_number=2, text="Page 2 content")
        elem3 = Paragraph(page_number=1, text="More page 1 content")

        doc.add_element(elem1)
        doc.add_element(elem2)
        doc.add_element(elem3)

        page1_elements = doc.get_elements_by_page(1)
        page2_elements = doc.get_elements_by_page(2)

        assert len(page1_elements) == 2
        assert len(page2_elements) == 1

    def test_generate_toc(self):
        """Test generating table of contents."""
        doc = DocumentStructure(doc_id="test-doc", total_pages=2)

        h1 = Heading(page_number=1, text="Chapter 1", level=HeadingLevel.H1)
        h2 = Heading(page_number=1, text="Section 1.1", level=HeadingLevel.H2)
        h1_2 = Heading(page_number=2, text="Chapter 2", level=HeadingLevel.H1)

        doc.add_element(h1)
        doc.add_element(h2)
        doc.add_element(h1_2)

        toc = doc.generate_toc()

        assert len(toc) == 3
        assert toc[0]["title"] == "Chapter 1"
        assert toc[0]["level"] == 1
        assert toc[1]["title"] == "Section 1.1"
        assert toc[1]["level"] == 2

    def test_validate_accessibility(self):
        """Test basic accessibility validation."""
        doc = DocumentStructure(doc_id="test-doc", total_pages=1)

        # Add heading with skip from H1 to H3 (accessibility issue)
        h1 = Heading(page_number=1, text="Title", level=HeadingLevel.H1)
        h3 = Heading(page_number=1, text="Subsection", level=HeadingLevel.H3)  # Skip H2

        # Add figure without alt text
        figure = Figure(page_number=1, text="Chart", alt_text=None)  # Missing alt text

        doc.add_element(h1)
        doc.add_element(h3)
        doc.add_element(figure)

        validation = doc.validate_accessibility()

        assert validation["is_accessible"] is False
        assert len(validation["issues"]) >= 2  # Heading skip + missing alt text
        assert validation["score"] < 100

    def test_reading_order_validation(self):
        """Test reading order validation."""
        doc = DocumentStructure(doc_id="test-doc", total_pages=1)

        element = Paragraph(page_number=1, text="Test")
        doc.add_element(element)

        # Valid reading order
        doc.reading_order = [element.id]
        # Should not raise error

        # Invalid reading order (non-existent ID)
        with pytest.raises(
            ValidationError, match="Reading order contains invalid element IDs"
        ):
            DocumentStructure(
                doc_id="test-doc",
                total_pages=1,
                elements=[element],
                reading_order=["non-existent-id"],
            )

    def test_page_number_validation(self):
        """Test page number validation."""
        # Valid page numbers
        doc = DocumentStructure(doc_id="test-doc", total_pages=2)

        elem1 = Paragraph(page_number=1, text="Page 1")
        elem2 = Paragraph(page_number=2, text="Page 2")

        doc.add_element(elem1)
        doc.add_element(elem2)
        # Should not raise error

        # Invalid page number (exceeds total)
        with pytest.raises(
            ValidationError, match="Elements reference pages beyond total_pages"
        ):
            DocumentStructure(
                doc_id="test-doc",
                total_pages=1,
                elements=[
                    Paragraph(
                        page_number=2, text="Invalid page"
                    )  # Page 2 but total is 1
                ],
            )

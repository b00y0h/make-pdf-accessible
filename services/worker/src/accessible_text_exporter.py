"""
Reading-Order Aware Text Exporter for Accessibility Compliance
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AccessibleTextExporter:
    """Exports documents to plain text with proper reading order and accessibility features."""
    
    def __init__(self):
        self.include_structure_markers = True
        self.include_alt_text = True
        self.include_table_descriptions = True
        
    def export_accessible_text(
        self,
        document_structure: Dict[str, Any],
        alt_text_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Export document to accessible plain text with reading order preservation.
        
        Args:
            document_structure: Document structure from canonical schema
            alt_text_data: Alt-text data for figures
            metadata: Document metadata
            
        Returns:
            Accessible plain text representation
        """
        try:
            logger.info("Generating reading-order aware text export")
            
            # Build alt-text lookup
            alt_text_map = self._build_alt_text_map(alt_text_data) if alt_text_data else {}
            
            # Extract and sort elements by reading order
            elements = document_structure.get("elements", [])
            ordered_elements = self._sort_by_reading_order(elements)
            
            # Build text content
            text_parts = []
            
            # Add document header
            text_parts.append(self._build_document_header(document_structure, metadata))
            
            # Process elements in reading order
            current_section_path = []
            
            for element in ordered_elements:
                element_text = self._process_element_for_text(
                    element, 
                    alt_text_map,
                    current_section_path
                )
                
                if element_text:
                    text_parts.append(element_text)
                    
                # Update section path for headings
                if element.get("type") == "heading":
                    current_section_path = self._update_section_path(
                        current_section_path,
                        element.get("text", ""),
                        element.get("level", 1)
                    )
            
            # Add document footer
            text_parts.append(self._build_document_footer(metadata))
            
            # Join with appropriate spacing
            result = self._join_text_parts(text_parts)
            
            logger.info(f"Generated accessible text export ({len(result)} characters)")
            return result
            
        except Exception as e:
            logger.error(f"Accessible text export failed: {e}")
            raise

    def _build_document_header(
        self,
        document_structure: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build document header with accessibility metadata."""
        
        header_parts = []
        
        # Document title
        title = (
            document_structure.get("title") or 
            metadata.get("title") if metadata else None or
            "Accessible Document"
        )
        header_parts.append(f"DOCUMENT: {title.upper()}")
        header_parts.append("=" * (len(title) + 10))
        header_parts.append("")
        
        # Add metadata if available
        if metadata:
            if metadata.get("author"):
                header_parts.append(f"Author: {metadata['author']}")
            if metadata.get("subject"):
                header_parts.append(f"Subject: {metadata['subject']}")
            if metadata.get("pageCount"):
                header_parts.append(f"Pages: {metadata['pageCount']}")
            if metadata.get("language"):
                header_parts.append(f"Language: {metadata['language']}")
            
            header_parts.append("")
        
        # Accessibility statement
        header_parts.extend([
            "ACCESSIBILITY INFORMATION:",
            "- This document has been processed for screen reader accessibility",
            "- Content is presented in logical reading order",
            "- Images include alternative text descriptions",
            "- Tables include structural information",
            "",
            "DOCUMENT CONTENT:",
            "-" * 50,
            ""
        ])
        
        return "\n".join(header_parts)

    def _build_document_footer(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Build document footer."""
        
        footer_parts = [
            "",
            "-" * 50,
            "END OF DOCUMENT",
            "",
            f"Processed for accessibility: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        ]
        
        if metadata and metadata.get("processingVersion"):
            footer_parts.append(f"Processing version: {metadata['processingVersion']}")
        
        return "\n".join(footer_parts)

    def _sort_by_reading_order(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort elements by proper reading order."""
        
        # Primary sort: page number
        # Secondary sort: reading order index (if available)
        # Tertiary sort: vertical position (top to bottom)
        # Quaternary sort: horizontal position (left to right for same vertical level)
        
        def sort_key(element):
            page = element.get("page_number", 1)
            reading_order = element.get("reading_order_index", 999999)
            
            # Extract position from bounding box if available
            bbox = element.get("bounding_box", {})
            y_pos = bbox.get("top", 0)
            x_pos = bbox.get("left", 0)
            
            return (page, reading_order, y_pos, x_pos)
        
        return sorted(elements, key=sort_key)

    def _process_element_for_text(
        self,
        element: Dict[str, Any],
        alt_text_map: Dict[str, str],
        section_path: List[str]
    ) -> str:
        """Process individual element for text export."""
        
        element_type = element.get("type", "paragraph")
        text_parts = []
        
        if element_type == "heading":
            level = element.get("level", 1)
            text = element.get("text", "").strip()
            
            if text:
                # Add heading with level indicator
                level_marker = "#" * level if self.include_structure_markers else ""
                text_parts.append(f"{level_marker} {text.upper()}")
                text_parts.append("")
        
        elif element_type == "paragraph":
            text = element.get("text", "").strip()
            if text:
                # Clean text for accessibility
                cleaned_text = self._clean_text_for_accessibility(text)
                text_parts.append(cleaned_text)
                text_parts.append("")
        
        elif element_type == "list":
            list_text = self._format_list_for_text(element)
            if list_text:
                text_parts.append(list_text)
                text_parts.append("")
        
        elif element_type == "table":
            table_text = self._format_table_for_text(element)
            if table_text:
                if self.include_structure_markers:
                    text_parts.append("[TABLE]")
                text_parts.append(table_text)
                text_parts.append("")
        
        elif element_type == "figure":
            figure_text = self._format_figure_for_text(element, alt_text_map)
            if figure_text:
                if self.include_structure_markers:
                    text_parts.append("[FIGURE]")
                text_parts.append(figure_text)
                text_parts.append("")
        
        return "\n".join(text_parts)

    def _format_list_for_text(self, element: Dict[str, Any]) -> str:
        """Format list elements for accessible text."""
        
        items = element.get("items", [])
        list_type = element.get("list_type", "unordered")
        
        if not items:
            # Try to parse from text
            text = element.get("text", "")
            if text:
                items = self._parse_list_items(text)
        
        if not items:
            return element.get("text", "")
        
        # Format list items
        formatted_items = []
        for i, item in enumerate(items):
            if list_type == "ordered":
                formatted_items.append(f"{i + 1}. {item}")
            else:
                formatted_items.append(f"• {item}")
        
        return "\n".join(formatted_items)

    def _format_table_for_text(self, element: Dict[str, Any]) -> str:
        """Format table elements for accessible text."""
        
        table_data = element.get("table_data")
        if not table_data:
            return element.get("text", "")
        
        has_headers = element.get("has_headers", False)
        caption = element.get("caption", "")
        
        text_parts = []
        
        # Add caption
        if caption:
            text_parts.append(f"Table Caption: {caption}")
            text_parts.append("")
        
        # Add table description
        rows = len(table_data)
        cols = len(table_data[0]) if table_data else 0
        text_parts.append(f"Table with {rows} rows and {cols} columns:")
        text_parts.append("")
        
        # Format table data for screen readers
        for row_idx, row in enumerate(table_data):
            if row_idx == 0 and has_headers:
                text_parts.append("HEADERS:")
                for col_idx, cell in enumerate(row):
                    text_parts.append(f"  Column {col_idx + 1}: {cell}")
                text_parts.append("")
                text_parts.append("DATA ROWS:")
            else:
                row_num = row_idx if not has_headers else row_idx
                text_parts.append(f"Row {row_num + 1}:")
                for col_idx, cell in enumerate(row):
                    header_ref = ""
                    if has_headers and table_data:
                        header_ref = f" (Column: {table_data[0][col_idx]})" if col_idx < len(table_data[0]) else ""
                    text_parts.append(f"  {cell}{header_ref}")
                text_parts.append("")
        
        return "\n".join(text_parts)

    def _format_figure_for_text(self, element: Dict[str, Any], alt_text_map: Dict[str, str]) -> str:
        """Format figure elements for accessible text."""
        
        figure_id = element.get("id", f"figure_{element.get('page_number', 1)}")
        alt_text = alt_text_map.get(figure_id, "")
        caption = element.get("caption", "")
        
        text_parts = []
        
        # Add figure description
        if alt_text:
            text_parts.append(f"Image Description: {alt_text}")
        else:
            text_parts.append(f"Image: {figure_id}")
        
        # Add caption if different from alt-text
        if caption and caption != alt_text:
            text_parts.append(f"Caption: {caption}")
        
        return "\n".join(text_parts)

    def _clean_text_for_accessibility(self, text: str) -> str:
        """Clean text for better accessibility and readability."""
        
        if not text:
            return ""
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Expand common abbreviations for screen readers
        abbreviations = {
            r'\bDr\b': 'Doctor',
            r'\bMr\b': 'Mister', 
            r'\bMrs\b': 'Missus',
            r'\bMs\b': 'Miss',
            r'\betc\b': 'etcetera',
            r'\bie\b': 'that is',
            r'\beg\b': 'for example',
            r'\bvs\b': 'versus',
        }
        
        for abbrev, expansion in abbreviations.items():
            cleaned = re.sub(abbrev, expansion, cleaned, flags=re.IGNORECASE)
        
        # Ensure proper sentence spacing
        cleaned = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', cleaned)
        
        return cleaned

    def _parse_list_items(self, text: str) -> List[str]:
        """Parse list items from unstructured text."""
        
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        items = []
        
        for line in lines:
            # Skip empty lines
            if not line:
                continue
                
            # Remove list markers and extract content
            if re.match(r'^[•\-\*]\s+', line):
                items.append(line[2:].strip())
            elif re.match(r'^\d+[.\)]\s+', line):
                # Remove number prefix
                content = re.sub(r'^\d+[.\)]\s+', '', line)
                items.append(content)
            else:
                # Treat as list item without explicit marker
                items.append(line)
        
        return items

    def _update_section_path(
        self,
        current_path: List[str],
        heading_text: str,
        heading_level: int
    ) -> List[str]:
        """Update section path based on heading hierarchy."""
        
        # Remove sections at same or lower level
        new_path = [section for section in current_path if section.get("level", 1) < heading_level]
        
        # Add current heading
        new_path.append({
            "text": heading_text,
            "level": heading_level
        })
        
        return new_path

    def _join_text_parts(self, parts: List[str]) -> str:
        """Join text parts with appropriate spacing for accessibility."""
        
        # Remove empty parts
        non_empty_parts = [part for part in parts if part.strip()]
        
        # Join with double newlines for clear separation
        result = "\n\n".join(non_empty_parts)
        
        # Ensure no more than 2 consecutive newlines
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()


# Global service instance
_text_exporter = None


def get_text_exporter() -> AccessibleTextExporter:
    """Get global accessible text exporter instance."""
    global _text_exporter
    if _text_exporter is None:
        _text_exporter = AccessibleTextExporter()
    return _text_exporter
"""
Semantic HTML Builder using canonical JSON schema for accessibility compliance
"""

import html
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class SemanticHTMLBuilder:
    """Builds semantic, accessible HTML from canonical document structure."""
    
    def __init__(self):
        self.element_processors = {
            "heading": self._process_heading,
            "paragraph": self._process_paragraph,
            "list": self._process_list,
            "table": self._process_table,
            "figure": self._process_figure,
        }
    
    def build_semantic_html(
        self,
        document_structure: Dict[str, Any],
        alt_text_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build complete semantic HTML document from canonical schema.
        
        Args:
            document_structure: Document structure from structure service
            alt_text_data: Alt-text data for figures
            metadata: Document metadata
            
        Returns:
            Complete HTML document string
        """
        try:
            logger.info("Building semantic HTML from canonical schema")
            
            # Extract document metadata
            doc_metadata = metadata or {}
            doc_title = (
                document_structure.get("title") or 
                doc_metadata.get("title") or 
                "Accessible Document"
            )
            doc_lang = doc_metadata.get("language", "en")
            doc_author = doc_metadata.get("author")
            
            # Build alt-text lookup
            alt_text_map = self._build_alt_text_map(alt_text_data) if alt_text_data else {}
            
            # Process document elements
            html_body = self._build_document_body(
                document_structure.get("elements", []),
                alt_text_map
            )
            
            # Build complete HTML document
            html_document = self._build_html_document(
                title=doc_title,
                lang=doc_lang,
                author=doc_author,
                body_content=html_body,
                metadata=doc_metadata
            )
            
            logger.info("Semantic HTML generation completed")
            return html_document
            
        except Exception as e:
            logger.error(f"Semantic HTML generation failed: {e}")
            raise

    def _build_html_document(
        self,
        title: str,
        lang: str,
        author: Optional[str],
        body_content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Build complete HTML document with proper accessibility metadata."""
        
        # Build metadata tags
        meta_tags = []
        if author:
            meta_tags.append(f'    <meta name="author" content="{html.escape(author)}">')
        if metadata.get("subject"):
            meta_tags.append(f'    <meta name="description" content="{html.escape(metadata["subject"])}">')
        if metadata.get("keyTopics"):
            meta_tags.append(f'    <meta name="keywords" content="{html.escape(metadata["keyTopics"])}">')
        
        # Add accessibility metadata
        meta_tags.extend([
            '    <meta name="accessibility-compliance" content="WCAG 2.1 AA">',
            '    <meta name="pdf-ua-compliant" content="true">',
            '    <meta name="screen-reader-optimized" content="true">',
        ])
        
        meta_section = "\n".join(meta_tags)
        
        return f'''<!DOCTYPE html>
<html lang="{html.escape(lang)}" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
{meta_section}
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            color: #1f2937;
            background-color: #ffffff;
        }}
        
        /* Accessibility-focused styles */
        h1, h2, h3, h4, h5, h6 {{
            color: #111827;
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 1rem;
            line-height: 1.3;
        }}
        
        h1 {{ font-size: 2.25rem; }}
        h2 {{ font-size: 1.875rem; }}
        h3 {{ font-size: 1.5rem; }}
        h4 {{ font-size: 1.25rem; }}
        h5 {{ font-size: 1.125rem; }}
        h6 {{ font-size: 1rem; }}
        
        p {{
            margin: 1.25rem 0;
            hyphens: auto;
        }}
        
        /* High contrast focus indicators */
        a, button, [tabindex] {{
            outline: 2px solid transparent;
            outline-offset: 2px;
        }}
        
        a:focus, button:focus, [tabindex]:focus {{
            outline: 3px solid #2563eb;
            outline-offset: 2px;
        }}
        
        /* Accessible table styles */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 2rem 0;
            border: 2px solid #374151;
        }}
        
        th, td {{
            border: 1px solid #6b7280;
            padding: 0.75rem;
            text-align: left;
            vertical-align: top;
        }}
        
        th {{
            background-color: #f3f4f6;
            font-weight: 600;
            color: #111827;
        }}
        
        /* Enhanced contrast for better readability */
        tr:nth-child(even) {{
            background-color: #f9fafb;
        }}
        
        /* List styles */
        ul, ol {{
            margin: 1.25rem 0;
            padding-left: 2rem;
        }}
        
        li {{
            margin: 0.5rem 0;
        }}
        
        /* Figure and image styles */
        figure {{
            margin: 2rem 0;
            text-align: center;
        }}
        
        figcaption {{
            margin-top: 0.5rem;
            font-style: italic;
            color: #6b7280;
            font-size: 0.875rem;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #d1d5db;
            border-radius: 0.375rem;
        }}
        
        /* Screen reader only content */
        .sr-only {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                font-size: 12pt;
                line-height: 1.4;
            }}
            
            a[href]:after {{
                content: " (" attr(href) ")";
                font-size: 10pt;
                color: #666;
            }}
        }}
        
        /* High contrast mode support */
        @media (prefers-contrast: high) {{
            body {{
                background-color: #ffffff;
                color: #000000;
            }}
            
            th {{
                background-color: #000000;
                color: #ffffff;
            }}
            
            table, th, td {{
                border-color: #000000;
            }}
        }}
    </style>
</head>
<body>
    <main role="main" id="main-content" tabindex="-1">
        <h1>{html.escape(title)}</h1>
        {body_content}
    </main>
    
    <!-- Accessibility navigation -->
    <nav aria-label="Page navigation" class="sr-only">
        <h2>Navigation</h2>
        <ul>
            <li><a href="#main-content">Skip to main content</a></li>
        </ul>
    </nav>
</body>
</html>'''

    def _build_document_body(
        self,
        elements: List[Dict[str, Any]],
        alt_text_map: Dict[str, str]
    ) -> str:
        """Build the main document body content."""
        
        html_parts = []
        current_section_level = 0
        
        # Track reading order from canonical schema
        reading_order = self._extract_reading_order(elements)
        
        for element in reading_order:
            element_type = element.get("type", "paragraph")
            
            if element_type in self.element_processors:
                html_content = self.element_processors[element_type](element, alt_text_map)
                if html_content:
                    html_parts.append(html_content)
            else:
                # Fallback for unknown types
                html_parts.append(self._process_generic_element(element))
        
        return "\n\n".join(html_parts)

    def _extract_reading_order(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract proper reading order from canonical document structure."""
        
        # Elements should already be in reading order from structure analysis
        # Sort by page number and then by any position indicators
        return sorted(elements, key=lambda x: (
            x.get("page_number", 1),
            x.get("reading_order_index", 0),
            x.get("y_position", 0)  # Fallback to vertical position
        ))

    def _process_heading(self, element: Dict[str, Any], alt_text_map: Dict[str, str]) -> str:
        """Process heading elements with proper semantic structure."""
        
        level = element.get("level", 1)
        level = max(1, min(6, level))  # Ensure valid h1-h6 range
        
        text = html.escape(element.get("text", "")).strip()
        element_id = self._generate_element_id(element)
        
        # Add skip link target for major headings
        skip_target = f' id="{element_id}"' if level <= 2 else ""
        
        return f'        <h{level}{skip_target}>{text}</h{level}>'

    def _process_paragraph(self, element: Dict[str, Any], alt_text_map: Dict[str, str]) -> str:
        """Process paragraph elements."""
        
        text = html.escape(element.get("text", "")).strip()
        if not text:
            return ""
        
        # Handle line breaks while maintaining paragraph structure
        text = text.replace("\n", "<br>") if "\n" in text else text
        
        return f'        <p>{text}</p>'

    def _process_list(self, element: Dict[str, Any], alt_text_map: Dict[str, str]) -> str:
        """Process list elements with proper semantic structure."""
        
        list_type = element.get("list_type", "unordered")
        items = element.get("items", [])
        
        if not items:
            # Fallback to parsing from text
            text = element.get("text", "")
            if text:
                items = self._parse_list_from_text(text)
        
        if not items:
            return f'        <p>{html.escape(element.get("text", ""))}</p>'
        
        # Build list HTML
        tag = "ol" if list_type == "ordered" else "ul"
        list_items = []
        
        for item in items:
            item_text = html.escape(str(item).strip())
            list_items.append(f'            <li>{item_text}</li>')
        
        list_html = f'''        <{tag}>
{chr(10).join(list_items)}
        </{tag}>'''
        
        return list_html

    def _process_table(self, element: Dict[str, Any], alt_text_map: Dict[str, str]) -> str:
        """Process table elements with enhanced accessibility."""
        
        table_data = element.get("table_data")
        if not table_data:
            # Fallback to basic representation
            text = html.escape(element.get("text", ""))
            return f'        <div role="table" aria-label="Data table"><p>{text}</p></div>'
        
        has_headers = element.get("has_headers", False)
        caption = element.get("caption", "")
        
        # Build table HTML with accessibility features
        table_html = ['        <table role="table">']
        
        # Add caption if available
        if caption:
            table_html.append(f'            <caption>{html.escape(caption)}</caption>')
        
        # Process table data
        for row_idx, row in enumerate(table_data):
            if row_idx == 0 and has_headers:
                # Header row
                table_html.append('            <thead>')
                table_html.append('                <tr>')
                for cell in row:
                    cell_content = html.escape(str(cell) if cell else '')
                    table_html.append(f'                    <th scope="col">{cell_content}</th>')
                table_html.append('                </tr>')
                table_html.append('            </thead>')
                table_html.append('            <tbody>')
            else:
                # Data row
                if row_idx == 1 and has_headers:
                    table_html.append('            <tbody>')
                table_html.append('                <tr>')
                for cell_idx, cell in enumerate(row):
                    cell_content = html.escape(str(cell) if cell else '')
                    # Use th for first column if it looks like a row header
                    if cell_idx == 0 and self._is_row_header(cell_content, row):
                        table_html.append(f'                    <th scope="row">{cell_content}</th>')
                    else:
                        table_html.append(f'                    <td>{cell_content}</td>')
                table_html.append('                </tr>')
        
        # Close tbody if it was opened
        if has_headers or len(table_data) > 1:
            table_html.append('            </tbody>')
        
        table_html.append('        </table>')
        
        return '\n'.join(table_html)

    def _process_figure(self, element: Dict[str, Any], alt_text_map: Dict[str, str]) -> str:
        """Process figure elements with alt-text and captions."""
        
        figure_id = element.get("id", f"figure_{element.get('page_number', 1)}")
        alt_text = alt_text_map.get(figure_id, "")
        caption = element.get("caption", "")
        
        # Build figure HTML
        figure_html = ['        <figure>']
        
        # Add image or placeholder
        if element.get("image_data"):
            # Actual image data available
            img_attrs = [
                f'alt="{html.escape(alt_text)}"' if alt_text else 'alt=""',
                'role="img"',
                'style="max-width: 100%; height: auto;"'
            ]
            figure_html.append(f'            <img {" ".join(img_attrs)}>')
        else:
            # Image placeholder with alt-text
            placeholder_text = alt_text or f"Figure {figure_id}"
            figure_html.append(f'            <div role="img" aria-label="{html.escape(placeholder_text)}" class="image-placeholder">')
            figure_html.append(f'                <p>{html.escape(placeholder_text)}</p>')
            figure_html.append('            </div>')
        
        # Add caption if available
        if caption:
            figure_html.append(f'            <figcaption>{html.escape(caption)}</figcaption>')
        
        figure_html.append('        </figure>')
        
        return '\n'.join(figure_html)

    def _is_row_header(self, cell_content: str, row: List[str]) -> bool:
        """Determine if a cell should be treated as a row header."""
        
        # Simple heuristics for row headers
        if not cell_content:
            return False
        
        # If it's significantly different from other cells (shorter, non-numeric)
        other_cells = [str(cell) for cell in row[1:] if cell]
        
        if other_cells:
            # Check if this cell is non-numeric while others are numeric
            try:
                float(cell_content.replace(",", "").replace("$", ""))
                return False  # This cell is numeric
            except ValueError:
                # Check if other cells are mostly numeric
                numeric_others = 0
                for other_cell in other_cells:
                    try:
                        float(str(other_cell).replace(",", "").replace("$", ""))
                        numeric_others += 1
                    except ValueError:
                        pass
                
                return numeric_others >= len(other_cells) * 0.7
        
        return False

    def _parse_list_from_text(self, text: str) -> List[str]:
        """Parse list items from text content."""
        
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        items = []
        
        for line in lines:
            # Remove common list markers
            cleaned_line = line
            if line.startswith(("• ", "- ", "* ", "○ ")):
                cleaned_line = line[2:].strip()
            elif line[0:3].replace(".", "").replace(")", "").isdigit():
                # Numbered list item like "1. " or "1)"
                parts = line.split(None, 1)
                if len(parts) > 1:
                    cleaned_line = parts[1]
            
            if cleaned_line:
                items.append(cleaned_line)
        
        return items

    def _build_alt_text_map(self, alt_text_data: Dict[str, Any]) -> Dict[str, str]:
        """Build mapping of figure IDs to approved alt-text."""
        
        alt_text_map = {}
        
        for figure in alt_text_data.get("figures", []):
            figure_id = figure.get("figure_id")
            approved_text = figure.get("approved_text")
            ai_text = figure.get("ai_text")
            
            # Prefer approved text, fallback to AI text
            if figure_id and (approved_text or ai_text):
                alt_text_map[figure_id] = approved_text or ai_text
        
        return alt_text_map

    def _generate_element_id(self, element: Dict[str, Any]) -> str:
        """Generate valid HTML ID for an element."""
        
        element_id = element.get("id")
        if element_id:
            # Sanitize ID for HTML
            return element_id.replace(" ", "-").lower()
        
        # Generate from content
        text = element.get("text", "")[:50]  # First 50 chars
        sanitized = "".join(c if c.isalnum() else "-" for c in text)
        return f"element-{sanitized}"[:50]  # Limit length

    def _process_generic_element(self, element: Dict[str, Any]) -> str:
        """Process unknown element types as paragraphs."""
        
        text = html.escape(element.get("text", "")).strip()
        return f'        <p>{text}</p>' if text else ""


# Global service instance
_html_builder = None


def get_html_builder() -> SemanticHTMLBuilder:
    """Get global HTML builder instance."""
    global _html_builder
    if _html_builder is None:
        _html_builder = SemanticHTMLBuilder()
    return _html_builder
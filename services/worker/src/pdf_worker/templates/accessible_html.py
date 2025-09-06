"""HTML template rendering for accessible document exports."""

from typing import Dict, Any, List, Optional
from jinja2 import Environment, BaseLoader, Template
from aws_lambda_powertools import Logger

from pdf_worker.models.document import DocumentStructure, DocumentElement, ElementType, Heading, TableElement, Figure, ListElement

logger = Logger()


class AccessibleHTMLRenderer:
    """Renderer for creating accessible HTML from document structure."""
    
    def __init__(self):
        """Initialize the HTML renderer."""
        self.env = Environment(loader=BaseLoader())
        self.env.filters['safe_id'] = self._safe_id_filter
    
    def render_document(
        self, 
        document: DocumentStructure,
        include_styles: bool = True,
        include_skip_links: bool = True
    ) -> str:
        """Render complete accessible HTML document.
        
        Args:
            document: Document structure to render
            include_styles: Whether to include CSS styles
            include_skip_links: Whether to include skip navigation links
            
        Returns:
            Complete HTML document string
        """
        template = self.env.from_string(self._get_main_template())
        
        # Prepare template context
        context = {
            'document': document,
            'title': document.title or f"Document {document.doc_id}",
            'language': document.language,
            'include_styles': include_styles,
            'include_skip_links': include_skip_links,
            'toc_headings': self._build_toc(document),
            'styles': self._get_css_styles() if include_styles else ""
        }
        
        return template.render(**context)
    
    def render_element(self, element: DocumentElement) -> str:
        """Render individual document element to HTML.
        
        Args:
            element: Document element to render
            
        Returns:
            HTML string for the element
        """
        element_type = element.type
        
        if element_type == ElementType.HEADING:
            return self._render_heading(element)
        elif element_type == ElementType.PARAGRAPH:
            return self._render_paragraph(element)
        elif element_type == ElementType.LIST:
            return self._render_list(element)
        elif element_type == ElementType.LIST_ITEM:
            return self._render_list_item(element)
        elif element_type == ElementType.TABLE:
            return self._render_table(element)
        elif element_type == ElementType.FIGURE:
            return self._render_figure(element)
        else:
            return self._render_generic(element)
    
    def _render_heading(self, heading: DocumentElement) -> str:
        """Render heading element."""
        if not isinstance(heading, Heading):
            level = 2  # Default fallback
        else:
            level = heading.level.value
        
        tag = f"h{level}"
        text = self._escape_html(heading.text)
        
        return f'<{tag} id="{heading.id}">{text}</{tag}>\n'
    
    def _render_paragraph(self, paragraph: DocumentElement) -> str:
        """Render paragraph element."""
        text = self._escape_html(paragraph.text)
        if not text.strip():
            return ""
        
        return f'<p id="{paragraph.id}">{text}</p>\n'
    
    def _render_list(self, list_element: DocumentElement) -> str:
        """Render list element."""
        if not isinstance(list_element, ListElement):
            tag = "ul"
            start_attr = ""
        else:
            if list_element.list_type.value == "ordered":
                tag = "ol"
                start_attr = f' start="{list_element.start_number}"' if list_element.start_number and list_element.start_number != 1 else ""
            else:
                tag = "ul"
                start_attr = ""
        
        html_parts = [f'<{tag} id="{list_element.id}"{start_attr}>\n']
        
        # Render child list items
        for child in list_element.children:
            if child.type == ElementType.LIST_ITEM:
                html_parts.append(self._render_list_item(child))
        
        html_parts.append(f'</{tag}>\n')
        return "".join(html_parts)
    
    def _render_list_item(self, list_item: DocumentElement) -> str:
        """Render list item element."""
        text = self._escape_html(list_item.text)
        
        # Render nested elements
        nested_content = ""
        for child in list_item.children:
            nested_content += self.render_element(child)
        
        content = text
        if nested_content:
            content += f"\n{nested_content}"
        
        return f'<li id="{list_item.id}">{content}</li>\n'
    
    def _render_table(self, table: DocumentElement) -> str:
        """Render table element."""
        if not isinstance(table, TableElement):
            return self._render_generic(table)
        
        html_parts = []
        
        # Table wrapper for accessibility
        html_parts.append(f'<div class="table-container">\n')
        
        # Table start with caption
        html_parts.append(f'<table id="{table.id}"')
        if table.summary:
            html_parts.append(f' aria-describedby="{table.id}-summary"')
        html_parts.append('>\n')
        
        # Caption
        if table.caption:
            html_parts.append(f'<caption>{self._escape_html(table.caption)}</caption>\n')
        
        # Summary (for screen readers)
        if table.summary:
            html_parts.append(f'<div id="{table.id}-summary" class="sr-only">{self._escape_html(table.summary)}</div>\n')
        
        # Table body (simplified - would need more complex logic for actual cell rendering)
        html_parts.append('<tbody>\n')
        
        # Render table cells (grouped by rows)
        cells_by_row = {}
        for child in table.children:
            if hasattr(child, 'row_index') and hasattr(child, 'column_index'):
                row = child.row_index
                if row not in cells_by_row:
                    cells_by_row[row] = []
                cells_by_row[row].append(child)
        
        for row_idx in sorted(cells_by_row.keys()):
            html_parts.append('<tr>\n')
            cells = sorted(cells_by_row[row_idx], key=lambda c: c.column_index)
            for cell in cells:
                cell_tag = "th" if getattr(cell, 'is_header', False) else "td"
                scope_attr = f' scope="{cell.scope}"' if getattr(cell, 'scope', None) else ""
                rowspan_attr = f' rowspan="{cell.row_span}"' if getattr(cell, 'row_span', 1) > 1 else ""
                colspan_attr = f' colspan="{cell.column_span}"' if getattr(cell, 'column_span', 1) > 1 else ""
                
                html_parts.append(f'<{cell_tag} id="{cell.id}"{scope_attr}{rowspan_attr}{colspan_attr}>')
                html_parts.append(self._escape_html(cell.text))
                html_parts.append(f'</{cell_tag}>\n')
            html_parts.append('</tr>\n')
        
        html_parts.append('</tbody>\n</table>\n</div>\n')
        return "".join(html_parts)
    
    def _render_figure(self, figure: DocumentElement) -> str:
        """Render figure element."""
        if not isinstance(figure, Figure):
            return self._render_generic(figure)
        
        html_parts = []
        
        html_parts.append(f'<figure id="{figure.id}" class="document-figure">\n')
        
        # Image or placeholder
        if figure.image_url:
            alt_text = figure.alt_text or ""
            html_parts.append(f'<img src="{figure.image_url}" alt="{self._escape_html(alt_text)}" />\n')
        else:
            # Placeholder for missing image
            alt_text = figure.alt_text or "Figure content not available"
            html_parts.append(f'<div class="figure-placeholder" role="img" aria-label="{self._escape_html(alt_text)}">')
            html_parts.append(f'<span class="figure-text">{self._escape_html(alt_text)}</span>')
            html_parts.append('</div>\n')
        
        # Caption
        if figure.caption:
            html_parts.append(f'<figcaption>{self._escape_html(figure.caption)}</figcaption>\n')
        
        # Long description
        if figure.long_description:
            html_parts.append(f'<div class="long-description" id="{figure.id}-desc">')
            html_parts.append(f'<h4>Description:</h4>')
            html_parts.append(f'<p>{self._escape_html(figure.long_description)}</p>')
            html_parts.append('</div>\n')
        
        html_parts.append('</figure>\n')
        return "".join(html_parts)
    
    def _render_generic(self, element: DocumentElement) -> str:
        """Render generic element."""
        text = self._escape_html(element.text)
        if not text.strip():
            return ""
        
        return f'<div id="{element.id}" class="element-{element.type.value}">{text}</div>\n'
    
    def _build_toc(self, document: DocumentStructure) -> List[Dict[str, Any]]:
        """Build table of contents from headings."""
        headings = [elem for elem in document.elements if elem.type == ElementType.HEADING]
        
        toc_items = []
        for heading in headings:
            if isinstance(heading, Heading):
                toc_items.append({
                    'id': heading.id,
                    'text': heading.text,
                    'level': heading.level.value,
                    'page': heading.page_number
                })
        
        return toc_items
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def _safe_id_filter(self, text: str) -> str:
        """Convert text to safe HTML ID."""
        import re
        return re.sub(r'[^a-zA-Z0-9-_]', '-', text.lower()).strip('-')
    
    def _get_main_template(self) -> str:
        """Get the main HTML template."""
        return """<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    {% if include_styles %}
    <style>{{ styles }}</style>
    {% endif %}
</head>
<body>
    {% if include_skip_links %}
    <nav aria-label="Skip navigation">
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <a href="#table-of-contents" class="skip-link">Skip to table of contents</a>
    </nav>
    {% endif %}

    <header role="banner">
        <h1>{{ title }}</h1>
        <p class="document-meta">
            Document ID: {{ document.doc_id }} | 
            Pages: {{ document.total_pages }} | 
            Elements: {{ document.elements|length }}
        </p>
    </header>

    <nav id="table-of-contents" role="navigation" aria-label="Table of Contents">
        <h2>Table of Contents</h2>
        {% if toc_headings %}
        <ol class="toc-list">
            {% for heading in toc_headings %}
            <li class="toc-level-{{ heading.level }}">
                <a href="#{{ heading.id }}">{{ heading.text }}</a>
                <span class="page-ref">(Page {{ heading.page }})</span>
            </li>
            {% endfor %}
        </ol>
        {% else %}
        <p>No headings found in document.</p>
        {% endif %}
    </nav>

    <main id="main-content" role="main">
        {% for element in document.elements %}
            {% if element.type == 'heading' %}
                {% set level = element.level %}
                <h{{ level }} id="{{ element.id }}">{{ element.text }}</h{{ level }}>
            {% elif element.type == 'paragraph' %}
                <p id="{{ element.id }}">{{ element.text }}</p>
            {% elif element.type == 'figure' %}
                <figure id="{{ element.id }}" class="document-figure">
                    {% if element.image_url %}
                    <img src="{{ element.image_url }}" alt="{{ element.alt_text or '' }}" />
                    {% else %}
                    <div class="figure-placeholder" role="img" aria-label="{{ element.alt_text or 'Figure content not available' }}">
                        <span class="figure-text">{{ element.alt_text or 'Figure content not available' }}</span>
                    </div>
                    {% endif %}
                    {% if element.caption %}
                    <figcaption>{{ element.caption }}</figcaption>
                    {% endif %}
                </figure>
            {% elif element.type == 'table' %}
                <div class="table-container">
                    <table id="{{ element.id }}">
                        {% if element.caption %}
                        <caption>{{ element.caption }}</caption>
                        {% endif %}
                        <tbody>
                            <tr><td colspan="{{ element.columns }}">Table content: {{ element.text }}</td></tr>
                        </tbody>
                    </table>
                </div>
            {% elif element.type == 'list' %}
                {% if element.list_type == 'ordered' %}
                <ol id="{{ element.id }}">
                {% else %}
                <ul id="{{ element.id }}">
                {% endif %}
                    {% for child in element.children %}
                    {% if child.type == 'list_item' %}
                    <li id="{{ child.id }}">{{ child.text }}</li>
                    {% endif %}
                    {% endfor %}
                {% if element.list_type == 'ordered' %}
                </ol>
                {% else %}
                </ul>
                {% endif %}
            {% else %}
                <div id="{{ element.id }}" class="element-{{ element.type }}">{{ element.text }}</div>
            {% endif %}
        {% endfor %}
    </main>

    <footer role="contentinfo">
        <p>Generated by PDF Accessibility Worker | 
           Created: {{ document.created_at }} | 
           Updated: {{ document.updated_at }}
        </p>
    </footer>
</body>
</html>"""
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for accessible document."""
        return """
/* Skip links for keyboard navigation */
.skip-link {
    position: absolute;
    top: -40px;
    left: 6px;
    background: #000;
    color: white;
    padding: 8px;
    text-decoration: none;
    border-radius: 4px;
    z-index: 1000;
}

.skip-link:focus {
    top: 6px;
}

/* Screen reader only content */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* Document layout */
body {
    font-family: Georgia, 'Times New Roman', serif;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
    background: #fff;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    font-family: Arial, Helvetica, sans-serif;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    line-height: 1.2;
}

h1 { font-size: 2em; color: #2c3e50; }
h2 { font-size: 1.5em; color: #34495e; }
h3 { font-size: 1.25em; color: #34495e; }
h4 { font-size: 1.1em; color: #34495e; }
h5 { font-size: 1em; font-weight: bold; }
h6 { font-size: 1em; font-weight: bold; font-style: italic; }

/* Paragraphs */
p {
    margin-bottom: 1em;
}

/* Lists */
ul, ol {
    padding-left: 2em;
    margin-bottom: 1em;
}

li {
    margin-bottom: 0.25em;
}

/* Table of contents */
#table-of-contents {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 4px;
    padding: 20px;
    margin-bottom: 2em;
}

.toc-list {
    list-style: none;
    padding-left: 0;
}

.toc-list li {
    margin-bottom: 0.5em;
}

.toc-level-1 { margin-left: 0; font-weight: bold; }
.toc-level-2 { margin-left: 1em; }
.toc-level-3 { margin-left: 2em; }
.toc-level-4 { margin-left: 3em; }
.toc-level-5 { margin-left: 4em; }
.toc-level-6 { margin-left: 5em; }

.page-ref {
    color: #666;
    font-size: 0.9em;
    margin-left: 0.5em;
}

/* Tables */
.table-container {
    overflow-x: auto;
    margin-bottom: 1em;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1em;
    border: 2px solid #333;
}

th, td {
    border: 1px solid #666;
    padding: 8px 12px;
    text-align: left;
    vertical-align: top;
}

th {
    background: #f1f3f4;
    font-weight: bold;
}

caption {
    font-weight: bold;
    margin-bottom: 0.5em;
    text-align: left;
    caption-side: top;
}

/* Figures */
.document-figure {
    margin: 1.5em 0;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 15px;
    background: #fafafa;
}

.figure-placeholder {
    background: #e9ecef;
    border: 2px dashed #6c757d;
    padding: 40px;
    text-align: center;
    border-radius: 4px;
    color: #495057;
}

.figure-text {
    font-style: italic;
}

figcaption {
    margin-top: 10px;
    font-style: italic;
    color: #666;
}

.long-description {
    margin-top: 15px;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 4px;
    border-left: 4px solid #007bff;
}

.long-description h4 {
    margin-top: 0;
    font-size: 1em;
    color: #007bff;
}

/* Links */
a {
    color: #007bff;
    text-decoration: underline;
}

a:hover, a:focus {
    color: #0056b3;
    background-color: #fff3cd;
    outline: 2px solid #007bff;
    outline-offset: 2px;
}

/* Focus indicators */
*:focus {
    outline: 2px solid #007bff;
    outline-offset: 2px;
}

/* Document metadata */
.document-meta {
    color: #666;
    font-size: 0.9em;
    margin-bottom: 2em;
}

/* Footer */
footer {
    margin-top: 3em;
    padding-top: 2em;
    border-top: 1px solid #e9ecef;
    color: #666;
    font-size: 0.9em;
}

/* Print styles */
@media print {
    .skip-link, #table-of-contents {
        display: none;
    }
    
    body {
        font-size: 12pt;
        line-height: 1.4;
    }
    
    h1 { font-size: 18pt; }
    h2 { font-size: 16pt; }
    h3 { font-size: 14pt; }
    h4, h5, h6 { font-size: 12pt; }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
    body {
        background: white;
        color: black;
    }
    
    th {
        background: white;
        border: 2px solid black;
    }
    
    td {
        border: 1px solid black;
    }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
"""
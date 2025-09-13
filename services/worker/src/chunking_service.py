"""
LLM Corpus Preparation Service - Chunking and Content Processing
"""

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for preparing document content for LLM consumption."""

    def __init__(self, max_chunk_size: int = 2000, chunk_overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def create_document_corpus(
        self,
        doc_id: str,
        document_structure: dict[str, Any],
        textract_results: dict[str, Any] | None = None,
        alt_text_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a complete document corpus for LLM processing.

        Args:
            doc_id: Document identifier
            document_structure: Structured document from structure service
            textract_results: Raw Textract output with queries
            alt_text_data: Alt-text data for figures

        Returns:
            DocumentCorpus dictionary ready for embeddings
        """
        try:
            logger.info(f"Creating document corpus for {doc_id}")

            # Extract basic metadata
            metadata = self._extract_document_metadata(
                document_structure,
                textract_results
            )

            # Create chunks from structured elements
            chunks = self._create_chunks_from_structure(
                doc_id,
                document_structure.get("elements", []),
                alt_text_data
            )

            # Build section hierarchy
            chunks_with_hierarchy = self._build_section_hierarchy(chunks)

            # Calculate corpus statistics
            corpus_stats = self._calculate_corpus_stats(chunks_with_hierarchy)

            # Create final corpus
            corpus = {
                "docId": doc_id,
                "metadata": metadata,
                "totalChunks": len(chunks_with_hierarchy),
                "chunks": chunks_with_hierarchy,
                **corpus_stats,
                "processedAt": datetime.utcnow(),
                "processingVersion": "1.0",
            }

            logger.info(f"Created corpus with {len(chunks_with_hierarchy)} chunks for document {doc_id}")
            return corpus

        except Exception as e:
            logger.error(f"Failed to create document corpus: {e}")
            raise

    def _extract_document_metadata(
        self,
        document_structure: dict[str, Any],
        textract_results: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Extract enhanced metadata from document structure and Textract queries."""

        metadata = {
            "title": document_structure.get("title"),
            "language": "en",  # Default, could be detected
        }

        # Add Textract query results if available
        if textract_results and "extracted_metadata" in textract_results:
            extracted_meta = textract_results["extracted_metadata"]
            if extracted_meta:
                metadata.update({
                    "author": extracted_meta.get("author"),
                    "subject": extracted_meta.get("subject"),
                    "keyTopics": extracted_meta.get("key_topics"),
                    "mainHeading": extracted_meta.get("main_heading"),
                })

        return metadata

    def _create_chunks_from_structure(
        self,
        doc_id: str,
        elements: list[dict[str, Any]],
        alt_text_data: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Create text chunks from structured document elements."""

        chunks = []
        alt_text_map = self._build_alt_text_map(alt_text_data) if alt_text_data else {}

        for i, element in enumerate(elements):
            self._determine_chunk_type(element)

            # Handle different element types
            if element.get("type") == "heading":
                chunk = self._create_heading_chunk(doc_id, i, element)
            elif element.get("type") == "table":
                chunk = self._create_table_chunk(doc_id, i, element)
            elif element.get("type") == "figure":
                chunk = self._create_figure_chunk(doc_id, i, element, alt_text_map)
            elif element.get("type") == "list":
                chunk = self._create_list_chunk(doc_id, i, element)
            else:  # paragraph or other text
                chunk = self._create_text_chunk(doc_id, i, element)

            # Split large chunks if needed
            if chunk["characterCount"] > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(chunk)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk)

        return chunks

    def _determine_chunk_type(self, element: dict[str, Any]) -> str:
        """Determine the appropriate chunk type for an element."""
        element_type = element.get("type", "paragraph")

        # Map element types to chunk types
        type_mapping = {
            "heading": "heading",
            "table": "table",
            "figure": "figure",
            "list": "list",
            "paragraph": "text"
        }

        return type_mapping.get(element_type, "text")

    def _create_heading_chunk(self, doc_id: str, index: int, element: dict[str, Any]) -> dict[str, Any]:
        """Create a chunk for heading elements."""

        text = element.get("text", "").strip()
        cleaned_text = self._clean_text_for_llm(text)

        return {
            "id": f"{doc_id}_chunk_{index}",
            "docId": doc_id,
            "chunkIndex": index,
            "type": "heading",
            "content": text,
            "cleanedContent": cleaned_text,
            "page": element.get("page_number", 1),
            "boundingBox": element.get("bounding_box"),
            "sectionPath": [text],  # Heading creates new section
            "hierarchyLevel": element.get("level", 1),
            "characterCount": len(text),
            "wordCount": len(text.split()),
            "extractionMethod": "textract",
            "extractionConfidence": element.get("confidence", 0.8),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

    def _create_table_chunk(self, doc_id: str, index: int, element: dict[str, Any]) -> dict[str, Any]:
        """Create a chunk for table elements with structured representation."""

        text = element.get("text", "").strip()
        cleaned_text = self._clean_text_for_llm(text)

        # Generate markdown representation with enhanced structure support
        markdown_table = self._convert_table_to_markdown(element)

        # Create enhanced JSON representation
        json_representation = self._enhance_table_json_representation(element)

        return {
            "id": f"{doc_id}_chunk_{index}",
            "docId": doc_id,
            "chunkIndex": index,
            "type": "table",
            "content": text,
            "cleanedContent": markdown_table or cleaned_text,
            "page": element.get("page_number", 1),
            "boundingBox": element.get("bounding_box"),
            "sectionPath": [],  # Will be filled by hierarchy builder
            "characterCount": len(text),
            "wordCount": len(text.split()),
            "tableStructure": {
                "rows": element.get("rows", 0),
                "columns": element.get("columns", 0),
                "hasHeaders": element.get("has_headers", False),
                "markdownRepresentation": markdown_table,
                "jsonRepresentation": json_representation,
                "columnTypes": json_representation.get("structure", {}).get("column_types", []),
                "accessibility": json_representation.get("accessibility", {}),
            },
            "extractionMethod": "textract",
            "extractionConfidence": element.get("confidence", 0.8),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

    def _create_figure_chunk(
        self,
        doc_id: str,
        index: int,
        element: dict[str, Any],
        alt_text_map: dict[str, str]
    ) -> dict[str, Any]:
        """Create a chunk for figure elements with alt-text."""

        figure_id = element.get("id", f"figure_{index}")
        alt_text = alt_text_map.get(figure_id, "")
        caption = element.get("caption", "")

        # Combine alt-text and caption
        full_text = ""
        if alt_text:
            full_text += f"Alt text: {alt_text}"
        if caption:
            full_text += f"\nCaption: {caption}"
        if not full_text:
            full_text = element.get("text", "Figure")

        cleaned_text = self._clean_text_for_llm(full_text)

        return {
            "id": f"{doc_id}_chunk_{index}",
            "docId": doc_id,
            "chunkIndex": index,
            "type": "figure",
            "content": full_text,
            "cleanedContent": cleaned_text,
            "page": element.get("page_number", 1),
            "boundingBox": element.get("bounding_box"),
            "sectionPath": [],  # Will be filled by hierarchy builder
            "characterCount": len(full_text),
            "wordCount": len(full_text.split()),
            "altText": alt_text,
            "caption": caption,
            "figureType": element.get("figure_type", "image"),
            "extractionMethod": "textract",
            "extractionConfidence": element.get("confidence", 0.8),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

    def _create_list_chunk(self, doc_id: str, index: int, element: dict[str, Any]) -> dict[str, Any]:
        """Create a chunk for list elements."""

        text = element.get("text", "").strip()
        cleaned_text = self._clean_text_for_llm(text)

        return {
            "id": f"{doc_id}_chunk_{index}",
            "docId": doc_id,
            "chunkIndex": index,
            "type": "list",
            "content": text,
            "cleanedContent": cleaned_text,
            "page": element.get("page_number", 1),
            "boundingBox": element.get("bounding_box"),
            "sectionPath": [],  # Will be filled by hierarchy builder
            "hierarchyLevel": element.get("list_level", 1),
            "characterCount": len(text),
            "wordCount": len(text.split()),
            "extractionMethod": "textract",
            "extractionConfidence": element.get("confidence", 0.8),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

    def _create_text_chunk(self, doc_id: str, index: int, element: dict[str, Any]) -> dict[str, Any]:
        """Create a chunk for text/paragraph elements."""

        text = element.get("text", "").strip()
        cleaned_text = self._clean_text_for_llm(text)

        return {
            "id": f"{doc_id}_chunk_{index}",
            "docId": doc_id,
            "chunkIndex": index,
            "type": "text",
            "content": text,
            "cleanedContent": cleaned_text,
            "page": element.get("page_number", 1),
            "boundingBox": element.get("bounding_box"),
            "sectionPath": [],  # Will be filled by hierarchy builder
            "characterCount": len(text),
            "wordCount": len(text.split()),
            "hasCode": self._detect_code(text),
            "hasMath": self._detect_math(text),
            "hasLinks": self._detect_links(text),
            "extractionMethod": "textract",
            "extractionConfidence": element.get("confidence", 0.8),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

    def _split_large_chunk(self, chunk: dict[str, Any]) -> list[dict[str, Any]]:
        """Split large chunks while preserving meaning."""

        content = chunk["content"]
        if len(content) <= self.max_chunk_size:
            return [chunk]

        sub_chunks = []
        text_parts = self._smart_split_text(content, self.max_chunk_size, self.chunk_overlap)

        for i, part in enumerate(text_parts):
            sub_chunk = chunk.copy()
            sub_chunk["id"] = f"{chunk['id']}_part_{i}"
            sub_chunk["content"] = part
            sub_chunk["cleanedContent"] = self._clean_text_for_llm(part)
            sub_chunk["characterCount"] = len(part)
            sub_chunk["wordCount"] = len(part.split())
            sub_chunk["chunkIndex"] = f"{chunk['chunkIndex']}.{i}"
            sub_chunks.append(sub_chunk)

        return sub_chunks

    def _smart_split_text(self, text: str, max_size: int, overlap: int) -> list[str]:
        """Split text intelligently at sentence boundaries."""

        if len(text) <= max_size:
            return [text]

        # Split by sentences
        sentences = re.split(r'[.!?]+\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed the limit
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence + "."

            if len(test_chunk) <= max_size:
                current_chunk = test_chunk
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk)

                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    # Take last few sentences for overlap
                    overlap_text = self._get_text_overlap(current_chunk, overlap)
                    current_chunk = overlap_text + " " + sentence + "."
                else:
                    current_chunk = sentence + "."

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_text_overlap(self, text: str, target_length: int) -> str:
        """Get the last part of text up to target_length for overlap."""

        if len(text) <= target_length:
            return text

        # Find good breaking point near the end
        overlap_start = max(0, len(text) - target_length)
        overlap_text = text[overlap_start:]

        # Try to break at sentence boundary
        sentence_match = re.search(r'[.!?]+\s+', overlap_text)
        if sentence_match:
            return overlap_text[sentence_match.end():]

        return overlap_text

    def _build_section_hierarchy(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build section path hierarchy for all chunks."""

        current_sections = []

        for chunk in chunks:
            if chunk["type"] == "heading":
                level = chunk.get("hierarchyLevel", 1)
                heading_text = chunk["content"].strip()

                # Update section hierarchy
                # Remove sections at same or lower level
                current_sections = [s for s in current_sections if s["level"] < level]

                # Add this heading as new section
                current_sections.append({
                    "level": level,
                    "text": heading_text
                })

                # Set section path for heading itself
                chunk["sectionPath"] = [s["text"] for s in current_sections]

            else:
                # Non-heading elements inherit current section path
                chunk["sectionPath"] = [s["text"] for s in current_sections]

        return chunks

    def _build_alt_text_map(self, alt_text_data: dict[str, Any] | None) -> dict[str, str]:
        """Build map of figure IDs to approved alt-text."""

        alt_text_map = {}

        if not alt_text_data:
            return alt_text_map

        for figure in alt_text_data.get("figures", []):
            figure_id = figure.get("figure_id")
            approved_text = figure.get("approved_text")
            ai_text = figure.get("ai_text")

            # Use approved text if available, otherwise AI text
            if figure_id and (approved_text or ai_text):
                alt_text_map[figure_id] = approved_text or ai_text

        return alt_text_map

    def _calculate_corpus_stats(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate statistics for the document corpus."""

        total_chars = sum(chunk["characterCount"] for chunk in chunks)
        total_words = sum(chunk["wordCount"] for chunk in chunks)
        chunk_sizes = [chunk["characterCount"] for chunk in chunks]

        # Content type distribution
        content_types = {}
        for chunk in chunks:
            chunk_type = chunk["type"]
            content_types[chunk_type] = content_types.get(chunk_type, 0) + 1

        # Calculate size distribution
        chunk_sizes.sort()
        n = len(chunk_sizes)

        size_distribution = {
            "min": min(chunk_sizes) if chunk_sizes else 0,
            "max": max(chunk_sizes) if chunk_sizes else 0,
            "median": chunk_sizes[n // 2] if chunk_sizes else 0,
            "p95": chunk_sizes[int(n * 0.95)] if chunk_sizes else 0,
        }

        return {
            "totalCharacters": total_chars,
            "totalWords": total_words,
            "averageChunkSize": total_chars / len(chunks) if chunks else 0,
            "chunkSizeDistribution": size_distribution,
            "contentTypes": content_types,
        }

    def _clean_text_for_llm(self, text: str) -> str:
        """Clean and normalize text for LLM consumption."""

        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove or normalize special characters that might confuse LLMs
        text = re.sub(r'[^\w\s\.,;:!?\-\'\"()[\]{}]', ' ', text)

        # Remove excessive punctuation
        text = re.sub(r'[.,;]{3,}', '...', text)

        # Normalize quotes
        text = re.sub(r'[""]', '"', text)
        text = re.sub(r'['']', "'", text)

        return text.strip()

    def _detect_code(self, text: str) -> bool:
        """Detect if text contains code snippets."""

        code_indicators = [
            r'\b(function|class|def|public|private|protected)\b',
            r'\b(import|include|require|from)\b',
            r'[{}();]',
            r'\/\/|\/\*|\*\/',
            r'=>|->|<-',
        ]

        for pattern in code_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_math(self, text: str) -> bool:
        """Detect if text contains mathematical expressions."""

        math_indicators = [
            r'[∀∃∄∅∆∇∈∉∋∌∏∑∫∬∭]',  # Math symbols
            r'[αβγδεζηθικλμνξοπρστυφχψω]',  # Greek letters
            r'\b(equation|formula|theorem|proof|lemma)\b',
            r'[₀₁₂₃₄₅₆₇₈₉]|[⁰¹²³⁴⁵⁶⁷⁸⁹]',  # Sub/superscripts
            r'\$.*?\$',  # LaTeX math
        ]

        for pattern in math_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_links(self, text: str) -> bool:
        """Detect if text contains URLs or email addresses."""

        link_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]

        for pattern in link_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _convert_table_to_markdown(self, element: dict[str, Any]) -> str | None:
        """Convert table element to markdown representation with enhanced structure support."""

        rows = element.get("rows", 0)
        cols = element.get("columns", 0)

        if rows == 0 or cols == 0:
            return None

        # Check if we have structured table data
        table_data = element.get("table_data")
        if table_data:
            return self._build_markdown_table(table_data, element.get("has_headers", False))

        # Fall back to parsing from text content if available
        text = element.get("text", "")
        if text:
            return self._parse_table_from_text(text, rows, cols, element.get("has_headers", False))

        # Final fallback - basic placeholder
        return f"| Table ({rows}x{cols}) |\n|{'---|' * cols}\n| Content not available |"

    def _build_markdown_table(self, table_data: list[list[str]], has_headers: bool = False) -> str:
        """Build markdown table from structured data."""

        if not table_data:
            return "| Empty table |"

        markdown_rows = []

        for row_idx, row in enumerate(table_data):
            # Clean and escape cell content
            cleaned_cells = []
            for cell in row:
                if cell is None:
                    cleaned_cells.append("")
                else:
                    # Clean cell content for markdown
                    cell_str = str(cell).strip()
                    # Escape markdown special characters in table cells
                    cell_str = cell_str.replace("|", "\\|").replace("\n", " ").replace("\r", "")
                    cleaned_cells.append(cell_str)

            # Build table row
            markdown_row = "| " + " | ".join(cleaned_cells) + " |"
            markdown_rows.append(markdown_row)

            # Add separator after header row
            if row_idx == 0 and has_headers:
                separator = "|" + "|".join(["---"] * len(cleaned_cells)) + "|"
                markdown_rows.append(separator)

        return "\n".join(markdown_rows)

    def _parse_table_from_text(self, text: str, rows: int, cols: int, has_headers: bool = False) -> str:
        """Parse table structure from raw text content."""

        # Attempt to identify table structure from text
        lines = text.split("\n")
        table_lines = [line.strip() for line in lines if line.strip()]

        if not table_lines:
            return f"| Table ({rows}x{cols}) - No content |\n|---|"

        # Simple heuristic: try to identify potential table rows
        potential_rows = []

        for line in table_lines:
            # Look for patterns that suggest tabular data
            if any(separator in line for separator in ['\t', '  ', '|']):
                # Split on common separators
                if '\t' in line:
                    cells = line.split('\t')
                elif '|' in line:
                    cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                else:
                    # Split on multiple spaces
                    cells = [cell.strip() for cell in line.split('  ') if cell.strip()]

                if len(cells) >= 2:  # At least 2 columns for a table
                    potential_rows.append(cells)

        # Build markdown table from identified rows
        if potential_rows:
            return self._build_markdown_table(potential_rows[:rows], has_headers)
        else:
            # No clear structure - create a simple representation
            return f"""
| Table Content ({rows}x{cols}) |
|---|
| {text[:200]}... |
"""

    def _enhance_table_json_representation(self, element: dict[str, Any]) -> dict[str, Any]:
        """Create enhanced JSON representation for complex tables."""

        table_json = {
            "type": "table",
            "metadata": {
                "rows": element.get("rows", 0),
                "columns": element.get("columns", 0),
                "has_headers": element.get("has_headers", False),
                "table_id": element.get("id"),
                "page": element.get("page_number", 1),
                "confidence": element.get("confidence", 0.8),
            },
            "structure": {},
            "accessibility": {
                "has_caption": bool(element.get("caption")),
                "has_summary": bool(element.get("summary")),
                "header_scope": "col" if element.get("has_headers") else None,
            }
        }

        # Add structured data if available
        table_data = element.get("table_data")
        if table_data:
            table_json["data"] = {
                "rows": table_data,
                "headers": table_data[0] if element.get("has_headers") and table_data else None,
                "body": table_data[1:] if element.get("has_headers") and len(table_data) > 1 else table_data,
            }

            # Analyze column types
            if table_data and len(table_data) > 1:
                column_types = self._analyze_column_types(table_data, element.get("has_headers", False))
                table_json["structure"]["column_types"] = column_types

        # Add relationships to other elements
        table_json["relationships"] = {
            "caption_element_id": element.get("caption_element_id"),
            "following_elements": element.get("following_elements", []),
            "preceding_elements": element.get("preceding_elements", []),
        }

        return table_json

    def _analyze_column_types(self, table_data: list[list[str]], has_headers: bool = False) -> list[dict[str, Any]]:
        """Analyze column data types and patterns."""

        if not table_data or len(table_data) < 2:
            return []

        # Skip header row if present
        data_rows = table_data[1:] if has_headers else table_data
        num_columns = len(table_data[0]) if table_data else 0

        column_analysis = []

        for col_idx in range(num_columns):
            column_values = []

            # Extract column values
            for row in data_rows:
                if col_idx < len(row) and row[col_idx]:
                    column_values.append(str(row[col_idx]).strip())

            if not column_values:
                column_analysis.append({"type": "empty", "pattern": None})
                continue

            # Analyze column type
            col_info = {
                "type": "text",  # default
                "pattern": None,
                "numeric_percentage": 0.0,
                "date_percentage": 0.0,
                "sample_values": column_values[:3],  # First 3 values as examples
            }

            # Count numeric values
            numeric_count = 0
            date_count = 0

            for value in column_values:
                # Check if numeric
                try:
                    float(value.replace(",", "").replace("$", "").replace("%", ""))
                    numeric_count += 1
                except ValueError:
                    pass

                # Check if date-like
                if any(pattern in value.lower() for pattern in ["jan", "feb", "mar", "apr", "may", "jun",
                                                               "jul", "aug", "sep", "oct", "nov", "dec",
                                                               "monday", "tuesday", "wednesday", "thursday",
                                                               "friday", "saturday", "sunday"]):
                    date_count += 1
                elif any(char in value for char in ["/", "-"]) and len(value) >= 6:
                    date_count += 1

            # Calculate percentages
            col_info["numeric_percentage"] = numeric_count / len(column_values)
            col_info["date_percentage"] = date_count / len(column_values)

            # Determine primary type
            if col_info["numeric_percentage"] > 0.7:
                col_info["type"] = "numeric"
            elif col_info["date_percentage"] > 0.5:
                col_info["type"] = "date"
            elif all(len(val) <= 10 and val.isalnum() for val in column_values):
                col_info["type"] = "category"
            else:
                col_info["type"] = "text"

            column_analysis.append(col_info)

        return column_analysis

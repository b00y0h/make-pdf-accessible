"""
LLM Corpus Preparation Service - Chunking and Content Processing
"""

import json
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for preparing document content for LLM consumption."""
    
    def __init__(self, max_chunk_size: int = 2000, chunk_overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        
    def create_document_corpus(
        self, 
        doc_id: str,
        document_structure: Dict[str, Any],
        textract_results: Optional[Dict[str, Any]] = None,
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
        document_structure: Dict[str, Any],
        textract_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
        elements: List[Dict[str, Any]],
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Create text chunks from structured document elements."""
        
        chunks = []
        alt_text_map = self._build_alt_text_map(alt_text_data) if alt_text_data else {}
        
        for i, element in enumerate(elements):
            chunk_type = self._determine_chunk_type(element)
            
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

    def _determine_chunk_type(self, element: Dict[str, Any]) -> str:
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

    def _create_heading_chunk(self, doc_id: str, index: int, element: Dict[str, Any]) -> Dict[str, Any]:
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

    def _create_table_chunk(self, doc_id: str, index: int, element: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chunk for table elements with structured representation."""
        
        text = element.get("text", "").strip()
        cleaned_text = self._clean_text_for_llm(text)
        
        # Generate markdown representation (simplified)
        markdown_table = self._convert_table_to_markdown(element)
        
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
        element: Dict[str, Any],
        alt_text_map: Dict[str, str]
    ) -> Dict[str, Any]:
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

    def _create_list_chunk(self, doc_id: str, index: int, element: Dict[str, Any]) -> Dict[str, Any]:
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

    def _create_text_chunk(self, doc_id: str, index: int, element: Dict[str, Any]) -> Dict[str, Any]:
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

    def _split_large_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    def _smart_split_text(self, text: str, max_size: int, overlap: int) -> List[str]:
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

    def _build_section_hierarchy(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    def _build_alt_text_map(self, alt_text_data: Optional[Dict[str, Any]]) -> Dict[str, str]:
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

    def _calculate_corpus_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    def _convert_table_to_markdown(self, element: Dict[str, Any]) -> Optional[str]:
        """Convert table element to markdown representation."""
        
        # This would need actual table cell data from Textract
        # For now, return a placeholder
        rows = element.get("rows", 0)
        cols = element.get("columns", 0)
        
        if rows == 0 or cols == 0:
            return None
            
        # Simple placeholder - in reality, would parse Textract table cells
        text = element.get("text", "")
        return f"Table ({rows}x{cols}): {text[:200]}..."
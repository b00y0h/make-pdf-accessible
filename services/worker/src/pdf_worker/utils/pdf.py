"""PDF utilities for processing and analysis."""

import io
from typing import Any

import PyPDF2
from aws_lambda_powertools import Logger, Tracer
from pdfminer.layout import LTFigure, LTImage, LTTextBox

from pdf_worker.core.exceptions import PDFProcessingError

logger = Logger()
tracer = Tracer()


class PDFUtils:
    """Utility class for PDF processing and analysis."""

    @staticmethod
    @tracer.capture_method
    def analyze_pdf_content_type(pdf_data: bytes) -> tuple[bool, int, dict[str, Any]]:
        """Analyze PDF to determine if it's image-based or text-based.
        
        Args:
            pdf_data: PDF file content as bytes
            
        Returns:
            Tuple of (is_image_based, page_count, metadata)
            
        Raises:
            PDFProcessingError: If PDF analysis fails
        """
        try:
            pdf_stream = io.BytesIO(pdf_data)
            reader = PyPDF2.PdfReader(pdf_stream)

            page_count = len(reader.pages)
            total_text_length = 0
            text_per_page = []

            # Sample pages to determine content type (max 5 pages for efficiency)
            pages_to_check = min(5, page_count)

            for i in range(pages_to_check):
                try:
                    page = reader.pages[i]
                    text = page.extract_text().strip()
                    text_length = len(text)
                    total_text_length += text_length
                    text_per_page.append(text_length)

                except Exception as e:
                    logger.warning(f"Failed to extract text from page {i + 1}: {e}")
                    text_per_page.append(0)

            # Calculate metrics
            avg_text_per_page = total_text_length / pages_to_check if pages_to_check > 0 else 0
            text_variance = sum((x - avg_text_per_page) ** 2 for x in text_per_page) / pages_to_check

            # Heuristics for determining image-based content
            # Consider image-based if:
            # 1. Very little text per page (< 50 chars average)
            # 2. High variance in text content (some pages have much more/less text)
            is_image_based = (
                avg_text_per_page < 50 or  # Very little text
                (avg_text_per_page < 200 and text_variance > 10000)  # Inconsistent text distribution
            )

            # Get additional metadata
            metadata = {
                'avg_text_per_page': avg_text_per_page,
                'text_variance': text_variance,
                'total_text_length': total_text_length,
                'pages_analyzed': pages_to_check,
                'text_per_page': text_per_page[:pages_to_check]
            }

            # Add PDF metadata if available
            if reader.metadata:
                metadata.update({
                    'title': reader.metadata.get('/Title'),
                    'author': reader.metadata.get('/Author'),
                    'creator': reader.metadata.get('/Creator'),
                    'producer': reader.metadata.get('/Producer'),
                    'creation_date': reader.metadata.get('/CreationDate'),
                    'modification_date': reader.metadata.get('/ModDate')
                })

            logger.info(
                f"PDF analysis: {page_count} pages, {avg_text_per_page:.1f} chars/page, "
                f"image-based: {is_image_based}"
            )

            return is_image_based, page_count, metadata

        except Exception as e:
            raise PDFProcessingError(f"Failed to analyze PDF content type: {e}") from e

    @staticmethod
    @tracer.capture_method
    def extract_text_by_pages(pdf_data: bytes) -> dict[int, str]:
        """Extract text from PDF using pdfminer.six with better layout preservation.
        
        Args:
            pdf_data: PDF file content as bytes
            
        Returns:
            Dictionary mapping page numbers (1-based) to text content
            
        Raises:
            PDFProcessingError: If text extraction fails
        """
        try:
            from pdfminer.converter import TextConverter
            from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
            from pdfminer.pdfpage import PDFPage

            text_by_page = {}
            pdf_stream = io.BytesIO(pdf_data)
            resource_manager = PDFResourceManager()

            for page_num, page in enumerate(PDFPage.get_pages(pdf_stream), 1):
                output_stream = io.StringIO()
                device = TextConverter(resource_manager, output_stream)
                interpreter = PDFPageInterpreter(resource_manager, device)

                try:
                    interpreter.process_page(page)
                    text = output_stream.getvalue()
                    text_by_page[page_num] = text

                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    text_by_page[page_num] = ""

                finally:
                    device.close()
                    output_stream.close()

            logger.info(f"Extracted text from {len(text_by_page)} pages using pdfminer")
            return text_by_page

        except Exception as e:
            raise PDFProcessingError(f"Failed to extract text by pages: {e}") from e

    @staticmethod
    @tracer.capture_method
    def extract_layout_objects(pdf_data: bytes) -> dict[int, list[dict[str, Any]]]:
        """Extract layout objects (text boxes, figures, etc.) from PDF.
        
        Args:
            pdf_data: PDF file content as bytes
            
        Returns:
            Dictionary mapping page numbers to lists of layout objects
            
        Raises:
            PDFProcessingError: If layout extraction fails
        """
        try:
            from pdfminer.converter import PDFPageAggregator
            from pdfminer.layout import LAParams
            from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
            from pdfminer.pdfpage import PDFPage

            layout_by_page = {}
            pdf_stream = io.BytesIO(pdf_data)
            resource_manager = PDFResourceManager()

            # Configure layout analysis parameters
            laparams = LAParams(
                char_margin=2.0,
                line_margin=0.5,
                word_margin=0.1
            )

            device = PDFPageAggregator(resource_manager, laparams=laparams)
            interpreter = PDFPageInterpreter(resource_manager, device)

            for page_num, page in enumerate(PDFPage.get_pages(pdf_stream), 1):
                try:
                    interpreter.process_page(page)
                    layout = device.get_result()

                    page_objects = []

                    def extract_objects(obj):
                        """Recursively extract objects from layout."""
                        if isinstance(obj, LTTextBox):
                            page_objects.append({
                                'type': 'textbox',
                                'bbox': obj.bbox,
                                'text': obj.get_text().strip(),
                                'width': obj.width,
                                'height': obj.height
                            })

                        elif isinstance(obj, LTFigure):
                            page_objects.append({
                                'type': 'figure',
                                'bbox': obj.bbox,
                                'width': obj.width,
                                'height': obj.height
                            })

                        elif isinstance(obj, LTImage):
                            page_objects.append({
                                'type': 'image',
                                'bbox': obj.bbox,
                                'width': obj.width,
                                'height': obj.height,
                                'name': getattr(obj, 'name', None),
                                'srcsize': getattr(obj, 'srcsize', None)
                            })

                        # Recursively process children
                        if hasattr(obj, '__iter__'):
                            for child in obj:
                                extract_objects(child)

                    extract_objects(layout)
                    layout_by_page[page_num] = page_objects

                except Exception as e:
                    logger.warning(f"Failed to extract layout from page {page_num}: {e}")
                    layout_by_page[page_num] = []

            total_objects = sum(len(objects) for objects in layout_by_page.values())
            logger.info(f"Extracted {total_objects} layout objects from {len(layout_by_page)} pages")

            return layout_by_page

        except Exception as e:
            raise PDFProcessingError(f"Failed to extract layout objects: {e}") from e

    @staticmethod
    @tracer.capture_method
    def detect_reading_order(layout_objects: list[dict[str, Any]]) -> list[int]:
        """Detect reading order of layout objects on a page.
        
        Args:
            layout_objects: List of layout objects with bbox information
            
        Returns:
            List of object indices in reading order
        """
        if not layout_objects:
            return []

        # Sort objects by top-to-bottom, left-to-right reading order
        objects_with_index = [(i, obj) for i, obj in enumerate(layout_objects)]

        # Sort by y-coordinate (top to bottom) then x-coordinate (left to right)
        # Note: PDF coordinates have origin at bottom-left, so higher y = higher on page
        objects_with_index.sort(key=lambda x: (-x[1]['bbox'][3], x[1]['bbox'][0]))

        reading_order = [i for i, _ in objects_with_index]

        logger.debug(f"Determined reading order for {len(reading_order)} objects")
        return reading_order

    @staticmethod
    @tracer.capture_method
    def estimate_font_sizes(text_objects: list[dict[str, Any]]) -> dict[str, Any]:
        """Estimate font sizes from text objects to identify headings.
        
        Args:
            text_objects: List of text objects with bbox information
            
        Returns:
            Dictionary with font size analysis
        """
        if not text_objects:
            return {'font_sizes': [], 'avg_font_size': 0, 'heading_threshold': 0}

        # Estimate font size based on text box height
        font_sizes = []
        for obj in text_objects:
            if obj.get('type') == 'textbox' and obj.get('text'):
                # Rough estimation: font size ≈ height of text box
                height = obj['bbox'][3] - obj['bbox'][1]
                # Account for line spacing by using a factor
                estimated_font_size = height * 0.7
                font_sizes.append(estimated_font_size)

        if not font_sizes:
            return {'font_sizes': [], 'avg_font_size': 0, 'heading_threshold': 0}

        # Calculate statistics
        avg_font_size = sum(font_sizes) / len(font_sizes)
        font_sizes_sorted = sorted(font_sizes, reverse=True)

        # Consider text 20% larger than average as potential headings
        heading_threshold = avg_font_size * 1.2

        analysis = {
            'font_sizes': font_sizes,
            'avg_font_size': avg_font_size,
            'max_font_size': max(font_sizes),
            'min_font_size': min(font_sizes),
            'heading_threshold': heading_threshold,
            'potential_headings': sum(1 for size in font_sizes if size > heading_threshold)
        }

        logger.debug(f"Font analysis: avg={avg_font_size:.1f}, threshold={heading_threshold:.1f}")
        return analysis

    @staticmethod
    def validate_pdf(pdf_data: bytes) -> dict[str, Any]:
        """Validate PDF file integrity and accessibility.
        
        Args:
            pdf_data: PDF file content as bytes
            
        Returns:
            Validation results dictionary
            
        Raises:
            PDFProcessingError: If validation fails
        """
        try:
            validation_results = {
                'is_valid': True,
                'is_encrypted': False,
                'has_text_content': False,
                'page_count': 0,
                'file_size': len(pdf_data),
                'issues': []
            }

            pdf_stream = io.BytesIO(pdf_data)

            try:
                reader = PyPDF2.PdfReader(pdf_stream)
                validation_results['page_count'] = len(reader.pages)

                # Check if encrypted
                if reader.is_encrypted:
                    validation_results['is_encrypted'] = True
                    validation_results['issues'].append('PDF is password protected')

                # Check for text content
                if validation_results['page_count'] > 0 and not reader.is_encrypted:
                    try:
                        sample_text = reader.pages[0].extract_text().strip()
                        validation_results['has_text_content'] = len(sample_text) > 0
                    except Exception:
                        validation_results['issues'].append('Unable to extract text from PDF')

                # Check metadata
                if reader.metadata:
                    validation_results['has_metadata'] = True
                    if reader.metadata.get('/Title'):
                        validation_results['has_title'] = True

            except PyPDF2.PdfReadError as e:
                validation_results['is_valid'] = False
                validation_results['issues'].append(f'PDF read error: {str(e)}')

            except Exception as e:
                validation_results['is_valid'] = False
                validation_results['issues'].append(f'Validation error: {str(e)}')

            # File size checks
            if validation_results['file_size'] > 100 * 1024 * 1024:  # 100MB
                validation_results['issues'].append('PDF file is very large (>100MB)')

            return validation_results

        except Exception as e:
            raise PDFProcessingError(f"Failed to validate PDF: {e}") from e

    @staticmethod
    def extract_images_info(pdf_data: bytes) -> list[dict[str, Any]]:
        """Extract information about images in the PDF.
        
        Args:
            pdf_data: PDF file content as bytes
            
        Returns:
            List of image information dictionaries
        """
        images_info = []

        try:
            pdf_stream = io.BytesIO(pdf_data)
            reader = PyPDF2.PdfReader(pdf_stream)

            for page_num, page in enumerate(reader.pages, 1):
                if '/XObject' in page.get('/Resources', {}):
                    xobjects = page['/Resources']['/XObject']

                    for obj_name in xobjects:
                        obj = xobjects[obj_name]

                        # Check if this is an image
                        if obj.get('/Subtype') == '/Image':
                            image_info = {
                                'page': page_num,
                                'name': str(obj_name),
                                'width': obj.get('/Width', 0),
                                'height': obj.get('/Height', 0),
                                'bits_per_component': obj.get('/BitsPerComponent', 0),
                                'color_space': str(obj.get('/ColorSpace', 'Unknown')),
                                'filter': obj.get('/Filter')
                            }
                            images_info.append(image_info)

            logger.info(f"Found {len(images_info)} images in PDF")

        except Exception as e:
            logger.warning(f"Failed to extract image info: {e}")

        return images_info

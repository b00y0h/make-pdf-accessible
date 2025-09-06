import json
import uuid
from typing import Dict, Any, Optional, List, Tuple
import boto3
from botocore.exceptions import ClientError
from pdfminer.high_level import extract_text_to_fp, extract_pages
from pdfminer.layout import LTTextBox, LTTextLine, LTFigure, LTImage
from pdfminer.converter import PDFPageInterpreter
from io import StringIO
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from models import (
    DocumentStructure, DocumentElement, ElementType, HeadingLevel,
    Heading, Paragraph, ListElement, ListItem, TableElement, Figure,
    BoundingBox, BedrockRequest, BedrockResponse
)

logger = Logger()
tracer = Tracer()
metrics = Metrics()


class StructureServiceError(Exception):
    """Custom exception for structure service errors."""
    pass


class StructureService:
    """Service for analyzing document structure using Textract + PDF text + Bedrock."""
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bedrock = boto3.client('bedrock-runtime')
        self.bucket_name = self._get_bucket_name()
    
    def _get_bucket_name(self) -> str:
        """Get the S3 bucket name from environment."""
        import os
        bucket = os.getenv('PDF_DERIVATIVES_BUCKET')
        if not bucket:
            raise StructureServiceError("PDF_DERIVATIVES_BUCKET environment variable not set")
        return bucket
    
    @tracer.capture_method
    def extract_pdf_text(self, s3_key: str) -> Dict[int, str]:
        """
        Extract text from PDF using pdfminer.six for text-based content.
        
        Returns:
            Dictionary mapping page numbers to text content
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=s3_key)
            pdf_content = response['Body'].read()
            
            # Extract text by pages
            text_by_page = {}
            output = StringIO()
            
            # Use pdfminer to extract text with better layout preservation
            from pdfminer.pdfpage import PDFPage
            from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
            from pdfminer.converter import TextConverter
            from io import BytesIO
            
            pdf_file = BytesIO(pdf_content)
            resource_manager = PDFResourceManager()
            
            for page_num, page in enumerate(PDFPage.get_pages(pdf_file), 1):
                output = StringIO()
                device = TextConverter(resource_manager, output)
                interpreter = PDFPageInterpreter(resource_manager, device)
                interpreter.process_page(page)
                text = output.getvalue()
                text_by_page[page_num] = text
                device.close()
                output.close()
            
            logger.info(f"Extracted text from {len(text_by_page)} pages")
            return text_by_page
            
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {str(e)}")
            raise StructureServiceError(f"PDF text extraction failed: {str(e)}")
    
    @tracer.capture_method
    def load_textract_results(self, textract_s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Load Textract results from S3 if available.
        
        Returns:
            Textract results dictionary or None if not available
        """
        if not textract_s3_key:
            return None
            
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=textract_s3_key)
            textract_data = json.loads(response['Body'].read())
            logger.info(f"Loaded Textract results with {len(textract_data.get('blocks', []))} blocks")
            return textract_data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info("No Textract results available")
                return None
            logger.error(f"Failed to load Textract results: {e}")
            raise StructureServiceError(f"Failed to load Textract results: {e}")
    
    @tracer.capture_method
    def call_bedrock_claude(self, request: BedrockRequest) -> BedrockResponse:
        """
        Call Bedrock Claude 3.5 for document structure analysis.
        """
        try:
            # Prepare the request payload for Claude 3.5 Sonnet
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{request.instructions}\n\n{request.content}"
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            
            # Parse response
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            usage = result.get('usage', {})
            
            logger.info(f"Bedrock analysis completed, tokens used: {usage}")
            metrics.add_metric(name="BedrockTokensUsed", unit=MetricUnit.Count, 
                             value=usage.get('total_tokens', 0))
            
            return BedrockResponse(content=content, usage=usage)
            
        except ClientError as e:
            logger.error(f"Bedrock API call failed: {e}")
            metrics.add_metric(name="BedrockAPIErrors", unit=MetricUnit.Count, value=1)
            raise StructureServiceError(f"Bedrock API call failed: {e}")
    
    @tracer.capture_method
    def analyze_document_structure(self, pdf_text: Dict[int, str], 
                                 textract_data: Optional[Dict[str, Any]]) -> DocumentStructure:
        """
        Analyze document structure using combined PDF text and Textract data with Bedrock.
        """
        try:
            # Combine all text content
            all_text = "\n".join([f"=== PAGE {page} ===\n{text}" 
                                for page, text in pdf_text.items()])
            
            # Add Textract structure information if available
            textract_info = ""
            if textract_data:
                blocks = textract_data.get('blocks', [])
                table_blocks = [b for b in blocks if b.get('BlockType') == 'TABLE']
                if table_blocks:
                    textract_info = f"\n\nTEXTRACT DETECTED {len(table_blocks)} TABLES"
            
            # Prepare Bedrock analysis prompt
            instructions = """
            Analyze this document and identify its logical structure. Return a JSON response with the following format:

            {
              "title": "Document title if identifiable",
              "elements": [
                {
                  "id": "unique_id",
                  "type": "heading|paragraph|list|table|figure",
                  "page_number": 1,
                  "text": "element text content",
                  "level": 1-6 (for headings only),
                  "confidence": 0.95
                }
              ],
              "reading_order": ["element_id_1", "element_id_2", ...]
            }

            Key requirements:
            1. Identify headings by font size, formatting, and context
            2. Recognize lists (bulleted and numbered)
            3. Detect tables and their basic structure
            4. Identify figures/images and their captions
            5. Maintain logical reading order
            6. Assign confidence scores (0.0-1.0)
            
            Focus on semantic structure, not visual formatting. Be conservative with heading levels.
            """
            
            bedrock_request = BedrockRequest(
                content=all_text + textract_info,
                instructions=instructions,
                max_tokens=4000
            )
            
            # Get Bedrock analysis
            bedrock_response = self.call_bedrock_claude(bedrock_request)
            
            # Parse Bedrock response
            try:
                structure_data = json.loads(bedrock_response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from response if wrapped in explanation
                content = bedrock_response.content
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    structure_data = json.loads(content[start:end])
                else:
                    raise StructureServiceError("Could not parse Bedrock response as JSON")
            
            # Convert to DocumentStructure
            doc_structure = self._convert_to_document_structure(
                structure_data, pdf_text, textract_data
            )
            
            logger.info(f"Document structure analysis completed: {len(doc_structure.elements)} elements")
            metrics.add_metric(name="DocumentsStructured", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="ElementsDetected", unit=MetricUnit.Count, 
                             value=len(doc_structure.elements))
            
            return doc_structure
            
        except Exception as e:
            logger.error(f"Document structure analysis failed: {str(e)}")
            metrics.add_metric(name="StructureAnalysisErrors", unit=MetricUnit.Count, value=1)
            raise StructureServiceError(f"Structure analysis failed: {str(e)}")
    
    def _convert_to_document_structure(self, structure_data: Dict[str, Any], 
                                     pdf_text: Dict[int, str],
                                     textract_data: Optional[Dict[str, Any]]) -> DocumentStructure:
        """Convert Bedrock analysis results to DocumentStructure model."""
        
        elements = []
        for elem_data in structure_data.get('elements', []):
            element_type = ElementType(elem_data.get('type', ElementType.PARAGRAPH))
            
            # Create appropriate element type
            if element_type == ElementType.HEADING:
                element = Heading(
                    id=elem_data.get('id', str(uuid.uuid4())),
                    page_number=elem_data.get('page_number', 1),
                    text=elem_data.get('text', ''),
                    level=HeadingLevel(elem_data.get('level', 1)),
                    confidence=elem_data.get('confidence', 0.8)
                )
            elif element_type == ElementType.TABLE:
                element = TableElement(
                    id=elem_data.get('id', str(uuid.uuid4())),
                    page_number=elem_data.get('page_number', 1),
                    text=elem_data.get('text', ''),
                    confidence=elem_data.get('confidence', 0.8),
                    rows=elem_data.get('rows', 1),
                    columns=elem_data.get('columns', 1),
                    cells=elem_data.get('cells', [])
                )
            elif element_type == ElementType.LIST:
                element = ListElement(
                    id=elem_data.get('id', str(uuid.uuid4())),
                    page_number=elem_data.get('page_number', 1),
                    text=elem_data.get('text', ''),
                    confidence=elem_data.get('confidence', 0.8),
                    ordered=elem_data.get('ordered', False)
                )
            elif element_type == ElementType.FIGURE:
                element = Figure(
                    id=elem_data.get('id', str(uuid.uuid4())),
                    page_number=elem_data.get('page_number', 1),
                    text=elem_data.get('text', ''),
                    confidence=elem_data.get('confidence', 0.8),
                    caption=elem_data.get('caption')
                )
            else:
                # Default to paragraph
                element = Paragraph(
                    id=elem_data.get('id', str(uuid.uuid4())),
                    page_number=elem_data.get('page_number', 1),
                    text=elem_data.get('text', ''),
                    confidence=elem_data.get('confidence', 0.8)
                )
            
            elements.append(element)
        
        return DocumentStructure(
            doc_id=structure_data.get('doc_id', 'unknown'),
            title=structure_data.get('title'),
            total_pages=len(pdf_text),
            elements=elements,
            reading_order=structure_data.get('reading_order', [elem.id for elem in elements]),
            metadata={
                'analysis_method': 'bedrock_claude',
                'textract_available': textract_data is not None,
                'total_pages': len(pdf_text)
            }
        )
    
    @tracer.capture_method
    def save_document_structure(self, doc_id: str, structure: DocumentStructure) -> str:
        """
        Save document structure to S3 as JSON.
        
        Returns:
            S3 key where structure was saved
        """
        try:
            s3_key = f"pdf-derivatives/{doc_id}/structure/document.json"
            
            # Convert to dict for JSON serialization
            structure_dict = structure.dict()
            
            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(structure_dict, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Saved document structure to {s3_key}")
            metrics.add_metric(name="StructuresSaved", unit=MetricUnit.Count, value=1)
            
            return s3_key
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to save document structure: {error_code}")
            raise StructureServiceError(f"Failed to save document structure: {error_code}")
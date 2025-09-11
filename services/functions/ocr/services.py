import json
import time
from typing import Tuple

import boto3
import PyPDF2
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import ClientError
from models import OCRStatus, TextractBlock, TextractJobStatus, TextractResponse, TextractQueryResult, DocumentMetadata

logger = Logger()
tracer = Tracer()
metrics = Metrics()


class OCRServiceError(Exception):
    """Custom exception for OCR service errors."""

    pass


class OCRService:
    """Service class for OCR operations using AWS Textract."""

    def __init__(self):
        self.textract = boto3.client("textract")
        self.s3 = boto3.client("s3")
        self.bucket_name = self._get_bucket_name()

    def _get_bucket_name(self) -> str:
        """Get the S3 bucket name from environment."""
        import os

        bucket = os.getenv("PDF_DERIVATIVES_BUCKET")
        if not bucket:
            raise OCRServiceError("PDF_DERIVATIVES_BUCKET environment variable not set")
        return bucket

    @tracer.capture_method
    def check_if_image_based(self, s3_key: str) -> Tuple[bool, int]:
        """
        Check if PDF is image-based by analyzing text content.

        Returns:
            Tuple of (is_image_based, page_count)
        """
        try:
            # Download PDF from S3
            response = self.s3.get_object(Bucket=self.bucket_name, Key=s3_key)
            pdf_content = response["Body"].read()

            # Analyze PDF with PyPDF2
            pdf_reader = PyPDF2.PdfReader(pdf_content)
            page_count = len(pdf_reader.pages)
            total_text_length = 0

            # Sample first 5 pages to determine if image-based
            pages_to_check = min(5, page_count)
            for i in range(pages_to_check):
                page = pdf_reader.pages[i]
                text = page.extract_text().strip()
                total_text_length += len(text)

            # Consider image-based if very little text per page
            avg_text_per_page = (
                total_text_length / pages_to_check if pages_to_check > 0 else 0
            )
            is_image_based = (
                avg_text_per_page < 50
            )  # Less than 50 chars per page on average

            logger.info(
                f"PDF analysis: {page_count} pages, {avg_text_per_page:.1f} chars/page, image-based: {is_image_based}"
            )

            return is_image_based, page_count

        except Exception as e:
            logger.error(f"Error analyzing PDF: {str(e)}")
            metrics.add_metric(name="PDFAnalysisError", unit=MetricUnit.Count, value=1)
            raise OCRServiceError(f"Failed to analyze PDF: {str(e)}")

    @tracer.capture_method
    def start_textract_job(self, s3_key: str, doc_id: str) -> str:
        """
        Start an asynchronous Textract document analysis job with queries.

        Returns:
            Textract job ID
        """
        try:
            # Define queries for metadata extraction
            queries = [
                {"Text": "What is the title of this document?", "Alias": "DOCUMENT_TITLE"},
                {"Text": "What is the main heading?", "Alias": "MAIN_HEADING"},
                {"Text": "What is the subject of this document?", "Alias": "DOCUMENT_SUBJECT"},
                {"Text": "Who is the author?", "Alias": "DOCUMENT_AUTHOR"},
                {"Text": "What are the key topics covered?", "Alias": "KEY_TOPICS"},
            ]

            # Use document analysis with queries for metadata extraction
            response = self.textract.start_document_analysis(
                DocumentLocation={
                    "S3Object": {"Bucket": self.bucket_name, "Name": s3_key}
                },
                FeatureTypes=["TABLES", "FORMS", "LAYOUT", "QUERIES"],
                QueriesConfig={"Queries": queries},
                JobTag=f"pdf-accessibility-{doc_id}",
            )

            job_id = response["JobId"]
            logger.info(f"Started Textract job {job_id} for document {doc_id}")
            metrics.add_metric(
                name="TextractJobsStarted", unit=MetricUnit.Count, value=1
            )

            return job_id

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"Textract job start failed: {error_code}")
            metrics.add_metric(
                name="TextractJobStartError", unit=MetricUnit.Count, value=1
            )
            raise OCRServiceError(f"Failed to start Textract job: {error_code}")

    @tracer.capture_method
    def poll_textract_job(
        self, job_id: str, max_wait_seconds: int = 600
    ) -> TextractJobStatus:
        """
        Poll Textract job status until completion or timeout.

        Args:
            job_id: Textract job ID
            max_wait_seconds: Maximum time to wait for completion

        Returns:
            TextractJobStatus with final status
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            try:
                response = self.textract.get_document_analysis(JobId=job_id)
                status = response["JobStatus"]

                if status == "SUCCEEDED":
                    completion_time = response.get("CompletionTime", time.time())
                    logger.info(f"Textract job {job_id} completed successfully")
                    metrics.add_metric(
                        name="TextractJobsCompleted", unit=MetricUnit.Count, value=1
                    )

                    return TextractJobStatus(
                        job_id=job_id,
                        status=OCRStatus.COMPLETED,
                        completion_time=str(completion_time),
                    )

                elif status == "FAILED":
                    error_message = response.get("StatusMessage", "Unknown error")
                    logger.error(f"Textract job {job_id} failed: {error_message}")
                    metrics.add_metric(
                        name="TextractJobsFailed", unit=MetricUnit.Count, value=1
                    )

                    return TextractJobStatus(
                        job_id=job_id,
                        status=OCRStatus.FAILED,
                        error_message=error_message,
                    )

                elif status in ["IN_PROGRESS", "PARTIAL_SUCCESS"]:
                    logger.info(f"Textract job {job_id} still processing... ({status})")
                    time.sleep(10)  # Wait 10 seconds before next poll

                else:
                    logger.warning(f"Unknown Textract status: {status}")
                    time.sleep(5)

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                logger.error(f"Error polling Textract job {job_id}: {error_code}")

                return TextractJobStatus(
                    job_id=job_id,
                    status=OCRStatus.FAILED,
                    error_message=f"Polling error: {error_code}",
                )

        # Timeout reached
        logger.error(
            f"Textract job {job_id} timed out after {max_wait_seconds} seconds"
        )
        metrics.add_metric(name="TextractJobsTimedOut", unit=MetricUnit.Count, value=1)

        return TextractJobStatus(
            job_id=job_id,
            status=OCRStatus.FAILED,
            error_message=f"Job timed out after {max_wait_seconds} seconds",
        )

    @tracer.capture_method
    def get_textract_results(self, job_id: str) -> TextractResponse:
        """
        Retrieve and process Textract job results.

        Returns:
            Structured TextractResponse with all blocks
        """
        try:
            blocks = []
            query_results = []
            next_token = None

            while True:
                if next_token:
                    response = self.textract.get_document_analysis(
                        JobId=job_id, NextToken=next_token
                    )
                else:
                    response = self.textract.get_document_analysis(JobId=job_id)

                # Process blocks
                for block in response.get("Blocks", []):
                    query_alias = None
                    
                    # Check if this block is part of a query result
                    if block["BlockType"] == "QUERY_RESULT":
                        # Find the associated query to get the alias
                        query_alias = self._find_query_alias(block, response.get("Blocks", []))
                        
                        # Store query result
                        query_result = TextractQueryResult(
                            alias=query_alias or "UNKNOWN",
                            text=block.get("Text"),
                            confidence=block.get("Confidence")
                        )
                        query_results.append(query_result)
                    
                    textract_block = TextractBlock(
                        id=block["Id"],
                        block_type=block["BlockType"],
                        text=block.get("Text"),
                        confidence=block.get("Confidence"),
                        bounding_box=block.get("Geometry", {}).get("BoundingBox"),
                        page=block.get("Page"),
                        query_alias=query_alias,
                    )
                    blocks.append(textract_block)

                next_token = response.get("NextToken")
                if not next_token:
                    break

            # Count pages
            page_blocks = [b for b in blocks if b.block_type == "PAGE"]
            total_pages = len(page_blocks)

            # Extract metadata from query results
            extracted_metadata = self._extract_metadata_from_queries(query_results)

            logger.info(
                f"Retrieved {len(blocks)} blocks, {len(query_results)} query results from Textract job {job_id}, {total_pages} pages"
            )

            return TextractResponse(
                job_id=job_id,
                document_metadata=response.get("DocumentMetadata", {}),
                blocks=blocks,
                total_pages=total_pages,
                query_results=query_results,
                extracted_metadata=extracted_metadata,
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(
                f"Failed to get Textract results for job {job_id}: {error_code}"
            )
            raise OCRServiceError(f"Failed to retrieve Textract results: {error_code}")

    @tracer.capture_method
    def save_textract_results(
        self, doc_id: str, textract_response: TextractResponse
    ) -> str:
        """
        Save Textract results to S3 as JSON.

        Returns:
            S3 key where results were saved
        """
        try:
            s3_key = f"pdf-derivatives/{doc_id}/textract/raw_output.json"

            # Convert to JSON-serializable format
            results_dict = {
                "job_id": textract_response.job_id,
                "document_metadata": textract_response.document_metadata,
                "total_pages": textract_response.total_pages,
                "blocks": [block.dict() for block in textract_response.blocks],
                "query_results": [qr.dict() for qr in textract_response.query_results],
                "extracted_metadata": textract_response.extracted_metadata.dict() if textract_response.extracted_metadata else None,
            }

            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(results_dict, indent=2),
                ContentType="application/json",
            )

            logger.info(f"Saved Textract results to {s3_key}")
            metrics.add_metric(
                name="TextractResultsSaved", unit=MetricUnit.Count, value=1
            )

            return s3_key

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"Failed to save Textract results: {error_code}")
            raise OCRServiceError(f"Failed to save Textract results: {error_code}")

    def _find_query_alias(self, query_result_block: dict, all_blocks: list) -> str:
        """
        Find the query alias associated with a query result block.
        
        Args:
            query_result_block: The QUERY_RESULT block
            all_blocks: All blocks from the Textract response
            
        Returns:
            Query alias string or None
        """
        try:
            # Look for relationships to find the associated QUERY block
            relationships = query_result_block.get("Relationships", [])
            for relationship in relationships:
                if relationship["Type"] == "ANSWER":
                    # Find the QUERY block this result answers
                    for block in all_blocks:
                        if block["Id"] in relationship["Ids"] and block["BlockType"] == "QUERY":
                            return block.get("Query", {}).get("Alias", "UNKNOWN")
            return "UNKNOWN"
        except Exception as e:
            logger.warning(f"Error finding query alias: {e}")
            return "UNKNOWN"

    def _extract_metadata_from_queries(self, query_results: List[TextractQueryResult]) -> DocumentMetadata:
        """
        Extract document metadata from Textract query results.
        
        Args:
            query_results: List of query results
            
        Returns:
            DocumentMetadata object
        """
        metadata = DocumentMetadata()
        
        for result in query_results:
            if not result.text or not result.text.strip():
                continue
                
            # Clean up the text
            text = result.text.strip()
            confidence = result.confidence or 0.0
            
            # Map query aliases to metadata fields
            if result.alias == "DOCUMENT_TITLE":
                metadata.title = text
                metadata.confidence_scores["title"] = confidence
            elif result.alias == "MAIN_HEADING":
                metadata.main_heading = text
                metadata.confidence_scores["main_heading"] = confidence
            elif result.alias == "DOCUMENT_SUBJECT":
                metadata.subject = text
                metadata.confidence_scores["subject"] = confidence
            elif result.alias == "DOCUMENT_AUTHOR":
                metadata.author = text
                metadata.confidence_scores["author"] = confidence
            elif result.alias == "KEY_TOPICS":
                metadata.key_topics = text
                metadata.confidence_scores["key_topics"] = confidence
        
        # Log extracted metadata
        extracted_fields = []
        if metadata.title:
            extracted_fields.append(f"title: {metadata.title[:50]}...")
        if metadata.author:
            extracted_fields.append(f"author: {metadata.author}")
        if metadata.subject:
            extracted_fields.append(f"subject: {metadata.subject[:50]}...")
            
        if extracted_fields:
            logger.info(f"Extracted metadata: {', '.join(extracted_fields)}")
        else:
            logger.info("No metadata extracted from queries")
            
        return metadata

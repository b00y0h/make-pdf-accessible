"""Textract client wrapper with async job handling and polling."""

import time
from enum import Enum
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

from pdf_worker.core.config import config
from pdf_worker.core.exceptions import TextractError, WorkerConfigError

logger = Logger()
tracer = Tracer()


class TextractJobStatus(str, Enum):
    """Textract job status enumeration."""

    IN_PROGRESS = "IN_PROGRESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TextractFeature(str, Enum):
    """Textract analysis features."""

    TABLES = "TABLES"
    FORMS = "FORMS"
    LAYOUT = "LAYOUT"
    QUERIES = "QUERIES"
    SIGNATURES = "SIGNATURES"


class TextractClient:
    """Enhanced Textract client with job management and result processing."""

    def __init__(self, region_name: str | None = None) -> None:
        """Initialize Textract client.

        Args:
            region_name: AWS region name. Defaults to config.aws_region.
        """
        try:
            self._client = boto3.client(
                "textract", region_name=region_name or config.aws_region
            )
        except Exception as e:
            raise WorkerConfigError(f"Failed to initialize Textract client: {e}")

        logger.info(
            f"Initialized Textract client for region: {region_name or config.aws_region}"
        )

    @tracer.capture_method
    def start_document_analysis(
        self,
        s3_bucket: str,
        s3_key: str,
        features: list[TextractFeature],
        job_tag: str | None = None,
        notification_channel: dict[str, str] | None = None,
        client_request_token: str | None = None,
    ) -> str:
        """Start asynchronous document analysis job.

        Args:
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key of the document
            features: List of Textract features to enable
            job_tag: Optional job tag for identification
            notification_channel: SNS notification configuration
            client_request_token: Unique token to prevent duplicate requests

        Returns:
            Textract job ID

        Raises:
            TextractError: If job start fails
        """
        try:
            request_params = {
                "DocumentLocation": {"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
                "FeatureTypes": [feature.value for feature in features],
            }

            if job_tag:
                request_params["JobTag"] = job_tag

            if notification_channel:
                request_params["NotificationChannel"] = notification_channel

            if client_request_token:
                request_params["ClientRequestToken"] = client_request_token

            response = self._client.start_document_analysis(**request_params)
            job_id = response["JobId"]

            logger.info(f"Started Textract analysis job: {job_id}")
            logger.debug(f"Job features: {[f.value for f in features]}")

            return job_id

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Handle specific error cases
            if error_code == "InvalidS3ObjectException":
                raise TextractError(
                    f"Invalid S3 object: s3://{s3_bucket}/{s3_key}", job_id=None
                )
            elif error_code == "UnsupportedDocumentException":
                raise TextractError(
                    "Document format not supported by Textract", job_id=None
                )
            elif error_code == "DocumentTooLargeException":
                raise TextractError("Document exceeds maximum size limit", job_id=None)

            raise TextractError(
                f"Failed to start Textract job: {error_code}", job_id=None
            ) from e

    @tracer.capture_method
    def start_document_text_detection(
        self,
        s3_bucket: str,
        s3_key: str,
        job_tag: str | None = None,
        notification_channel: dict[str, str] | None = None,
    ) -> str:
        """Start asynchronous text detection job (text only, no analysis).

        Args:
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key of the document
            job_tag: Optional job tag for identification
            notification_channel: SNS notification configuration

        Returns:
            Textract job ID
        """
        try:
            request_params = {
                "DocumentLocation": {"S3Object": {"Bucket": s3_bucket, "Name": s3_key}}
            }

            if job_tag:
                request_params["JobTag"] = job_tag

            if notification_channel:
                request_params["NotificationChannel"] = notification_channel

            response = self._client.start_document_text_detection(**request_params)
            job_id = response["JobId"]

            logger.info(f"Started Textract text detection job: {job_id}")
            return job_id

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise TextractError(
                f"Failed to start text detection job: {error_code}", job_id=None
            ) from e

    @tracer.capture_method
    def get_job_status(
        self, job_id: str, analysis_type: str = "analysis"
    ) -> dict[str, Any]:
        """Get status of a Textract job.

        Args:
            job_id: Textract job ID
            analysis_type: Type of job ("analysis" or "detection")

        Returns:
            Job status information

        Raises:
            TextractError: If status check fails
        """
        try:
            if analysis_type == "analysis":
                response = self._client.get_document_analysis(JobId=job_id)
            else:
                response = self._client.get_document_text_detection(JobId=job_id)

            job_info = {
                "job_id": job_id,
                "job_status": response["JobStatus"],
                "status_message": response.get("StatusMessage"),
                "document_metadata": response.get("DocumentMetadata", {}),
                "analysis_start_timestamp": response.get("AnalysisStartTimestamp"),
                "analysis_completion_timestamp": response.get(
                    "AnalysisCompletionTimestamp"
                ),
            }

            logger.debug(f"Job {job_id} status: {job_info['job_status']}")
            return job_info

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "InvalidJobIdException":
                raise TextractError(f"Invalid job ID: {job_id}", job_id=job_id)

            raise TextractError(
                f"Failed to get job status: {error_code}", job_id=job_id
            ) from e

    @tracer.capture_method
    def poll_job_completion(
        self,
        job_id: str,
        analysis_type: str = "analysis",
        max_wait_seconds: int = 600,
        poll_interval_seconds: int = 10,
    ) -> dict[str, Any]:
        """Poll Textract job until completion or timeout.

        Args:
            job_id: Textract job ID
            analysis_type: Type of job ("analysis" or "detection")
            max_wait_seconds: Maximum time to wait for completion
            poll_interval_seconds: Time between status checks

        Returns:
            Final job status information

        Raises:
            TextractError: If job fails or times out
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            job_info = self.get_job_status(job_id, analysis_type)
            status = TextractJobStatus(job_info["job_status"])

            if status == TextractJobStatus.SUCCEEDED:
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Textract job {job_id} completed successfully in {elapsed_time:.1f}s"
                )
                return job_info

            elif status == TextractJobStatus.FAILED:
                error_message = job_info.get("status_message", "Job failed")
                raise TextractError(
                    f"Textract job failed: {error_message}",
                    job_id=job_id,
                    job_status=status.value,
                )

            elif status in [
                TextractJobStatus.IN_PROGRESS,
                TextractJobStatus.PARTIAL_SUCCESS,
            ]:
                logger.debug(f"Job {job_id} still processing ({status.value})")
                time.sleep(poll_interval_seconds)

            else:
                logger.warning(f"Unknown job status: {status.value}")
                time.sleep(poll_interval_seconds)

        # Timeout reached
        elapsed_time = time.time() - start_time
        raise TextractError(
            f"Textract job {job_id} timed out after {elapsed_time:.1f}s",
            job_id=job_id,
            job_status="TIMEOUT",
        )

    @tracer.capture_method
    def get_document_analysis_results(
        self, job_id: str, max_results: int | None = None
    ) -> dict[str, Any]:
        """Get complete results from document analysis job.

        Args:
            job_id: Textract job ID
            max_results: Maximum number of blocks to return per call

        Returns:
            Complete analysis results with all blocks

        Raises:
            TextractError: If results retrieval fails
        """
        try:
            all_blocks = []
            next_token = None
            document_metadata = None

            while True:
                request_params = {"JobId": job_id}

                if next_token:
                    request_params["NextToken"] = next_token

                if max_results:
                    request_params["MaxResults"] = max_results

                response = self._client.get_document_analysis(**request_params)

                # Store metadata from first response
                if document_metadata is None:
                    document_metadata = response.get("DocumentMetadata", {})

                # Collect blocks
                blocks = response.get("Blocks", [])
                all_blocks.extend(blocks)

                # Check for more results
                next_token = response.get("NextToken")
                if not next_token:
                    break

            results = {
                "job_id": job_id,
                "document_metadata": document_metadata,
                "blocks": all_blocks,
                "total_blocks": len(all_blocks),
            }

            logger.info(
                f"Retrieved {len(all_blocks)} blocks from Textract job {job_id}"
            )
            return results

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise TextractError(
                f"Failed to get analysis results: {error_code}", job_id=job_id
            ) from e

    @tracer.capture_method
    def get_document_text_detection_results(
        self, job_id: str, max_results: int | None = None
    ) -> dict[str, Any]:
        """Get complete results from text detection job.

        Args:
            job_id: Textract job ID
            max_results: Maximum number of blocks to return per call

        Returns:
            Complete text detection results
        """
        try:
            all_blocks = []
            next_token = None
            document_metadata = None

            while True:
                request_params = {"JobId": job_id}

                if next_token:
                    request_params["NextToken"] = next_token

                if max_results:
                    request_params["MaxResults"] = max_results

                response = self._client.get_document_text_detection(**request_params)

                # Store metadata from first response
                if document_metadata is None:
                    document_metadata = response.get("DocumentMetadata", {})

                # Collect blocks
                blocks = response.get("Blocks", [])
                all_blocks.extend(blocks)

                # Check for more results
                next_token = response.get("NextToken")
                if not next_token:
                    break

            results = {
                "job_id": job_id,
                "document_metadata": document_metadata,
                "blocks": all_blocks,
                "total_blocks": len(all_blocks),
            }

            logger.info(
                f"Retrieved {len(all_blocks)} blocks from text detection job {job_id}"
            )
            return results

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise TextractError(
                f"Failed to get text detection results: {error_code}", job_id=job_id
            ) from e

    @tracer.capture_method
    def analyze_document_sync(
        self,
        s3_bucket: str,
        s3_key: str,
        features: list[TextractFeature],
        queries: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Analyze document synchronously (for smaller documents).

        Args:
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key of the document
            features: List of Textract features to enable
            queries: Optional list of queries for QUERIES feature

        Returns:
            Analysis results

        Raises:
            TextractError: If analysis fails
        """
        try:
            request_params = {
                "Document": {"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
                "FeatureTypes": [feature.value for feature in features],
            }

            if queries and TextractFeature.QUERIES in features:
                request_params["QueriesConfig"] = {"Queries": queries}

            response = self._client.analyze_document(**request_params)

            results = {
                "document_metadata": response.get("DocumentMetadata", {}),
                "blocks": response.get("Blocks", []),
                "total_blocks": len(response.get("Blocks", [])),
            }

            logger.info(
                f"Synchronously analyzed document with {results['total_blocks']} blocks"
            )
            return results

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "DocumentTooLargeException":
                raise TextractError(
                    "Document too large for synchronous analysis, use async instead"
                )

            raise TextractError(f"Sync analysis failed: {error_code}") from e

    def extract_text_from_blocks(self, blocks: list[dict[str, Any]]) -> str:
        """Extract plain text from Textract blocks.

        Args:
            blocks: List of Textract blocks

        Returns:
            Extracted plain text
        """
        text_lines = []

        for block in blocks:
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "").strip()
                if text:
                    text_lines.append(text)

        return "\n".join(text_lines)

    def extract_tables_from_blocks(
        self, blocks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract table data from Textract blocks.

        Args:
            blocks: List of Textract blocks

        Returns:
            List of table dictionaries with structure information
        """
        # Create block lookup
        block_map = {block["Id"]: block for block in blocks}

        tables = []

        for block in blocks:
            if block.get("BlockType") == "TABLE":
                table = {
                    "id": block["Id"],
                    "confidence": block.get("Confidence", 0),
                    "geometry": block.get("Geometry"),
                    "rows": [],
                    "cells": [],
                }

                # Extract cells
                if "Relationships" in block:
                    for relationship in block["Relationships"]:
                        if relationship["Type"] == "CHILD":
                            for cell_id in relationship["Ids"]:
                                cell_block = block_map.get(cell_id)
                                if cell_block and cell_block.get("BlockType") == "CELL":
                                    cell_info = {
                                        "id": cell_id,
                                        "row_index": cell_block.get("RowIndex", 0),
                                        "column_index": cell_block.get(
                                            "ColumnIndex", 0
                                        ),
                                        "text": "",
                                        "confidence": cell_block.get("Confidence", 0),
                                    }

                                    # Get cell text
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                cell_text = []
                                                for word_id in cell_rel["Ids"]:
                                                    word_block = block_map.get(word_id)
                                                    if word_block and word_block.get(
                                                        "Text"
                                                    ):
                                                        cell_text.append(
                                                            word_block["Text"]
                                                        )
                                                cell_info["text"] = " ".join(cell_text)

                                    table["cells"].append(cell_info)

                tables.append(table)

        logger.debug(f"Extracted {len(tables)} tables from Textract blocks")
        return tables

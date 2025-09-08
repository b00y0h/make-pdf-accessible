"""Tests for router function services."""

import json
from unittest.mock import Mock, patch

import httpx
import pytest
from botocore.exceptions import ClientError
from models import (
    DocumentRecord,
    DocumentSource,
    JobRecord,
    JobStep,
    ProcessMessage,
)

from services import AWSServiceError, RouterService


@pytest.fixture
def router_service():
    """Create a RouterService instance for testing."""
    return RouterService(
        documents_table="test-documents",
        jobs_table="test-jobs",
        pdf_originals_bucket="test-originals",
        process_queue_url="https://sqs.us-east-1.amazonaws.com/123456789/test-process",
        priority_process_queue_url="https://sqs.us-east-1.amazonaws.com/123456789/test-priority",
        region="us-east-1"
    )


class TestRouterService:
    """Test RouterService methods."""

    @patch('services.boto3.resource')
    def test_check_document_exists_true(self, mock_resource, router_service):
        """Test document exists check returns True."""
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': {'docId': 'test-doc-123'}}

        router_service.documents_table_resource = mock_table

        result = router_service.check_document_exists("test-doc-123")

        assert result is True
        mock_table.get_item.assert_called_once_with(Key={'docId': 'test-doc-123'})

    @patch('services.boto3.resource')
    def test_check_document_exists_false(self, mock_resource, router_service):
        """Test document exists check returns False."""
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {}  # No Item key

        router_service.documents_table_resource = mock_table

        result = router_service.check_document_exists("test-doc-123")

        assert result is False
        mock_table.get_item.assert_called_once_with(Key={'docId': 'test-doc-123'})

    @patch('services.boto3.resource')
    def test_check_document_exists_error(self, mock_resource, router_service):
        """Test document exists check handles errors."""
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException'}},
            operation_name='GetItem'
        )

        router_service.documents_table_resource = mock_table

        with pytest.raises(AWSServiceError):
            router_service.check_document_exists("test-doc-123")

    @patch('services.boto3.client')
    @pytest.mark.asyncio
    async def test_download_and_store_from_url_success(self, mock_s3_client, router_service):
        """Test successful download and store from URL."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_s3_client.return_value = mock_s3
        router_service.s3_client = mock_s3

        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"PDF content here"
        mock_response.headers = {"content-type": "application/pdf"}

        with patch('services.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await router_service.download_and_store_from_url(
                doc_id="test-doc-123",
                source_url="https://example.com/document.pdf",
                filename="document.pdf"
            )

        assert result == "originals/test-doc-123/document.pdf"
        mock_s3.put_object.assert_called_once()

        # Check put_object call arguments
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Bucket'] == "test-originals"
        assert call_args[1]['Key'] == "originals/test-doc-123/document.pdf"
        assert call_args[1]['Body'] == b"PDF content here"
        assert call_args[1]['ContentType'] == "application/pdf"

    @patch('services.boto3.client')
    @pytest.mark.asyncio
    async def test_download_and_store_from_url_http_error(self, mock_s3_client, router_service):
        """Test download failure due to HTTP error."""
        router_service.s3_client = Mock()

        with patch('services.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPError("Connection failed")

            with pytest.raises(AWSServiceError) as exc_info:
                await router_service.download_and_store_from_url(
                    doc_id="test-doc-123",
                    source_url="https://example.com/document.pdf"
                )

            assert "Failed to download file" in str(exc_info.value)

    @patch('services.boto3.client')
    def test_copy_uploaded_file_success(self, mock_s3_client, router_service):
        """Test successful file copy."""
        mock_s3 = Mock()
        mock_s3_client.return_value = mock_s3
        router_service.s3_client = mock_s3

        result = router_service.copy_uploaded_file(
            doc_id="test-doc-123",
            source_s3_key="temp-bucket/temp-key.pdf",
            filename="document.pdf"
        )

        assert result == "originals/test-doc-123/document.pdf"
        mock_s3.copy_object.assert_called_once()

        # Check copy_object call arguments
        call_args = mock_s3.copy_object.call_args
        assert call_args[1]['CopySource'] == {'Bucket': 'temp-bucket', 'Key': 'temp-key.pdf'}
        assert call_args[1]['Bucket'] == "test-originals"
        assert call_args[1]['Key'] == "originals/test-doc-123/document.pdf"

    @patch('services.boto3.client')
    def test_copy_uploaded_file_error(self, mock_s3_client, router_service):
        """Test file copy error handling."""
        mock_s3 = Mock()
        mock_s3_client.return_value = mock_s3
        mock_s3.copy_object.side_effect = ClientError(
            error_response={'Error': {'Code': 'NoSuchBucket'}},
            operation_name='CopyObject'
        )
        router_service.s3_client = mock_s3

        with pytest.raises(AWSServiceError):
            router_service.copy_uploaded_file(
                doc_id="test-doc-123",
                source_s3_key="temp-key.pdf"
            )

    @patch('services.boto3.resource')
    def test_save_document_record_success(self, mock_resource, router_service):
        """Test successful document record save."""
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        router_service.documents_table_resource = mock_table

        document = DocumentRecord(
            doc_id="test-doc-123",
            user_id="user-123",
            source=DocumentSource.UPLOAD,
            filename="document.pdf",
            s3_key_original="originals/test-doc-123/document.pdf"
        )

        router_service.save_document_record(document)

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']

        assert item['docId'] == "test-doc-123"
        assert item['userId'] == "user-123"
        assert item['source'] == "upload"
        assert item['filename'] == "document.pdf"
        assert item['s3KeyOriginal'] == "originals/test-doc-123/document.pdf"

    @patch('services.boto3.resource')
    def test_create_job_record_success(self, mock_resource, router_service):
        """Test successful job record creation."""
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        router_service.jobs_table_resource = mock_table

        job = JobRecord(
            doc_id="test-doc-123",
            step=JobStep.OCR,
            priority=True,
            input_data={"s3_key": "test-key"}
        )

        router_service.create_job_record(job)

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']

        assert item['docId'] == "test-doc-123"
        assert item['step'] == "ocr"
        assert item['priority'] is True
        assert item['inputData'] == {"s3_key": "test-key"}

    @patch('services.boto3.client')
    def test_enqueue_process_message_standard(self, mock_sqs_client, router_service):
        """Test enqueuing to standard process queue."""
        mock_sqs = Mock()
        mock_sqs_client.return_value = mock_sqs
        router_service.sqs_client = mock_sqs

        message = ProcessMessage(
            job_id="job-123",
            doc_id="doc-123",
            step=JobStep.OCR,
            priority=False,
            input_data={"test": "data"}
        )

        router_service.enqueue_process_message(message)

        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args

        assert call_args[1]['QueueUrl'] == router_service.process_queue_url

        # Check message body
        body = json.loads(call_args[1]['MessageBody'])
        assert body['jobId'] == "job-123"
        assert body['step'] == "ocr"
        assert body['priority'] is False

    @patch('services.boto3.client')
    def test_enqueue_process_message_priority(self, mock_sqs_client, router_service):
        """Test enqueuing to priority process queue."""
        mock_sqs = Mock()
        mock_sqs_client.return_value = mock_sqs
        router_service.sqs_client = mock_sqs

        message = ProcessMessage(
            job_id="job-123",
            doc_id="doc-123",
            step=JobStep.OCR,
            priority=True
        )

        router_service.enqueue_process_message(message)

        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args

        assert call_args[1]['QueueUrl'] == router_service.priority_process_queue_url

    @patch('services.boto3.client')
    def test_enqueue_process_message_error(self, mock_sqs_client, router_service):
        """Test enqueue process message error handling."""
        mock_sqs = Mock()
        mock_sqs_client.return_value = mock_sqs
        mock_sqs.send_message.side_effect = ClientError(
            error_response={'Error': {'Code': 'QueueDoesNotExist'}},
            operation_name='SendMessage'
        )
        router_service.sqs_client = mock_sqs

        message = ProcessMessage(
            job_id="job-123",
            doc_id="doc-123",
            step=JobStep.OCR
        )

        with pytest.raises(AWSServiceError):
            router_service.enqueue_process_message(message)

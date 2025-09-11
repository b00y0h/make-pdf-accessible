"""Tests for router function main handler."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Mock the services module before importing main
with patch("main.RouterService") as mock_service_class:
    mock_service = Mock()
    mock_service_class.return_value = mock_service

    from main import lambda_handler, process_document
    from models import DocumentSource, IngestMessage


class MockLambdaContext:
    """Mock Lambda context for testing."""

    def __init__(self):
        self.function_name = "test-router"
        self.function_version = "1"
        self.aws_request_id = "test-request-id"


class TestProcessDocument:
    """Test process_document function."""

    @pytest.mark.asyncio
    @patch("main.router_service")
    async def test_process_document_success_upload(self, mock_service):
        """Test successful document processing for upload."""
        # Setup mocks
        mock_service.check_document_exists.return_value = False
        mock_service.copy_uploaded_file.return_value = (
            "originals/test-doc-123/document.pdf"
        )
        mock_service.save_document_record = Mock()
        mock_service.create_job_record = Mock()
        mock_service.enqueue_process_message = Mock()

        # Mock tracer
        with patch("main.tracer") as mock_tracer:
            mock_tracer.provider.get_start_time.return_value = 1234567890
            mock_tracer.provider.get_elapsed_time_ms.return_value = 150

            # Create test message
            ingest_message = IngestMessage(
                doc_id="test-doc-123",
                source=DocumentSource.UPLOAD,
                s3_key="temp/test-doc-123/document.pdf",
                filename="document.pdf",
                user_id="user-123",
                priority=False,
            )

            # Process document
            result = await process_document(ingest_message)

        # Verify result
        assert result["status"] == "success"
        assert result["doc_id"] == "test-doc-123"
        assert "file_copied_to_originals" in result["actions_performed"]
        assert "document_record_saved" in result["actions_performed"]
        assert "ocr_job_created" in result["actions_performed"]
        assert "process_message_enqueued" in result["actions_performed"]
        assert result["processing_time_ms"] == 150

        # Verify service calls
        mock_service.check_document_exists.assert_called_once_with("test-doc-123")
        mock_service.copy_uploaded_file.assert_called_once()
        mock_service.save_document_record.assert_called_once()
        mock_service.create_job_record.assert_called_once()
        mock_service.enqueue_process_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("main.router_service")
    async def test_process_document_success_url(self, mock_service):
        """Test successful document processing for URL."""
        # Setup mocks
        mock_service.check_document_exists.return_value = False
        mock_service.download_and_store_from_url = AsyncMock(
            return_value="originals/test-doc-123/document.pdf"
        )
        mock_service.save_document_record = Mock()
        mock_service.create_job_record = Mock()
        mock_service.enqueue_process_message = Mock()

        # Mock tracer
        with patch("main.tracer") as mock_tracer:
            mock_tracer.provider.get_start_time.return_value = 1234567890
            mock_tracer.provider.get_elapsed_time_ms.return_value = 300

            # Create test message
            ingest_message = IngestMessage(
                doc_id="test-doc-456",
                source=DocumentSource.URL,
                source_url="https://example.com/document.pdf",
                filename="document.pdf",
                user_id="user-456",
                priority=True,
            )

            # Process document
            result = await process_document(ingest_message)

        # Verify result
        assert result["status"] == "success"
        assert result["doc_id"] == "test-doc-456"
        assert "file_downloaded_from_url" in result["actions_performed"]

        # Verify URL download was called
        mock_service.download_and_store_from_url.assert_called_once_with(
            doc_id="test-doc-456",
            source_url="https://example.com/document.pdf",
            filename="document.pdf",
        )

    @pytest.mark.asyncio
    @patch("main.router_service")
    async def test_process_document_already_exists(self, mock_service):
        """Test document already exists (idempotency)."""
        # Setup mocks
        mock_service.check_document_exists.return_value = True

        # Create test message
        ingest_message = IngestMessage(
            doc_id="existing-doc-123",
            source=DocumentSource.UPLOAD,
            s3_key="temp/existing-doc-123/document.pdf",
            filename="document.pdf",
        )

        # Process document
        result = await process_document(ingest_message)

        # Verify result
        assert result["status"] == "skipped"
        assert result["reason"] == "document already exists"
        assert result["doc_id"] == "existing-doc-123"

        # Verify only idempotency check was called
        mock_service.check_document_exists.assert_called_once_with("existing-doc-123")
        mock_service.copy_uploaded_file.assert_not_called()
        mock_service.save_document_record.assert_not_called()

    @pytest.mark.asyncio
    @patch("main.router_service")
    async def test_process_document_aws_service_error(self, mock_service):
        """Test AWS service error handling."""
        from services import AWSServiceError

        # Setup mocks
        mock_service.check_document_exists.return_value = False
        mock_service.copy_uploaded_file.side_effect = AWSServiceError("S3 error")

        # Create test message
        ingest_message = IngestMessage(
            doc_id="error-doc-123",
            source=DocumentSource.UPLOAD,
            s3_key="temp/error-doc-123/document.pdf",
            filename="document.pdf",
        )

        # Process document
        result = await process_document(ingest_message)

        # Verify result
        assert result["status"] == "failed"
        assert "AWS service error" in result["error"]
        assert result["doc_id"] == "error-doc-123"


class TestLambdaHandler:
    """Test lambda_handler function."""

    def test_lambda_handler_success(self):
        """Test successful Lambda handler execution."""
        # Create test event
        test_event = {
            "Records": [
                {
                    "messageId": "test-message-1",
                    "body": json.dumps(
                        {
                            "doc_id": "test-doc-123",
                            "source": "upload",
                            "s3_key": "temp/test-doc-123/document.pdf",
                            "filename": "document.pdf",
                            "user_id": "user-123",
                            "priority": False,
                        }
                    ),
                },
                {
                    "messageId": "test-message-2",
                    "body": json.dumps(
                        {
                            "doc_id": "test-doc-456",
                            "source": "url",
                            "source_url": "https://example.com/document.pdf",
                            "filename": "document.pdf",
                            "user_id": "user-456",
                            "priority": True,
                        }
                    ),
                },
            ]
        }

        # Mock process_document function
        with patch("main.process_document") as mock_process:
            mock_process.side_effect = [
                {
                    "status": "success",
                    "doc_id": "test-doc-123",
                    "actions_performed": ["test"],
                },
                {
                    "status": "success",
                    "doc_id": "test-doc-456",
                    "actions_performed": ["test"],
                },
            ]

            # Execute handler
            result = lambda_handler(test_event, MockLambdaContext())

        # Verify results
        assert result["processed"] == 2
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert len(result["results"]) == 2

        # Verify process_document was called twice
        assert mock_process.call_count == 2

    def test_lambda_handler_mixed_results(self):
        """Test Lambda handler with mixed success/failure results."""
        # Create test event
        test_event = {
            "Records": [
                {
                    "messageId": "success-message",
                    "body": json.dumps(
                        {
                            "doc_id": "success-doc",
                            "source": "upload",
                            "s3_key": "temp/success-doc/document.pdf",
                            "filename": "document.pdf",
                        }
                    ),
                },
                {
                    "messageId": "skip-message",
                    "body": json.dumps(
                        {
                            "doc_id": "skip-doc",
                            "source": "upload",
                            "s3_key": "temp/skip-doc/document.pdf",
                            "filename": "document.pdf",
                        }
                    ),
                },
                {
                    "messageId": "fail-message",
                    "body": json.dumps(
                        {
                            "doc_id": "fail-doc",
                            "source": "upload",
                            "s3_key": "temp/fail-doc/document.pdf",
                            "filename": "document.pdf",
                        }
                    ),
                },
            ]
        }

        # Mock process_document function
        with patch("main.process_document") as mock_process:
            mock_process.side_effect = [
                {"status": "success", "doc_id": "success-doc"},
                {"status": "skipped", "doc_id": "skip-doc"},
                {"status": "failed", "doc_id": "fail-doc", "error": "Test error"},
            ]

            # Execute handler
            result = lambda_handler(test_event, MockLambdaContext())

        # Verify results
        assert result["processed"] == 1
        assert result["skipped"] == 1
        assert result["failed"] == 1
        assert len(result["results"]) == 3

    def test_lambda_handler_invalid_message(self):
        """Test Lambda handler with invalid message format."""
        # Create test event with invalid JSON
        test_event = {
            "Records": [{"messageId": "invalid-message", "body": "invalid json"}]
        }

        # Execute handler
        result = lambda_handler(test_event, MockLambdaContext())

        # Verify results
        assert result["processed"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "failed"
        assert "Failed to process SQS record" in result["results"][0]["error"]

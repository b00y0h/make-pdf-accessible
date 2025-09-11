from datetime import datetime
from uuid import UUID

import pytest
from app.models import (
    DocumentResponse,
    DocumentStatus,
    DocumentType,
    DocumentUploadRequest,
    DownloadRequest,
    ErrorResponse,
    PaginationParams,
    UserRole,
    WebhookPayload,
)
from pydantic import ValidationError


class TestDocumentModels:
    """Test document-related models"""

    def test_document_upload_request_valid(self):
        """Test valid document upload request"""
        request = DocumentUploadRequest(
            source_url="https://example.com/doc.pdf",
            filename="test.pdf",
            metadata={"source": "test"},
            priority=True,
            webhook_url="https://webhook.example.com",
        )

        assert request.source_url == "https://example.com/doc.pdf"
        assert request.filename == "test.pdf"
        assert request.metadata == {"source": "test"}
        assert request.priority is True
        assert request.webhook_url == "https://webhook.example.com"

    def test_document_upload_request_invalid_url(self):
        """Test invalid URL in upload request"""
        with pytest.raises(ValidationError) as exc_info:
            DocumentUploadRequest(source_url="not-a-url")

        assert "source_url must be a valid HTTP/HTTPS URL" in str(exc_info.value)

    def test_document_response_serialization(self):
        """Test document response serialization"""
        response = DocumentResponse(
            doc_id=UUID("12345678-1234-1234-1234-123456789012"),
            status=DocumentStatus.COMPLETED,
            filename="test.pdf",
            created_at=datetime(2023, 1, 1, 0, 0, 0),
            updated_at=datetime(2023, 1, 1, 1, 0, 0),
            user_id="test-user",
            metadata={"key": "value"},
            artifacts={"pdf": "s3://bucket/key"},
        )

        data = response.model_dump()

        assert data["doc_id"] == "12345678-1234-1234-1234-123456789012"
        assert data["status"] == "completed"
        assert data["filename"] == "test.pdf"
        assert data["user_id"] == "test-user"
        assert "created_at" in data
        assert "updated_at" in data


class TestValidationModels:
    """Test validation-related models"""

    def test_pagination_params_valid(self):
        """Test valid pagination parameters"""
        params = PaginationParams(page=2, per_page=20)

        assert params.page == 2
        assert params.per_page == 20
        assert params.offset == 20  # (page - 1) * per_page

    def test_pagination_params_invalid(self):
        """Test invalid pagination parameters"""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)  # Must be >= 1

        with pytest.raises(ValidationError):
            PaginationParams(per_page=101)  # Must be <= 100

    def test_download_request_valid(self):
        """Test valid download request"""
        request = DownloadRequest(document_type=DocumentType.PDF, expires_in=7200)

        assert request.document_type == DocumentType.PDF
        assert request.expires_in == 7200

    def test_download_request_invalid_expiration(self):
        """Test invalid expiration time"""
        with pytest.raises(ValidationError):
            DownloadRequest(
                document_type=DocumentType.PDF, expires_in=100  # Too short (< 300)
            )

        with pytest.raises(ValidationError):
            DownloadRequest(
                document_type=DocumentType.PDF, expires_in=90000  # Too long (> 86400)
            )


class TestWebhookModels:
    """Test webhook-related models"""

    def test_webhook_payload_valid(self):
        """Test valid webhook payload"""
        payload = WebhookPayload(
            event_type="document.completed",
            doc_id=UUID("12345678-1234-1234-1234-123456789012"),
            status=DocumentStatus.COMPLETED,
            timestamp=datetime(2023, 1, 1, 0, 0, 0),
            data={"processing_time": 30},
        )

        assert payload.event_type == "document.completed"
        assert payload.status == DocumentStatus.COMPLETED
        assert payload.data["processing_time"] == 30

    def test_webhook_payload_serialization(self):
        """Test webhook payload JSON serialization"""
        payload = WebhookPayload(
            event_type="document.failed",
            doc_id=UUID("12345678-1234-1234-1234-123456789012"),
            status=DocumentStatus.FAILED,
            timestamp=datetime(2023, 1, 1, 0, 0, 0),
        )

        data = payload.model_dump()

        assert data["doc_id"] == "12345678-1234-1234-1234-123456789012"
        assert "timestamp" in data


class TestEnumModels:
    """Test enum models"""

    def test_document_status_enum(self):
        """Test document status enum values"""
        assert DocumentStatus.PENDING == "pending"
        assert DocumentStatus.PROCESSING == "processing"
        assert DocumentStatus.COMPLETED == "completed"
        assert DocumentStatus.FAILED == "failed"

    def test_document_type_enum(self):
        """Test document type enum values"""
        assert DocumentType.PDF == "pdf"
        assert DocumentType.HTML == "html"
        assert DocumentType.JSON == "json"
        assert DocumentType.CSV_ZIP == "csvzip"

    def test_user_role_enum(self):
        """Test user role enum values"""
        assert UserRole.VIEWER == "viewer"
        assert UserRole.ADMIN == "admin"


class TestErrorModel:
    """Test error response model"""

    def test_error_response_basic(self):
        """Test basic error response"""
        error = ErrorResponse(
            error="validation_error", message="Invalid input provided"
        )

        assert error.error == "validation_error"
        assert error.message == "Invalid input provided"
        assert error.details is None
        assert error.request_id is None
        assert isinstance(error.timestamp, datetime)

    def test_error_response_with_details(self):
        """Test error response with details"""
        error = ErrorResponse(
            error="validation_error",
            message="Invalid input",
            details={"field": "source_url", "issue": "invalid format"},
            request_id="req-123",
        )

        assert error.details["field"] == "source_url"
        assert error.request_id == "req-123"

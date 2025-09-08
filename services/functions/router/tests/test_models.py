"""Tests for router function models."""

from datetime import datetime

import pytest
from models import (
    DocumentRecord,
    DocumentSource,
    DocumentStatus,
    IngestMessage,
    JobRecord,
    JobStatus,
    JobStep,
    ProcessMessage,
)
from pydantic import ValidationError


class TestIngestMessage:
    """Test IngestMessage model."""

    def test_valid_upload_message(self):
        """Test valid upload message."""
        message = IngestMessage(
            doc_id="test-doc-123",
            source=DocumentSource.UPLOAD,
            s3_key="temp/test-doc-123/document.pdf",
            filename="document.pdf",
            user_id="user-123",
            priority=False
        )

        assert message.doc_id == "test-doc-123"
        assert message.source == DocumentSource.UPLOAD
        assert message.s3_key == "temp/test-doc-123/document.pdf"
        assert message.filename == "document.pdf"
        assert message.user_id == "user-123"
        assert message.priority is False

    def test_valid_url_message(self):
        """Test valid URL message."""
        message = IngestMessage(
            doc_id="test-doc-456",
            source=DocumentSource.URL,
            source_url="https://example.com/document.pdf",
            filename="document.pdf",
            user_id="user-456",
            priority=True,
            webhook_url="https://webhook.example.com/notify"
        )

        assert message.doc_id == "test-doc-456"
        assert message.source == DocumentSource.URL
        assert message.source_url == "https://example.com/document.pdf"
        assert message.webhook_url == "https://webhook.example.com/notify"
        assert message.priority is True

    def test_upload_missing_s3_key(self):
        """Test upload message missing required s3_key."""
        with pytest.raises(ValidationError) as exc_info:
            IngestMessage(
                doc_id="test-doc-123",
                source=DocumentSource.UPLOAD,
                filename="document.pdf"
            )

        assert "s3_key is required when source is upload" in str(exc_info.value)

    def test_url_missing_source_url(self):
        """Test URL message missing required source_url."""
        with pytest.raises(ValidationError) as exc_info:
            IngestMessage(
                doc_id="test-doc-123",
                source=DocumentSource.URL,
                filename="document.pdf"
            )

        assert "source_url is required when source is URL" in str(exc_info.value)

    def test_invalid_source_url(self):
        """Test invalid source URL format."""
        with pytest.raises(ValidationError) as exc_info:
            IngestMessage(
                doc_id="test-doc-123",
                source=DocumentSource.URL,
                source_url="not-a-url",
                filename="document.pdf"
            )

        assert "source_url must be a valid HTTP/HTTPS URL" in str(exc_info.value)


class TestDocumentRecord:
    """Test DocumentRecord model."""

    def test_valid_document_record(self):
        """Test valid document record creation."""
        record = DocumentRecord(
            doc_id="test-doc-123",
            user_id="user-123",
            source=DocumentSource.UPLOAD,
            filename="document.pdf",
            s3_key_original="originals/test-doc-123/document.pdf",
            metadata={"test": True}
        )

        assert record.doc_id == "test-doc-123"
        assert record.status == DocumentStatus.PENDING
        assert record.source == DocumentSource.UPLOAD
        assert isinstance(record.created_at, datetime)
        assert isinstance(record.updated_at, datetime)
        assert record.metadata == {"test": True}

    def test_default_values(self):
        """Test document record default values."""
        record = DocumentRecord(
            doc_id="test-doc-123",
            source=DocumentSource.URL
        )

        assert record.status == DocumentStatus.PENDING
        assert record.metadata == {}
        assert record.artifacts == {}
        assert record.processing_stats == {}


class TestJobRecord:
    """Test JobRecord model."""

    def test_valid_job_record(self):
        """Test valid job record creation."""
        job = JobRecord(
            doc_id="test-doc-123",
            step=JobStep.OCR,
            priority=True,
            input_data={"s3_key": "test-key"}
        )

        assert job.doc_id == "test-doc-123"
        assert job.step == JobStep.OCR
        assert job.status == JobStatus.PENDING
        assert job.priority is True
        assert job.input_data == {"s3_key": "test-key"}
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert isinstance(job.created_at, datetime)

    def test_job_id_generation(self):
        """Test that job_id is automatically generated."""
        job = JobRecord(
            doc_id="test-doc-123",
            step=JobStep.OCR
        )

        assert job.job_id is not None
        assert len(job.job_id) > 0

    def test_default_values(self):
        """Test job record default values."""
        job = JobRecord(
            doc_id="test-doc-123",
            step=JobStep.STRUCTURE
        )

        assert job.status == JobStatus.PENDING
        assert job.priority is False
        assert job.input_data == {}
        assert job.output_data == {}
        assert job.retry_count == 0
        assert job.max_retries == 3


class TestProcessMessage:
    """Test ProcessMessage model."""

    def test_valid_process_message(self):
        """Test valid process message creation."""
        message = ProcessMessage(
            job_id="job-123",
            doc_id="doc-123",
            step=JobStep.OCR,
            priority=True,
            input_data={"test": "data"},
            retry_count=1
        )

        assert message.job_id == "job-123"
        assert message.doc_id == "doc-123"
        assert message.step == JobStep.OCR
        assert message.priority is True
        assert message.input_data == {"test": "data"}
        assert message.retry_count == 1

    def test_default_values(self):
        """Test process message default values."""
        message = ProcessMessage(
            job_id="job-123",
            doc_id="doc-123",
            step=JobStep.VALIDATOR
        )

        assert message.priority is False
        assert message.input_data == {}
        assert message.retry_count == 0


class TestEnums:
    """Test enum values."""

    def test_document_source_values(self):
        """Test DocumentSource enum values."""
        assert DocumentSource.UPLOAD.value == "upload"
        assert DocumentSource.URL.value == "url"

    def test_document_status_values(self):
        """Test DocumentStatus enum values."""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.PROCESSING.value == "processing"
        assert DocumentStatus.COMPLETED.value == "completed"
        assert DocumentStatus.FAILED.value == "failed"

    def test_job_step_values(self):
        """Test JobStep enum values."""
        assert JobStep.OCR.value == "ocr"
        assert JobStep.STRUCTURE.value == "structure"
        assert JobStep.TAGGER.value == "tagger"
        assert JobStep.EXPORTER.value == "exporter"
        assert JobStep.VALIDATOR.value == "validator"
        assert JobStep.NOTIFIER.value == "notifier"

    def test_job_status_values(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.SKIPPED.value == "skipped"

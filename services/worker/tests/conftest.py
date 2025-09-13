import os
from unittest.mock import MagicMock, patch

import pytest

# Set test environment
os.environ.update(
    {
        "TESTING": "true",
        "CELERY_TASK_ALWAYS_EAGER": "true",
        "CELERY_TASK_EAGER_PROPAGATES": "true",
        "DATABASE_URL": "postgresql://postgres:test@localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379/0",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "us-east-1",
    }
)

from src.pdf_worker.app import create_app
from src.pdf_worker.core.celery import celery_app


@pytest.fixture
def app():
    """Create worker app for testing."""
    app = create_app(testing=True)
    return app


@pytest.fixture
def celery_worker():
    """Create Celery app for testing."""
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        result_backend="cache+memory://",
        broker_url="memory://",
    )
    return celery_app


@pytest.fixture
def mock_aws_services():
    """Mock AWS services for worker tests."""
    with (
        patch("boto3.client") as mock_boto3_client,
        patch("boto3.resource"),
    ):

        # Mock S3
        mock_s3 = MagicMock()
        mock_s3.download_file.return_value = None
        mock_s3.upload_file.return_value = None
        mock_s3.head_object.return_value = {"ContentLength": 1024}

        # Mock Lambda
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 200, "Payload": MagicMock()}

        def boto3_client_side_effect(service_name, **kwargs):
            if service_name == "s3":
                return mock_s3
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3_client.side_effect = boto3_client_side_effect

        yield {"s3": mock_s3, "lambda": mock_lambda}


@pytest.fixture
def sample_document_task():
    """Sample document processing task data."""
    return {
        "document_id": "test-doc-123",
        "filename": "test-document.pdf",
        "s3_bucket": "pdf-uploads",
        "s3_key": "documents/test-doc-123.pdf",
        "user_id": "user-123",
        "tenant_id": "tenant-123",
        "priority": False,
        "webhook_url": "https://example.com/webhook",
    }

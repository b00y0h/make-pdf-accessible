import os
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "ENVIRONMENT": "test",
        # Worker-specific environment variables
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
        "DATABASE_URL": "postgresql://testuser:testpass@localhost:5432/testdb",
        "REDIS_URL": "redis://localhost:6379/0"
    }

    with patch.dict(os.environ, test_env):
        yield

@pytest.fixture
def mock_celery_app():
    """Mock Celery app"""
    with patch('celery.Celery') as mock_celery:
        mock_app = Mock()
        mock_celery.return_value = mock_app

        # Mock task decorator
        def mock_task(func):
            func.delay = Mock(return_value=Mock(id='test-task-id'))
            func.apply_async = Mock(return_value=Mock(id='test-task-id'))
            return func

        mock_app.task = mock_task
        mock_app.tasks = {}

        yield mock_app

@pytest.fixture
def sample_document_job():
    """Sample document processing job"""
    return {
        "job_id": "test-job-123",
        "document_id": "test-doc-456",
        "user_id": "test-user-789",
        "source_bucket": "test-source-bucket",
        "source_key": "documents/test.pdf",
        "processing_options": {
            "ocr_enabled": True,
            "structure_analysis": True,
            "accessibility_validation": True
        },
        "callback_url": "https://api.example.com/webhooks/job-complete"
    }

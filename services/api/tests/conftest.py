import os
from unittest.mock import Mock, patch

import boto3
import pytest
from app.main import app
from fastapi.testclient import TestClient
from moto import mock_aws


# Test settings
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    os.environ.update(
        {
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "COGNITO_USER_POOL_ID": "us-east-1_test123",
            "COGNITO_CLIENT_ID": "test-client-id",
            "WEBHOOK_SECRET_KEY": "test-secret-key",
            "DOCUMENTS_TABLE": "test-documents",
            "JOBS_TABLE": "test-jobs",
            "PDF_ORIGINALS_BUCKET": "test-originals",
            "PDF_DERIVATIVES_BUCKET": "test-derivatives",
            "INGEST_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-ingest",
            "ENVIRONMENT": "test",
        }
    )


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def aws_mock(aws_credentials):
    """Mock AWS services"""
    with mock_aws():
        # Create DynamoDB tables
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        dynamodb.create_table(
            TableName="test-documents",
            KeySchema=[{"AttributeName": "docId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "docId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        dynamodb.create_table(
            TableName="test-jobs",
            KeySchema=[{"AttributeName": "jobId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "jobId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create S3 buckets
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-originals")
        s3.create_bucket(Bucket="test-derivatives")

        # Create SQS queues
        sqs = boto3.client("sqs", region_name="us-east-1")
        sqs.create_queue(QueueName="test-ingest")

        yield {"dynamodb": dynamodb, "s3": s3, "sqs": sqs}


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    from app.auth import User
    from app.models import UserRole

    return User(
        sub="test-user-123",
        username="testuser",
        email="test@example.com",
        roles=[UserRole.VIEWER.value],
        token_claims={"sub": "test-user-123", "username": "testuser"},
    )


@pytest.fixture
def mock_admin_user():
    """Mock admin user"""
    from app.auth import User
    from app.models import UserRole

    return User(
        sub="admin-user-123",
        username="admin",
        email="admin@example.com",
        roles=[UserRole.ADMIN.value],
        token_claims={"sub": "admin-user-123", "username": "admin"},
    )


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing"""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6InRlc3Qta2lkIn0.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInRva2VuX3VzZSI6ImFjY2VzcyIsImF1ZCI6InRlc3QtY2xpZW50LWlkIiwiaXNzIjoiaHR0cHM6Ly9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbS91cy1lYXN0LTFfdGVzdDEyMyIsImV4cCI6OTk5OTk5OTk5OX0"


@pytest.fixture(autouse=True)
def mock_powertools():
    """Mock AWS Powertools to avoid dependencies in tests"""
    with (
        patch("app.main.logger") as mock_logger,
        patch("app.main.tracer") as mock_tracer,
        patch("app.main.metrics") as mock_metrics,
    ):

        mock_logger.info = Mock()
        mock_logger.error = Mock()
        mock_logger.warning = Mock()
        mock_logger.exception = Mock()
        mock_logger.set_correlation_id = Mock()
        mock_logger.inject_lambda_context = lambda x: lambda f: f

        mock_tracer.capture_method = lambda f: f
        mock_tracer.capture_lambda_handler = lambda f: f

        mock_metrics.add_metric = Mock()
        mock_metrics.log_metrics = lambda f: f

        yield {"logger": mock_logger, "tracer": mock_tracer, "metrics": mock_metrics}


@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "docId": "test-doc-123",
        "userId": "test-user-123",
        "status": "pending",
        "filename": "test.pdf",
        "createdAt": "2023-01-01T00:00:00",
        "updatedAt": "2023-01-01T00:00:00",
        "metadata": {"source": "test"},
        "artifacts": {},
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload for testing"""
    return {
        "event_type": "document.completed",
        "doc_id": "test-doc-123",
        "status": "completed",
        "timestamp": "2023-01-01T00:00:00Z",
        "data": {"processing_time": 30},
    }

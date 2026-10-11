import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import Mock, patch

import boto3
import pytest
from app.auth import User, get_current_user
from app.config import settings
from app.main import app
from fastapi.testclient import TestClient
from moto import mock_aws


@pytest.fixture
def callback_queue():
    """Mocked SQS callback queue that the webhook route sends to"""
    with mock_aws():
        sqs = boto3.client("sqs", region_name=settings.aws_region)
        queue_url = sqs.create_queue(QueueName="test-callbacks")["QueueUrl"]

        with patch("app.routes.webhooks.settings.callback_queue_url", queue_url):
            yield sqs, queue_url


class TestIntegrationEndpoints:
    """Integration tests for API endpoints"""

    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test health check endpoint"""
        with patch("boto3.client") as mock_boto:
            # Mock successful AWS connection
            mock_sts = mock_boto.return_value
            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "version" in data
            assert "dependencies" in data
            assert "aws" in data["dependencies"]

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_webhook_health_endpoint(self):
        """Test webhook health endpoint"""
        response = self.client.get("/v1/webhooks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webhooks"

    def test_reports_health_endpoint(self):
        """Test reports health endpoint"""
        response = self.client.get("/v1/reports/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "reports"
        assert "features" in data

    def test_webhook_test_endpoint_development(self):
        """Test webhook test endpoint in development"""
        with patch("app.config.settings.environment", "development"):
            test_payload = {
                "event_type": "test.event",
                "doc_id": "12345678-1234-1234-1234-123456789012",
                "data": {"test": True},
            }

            response = self.client.post("/v1/webhooks/test", json=test_payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "test_received"
            assert data["received_payload"] == test_payload

    def test_webhook_test_endpoint_production(self):
        """Test webhook test endpoint blocked in production"""
        with patch("app.config.settings.environment", "production"):
            response = self.client.post("/v1/webhooks/test", json={"test": True})

            assert response.status_code == 404
            assert "not available in production" in response.json()["message"]

    def test_cors_headers(self):
        """Test CORS headers on preflight requests from allowed origins only"""
        preflight = {"Access-Control-Request-Method": "GET"}

        # The default allowed origins are the local dashboard and web app
        response = self.client.options(
            "/health", headers={**preflight, "Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == (
            "http://localhost:3000"
        )
        assert "access-control-allow-methods" in response.headers

        response = self.client.options(
            "/health", headers={**preflight, "Origin": "https://example.com"}
        )

        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_openapi_docs_available(self):
        """Test OpenAPI documentation is available"""
        response = self.client.get("/docs")
        assert response.status_code == 200

        response = self.client.get("/openapi.json")
        assert response.status_code == 200

        # Verify it's valid JSON
        openapi_spec = response.json()
        assert "openapi" in openapi_spec
        assert "info" in openapi_spec
        assert "paths" in openapi_spec

    def test_error_response_format(self):
        """Test error responses follow standard format"""
        # Test 404 error
        response = self.client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data

    def test_correlation_id_header(self):
        """Test correlation ID is added to responses"""
        response = self.client.get("/health")

        assert response.status_code == 200
        assert "x-correlation-id" in response.headers
        assert len(response.headers["x-correlation-id"]) > 0

    def test_custom_correlation_id(self):
        """Test custom correlation ID is preserved"""
        custom_id = "custom-correlation-123"

        response = self.client.get("/health", headers={"x-correlation-id": custom_id})

        assert response.status_code == 200
        assert response.headers["x-correlation-id"] == custom_id


class TestAuthenticationIntegration:
    """Integration tests for authentication"""

    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)

    def teardown_method(self):
        """Remove dependency overrides"""
        app.dependency_overrides.pop(get_current_user, None)

    def test_protected_endpoint_without_auth(self):
        """Test protected endpoint rejects requests without a session"""
        response = self.client.get("/documents")

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "http_403"
        assert data["message"] == "Not authenticated"

    def test_protected_endpoint_ignores_authorization_header(self):
        """Test an Authorization header alone does not authenticate"""
        response = self.client.get(
            "/documents", headers={"Authorization": "Basic invalid-token"}
        )

        assert response.status_code == 403
        data = response.json()
        assert data["message"] == "Not authenticated"

    def test_admin_endpoint_requires_admin_role(self):
        """Test admin endpoint requires admin role"""
        viewer_user = User(sub="viewer-123", name="viewer", role="viewer")
        app.dependency_overrides[get_current_user] = lambda: viewer_user

        response = self.client.get("/v1/reports/summary")

        assert response.status_code == 403
        data = response.json()
        assert "Required roles" in data["message"]

    def test_admin_can_get_summary_report(self):
        """Test admins can read the summary report"""
        admin_user = User(sub="admin-123", name="admin", role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin_user

        doc_repo = Mock()
        doc_repo.get_processing_summary.return_value = {
            "total_documents": 4,
            "completed_documents": 3,
            "failed_documents": 1,
            "processing_documents": 0,
            "pending_documents": 0,
            "completion_rate": 0.75,
            "avg_processing_time_hours": 0.5,
        }
        doc_repo.get_weekly_stats.return_value = [
            {
                "week": "2026-W40",
                "documents": 4,
                "completed": 3,
                "failed": 1,
                "success_rate": 0.75,
            }
        ]

        with patch(
            "app.services.reports.get_document_repository", return_value=doc_repo
        ):
            response = self.client.get("/v1/reports/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 4
        assert data["completion_rate"] == 75.0
        assert data["weekly_stats"] == [
            {
                "week": "2026-W40",
                "total_documents": 4,
                "completed_documents": 3,
                "failed_documents": 1,
                "success_rate": 75.0,
            }
        ]


class TestReportsExportIntegration:
    """Integration tests for the CSV report export"""

    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)
        admin_user = User(sub="admin-123", name="admin", role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin_user

    def teardown_method(self):
        """Remove dependency overrides"""
        app.dependency_overrides.pop(get_current_user, None)

    def test_admin_can_export_documents_csv(self):
        """Test the export streams filtered documents as CSV"""
        doc_repo = Mock()
        doc_repo.aggregate.return_value = [
            {
                "docId": "12345678-1234-1234-1234-123456789012",
                "filename": "report.pdf",
                "ownerId": "user-123",
                "status": "completed",
                "createdAt": datetime(2026, 10, 1, 12, 0, 0),
                "updatedAt": datetime(2026, 10, 1, 12, 5, 0),
                "completedAt": datetime(2026, 10, 1, 12, 5, 0),
                "fileSize": 2048,
                "contentType": "application/pdf",
                "totalIssues": 2,
                "priority": False,
            }
        ]

        with patch(
            "app.services.reports.get_document_repository", return_value=doc_repo
        ):
            response = self.client.get(
                "/v1/reports/export.csv",
                params={"status_filter": "completed", "owner_filter": "user-123"},
            )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "status_completed" in response.headers["content-disposition"]

        # UTF-8 with BOM, so Excel detects the encoding
        assert response.content.startswith(b"\xef\xbb\xbf")
        lines = response.content.decode("utf-8-sig").splitlines()
        assert lines[0].startswith("Document ID,Filename,Owner ID,Status,Created At")
        assert lines[1].startswith(
            "12345678-1234-1234-1234-123456789012,report.pdf,user-123,completed,"
            "2026-10-01T12:00:00,"
        )
        assert len(lines) == 2

        pipeline = doc_repo.aggregate.call_args.args[0]
        assert pipeline[0] == {"$match": {"ownerId": "user-123", "status": "completed"}}

    def test_export_without_documents_writes_headers(self):
        """Test an empty export still has the CSV header row"""
        doc_repo = Mock()
        doc_repo.aggregate.return_value = []

        with patch(
            "app.services.reports.get_document_repository", return_value=doc_repo
        ):
            response = self.client.get("/v1/reports/export.csv")

        assert response.status_code == 200
        lines = response.content.decode("utf-8-sig").splitlines()
        assert len(lines) == 1
        assert lines[0].startswith("Document ID,Filename,Owner ID,Status")

        # Without filters the pipeline has no $match stage
        pipeline = doc_repo.aggregate.call_args.args[0]
        assert "$match" not in pipeline[0]


class TestWebhookIntegration:
    """Integration tests for webhooks"""

    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)

    def test_webhook_without_signature(self):
        """Test webhook without signature header"""
        payload = {
            "event_type": "document.completed",
            "doc_id": "12345678-1234-1234-1234-123456789012",
            "status": "completed",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        response = self.client.post("/v1/webhooks", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "Missing webhook signature" in data["message"]

    def test_webhook_with_invalid_json(self):
        """Test webhook with invalid JSON payload"""
        response = self.client.post(
            "/v1/webhooks",
            content="invalid-json",
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=test-signature",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid JSON payload" in data["message"]

    def test_webhook_missing_required_fields(self):
        """Test webhook with missing required fields"""
        incomplete_payload = {
            "event_type": "document.completed",
            # Missing required fields: doc_id, status, timestamp
        }

        # Without a secret the route skips signature verification
        with patch("app.routes.webhooks.settings.webhook_secret_key", ""):
            response = self.client.post(
                "/v1/webhooks",
                json=incomplete_payload,
                headers={"X-Hub-Signature-256": "sha256=valid-signature"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "Missing required fields" in data["message"]

    def test_signed_webhook_is_processed(self, callback_queue):
        """Test a correctly signed webhook is verified and queued"""
        sqs, queue_url = callback_queue
        secret = "test-secret-key"
        body = json.dumps(
            {
                "event_type": "document.completed",
                "doc_id": "12345678-1234-1234-1234-123456789012",
                "status": "completed",
                "timestamp": "2023-01-01T00:00:00Z",
            }
        )
        signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256)

        with patch("app.routes.webhooks.settings.webhook_secret_key", secret):
            response = self.client.post(
                "/v1/webhooks",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": f"sha256={signature.hexdigest()}",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "received"

        messages = sqs.receive_message(
            QueueUrl=queue_url, MessageAttributeNames=["All"]
        )["Messages"]
        assert len(messages) == 1
        assert json.loads(messages[0]["Body"]) == json.loads(body)
        event_type = messages[0]["MessageAttributes"]["eventType"]["StringValue"]
        assert event_type == "document.completed"

    def test_webhook_with_wrong_signature_is_rejected(self, callback_queue):
        """Test a webhook signed with the wrong secret is rejected and not queued"""
        sqs, queue_url = callback_queue
        body = json.dumps(
            {
                "event_type": "document.completed",
                "doc_id": "12345678-1234-1234-1234-123456789012",
                "status": "completed",
                "timestamp": "2023-01-01T00:00:00Z",
            }
        )
        signature = hmac.new(b"wrong-secret", body.encode(), hashlib.sha256)

        with patch(
            "app.routes.webhooks.settings.webhook_secret_key", "test-secret-key"
        ):
            response = self.client.post(
                "/v1/webhooks",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": f"sha256={signature.hexdigest()}",
                },
            )

        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["message"]
        assert "Messages" not in sqs.receive_message(QueueUrl=queue_url)

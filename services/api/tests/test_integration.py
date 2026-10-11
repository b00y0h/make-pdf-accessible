import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from app.auth import User, get_current_user
from app.main import app
from fastapi.testclient import TestClient


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

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "app/services/ shadows app/services.py, and its ReportsService is an "
            "empty placeholder without get_summary_report"
        ),
    )
    def test_admin_can_get_summary_report(self):
        """Test admins can read the summary report"""
        admin_user = User(sub="admin-123", name="admin", role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin_user

        response = self.client.get("/v1/reports/summary")

        assert response.status_code == 200


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

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "app/services/ shadows app/services.py, and its WebhookService is an "
            "empty placeholder without verify_webhook_signature or process_webhook"
        ),
    )
    def test_signed_webhook_is_processed(self):
        """Test a correctly signed webhook is verified and processed"""
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

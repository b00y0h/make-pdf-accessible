"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test class for API endpoints."""

    def test_root_endpoint_response_format(self):
        """Test root endpoint response format."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint_response_format(self):
        """Test health endpoint response format."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # In test environment, AWS will be unhealthy, so status should be degraded
        assert data["status"] in ["healthy", "degraded"]

    def test_health_endpoint_headers(self):
        """Test health endpoint response headers."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    def test_nonexistent_endpoint(self):
        """Test nonexistent endpoint returns 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_root_endpoint_methods(self):
        """Test root endpoint only accepts GET method."""
        # GET should work
        response = client.get("/")
        assert response.status_code == 200

        # POST should not be allowed
        response = client.post("/")
        assert response.status_code == 405  # Method Not Allowed

    def test_health_endpoint_methods(self):
        """Test health endpoint only accepts GET method."""
        # GET should work
        response = client.get("/health")
        assert response.status_code == 200

        # POST should not be allowed
        response = client.post("/health")
        assert response.status_code == 405  # Method Not Allowed

    @pytest.mark.parametrize("endpoint", ["/", "/health"])
    def test_endpoint_response_time(self, endpoint):
        """Test endpoint response time is reasonable."""
        import time

        start_time = time.time()
        response = client.get(endpoint)
        end_time = time.time()

        assert response.status_code == 200
        # Response should be under 1 second
        assert (end_time - start_time) < 1.0

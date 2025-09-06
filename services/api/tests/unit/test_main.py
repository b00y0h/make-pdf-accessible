"""Unit tests for main API module."""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "dependencies" in data
    # AWS will be unhealthy in test environment, so status should be degraded
    assert data["status"] in ["healthy", "degraded"]


def test_app_metadata():
    """Test FastAPI app metadata."""
    assert app.title == "PDF Accessibility Platform API"
    assert app.description == "API for PDF accessibility processing platform"
    assert app.version == "1.0.0"

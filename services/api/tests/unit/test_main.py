"""Unit tests for main API module."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "PDF Accessibility API is running"}


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_app_metadata():
    """Test FastAPI app metadata."""
    assert app.title == "PDF Accessibility API"
    assert app.description == "Main API gateway for PDF accessibility services"
    assert app.version == "1.0.0"

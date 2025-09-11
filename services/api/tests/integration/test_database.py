"""Integration tests for database connectivity."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


@pytest.fixture
def database_url():
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb"
    )


def test_database_connection(database_url):
    """Test database connection."""
    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
    except OperationalError:
        pytest.skip("Database not available for integration testing")


def test_database_version(database_url):
    """Test database version query."""
    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            assert "PostgreSQL" in version
    except OperationalError:
        pytest.skip("Database not available for integration testing")

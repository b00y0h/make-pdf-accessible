"""Integration tests for Redis connectivity."""

import os

import pytest
import redis
from redis.exceptions import ConnectionError


@pytest.fixture
def redis_url():
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def test_redis_connection(redis_url):
    """Test Redis connection."""
    try:
        r = redis.from_url(redis_url)
        assert r.ping() is True
    except ConnectionError:
        pytest.skip("Redis not available for integration testing")


def test_redis_set_get(redis_url):
    """Test Redis set and get operations."""
    try:
        r = redis.from_url(redis_url)
        test_key = "test:api:integration"
        test_value = "test_value"

        # Set value
        r.set(test_key, test_value, ex=60)  # Expire in 60 seconds

        # Get value
        retrieved_value = r.get(test_key)
        assert retrieved_value.decode() == test_value

        # Clean up
        r.delete(test_key)
    except ConnectionError:
        pytest.skip("Redis not available for integration testing")

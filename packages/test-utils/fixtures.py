"""
Pytest fixtures for Testcontainers integration.
These fixtures provide real database and service instances for integration testing.
"""

from collections.abc import Generator

import pytest
import pytest_asyncio

from .testcontainers import (
    DatabaseTestContainer,
    LocalStackTestContainer,
    RedisTestContainer,
    TestEnvironment,
)


# Session-scoped fixtures for expensive container startup
@pytest.fixture(scope="session")
def postgres_container_session() -> Generator[DatabaseTestContainer, None, None]:
    """Session-scoped PostgreSQL container for integration tests."""
    container = DatabaseTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def redis_container_session() -> Generator[RedisTestContainer, None, None]:
    """Session-scoped Redis container for integration tests."""
    container = RedisTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def localstack_container_session() -> Generator[LocalStackTestContainer, None, None]:
    """Session-scoped LocalStack container for AWS service mocking."""
    container = LocalStackTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def test_environment_session() -> Generator[TestEnvironment, None, None]:
    """Session-scoped complete test environment."""
    env = TestEnvironment()
    try:
        env.start()
        yield env
    finally:
        env.stop()


# Function-scoped fixtures for test isolation
@pytest.fixture
def postgres_container() -> Generator[DatabaseTestContainer, None, None]:
    """Function-scoped PostgreSQL container with fresh state per test."""
    container = DatabaseTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@pytest.fixture
def redis_container() -> Generator[RedisTestContainer, None, None]:
    """Function-scoped Redis container with fresh state per test."""
    container = RedisTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@pytest.fixture
def localstack_container() -> Generator[LocalStackTestContainer, None, None]:
    """Function-scoped LocalStack container with fresh state per test."""
    container = LocalStackTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


# Async fixtures for database operations
@pytest_asyncio.fixture
async def postgres_pool(postgres_container_session: DatabaseTestContainer):
    """Async fixture providing a PostgreSQL connection pool."""
    pool = await postgres_container_session.get_connection_pool()
    yield pool


@pytest_asyncio.fixture
async def clean_postgres_session(postgres_container_session: DatabaseTestContainer):
    """Clean PostgreSQL state between tests (session-scoped container)."""
    # Clean up before test
    await _clean_postgres_database(postgres_container_session)

    yield postgres_container_session

    # Clean up after test
    await _clean_postgres_database(postgres_container_session)


@pytest_asyncio.fixture
async def clean_postgres(postgres_container: DatabaseTestContainer):
    """Clean PostgreSQL state for isolated tests (function-scoped container)."""
    yield postgres_container


async def _clean_postgres_database(container: DatabaseTestContainer) -> None:
    """Helper to clean PostgreSQL database state."""
    pool = await container.get_connection_pool()
    async with pool.acquire() as conn:
        # Drop all tables in the public schema
        await conn.execute(
            """
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO public;
        """
        )


@pytest.fixture
def clean_redis_session(redis_container_session: RedisTestContainer):
    """Clean Redis state between tests (session-scoped container)."""
    client = redis_container_session.get_client()

    # Clean up before test
    client.flushall()

    yield redis_container_session

    # Clean up after test
    client.flushall()


@pytest.fixture
def clean_redis(redis_container: RedisTestContainer):
    """Clean Redis state for isolated tests (function-scoped container)."""
    yield redis_container


# Specialized fixtures for different test scenarios
@pytest.fixture
def postgres_for_api_tests(postgres_container_session: DatabaseTestContainer):
    """PostgreSQL container configured for API integration tests."""
    # Could add API-specific setup here (migrations, seed data, etc.)
    return postgres_container_session


@pytest.fixture
def postgres_for_worker_tests(postgres_container_session: DatabaseTestContainer):
    """PostgreSQL container configured for worker integration tests."""
    # Could add worker-specific setup here
    return postgres_container_session


@pytest.fixture
def localstack_for_s3_tests() -> Generator[LocalStackTestContainer, None, None]:
    """LocalStack container with only S3 service for focused testing."""
    container = LocalStackTestContainer(services=["s3"])
    try:
        container.start()

        # Setup S3 buckets for testing
        import boto3

        s3_client = boto3.client(
            "s3",
            endpoint_url=container.get_endpoint_url(),
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        # Create test buckets
        test_buckets = ["pdf-uploads", "pdf-processed", "pdf-exports"]
        for bucket in test_buckets:
            try:
                s3_client.create_bucket(Bucket=bucket)
            except Exception:
                pass  # Bucket might already exist

        yield container
    finally:
        container.stop()


@pytest.fixture
def localstack_for_lambda_tests() -> Generator[LocalStackTestContainer, None, None]:
    """LocalStack container with Lambda and related services."""
    container = LocalStackTestContainer(services=["lambda", "apigateway", "sts", "iam"])
    try:
        container.start()
        yield container
    finally:
        container.stop()


# Composite fixtures for end-to-end testing
@pytest.fixture
def full_test_environment() -> Generator[TestEnvironment, None, None]:
    """Complete test environment for full integration tests."""
    env = TestEnvironment(
        include_postgres=True,
        include_redis=True,
        include_localstack=True,
        localstack_services=["s3", "dynamodb", "lambda", "apigateway", "sts"],
    )
    try:
        env.start()
        yield env
    finally:
        env.stop()


@pytest.fixture
def minimal_test_environment() -> Generator[TestEnvironment, None, None]:
    """Minimal test environment with just PostgreSQL and Redis."""
    env = TestEnvironment(
        include_postgres=True, include_redis=True, include_localstack=False
    )
    try:
        env.start()
        yield env
    finally:
        env.stop()


# Database migration fixtures
@pytest_asyncio.fixture
async def postgres_with_migrations(postgres_container: DatabaseTestContainer):
    """PostgreSQL container with database migrations applied."""
    # Run migrations here if you have a migration system
    # For example:
    # await run_alembic_migrations(postgres_container.get_connection_url())

    yield postgres_container


# Mark fixtures for different test categories
pytest.mark.integration = pytest.mark.mark
pytest.mark.database = pytest.mark.mark
pytest.mark.aws = pytest.mark.mark
pytest.mark.redis = pytest.mark.mark


# Utility functions for test setup
def pytest_configure(config):
    """Configure pytest with custom markers for container tests."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring containers"
    )
    config.addinivalue_line(
        "markers", "database: marks tests requiring PostgreSQL database"
    )
    config.addinivalue_line("markers", "redis: marks tests requiring Redis")
    config.addinivalue_line(
        "markers", "aws: marks tests requiring AWS services (LocalStack)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (container startup overhead)"
    )

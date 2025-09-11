"""
Testcontainers utilities for integration testing with real databases and services.
Provides Docker containers for PostgreSQL, Redis, and LocalStack (AWS services).
"""

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Dict, Optional

import asyncpg
import redis
from testcontainers.localstack import LocalStackContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

logger = logging.getLogger(__name__)


class DatabaseTestContainer:
    """PostgreSQL test container for integration tests."""

    def __init__(self, postgres_version: str = "15-alpine"):
        self.postgres_version = postgres_version
        self._container: Optional[PostgresContainer] = None
        self._connection_pool: Optional[asyncpg.Pool] = None

    def start(self) -> Dict[str, str]:
        """Start PostgreSQL container and return connection info."""
        if self._container is not None:
            raise RuntimeError("Container already started")

        self._container = PostgresContainer(
            image=f"postgres:{self.postgres_version}",
            username="testuser",
            password="testpass",
            dbname="testdb",
        )
        self._container.start()

        # Wait for container to be ready
        self._wait_for_container()

        connection_info = {
            "host": self._container.get_container_host_ip(),
            "port": str(self._container.get_exposed_port(5432)),
            "username": "testuser",
            "password": "testpass",
            "database": "testdb",
        }

        # Set environment variables for other services
        os.environ.update(
            {
                "DATABASE_URL": self.get_connection_url(),
                "DB_HOST": connection_info["host"],
                "DB_PORT": connection_info["port"],
                "DB_USER": connection_info["username"],
                "DB_PASSWORD": connection_info["password"],
                "DB_NAME": connection_info["database"],
            }
        )

        logger.info(f"PostgreSQL container started: {self.get_connection_url()}")
        return connection_info

    def stop(self) -> None:
        """Stop the PostgreSQL container."""
        if self._connection_pool:
            asyncio.run(self._connection_pool.close())
            self._connection_pool = None

        if self._container:
            self._container.stop()
            self._container = None
            logger.info("PostgreSQL container stopped")

    def get_connection_url(self) -> str:
        """Get the PostgreSQL connection URL."""
        if not self._container:
            raise RuntimeError("Container not started")

        host = self._container.get_container_host_ip()
        port = self._container.get_exposed_port(5432)
        return f"postgresql://testuser:testpass@{host}:{port}/testdb"

    async def get_connection_pool(self) -> asyncpg.Pool:
        """Get an asyncpg connection pool."""
        if not self._connection_pool:
            self._connection_pool = await asyncpg.create_pool(
                self.get_connection_url(), min_size=1, max_size=10
            )
        return self._connection_pool

    async def execute_sql(self, sql: str, *args) -> None:
        """Execute SQL directly on the test database."""
        pool = await self.get_connection_pool()
        async with pool.acquire() as conn:
            await conn.execute(sql, *args)

    async def fetch_sql(self, sql: str, *args):
        """Fetch SQL results from the test database."""
        pool = await self.get_connection_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    def _wait_for_container(self, timeout: int = 30) -> None:
        """Wait for PostgreSQL to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to connect
                import psycopg2

                conn = psycopg2.connect(
                    host=self._container.get_container_host_ip(),
                    port=self._container.get_exposed_port(5432),
                    user="testuser",
                    password="testpass",
                    database="testdb",
                )
                conn.close()
                return
            except Exception:
                time.sleep(0.5)

        raise TimeoutError(f"PostgreSQL container not ready after {timeout} seconds")


class RedisTestContainer:
    """Redis test container for integration tests."""

    def __init__(self, redis_version: str = "7-alpine"):
        self.redis_version = redis_version
        self._container: Optional[RedisContainer] = None
        self._client: Optional[redis.Redis] = None

    def start(self) -> Dict[str, str]:
        """Start Redis container and return connection info."""
        if self._container is not None:
            raise RuntimeError("Container already started")

        self._container = RedisContainer(image=f"redis:{self.redis_version}")
        self._container.start()

        connection_info = {
            "host": self._container.get_container_host_ip(),
            "port": str(self._container.get_exposed_port(6379)),
        }

        # Set environment variables
        os.environ.update(
            {
                "REDIS_URL": self.get_connection_url(),
                "REDIS_HOST": connection_info["host"],
                "REDIS_PORT": connection_info["port"],
            }
        )

        logger.info(f"Redis container started: {self.get_connection_url()}")
        return connection_info

    def stop(self) -> None:
        """Stop the Redis container."""
        if self._client:
            self._client.close()
            self._client = None

        if self._container:
            self._container.stop()
            self._container = None
            logger.info("Redis container stopped")

    def get_connection_url(self) -> str:
        """Get the Redis connection URL."""
        if not self._container:
            raise RuntimeError("Container not started")

        host = self._container.get_container_host_ip()
        port = self._container.get_exposed_port(6379)
        return f"redis://{host}:{port}/0"

    def get_client(self) -> redis.Redis:
        """Get a Redis client."""
        if not self._client:
            host = self._container.get_container_host_ip()
            port = self._container.get_exposed_port(6379)
            self._client = redis.Redis(host=host, port=port, decode_responses=True)
        return self._client


class LocalStackTestContainer:
    """LocalStack container for AWS service mocking."""

    def __init__(self, services: Optional[list] = None):
        self.services = services or ["s3", "dynamodb", "sts", "lambda", "apigateway"]
        self._container: Optional[LocalStackContainer] = None

    def start(self) -> Dict[str, str]:
        """Start LocalStack container."""
        if self._container is not None:
            raise RuntimeError("Container already started")

        # Configure LocalStack
        self._container = LocalStackContainer(image="localstack/localstack:latest")
        self._container.with_services(*self.services)

        # Start container
        self._container.start()

        connection_info = {
            "host": self._container.get_container_host_ip(),
            "port": str(self._container.get_exposed_port(4566)),
            "endpoint_url": f"http://{self._container.get_container_host_ip()}:{self._container.get_exposed_port(4566)}",
        }

        # Set environment variables for AWS SDK
        os.environ.update(
            {
                "AWS_ENDPOINT_URL": connection_info["endpoint_url"],
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_DEFAULT_REGION": "us-east-1",
                "LOCALSTACK_HOST": connection_info["host"],
                "LOCALSTACK_PORT": connection_info["port"],
            }
        )

        logger.info(f"LocalStack container started: {connection_info['endpoint_url']}")
        return connection_info

    def stop(self) -> None:
        """Stop the LocalStack container."""
        if self._container:
            self._container.stop()
            self._container = None
            logger.info("LocalStack container stopped")

    def get_endpoint_url(self) -> str:
        """Get the LocalStack endpoint URL."""
        if not self._container:
            raise RuntimeError("Container not started")

        host = self._container.get_container_host_ip()
        port = self._container.get_exposed_port(4566)
        return f"http://{host}:{port}"


class TestEnvironment:
    """Complete test environment with all containers."""

    def __init__(
        self,
        include_postgres: bool = True,
        include_redis: bool = True,
        include_localstack: bool = True,
        localstack_services: Optional[list] = None,
    ):
        self.include_postgres = include_postgres
        self.include_redis = include_redis
        self.include_localstack = include_localstack

        self.postgres: Optional[DatabaseTestContainer] = None
        self.redis: Optional[RedisTestContainer] = None
        self.localstack: Optional[LocalStackTestContainer] = None

        if include_postgres:
            self.postgres = DatabaseTestContainer()
        if include_redis:
            self.redis = RedisTestContainer()
        if include_localstack:
            self.localstack = LocalStackTestContainer(services=localstack_services)

    def start(self) -> Dict[str, Dict[str, str]]:
        """Start all containers."""
        connection_info = {}

        try:
            if self.postgres:
                connection_info["postgres"] = self.postgres.start()

            if self.redis:
                connection_info["redis"] = self.redis.start()

            if self.localstack:
                connection_info["localstack"] = self.localstack.start()

            logger.info("Test environment started successfully")
            return connection_info

        except Exception as e:
            # Clean up on error
            self.stop()
            raise RuntimeError(f"Failed to start test environment: {e}") from e

    def stop(self) -> None:
        """Stop all containers."""
        errors = []

        if self.postgres:
            try:
                self.postgres.stop()
            except Exception as e:
                errors.append(f"PostgreSQL: {e}")

        if self.redis:
            try:
                self.redis.stop()
            except Exception as e:
                errors.append(f"Redis: {e}")

        if self.localstack:
            try:
                self.localstack.stop()
            except Exception as e:
                errors.append(f"LocalStack: {e}")

        if errors:
            logger.warning(f"Errors stopping containers: {'; '.join(errors)}")
        else:
            logger.info("Test environment stopped successfully")


# Context managers for easy usage
@asynccontextmanager
async def postgres_container() -> AsyncGenerator[DatabaseTestContainer, None]:
    """Context manager for PostgreSQL container."""
    container = DatabaseTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@asynccontextmanager
async def redis_container() -> AsyncGenerator[RedisTestContainer, None]:
    """Context manager for Redis container."""
    container = RedisTestContainer()
    try:
        container.start()
        yield container
    finally:
        container.stop()


@asynccontextmanager
async def localstack_container(
    services: Optional[list] = None,
) -> AsyncGenerator[LocalStackTestContainer, None]:
    """Context manager for LocalStack container."""
    container = LocalStackTestContainer(services=services)
    try:
        container.start()
        yield container
    finally:
        container.stop()


@asynccontextmanager
async def test_environment(**kwargs) -> AsyncGenerator[TestEnvironment, None]:
    """Context manager for complete test environment."""
    env = TestEnvironment(**kwargs)
    try:
        env.start()
        yield env
    finally:
        env.stop()

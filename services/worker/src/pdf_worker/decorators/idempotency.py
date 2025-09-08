"""Idempotency decorator for ensuring operations execute only once."""

import functools
import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, TypeVar, cast

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from pdf_worker.aws.dynamodb import DynamoDBRepository
from pdf_worker.core.config import config
from pdf_worker.core.exceptions import IdempotencyError, WorkerConfigError

logger = Logger()
tracer = Tracer()

F = TypeVar('F', bound=Callable[..., Any])


class IdempotencyStore:
    """Store for managing idempotency records."""

    def __init__(self, table_name: str | None = None, ttl_seconds: int = 3600) -> None:
        """Initialize idempotency store.
        
        Args:
            table_name: DynamoDB table name for idempotency records
            ttl_seconds: TTL for idempotency records in seconds
        """
        self.table_name = table_name or config.idempotency_table
        self.ttl_seconds = ttl_seconds

        if not self.table_name:
            raise WorkerConfigError("Idempotency table not configured")

        self._repository = DynamoDBRepository(
            table_name=self.table_name,
            primary_key='idempotency_key'
        )

        logger.debug(f"Initialized idempotency store with table: {self.table_name}")

    @tracer.capture_method
    def get_record(self, idempotency_key: str) -> dict[str, Any] | None:
        """Get existing idempotency record.
        
        Args:
            idempotency_key: Unique key for the operation
            
        Returns:
            Existing record if found and not expired, None otherwise
        """
        try:
            record = self._repository.get_item(idempotency_key)

            if record:
                # Check if record is expired
                expiry_time = datetime.fromisoformat(record['expires_at'])
                if datetime.utcnow() > expiry_time:
                    # Record expired, delete it
                    self._repository.delete_item(idempotency_key)
                    return None

                return record

            return None

        except Exception as e:
            logger.warning(f"Failed to get idempotency record: {e}")
            return None

    @tracer.capture_method
    def save_inprogress(self, idempotency_key: str, request_data: dict[str, Any]) -> None:
        """Save in-progress idempotency record.
        
        Args:
            idempotency_key: Unique key for the operation
            request_data: Original request data
        """
        try:
            expiry_time = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

            record = {
                'idempotency_key': idempotency_key,
                'status': 'INPROGRESS',
                'request_data': request_data,
                'expires_at': expiry_time.isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }

            # Use condition to prevent overwriting existing records
            self._repository.put_item(
                item=record,
                condition_expression='attribute_not_exists(idempotency_key)'
            )

            logger.debug(f"Saved INPROGRESS record for key: {idempotency_key}")

        except Exception as e:
            if 'ConditionalCheckFailedException' in str(e):
                raise IdempotencyError(
                    f"Operation already in progress for key: {idempotency_key}",
                    key=idempotency_key
                )
            raise IdempotencyError(f"Failed to save idempotency record: {e}")

    @tracer.capture_method
    def save_success(
        self,
        idempotency_key: str,
        response_data: dict[str, Any]
    ) -> None:
        """Save successful operation result.
        
        Args:
            idempotency_key: Unique key for the operation
            response_data: Operation response data
        """
        try:
            self._repository.update_item(
                key=idempotency_key,
                update_expression='SET #status = :status, response_data = :response, completed_at = :completed',
                expression_attribute_names={'#status': 'status'},
                expression_attribute_values={
                    ':status': 'COMPLETED',
                    ':response': response_data,
                    ':completed': datetime.utcnow().isoformat()
                }
            )

            logger.debug(f"Saved COMPLETED record for key: {idempotency_key}")

        except Exception as e:
            logger.warning(f"Failed to save success record: {e}")

    @tracer.capture_method
    def delete_record(self, idempotency_key: str) -> None:
        """Delete idempotency record (used for cleanup on error).
        
        Args:
            idempotency_key: Unique key for the operation
        """
        try:
            self._repository.delete_item(idempotency_key)
            logger.debug(f"Deleted idempotency record for key: {idempotency_key}")

        except Exception as e:
            logger.warning(f"Failed to delete idempotency record: {e}")


class IdempotencyConfig:
    """Configuration for idempotency behavior."""

    def __init__(
        self,
        event_key_jmespath: str = "docId",
        payload_validation_jmespath: str | None = None,
        raise_on_no_idempotency_key: bool = True,
        expires_after_seconds: int = 3600,
        use_local_cache: bool = False
    ):
        """Initialize idempotency configuration.
        
        Args:
            event_key_jmespath: JMESPath expression to extract idempotency key from event
            payload_validation_jmespath: JMESPath for payload validation hash
            raise_on_no_idempotency_key: Whether to raise error if key not found
            expires_after_seconds: Expiration time for records
            use_local_cache: Whether to use local in-memory cache
        """
        self.event_key_jmespath = event_key_jmespath
        self.payload_validation_jmespath = payload_validation_jmespath
        self.raise_on_no_idempotency_key = raise_on_no_idempotency_key
        self.expires_after_seconds = expires_after_seconds
        self.use_local_cache = use_local_cache


def generate_idempotency_key(
    event: dict[str, Any],
    context: LambdaContext,
    config: IdempotencyConfig
) -> str:
    """Generate idempotency key from Lambda event.
    
    Args:
        event: Lambda event data
        context: Lambda context
        config: Idempotency configuration
        
    Returns:
        Generated idempotency key
        
    Raises:
        IdempotencyError: If key cannot be generated
    """
    try:
        # Extract base key from event using simple key path
        key_parts = config.event_key_jmespath.split('.')
        base_key = event

        for part in key_parts:
            if isinstance(base_key, dict) and part in base_key:
                base_key = base_key[part]
            else:
                if config.raise_on_no_idempotency_key:
                    raise IdempotencyError(f"Idempotency key not found: {config.event_key_jmespath}")
                base_key = "unknown"
                break

        # Create hash components
        hash_data = {
            'function_name': context.function_name,
            'key': str(base_key)
        }

        # Add payload validation if configured
        if config.payload_validation_jmespath:
            validation_parts = config.payload_validation_jmespath.split('.')
            validation_data = event

            for part in validation_parts:
                if isinstance(validation_data, dict) and part in validation_data:
                    validation_data = validation_data[part]
                else:
                    validation_data = None
                    break

            if validation_data:
                hash_data['payload_hash'] = hashlib.md5(
                    json.dumps(validation_data, sort_keys=True).encode()
                ).hexdigest()

        # Generate hash
        content = json.dumps(hash_data, sort_keys=True)
        key_hash = hashlib.sha256(content.encode()).hexdigest()

        return f"{context.function_name}#{key_hash}"

    except Exception as e:
        raise IdempotencyError(f"Failed to generate idempotency key: {e}")


def idempotent(
    config: IdempotencyConfig | None = None,
    persistence_store: IdempotencyStore | None = None
) -> Callable[[F], F]:
    """Decorator to make Lambda functions idempotent.
    
    Args:
        config: Idempotency configuration
        persistence_store: Custom persistence store
        
    Returns:
        Decorated function that handles idempotency
        
    Example:
        @idempotent(config=IdempotencyConfig(event_key_jmespath="docId"))
        def lambda_handler(event, context):
            return {"status": "processed", "docId": event["docId"]}
    """
    # Use default config if none provided
    if config is None:
        config = IdempotencyConfig()

    # Use default store if none provided
    if persistence_store is None:
        persistence_store = IdempotencyStore(
            ttl_seconds=config.expires_after_seconds
        )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract event and context from args
            if len(args) < 2:
                raise IdempotencyError("Lambda function must have event and context parameters")

            event = args[0]
            context = args[1]

            if not isinstance(event, dict):
                raise IdempotencyError("Event must be a dictionary")

            try:
                # Generate idempotency key
                idempotency_key = generate_idempotency_key(event, context, config)

                logger.debug(f"Processing with idempotency key: {idempotency_key}")

                # Check for existing record
                existing_record = persistence_store.get_record(idempotency_key)

                if existing_record:
                    if existing_record['status'] == 'COMPLETED':
                        logger.info("Returning cached result for idempotent operation")
                        return existing_record['response_data']

                    elif existing_record['status'] == 'INPROGRESS':
                        raise IdempotencyError(
                            f"Operation already in progress: {idempotency_key}",
                            key=idempotency_key
                        )

                # Save in-progress record
                persistence_store.save_inprogress(
                    idempotency_key=idempotency_key,
                    request_data=event
                )

                try:
                    # Execute original function
                    result = func(*args, **kwargs)

                    # Save successful result
                    persistence_store.save_success(
                        idempotency_key=idempotency_key,
                        response_data=result
                    )

                    logger.info("Successfully completed idempotent operation")
                    return result

                except Exception as e:
                    # Clean up in-progress record on error
                    persistence_store.delete_record(idempotency_key)
                    raise e

            except IdempotencyError:
                raise
            except Exception as e:
                logger.error(f"Idempotency handling failed: {e}")
                # Fall back to executing function without idempotency
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


# Convenience decorators for common patterns
def idempotent_by_doc_id(
    expires_after_seconds: int = 3600
) -> Callable[[F], F]:
    """Decorator for functions that should be idempotent by document ID.
    
    Args:
        expires_after_seconds: Expiration time for idempotency records
        
    Returns:
        Decorated function
    """
    return idempotent(
        config=IdempotencyConfig(
            event_key_jmespath="docId",
            expires_after_seconds=expires_after_seconds
        )
    )


def idempotent_by_job_id(
    expires_after_seconds: int = 3600
) -> Callable[[F], F]:
    """Decorator for functions that should be idempotent by job ID.
    
    Args:
        expires_after_seconds: Expiration time for idempotency records
        
    Returns:
        Decorated function
    """
    return idempotent(
        config=IdempotencyConfig(
            event_key_jmespath="jobId",
            expires_after_seconds=expires_after_seconds
        )
    )

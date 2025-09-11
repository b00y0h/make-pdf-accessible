"""Custom exceptions for PDF worker package."""

from typing import Any


class WorkerError(Exception):
    """Base exception for PDF worker errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize worker error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "WORKER_ERROR"
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class WorkerConfigError(WorkerError):
    """Configuration-related errors."""

    def __init__(self, message: str, missing_config: str | None = None) -> None:
        super().__init__(
            message,
            error_code="CONFIG_ERROR",
            details={"missing_config": missing_config} if missing_config else None,
        )


class S3Error(WorkerError):
    """S3-related errors."""

    def __init__(
        self, message: str, bucket: str | None = None, key: str | None = None
    ) -> None:
        super().__init__(
            message, error_code="S3_ERROR", details={"bucket": bucket, "key": key}
        )


class DynamoDBError(WorkerError):
    """DynamoDB-related errors."""

    def __init__(
        self, message: str, table: str | None = None, operation: str | None = None
    ) -> None:
        super().__init__(
            message,
            error_code="DYNAMODB_ERROR",
            details={"table": table, "operation": operation},
        )


class SQSError(WorkerError):
    """SQS-related errors."""

    def __init__(
        self, message: str, queue_url: str | None = None, message_id: str | None = None
    ) -> None:
        super().__init__(
            message,
            error_code="SQS_ERROR",
            details={"queue_url": queue_url, "message_id": message_id},
        )


class TextractError(WorkerError):
    """Textract-related errors."""

    def __init__(
        self, message: str, job_id: str | None = None, job_status: str | None = None
    ) -> None:
        super().__init__(
            message,
            error_code="TEXTRACT_ERROR",
            details={"job_id": job_id, "job_status": job_status},
        )


class BedrockError(WorkerError):
    """Bedrock-related errors."""

    def __init__(
        self, message: str, model_id: str | None = None, request_id: str | None = None
    ) -> None:
        super().__init__(
            message,
            error_code="BEDROCK_ERROR",
            details={"model_id": model_id, "request_id": request_id},
        )


class PDFProcessingError(WorkerError):
    """PDF processing-related errors."""

    def __init__(
        self, message: str, doc_id: str | None = None, operation: str | None = None
    ) -> None:
        super().__init__(
            message,
            error_code="PDF_PROCESSING_ERROR",
            details={"doc_id": doc_id, "operation": operation},
        )


class IdempotencyError(WorkerError):
    """Idempotency-related errors."""

    def __init__(self, message: str, key: str | None = None) -> None:
        super().__init__(message, error_code="IDEMPOTENCY_ERROR", details={"key": key})


class ValidationError(WorkerError):
    """Data validation errors."""

    def __init__(
        self, message: str, field: str | None = None, value: Any | None = None
    ) -> None:
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details={
                "field": field,
                "value": str(value) if value is not None else None,
            },
        )

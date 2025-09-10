"""Core configuration management for PDF worker."""

import os
from dataclasses import dataclass, field

from aws_lambda_powertools import Logger

logger = Logger()


@dataclass(frozen=True)
class WorkerConfig:
    """Central configuration for PDF worker components."""

    # AWS Configuration
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))

    # S3 Buckets
    pdf_originals_bucket: str | None = field(
        default_factory=lambda: os.getenv("PDF_ORIGINALS_BUCKET")
    )
    pdf_derivatives_bucket: str | None = field(
        default_factory=lambda: os.getenv("PDF_DERIVATIVES_BUCKET")
    )
    pdf_accessible_bucket: str | None = field(
        default_factory=lambda: os.getenv("PDF_ACCESSIBLE_BUCKET")
    )
    pdf_temp_bucket: str | None = field(
        default_factory=lambda: os.getenv("PDF_TEMP_BUCKET")
    )

    # DynamoDB Tables
    documents_table: str | None = field(
        default_factory=lambda: os.getenv("DOCUMENTS_TABLE")
    )
    jobs_table: str | None = field(
        default_factory=lambda: os.getenv("JOBS_TABLE")
    )

    # SQS Queues
    ingest_queue_url: str | None = field(
        default_factory=lambda: os.getenv("INGEST_QUEUE_URL")
    )
    process_queue_url: str | None = field(
        default_factory=lambda: os.getenv("PROCESS_QUEUE_URL")
    )
    priority_process_queue_url: str | None = field(
        default_factory=lambda: os.getenv("PRIORITY_PROCESS_QUEUE_URL")
    )
    dlq_url: str | None = field(
        default_factory=lambda: os.getenv("DLQ_URL")
    )

    # SNS Topics
    notifications_topic_arn: str | None = field(
        default_factory=lambda: os.getenv("NOTIFICATIONS_TOPIC_ARN")
    )
    alerts_topic_arn: str | None = field(
        default_factory=lambda: os.getenv("ALERTS_TOPIC_ARN")
    )

    # Processing Configuration
    textract_job_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("TEXTRACT_JOB_TIMEOUT_SECONDS", "600"))
    )
    bedrock_model_id: str = field(
        default_factory=lambda: os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
    )
    bedrock_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("BEDROCK_MAX_TOKENS", "4000"))
    )

    # Idempotency Configuration
    idempotency_table: str | None = field(
        default_factory=lambda: os.getenv("IDEMPOTENCY_TABLE")
    )
    idempotency_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "3600"))
    )

    # Authentication Configuration - BetterAuth
    better_auth_secret: str | None = field(
        default_factory=lambda: os.getenv("API_JWT_SECRET")
    )
    jwt_algorithm: str = field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )
    jwt_issuer: str = field(
        default_factory=lambda: os.getenv("JWT_ISSUER", "accesspdf-dashboard")
    )
    jwt_audience: str = field(
        default_factory=lambda: os.getenv("JWT_AUDIENCE", "accesspdf-api")
    )

    # Environment
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "dev")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        logger.info(f"Initializing WorkerConfig for environment: {self.environment}")

        # Log bucket configuration (without sensitive details)
        logger.debug(f"S3 buckets configured: "
                    f"originals={'set' if self.pdf_originals_bucket else 'unset'}, "
                    f"derivatives={'set' if self.pdf_derivatives_bucket else 'unset'}, "
                    f"accessible={'set' if self.pdf_accessible_bucket else 'unset'}")

    def get_s3_key_prefix(self, doc_id: str, key_type: str) -> str:
        """Generate standardized S3 key prefixes."""
        prefixes = {
            "textract": f"pdf-derivatives/{doc_id}/textract/",
            "structure": f"pdf-derivatives/{doc_id}/structure/",
            "alt_text": f"pdf-derivatives/{doc_id}/alt-text/",
            "tagged_pdf": f"pdf-accessible/{doc_id}/",
            "exports": f"pdf-accessible/{doc_id}/exports/",
            "temp": f"temp/{doc_id}/"
        }

        if key_type not in prefixes:
            raise ValueError(f"Unknown key type: {key_type}")

        return prefixes[key_type]

    def get_bucket_for_key_type(self, key_type: str) -> str | None:
        """Get the appropriate bucket for a given key type."""
        bucket_mapping = {
            "originals": self.pdf_originals_bucket,
            "textract": self.pdf_derivatives_bucket,
            "structure": self.pdf_derivatives_bucket,
            "alt_text": self.pdf_derivatives_bucket,
            "tagged_pdf": self.pdf_accessible_bucket,
            "exports": self.pdf_accessible_bucket,
            "temp": self.pdf_temp_bucket
        }

        return bucket_mapping.get(key_type)


# Global configuration instance
config = WorkerConfig()

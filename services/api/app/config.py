from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    api_title: str = "PDF Accessibility Platform API"
    api_version: str = "1.0.0"
    api_description: str = "API for PDF accessibility processing platform"
    debug: bool = Field(False, env="DEBUG")

    # AWS Configuration
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    aws_account_id: Optional[str] = Field(None, env="AWS_ACCOUNT_ID")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_endpoint_url: Optional[str] = Field(None, env="AWS_ENDPOINT_URL")
    s3_bucket: str = Field("pdf-accessibility-dev-pdf-originals", env="S3_BUCKET")
    s3_bucket_name: str = Field(
        "pdf-accessibility-dev-pdf-originals", env="S3_BUCKET_NAME"
    )
    app_env: str = Field("development", env="APP_ENV")

    # DynamoDB Tables
    documents_table: str = Field(
        "pdf-accessibility-dev-documents", env="DOCUMENTS_TABLE"
    )
    jobs_table: str = Field("pdf-accessibility-dev-jobs", env="JOBS_TABLE")
    user_sessions_table: str = Field(
        "pdf-accessibility-dev-user-sessions", env="USER_SESSIONS_TABLE"
    )

    # S3 Buckets
    pdf_originals_bucket: str = Field(
        "pdf-accessibility-dev-pdf-originals", env="PDF_ORIGINALS_BUCKET"
    )
    pdf_derivatives_bucket: str = Field(
        "pdf-accessibility-dev-pdf-derivatives", env="PDF_DERIVATIVES_BUCKET"
    )
    pdf_temp_bucket: str = Field(
        "pdf-accessibility-dev-pdf-temp", env="PDF_TEMP_BUCKET"
    )
    pdf_reports_bucket: str = Field(
        "pdf-accessibility-dev-pdf-reports", env="PDF_REPORTS_BUCKET"
    )

    # SQS Queues
    ingest_queue_url: str = Field("", env="INGEST_QUEUE_URL")
    process_queue_url: str = Field("", env="PROCESS_QUEUE_URL")
    callback_queue_url: str = Field("", env="CALLBACK_QUEUE_URL")
    priority_process_queue_url: str = Field("", env="PRIORITY_PROCESS_QUEUE_URL")

    # BetterAuth Configuration
    better_auth_dashboard_url: str = Field(
        "http://host.docker.internal:3001", env="BETTER_AUTH_DASHBOARD_URL"
    )

    # Security
    webhook_secret_key: str = Field("", env="WEBHOOK_SECRET_KEY")
    cors_origins: Optional[list[str]] = Field(None, env="CORS_ORIGINS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        # If not set, use defaults
        if v is None:
            return [
                "http://localhost:3000",
                "https://localhost:3000",
                "http://localhost:3001",
                "https://localhost:3001",
            ]
        # If it's a string from environment, split it
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("aws_access_key_id", "aws_secret_access_key", mode="after")
    @classmethod
    def validate_aws_credentials(cls, v, info):
        """Validate AWS credentials are set in non-development environments"""
        import os

        if v is None:
            # Check app_env from environment directly since we're in validation
            if os.getenv("APP_ENV", "development") != "development":
                raise ValueError(
                    f"{info.field_name} is required in non-development environments"
                )
        return v

    @field_validator("api_jwt_secret", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret is secure in non-development environments"""
        import os

        app_env = os.getenv("APP_ENV", "development")

        if app_env != "development":
            if v is None:
                raise ValueError(
                    "API_JWT_SECRET is required in non-development environments"
                )

            # Reject obvious placeholder values (exact patterns that indicate development values)
            insecure_patterns = [
                "change-in-production",
                "your-secret-key",
                "changeme",
                "secret-key-here",
                "replace-this",
                "placeholder",
            ]
            if any(pattern in v.lower() for pattern in insecure_patterns):
                raise ValueError("API_JWT_SECRET contains insecure placeholder value")

            # Require minimum length
            if len(v) < 32:
                raise ValueError(
                    "API_JWT_SECRET must be at least 32 characters in production"
                )

        return v

    @field_validator("aws_endpoint_url", mode="after")
    @classmethod
    def validate_endpoint_url(cls, v):
        """Validate endpoint URL is not LocalStack in non-development environments"""
        import os

        app_env = os.getenv("APP_ENV", "development")

        if v is not None and app_env != "development":
            if "localhost" in v or "localstack" in v:
                raise ValueError(
                    "LocalStack/localhost endpoint not allowed in non-development environments"
                )
        return v

    @field_validator("allowed_file_types", mode="before")
    @classmethod
    def parse_allowed_file_types(cls, v):
        # If not set, use defaults
        if v is None:
            return [".pdf", ".doc", ".docx", ".txt"]
        # If it's a string from environment, split it
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v

    # Virus Scanning Configuration
    enable_virus_scanning: bool = Field(True, env="ENABLE_VIRUS_SCANNING")
    clamav_host: str = Field("localhost", env="CLAMAV_HOST")
    clamav_port: int = Field(3310, env="CLAMAV_PORT")
    clamav_timeout: int = Field(30, env="CLAMAV_TIMEOUT")  # seconds

    # Processing Security Configuration
    max_processing_time: int = Field(300, env="MAX_PROCESSING_TIME")  # 5 minutes
    enable_processing_isolation: bool = Field(True, env="ENABLE_PROCESSING_ISOLATION")
    enable_security_audit_logging: bool = Field(
        True, env="ENABLE_SECURITY_AUDIT_LOGGING"
    )

    # File Upload Configuration
    max_file_size: int = Field(100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_file_types: Optional[list[str]] = None

    # Rate Limiting
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(1000, env="RATE_LIMIT_PER_HOUR")
    disable_rate_limiting: bool = Field(False, env="DISABLE_RATE_LIMITING")

    # Pre-signed URL Configuration
    presigned_url_expiration: int = Field(
        3600, env="PRESIGNED_URL_EXPIRATION"
    )  # 1 hour
    max_presigned_url_expiration: int = Field(
        86400, env="MAX_PRESIGNED_URL_EXPIRATION"
    )  # 24 hours

    # Pagination
    default_page_size: int = Field(10, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(100, env="MAX_PAGE_SIZE")

    # Monitoring and Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    powertools_service_name: str = Field(
        "pdf-accessibility-api", env="POWERTOOLS_SERVICE_NAME"
    )
    powertools_metrics_namespace: str = Field(
        "PDF-Accessibility", env="POWERTOOLS_METRICS_NAMESPACE"
    )

    # BetterAuth JWT Configuration
    api_jwt_secret: Optional[str] = Field(None, env="API_JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_issuer: str = Field("accesspdf-dashboard", env="JWT_ISSUER")
    jwt_audience: str = Field("accesspdf-api", env="JWT_AUDIENCE")

    # Environment
    environment: str = Field("dev", env="ENVIRONMENT")
    stage: str = Field("dev", env="STAGE")

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    def get_table_name(self, table_type: str) -> str:
        """Get full table name with environment prefix"""
        table_map = {
            "documents": self.documents_table,
            "jobs": self.jobs_table,
            "user_sessions": self.user_sessions_table,
        }
        return table_map.get(table_type, "")

    def get_bucket_name(self, bucket_type: str) -> str:
        """Get full bucket name"""
        bucket_map = {
            "originals": self.pdf_originals_bucket,
            "derivatives": self.pdf_derivatives_bucket,
            "temp": self.pdf_temp_bucket,
            "reports": self.pdf_reports_bucket,
        }
        return bucket_map.get(bucket_type, "")


# Global settings instance
settings = Settings()

from typing import Optional

from pydantic import ConfigDict, Field
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

    # DynamoDB Tables
    documents_table: str = Field("pdf-accessibility-dev-documents", env="DOCUMENTS_TABLE")
    jobs_table: str = Field("pdf-accessibility-dev-jobs", env="JOBS_TABLE")
    user_sessions_table: str = Field("pdf-accessibility-dev-user-sessions", env="USER_SESSIONS_TABLE")

    # S3 Buckets
    pdf_originals_bucket: str = Field("pdf-accessibility-dev-pdf-originals", env="PDF_ORIGINALS_BUCKET")
    pdf_derivatives_bucket: str = Field("pdf-accessibility-dev-pdf-derivatives", env="PDF_DERIVATIVES_BUCKET")
    pdf_temp_bucket: str = Field("pdf-accessibility-dev-pdf-temp", env="PDF_TEMP_BUCKET")
    pdf_reports_bucket: str = Field("pdf-accessibility-dev-pdf-reports", env="PDF_REPORTS_BUCKET")

    # SQS Queues
    ingest_queue_url: str = Field("", env="INGEST_QUEUE_URL")
    process_queue_url: str = Field("", env="PROCESS_QUEUE_URL")
    callback_queue_url: str = Field("", env="CALLBACK_QUEUE_URL")
    priority_process_queue_url: str = Field("", env="PRIORITY_PROCESS_QUEUE_URL")

    # BetterAuth Configuration
    better_auth_secret: str = Field("", env="API_JWT_SECRET")
    better_auth_dashboard_url: str = Field("http://localhost:3001", env="BETTER_AUTH_DASHBOARD_URL")

    # JWT Configuration
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_issuer: str = Field("accesspdf-dashboard", env="JWT_ISSUER") 
    jwt_audience: str = Field("accesspdf-api", env="JWT_AUDIENCE")

    # Security
    webhook_secret_key: str = Field("", env="WEBHOOK_SECRET_KEY")
    cors_origins: list[str] = Field(
        ["http://localhost:3000", "https://localhost:3000"],
        env="CORS_ORIGINS"
    )

    # File Upload Configuration
    max_file_size: int = Field(100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_file_types: list[str] = Field(
        [".pdf", ".doc", ".docx", ".txt"],
        env="ALLOWED_FILE_TYPES"
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(1000, env="RATE_LIMIT_PER_HOUR")

    # Pre-signed URL Configuration
    presigned_url_expiration: int = Field(3600, env="PRESIGNED_URL_EXPIRATION")  # 1 hour
    max_presigned_url_expiration: int = Field(86400, env="MAX_PRESIGNED_URL_EXPIRATION")  # 24 hours

    # Pagination
    default_page_size: int = Field(10, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(100, env="MAX_PAGE_SIZE")

    # Monitoring and Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    powertools_service_name: str = Field("pdf-accessibility-api", env="POWERTOOLS_SERVICE_NAME")
    powertools_metrics_namespace: str = Field("PDF-Accessibility", env="POWERTOOLS_METRICS_NAMESPACE")

    # Environment
    environment: str = Field("dev", env="ENVIRONMENT")
    stage: str = Field("dev", env="STAGE")

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )


    def get_table_name(self, table_type: str) -> str:
        """Get full table name with environment prefix"""
        table_map = {
            "documents": self.documents_table,
            "jobs": self.jobs_table,
            "user_sessions": self.user_sessions_table
        }
        return table_map.get(table_type, "")

    def get_bucket_name(self, bucket_type: str) -> str:
        """Get full bucket name"""
        bucket_map = {
            "originals": self.pdf_originals_bucket,
            "derivatives": self.pdf_derivatives_bucket,
            "temp": self.pdf_temp_bucket,
            "reports": self.pdf_reports_bucket
        }
        return bucket_map.get(bucket_type, "")


# Global settings instance
settings = Settings()

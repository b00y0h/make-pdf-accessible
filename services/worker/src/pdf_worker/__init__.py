"""PDF Accessibility Worker Package.

Shared utilities for PDF accessibility processing pipeline.
"""

from pdf_worker.core.config import WorkerConfig
from pdf_worker.core.exceptions import WorkerError, WorkerConfigError
from pdf_worker.aws.s3 import S3Client
from pdf_worker.aws.dynamodb import DynamoDBRepository
from pdf_worker.aws.sqs import SQSClient
from pdf_worker.aws.textract import TextractClient
from pdf_worker.aws.bedrock import BedrockClient
from pdf_worker.decorators.idempotency import idempotent
from pdf_worker.utils.pdf import PDFUtils
from pdf_worker.models.document import DocumentStructure, DocumentElement

__version__ = "1.0.0"
__author__ = "PDF Accessibility Team"

__all__ = [
    "WorkerConfig",
    "WorkerError",
    "WorkerConfigError",
    "S3Client",
    "DynamoDBRepository", 
    "SQSClient",
    "TextractClient",
    "BedrockClient",
    "idempotent",
    "PDFUtils",
    "DocumentStructure",
    "DocumentElement",
]
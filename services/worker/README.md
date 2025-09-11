# PDF Accessibility Worker Package

A comprehensive Python package providing shared utilities for PDF accessibility processing pipelines. This package eliminates code duplication across Lambda functions and provides a consistent, type-safe API for AWS services integration.

## Features

### 🔧 Core Utilities

- **Configuration Management**: Centralized environment-based configuration
- **Error Handling**: Comprehensive custom exceptions with context
- **Type Safety**: Full type hints and mypy compliance

### ☁️ AWS Service Integrations

- **S3 Client**: Enhanced S3 operations with metadata, tagging, and error handling
- **DynamoDB Repository**: Generic repository pattern with CRUD operations
- **SQS Client**: Message handling with batch processing and error recovery
- **Textract Client**: Async job management with polling and result processing
- **Bedrock Client**: Claude 3.5 integration with structured responses

### 🔄 Processing Utilities

- **PDF Utils**: Content analysis, text extraction, and layout detection
- **Idempotency**: Decorator-based idempotency with DynamoDB backing
- **Document Models**: Comprehensive Pydantic models for document structure
- **HTML Rendering**: Accessible HTML generation with WCAG compliance

### 🧪 Quality Assurance

- **Comprehensive Tests**: 90%+ test coverage with unit and integration tests
- **Type Checking**: Strict mypy configuration for type safety
- **JSON Schemas**: Validation schemas for data interchange
- **Documentation**: Extensive docstrings and examples

## Installation

### Development Installation

```bash
cd services/worker
pip install -e ".[dev]"
```

### Production Installation

```bash
pip install pdf-accessibility-worker
```

## Quick Start

### Basic S3 Operations

```python
from pdf_worker import S3Client

# Initialize client
s3 = S3Client()

# Upload JSON data
data = {"doc_id": "123", "status": "processed"}
s3_uri = s3.upload_json(
    data=data,
    bucket="my-bucket",
    key="documents/doc-123.json",
    tags={"type": "document", "env": "prod"}
)

# Download and parse JSON
downloaded_data = s3.download_json("my-bucket", "documents/doc-123.json")
```

### DynamoDB Operations

```python
from pdf_worker import DocumentRepository

# Initialize repository
repo = DocumentRepository()

# Create document record
doc_data = {
    "docId": "doc-123",
    "status": "processing",
    "title": "Sample Document"
}
created_doc = repo.create_document(doc_data)

# Update document status
updated_doc = repo.update_document_status(
    doc_id="doc-123",
    status="completed",
    additional_data={"processed_at": "2024-01-15T10:30:00Z"}
)
```

### Idempotency Pattern

```python
from pdf_worker import idempotent_by_doc_id

@idempotent_by_doc_id(expires_after_seconds=3600)
def process_document(event, context):
    doc_id = event["docId"]
    # Processing logic here
    return {"status": "completed", "docId": doc_id}
```

### Document Structure Analysis

```python
from pdf_worker import BedrockClient, PDFUtils

# Analyze PDF content
pdf_data = b"..."  # PDF file bytes
is_image_based, page_count, metadata = PDFUtils.analyze_pdf_content_type(pdf_data)

# Extract text by pages
text_by_page = PDFUtils.extract_text_by_pages(pdf_data)

# Analyze structure with Bedrock
bedrock = BedrockClient()
response = bedrock.analyze_document_structure(
    document_text="\n".join(text_by_page.values()),
    custom_instructions="Focus on headings and tables"
)

# Parse structured response
if response.try_parse_json():
    structure_data = response.try_parse_json()
```

### HTML Rendering

```python
from pdf_worker.templates import AccessibleHTMLRenderer
from pdf_worker.models.document import DocumentStructure

# Create renderer
renderer = AccessibleHTMLRenderer()

# Render document to accessible HTML
html_output = renderer.render_document(
    document=document_structure,
    include_styles=True,
    include_skip_links=True
)
```

## Configuration

The package uses environment variables for configuration:

```bash
# AWS Configuration
AWS_REGION=us-east-1

# S3 Buckets
PDF_ORIGINALS_BUCKET=my-originals-bucket
PDF_DERIVATIVES_BUCKET=my-derivatives-bucket
PDF_ACCESSIBLE_BUCKET=my-accessible-bucket

# DynamoDB Tables
DOCUMENTS_TABLE=pdf-documents
JOBS_TABLE=pdf-jobs

# SQS Queues
PROCESS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123/process-queue

# Processing Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
TEXTRACT_JOB_TIMEOUT_SECONDS=600

# Environment
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

## Architecture

```
pdf_worker/
├── core/                   # Core utilities
│   ├── config.py          # Configuration management
│   └── exceptions.py      # Custom exceptions
├── aws/                   # AWS service clients
│   ├── s3.py             # Enhanced S3 client
│   ├── dynamodb.py       # Repository pattern
│   ├── sqs.py            # Message handling
│   ├── textract.py       # OCR integration
│   └── bedrock.py        # AI/ML integration
├── models/               # Data models
│   └── document.py       # Document structure
├── utils/                # Processing utilities
│   └── pdf.py           # PDF analysis
├── decorators/           # Decorators
│   └── idempotency.py   # Idempotency handling
├── templates/            # Rendering
│   └── accessible_html.py # HTML generation
└── schemas/              # JSON schemas
    └── document_schema.py # Validation schemas
```

## Data Models

### Document Structure

The package provides comprehensive Pydantic models for document structure:

```python
# Document elements
document = DocumentStructure(
    doc_id="doc-123",
    title="Sample Document",
    total_pages=5,
    elements=[
        Heading(
            page_number=1,
            text="Introduction",
            level=HeadingLevel.H1,
            confidence=0.95
        ),
        Paragraph(
            page_number=1,
            text="This document demonstrates...",
            confidence=0.88
        ),
        TableElement(
            page_number=2,
            rows=3,
            columns=4,
            caption="Sales Data",
            has_header=True
        ),
        Figure(
            page_number=3,
            figure_type=FigureType.CHART,
            alt_text="Bar chart showing quarterly results",
            caption="Q1-Q4 Performance"
        )
    ]
)
```

### Error Handling

All operations use typed exceptions for better error handling:

```python
from pdf_worker.core.exceptions import S3Error, BedrockError

try:
    s3.upload_json(data, "bucket", "key")
except S3Error as e:
    logger.error(f"S3 operation failed: {e.error_code} - {e.message}")
    # Access structured error details
    error_details = e.to_dict()
```

## Testing

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=pdf_worker --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Exclude slow tests

# Type checking
mypy src/pdf_worker

# Linting
ruff check src/pdf_worker
black --check src/pdf_worker
```

### Test Categories

- **Unit Tests**: Test individual components with mocked dependencies
- **Integration Tests**: Test AWS service integrations (require credentials)
- **Model Tests**: Validate Pydantic models and serialization
- **Schema Tests**: Validate JSON schemas

### Example Test

```python
def test_s3_upload_json(s3_client, mock_s3_setup):
    """Test JSON upload with metadata."""
    data = {"key": "value", "count": 42}
    result = s3_client.upload_json(
        data=data,
        bucket="test-bucket",
        key="test.json",
        metadata={"version": "1.0"}
    )

    assert result.startswith("s3://")

    # Verify round-trip
    downloaded = s3_client.download_json("test-bucket", "test.json")
    assert downloaded == data
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/pdf-accessibility-worker
cd services/worker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install in development mode
pip install -e ".[dev,docs]"

# Setup pre-commit hooks
pre-commit install
```

### Code Quality

```bash
# Format code
black src/pdf_worker tests/
ruff check src/pdf_worker tests/ --fix

# Type checking
mypy src/pdf_worker

# Run all quality checks
pre-commit run --all-files
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build documentation
mkdocs build

# Serve locally
mkdocs serve
```

## Lambda Function Integration

### Using in Lambda Functions

1. **Add to requirements.txt**:

```
pdf-accessibility-worker>=1.0.0
```

2. **Update Lambda function**:

```python
from pdf_worker import S3Client, DocumentRepository, idempotent_by_doc_id
from aws_lambda_powertools import Logger

logger = Logger()

@idempotent_by_doc_id()
def lambda_handler(event, context):
    s3 = S3Client()
    repo = DocumentRepository()

    # Your processing logic here
    return {"status": "completed"}
```

3. **Environment Variables**: Set required environment variables in Lambda configuration

4. **IAM Permissions**: Ensure Lambda execution role has required permissions

### Docker Deployment

```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install dependencies including worker package
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY *.py ${LAMBDA_TASK_ROOT}/

CMD ["main.lambda_handler"]
```

## Performance Considerations

### Memory Usage

- S3Client: Streams large files to minimize memory usage
- DynamoDB: Uses batch operations for bulk operations
- PDF processing: Processes pages incrementally

### Cost Optimization

- Bedrock: Token usage tracking and estimation
- Textract: Optimal polling intervals to reduce API calls
- S3: Lifecycle policies for temporary files

### Monitoring

The package integrates with AWS Lambda Powertools for:

- **Structured Logging**: Correlation IDs and request tracking
- **Metrics**: Custom metrics for monitoring
- **Tracing**: X-Ray integration for performance analysis

```python
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger(service="pdf-processing")
tracer = Tracer(service="pdf-processing")
metrics = Metrics(namespace="PDF-Accessibility")

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event, context):
    # Your code here
    pass
```

## Contributing

### Guidelines

1. **Type Hints**: All public APIs must have type hints
2. **Tests**: New features require tests (aim for >90% coverage)
3. **Documentation**: Update docstrings and README for new features
4. **Error Handling**: Use appropriate custom exceptions
5. **Backward Compatibility**: Follow semantic versioning

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run quality checks: `pre-commit run --all-files`
4. Update documentation if needed
5. Submit pull request with clear description

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: [Internal docs](https://docs.example.com/pdf-worker)
- **Issues**: Use GitHub issues for bug reports
- **Slack**: #pdf-accessibility channel for questions

# PDF Accessibility Processing Pipeline

## Overview

Complete end-to-end PDF accessibility processing pipeline using AWS Step Functions and Lambda functions. Transforms PDFs into fully accessible documents with proper tagging, alternative text, and multiple export formats.

## Architecture

### Step Functions Workflow
```
Upload PDF → Router → Step Functions → Accessible Outputs
```

### Processing Steps
1. **OCR** - AWS Textract for image-based PDFs
2. **STRUCTURE** - Bedrock Claude for document structure analysis  
3. **ALT TEXT** - Bedrock Vision + Rekognition for figure descriptions
4. **TAG PDF** - pikepdf for accessibility tagging
5. **EXPORTS** - HTML, EPUB, CSV generation
6. **VALIDATE** - PDF/UA and WCAG compliance checks
7. **NOTIFY** - Status updates and webhooks

## Files Created

### Step Functions
- `infra/step-functions/pdf-processing-workflow.json` - Complete ASL workflow definition
- `infra/terraform/step-functions.tf` - Step Functions infrastructure

### Lambda Functions

#### OCR Function
- `services/functions/ocr/main.py` - Textract integration with polling
- `services/functions/ocr/models.py` - OCR data models
- `services/functions/ocr/services.py` - Textract service wrapper
- `services/functions/ocr/requirements.txt` - Dependencies
- `services/functions/ocr/Dockerfile` - Container configuration

#### Structure Function  
- `services/functions/structure/main.py` - Bedrock Claude integration
- `services/functions/structure/models.py` - Document structure models
- `services/functions/structure/services.py` - PDF analysis + Bedrock service
- `services/functions/structure/requirements.txt` - Dependencies including pdfminer.six
- `services/functions/structure/Dockerfile` - Container configuration

#### Processing Functions (Alt Text, Tag PDF, Exports, Validate, Notify)
- `services/functions/{function}/main.py` - Lambda handlers with error handling
- All functions include proper AWS Powertools integration
- Clear input/output contracts using Pydantic models

### Infrastructure
- `infra/terraform/processing-lambdas.tf` - All Lambda functions infrastructure
- `infra/terraform/step-functions.tf` - Step Functions state machine
- Complete IAM roles and policies
- CloudWatch monitoring and alarms
- ECR repositories for container deployment

### Testing
- `tests/test_pipeline_integration.py` - Comprehensive integration tests
- `tests/fixtures/sample_document_structure.json` - Sample data for testing
- `services/shared/models.py` - Shared data models across functions

## Key Features Implemented

### ✅ Complete Pipeline
- Step Functions orchestrates 7 Lambda functions
- Error handling with DLQ and retry policies
- Proper timeouts and resource allocation

### ✅ OCR Processing
- Detects image-based vs text-based PDFs
- Async Textract integration with polling
- Saves raw OCR data to S3

### ✅ Structure Analysis
- Combines PDFMiner text extraction + Textract data
- Bedrock Claude 3.5 for semantic structure analysis
- Identifies headings, lists, tables, figures with confidence scores

### ✅ Accessibility Features
- Alt text generation for figures using Bedrock Vision
- PDF tagging with proper heading hierarchy
- Reading order preservation
- HTML/EPUB exports with ARIA landmarks
- CSV table extraction

### ✅ Validation & Compliance
- PDF/UA compliance checking
- WCAG 2.1 AA validation
- Accessibility scoring with detailed issues report

### ✅ Infrastructure as Code
- Complete Terraform configuration
- ECR repositories for container deployment
- CloudWatch monitoring and alerting
- Proper IAM permissions with least privilege

## Input/Output Contracts

### Step Functions Input
```json
{
  "docId": "test-doc-123",
  "s3Key": "pdfs/document.pdf", 
  "userId": "user-456",
  "priority": false
}
```

### Final Output
```json
{
  "doc_id": "test-doc-123",
  "status": "completed",
  "results": {
    "taggedPdfS3Key": "pdf-accessible/test-doc-123/document_tagged.pdf",
    "htmlS3Key": "pdf-accessible/test-doc-123/exports/document.html",
    "epubS3Key": "pdf-accessible/test-doc-123/exports/document.epub", 
    "csvZipS3Key": "pdf-accessible/test-doc-123/exports/tables.zip",
    "validationScore": 92.5,
    "validationIssues": [...]
  }
}
```

## S3 Structure
```
pdf-originals/{docId}/          # Original PDFs
pdf-derivatives/{docId}/        # Processing artifacts
├── textract/raw_output.json   # OCR results
├── structure/document.json    # Document structure
└── alt-text/alt.json         # Figure descriptions

pdf-accessible/{docId}/         # Final outputs  
├── document_tagged.pdf        # Tagged PDF
└── exports/                   # Alternative formats
    ├── document.html
    ├── document.epub
    └── tables.zip
```

## Deployment

### 1. Infrastructure
```bash
cd infra/terraform
terraform init
terraform plan -var="github_repo=owner/repo"
terraform apply
```

### 2. Build and Deploy Functions
```bash
# Build all container images
for service in ocr structure alt_text tag_pdf exports validate notify; do
  cd services/functions/$service
  docker build -t pdf-accessibility-dev-$service .
  # Push to ECR (automated in CI/CD)
done
```

### 3. Update Step Functions Definition
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:region:account:stateMachine:pdf-accessibility-dev-pdf-processing \
  --definition file://infra/step-functions/pdf-processing-workflow.json
```

## Usage

### Trigger Processing
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:region:account:stateMachine:pdf-processing \
  --input '{
    "docId": "doc-123",
    "s3Key": "pdfs/document.pdf",
    "userId": "user-456", 
    "priority": false
  }'
```

### Monitor Progress
- CloudWatch dashboards for metrics
- X-Ray distributed tracing
- Step Functions execution logs

## Testing

```bash
# Run integration tests
cd tests
python -m pytest test_pipeline_integration.py -v

# Test individual functions
cd services/functions/ocr
python -m pytest tests/ -v
```

## Error Handling

- Each step has retry policies (2-3 attempts)
- Failed executions trigger notification Lambda
- Dead letter queues for unrecoverable errors
- Detailed error logging with correlation IDs

## Monitoring & Observability

- Step Functions execution metrics
- Lambda function performance monitoring
- Custom CloudWatch dashboards
- SNS alerts for failures
- X-Ray distributed tracing

## Security

- Least privilege IAM roles
- VPC configuration support
- KMS encryption for logs and S3
- Container image vulnerability scanning

## Cost Optimization

- Right-sized Lambda memory allocation
- ECR lifecycle policies
- CloudWatch log retention policies
- Efficient S3 storage classes

This implementation provides a complete, production-ready PDF accessibility processing pipeline with proper error handling, monitoring, and infrastructure as code.
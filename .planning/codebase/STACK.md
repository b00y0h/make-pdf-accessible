# Technology Stack

## Programming Languages

- **Python**: 3.9+ (tested on 3.9, 3.10, 3.11) - Backend services
- **TypeScript**: 5.2.2-5.3.3 - Frontend applications
- **PHP**: WordPress plugin integration

## Backend Frameworks

- **FastAPI**: 0.100+ - HTTP API framework for all microservices
- **Uvicorn**: 0.23+ - ASGI server with hot reload support
- **Celery**: 5.3+ - Distributed task queue for async processing
- **SQLAlchemy**: 2.0+ - ORM for PostgreSQL
- **Pydantic**: Data validation and settings management

## Frontend Frameworks

- **Next.js**: 13.4.19 (web), 15.5.7 (dashboard)
- **React**: 18.2.0
- **TailwindCSS**: Utility-first CSS framework
- **Radix UI**: Component primitives
- **TanStack Query**: Server state management

## Databases

- **PostgreSQL**: 15 - Primary application data, BetterAuth
- **MongoDB**: 7.0 - Document storage and job tracking
- **Redis**: 7 - Caching, message queue, Celery broker

## PDF Processing Libraries

- **PyPDF2**: 3.0+ - PDF manipulation
- **pikepdf**: 8.0+ - Advanced PDF operations
- **pdfplumber**: 0.10+ - PDF text extraction
- **PyMuPDF**: 1.23+ - PDF rendering
- **pdf2image**: 1.16+ - PDF to image conversion
- **Pillow**: 10.0+ - Image processing

## AWS Services (LocalStack in dev)

- **S3**: File storage (uploads, processed, reports buckets)
- **SQS**: Async job queues
- **SNS**: Notifications
- **Secrets Manager**: Credential storage
- **Step Functions**: Workflow orchestration
- **API Gateway v2**: REST endpoints (production)
- **Cognito**: User authentication (production)
- **CloudFront**: CDN for web assets

## Security

- **python-jose**: JWT token handling (HS256)
- **BetterAuth**: 1.3.9 - Authentication framework
- **ClamAV**: Virus scanning (docker-clamav alpine)

## Build & Package Tools

- **Docker**: Container runtime
- **docker-compose**: Multi-container orchestration
- **pnpm**: 8.15.0 - JavaScript package manager
- **pip/uv**: Python package management
- **Terraform**: Infrastructure as Code

## Code Quality Tools

- **Black**: Python formatter (88-char lines)
- **Ruff**: Fast Python linter
- **MyPy**: Static type checker (strict mode)
- **ESLint**: TypeScript linter
- **Prettier**: Code formatter

## Testing Frameworks

- **pytest**: 7.4.0+ - Python testing
- **pytest-asyncio**: 0.21.0+ - Async test support
- **pytest-cov**: 4.1.0+ - Coverage reporting
- **Jest**: JavaScript testing
- **Vitest**: Frontend unit testing
- **Playwright**: E2E testing

## Development Tools

- **Makefile**: Task automation
- **Pre-commit**: Git hooks for code quality
- **Node.js**: 18.0+ required

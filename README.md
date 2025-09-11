# Make PDF Accessible - Monorepo

A comprehensive monorepo for PDF accessibility tools and services, providing microservices architecture for processing, analyzing, and making PDF documents accessible.

## 📊 Project Status

**Current Version:** 2.0.0  
**Overall Completion:** 95% Enterprise-Ready Platform Complete  
**Last Updated:** 2025-09-11

### ✅ What's Working (Major Updates)

- **🚀 Full UI Applications**: Both web app (3000) and dashboard (3001) fully operational
- **🤖 AI-Enhanced Processing**: Bedrock integration with confidence scoring and A2I review routing
- **🔍 LLM Integration**: Public embeddings API for ChatGPT, Claude, Gemini access
- **📊 RAG Capabilities**: Semantic search, Q&A generation, citation tracking
- **🔐 Security**: Enhanced authentication, comprehensive validation, virus scanning ready
- **🗑️ Document Management**: Two-stage deletion with complete artifact cleanup
- **📈 Monitoring**: CloudWatch dashboards, alarms, comprehensive metrics
- **🔧 Client Integration**: WordPress plugin and CDN script for easy website integration
- **♿ Accessibility**: PDF/UA compliance, WCAG 2.1 AA validation, semantic exports

### 🎯 New Enterprise Features (v2.0)

- **Semantic HTML Builder**: WCAG-compliant exports using canonical schema
- **Vector Embeddings**: Titan embeddings with similarity search
- **AI Learning System**: Feedback loops for continuous improvement
- **Public Discovery API**: Zero-auth LLM access with rate limiting
- **Client Registration**: Domain-based auth for secure integrations

📋 **For detailed status, see:** [STATUS.md](STATUS.md)  
🔍 **For gap analysis, see:** [docs/gap-report.md](docs/gap-report.md)  
🛣️ **For implementation roadmap, see:** [docs/implementation-plan.md](docs/implementation-plan.md)

## 📁 Repository Structure

```
.
├── infra/
│   └── terraform/           # Infrastructure as Code (Terraform)
├── services/
│   ├── api/                 # Main API gateway service
│   ├── worker/              # Background job processing
│   └── functions/           # Microservices for specific tasks
│       ├── router/          # Request routing and load balancing
│       ├── ocr/             # Optical Character Recognition
│       ├── structure/       # Document structure analysis
│       ├── tagger/          # Content tagging and categorization
│       ├── exporter/        # Export to various formats
│       ├── validator/       # Accessibility validation
│       └── notifier/        # Notification service
├── web/                     # Frontend web application
├── integrations/            # Third-party integrations
│   ├── wordpress/           # WordPress plugin
│   └── lti/                # Learning Tools Interoperability
├── packages/
│   └── schemas/            # Shared data schemas and types
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
└── docs/                   # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- pnpm 8+
- Python 3.9+
- Make

### Local Development Setup

1. **Clone and initialize the repository:**

   ```bash
   git clone <repository-url>
   cd make-pdf-accessible
   make init
   ```

2. **Start the development environment:**

   ```bash
   make dev
   ```

3. **Access the services:**
   - Web Application: http://localhost:3000
   - API Gateway: http://localhost:8000
   - Function Services: http://localhost:8001-8007

## 🏗️ Architecture Overview

### Core Services

- **API Service** (`services/api/`): Main API gateway handling authentication, request routing, and business logic
- **Worker Service** (`services/worker/`): Background job processor using Celery for heavy tasks
- **Web Application** (`web/`): Next.js frontend providing user interface

### Microservices Functions

- **Router** (`services/functions/router/`): Intelligent request routing and load balancing
- **OCR** (`services/functions/ocr/`): Text extraction from PDF images and scanned documents
- **Structure** (`services/functions/structure/`): Document structure analysis and semantic understanding
- **Tagger** (`services/functions/tagger/`): Content classification and metadata tagging
- **Exporter** (`services/functions/exporter/`): Export to accessible formats (HTML, EPUB, etc.)
- **Validator** (`services/functions/validator/`): WCAG compliance and accessibility validation
- **Notifier** (`services/functions/notifier/`): Email, webhook, and push notification service

### Infrastructure

- **Terraform** (`infra/terraform/`): Cloud infrastructure provisioning and management
- **Docker Compose**: Local development environment orchestration
- **GitHub Actions** (`.github/workflows/`): CI/CD pipelines

### Integrations

- **WordPress Plugin** (`integrations/wordpress/`): WordPress integration for CMS users
- **LTI Integration** (`integrations/lti/`): Learning Management System integration

## 🛠️ Development Commands

### Make Targets

```bash
make help        # Show available commands
make init        # Initialize development environment
make dev         # Start development environment
make test        # Run all tests
make build       # Build all services
make deploy      # Deploy to production
make lint        # Run linters
make format      # Format code
make clean       # Clean build artifacts
```

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Rebuild specific service
docker-compose build [service-name]

# Stop all services
docker-compose down
```

### Testing

```bash
# Run all tests
make test

# Run tests for specific service
docker-compose run --rm api pytest
docker-compose run --rm worker pytest

# Run frontend tests
pnpm --filter web test
```

## 🔧 Configuration

### Environment Variables

Create `.env` files in each service directory with the following variables:

```env
# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/app_db

# Redis
REDIS_URL=redis://redis:6379

# API Configuration
API_SECRET_KEY=your-secret-key
API_DEBUG=true

# External Services
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

### Service Configuration

Each service has its own configuration files:

- Python services: `config/settings.py`
- Node.js services: `config/index.js`
- Docker services: `Dockerfile` and `docker-compose.yml`

## 📦 Package Management

### Python Dependencies

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Update dependencies
pip-tools compile requirements.in
```

### Node.js Dependencies

```bash
# Install dependencies for all workspaces
pnpm install

# Add dependency to specific workspace
pnpm add package-name --filter web
```

## 🧪 Testing Strategy

### Unit Tests

- **Python**: pytest with coverage reporting
- **TypeScript/JavaScript**: Jest with React Testing Library

### Integration Tests

- API endpoint testing with FastAPI TestClient
- Database integration tests with test containers

### End-to-End Tests

- Playwright for web application testing
- Service-to-service communication testing

## 🚀 Deployment

### Local Development

```bash
make dev
```

### Staging/Production

```bash
# Build production images
make build

# Deploy with Terraform
make deploy
```

### CI/CD Pipeline

GitHub Actions workflows handle:

- Code quality checks (linting, formatting)
- Security scanning
- Automated testing
- Docker image building
- Deployment to staging/production

## 🔒 Security

- Pre-commit hooks enforce code quality
- Dependency vulnerability scanning
- Container security scanning
- HTTPS/TLS enforcement
- Authentication and authorization

## 📚 Documentation

- **API Documentation**: Auto-generated with FastAPI/Swagger
- **Architecture Decisions**: `/docs/adr/`
- **Deployment Guide**: `/docs/deployment.md`
- **Contributing Guide**: `/docs/contributing.md`

## 🤝 Contributing

1. Create a feature branch from `main`
2. Make your changes following the code standards
3. Run tests: `make test`
4. Run linters: `make lint`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs/`
- **Development Setup**: This README

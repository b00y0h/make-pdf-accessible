# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a microservices monorepo for PDF accessibility processing. The system consists of:

- **API Gateway** (`services/api/`) - Main entry point at port 8000
- **Microservice Functions** - Specialized services on ports 8001-8007:
  - Router (8001), OCR (8002), Structure (8003), Tagger (8004), Exporter (8005), Validator (8006), Notifier (8007)
- **Worker Service** (`services/worker/`) - Celery-based background processing
- **Web Application** (`web/`) - Next.js frontend at port 3000
- **Shared Infrastructure** - PostgreSQL database, Redis message broker

Services communicate via Redis queues for async processing and direct HTTP for synchronous requests.

## Technology Stack

- **Backend**: Python 3.9+ with FastAPI, Uvicorn, SQLAlchemy 2.0+, Celery 5.3+
- **Frontend**: Next.js 13.4.19, React 18.2.0, TypeScript 5.2.2
- **Infrastructure**: Docker Compose for local development, Terraform for deployment
- **Database**: PostgreSQL 15, Redis 7
- **Code Quality**: Black, Ruff, MyPy (Python), ESLint, Prettier (TypeScript)

## Essential Commands

### Initial Setup

```bash
make init          # Complete environment setup (creates venv, installs pnpm deps, builds containers)
source venv/bin/activate  # Activate Python virtual environment
```

### Development

```bash
make dev           # Start all services with hot reload
make dev-stop      # Stop all services
docker-compose logs -f [service-name]  # View service logs
```

### Testing

```bash
make test          # Run all tests
docker-compose run --rm api pytest            # Run API tests only
docker-compose run --rm worker pytest         # Run worker tests only
pnpm -r test                                   # Run all workspace tests
pnpm --filter web test                         # Run web tests only
```

### Code Quality

```bash
make lint          # Run all linters (uses venv/bin/ruff, pnpm -r lint)
make format        # Format all code (uses venv/bin/black, venv/bin/ruff --fix, pnpm -r format)
./venv/bin/ruff check . --fix                 # Quick Python linting
./venv/bin/black .                             # Quick Python formatting
pnpm -r lint                                   # Run all workspace linters
pnpm -r format                                 # Format all workspace code
```

### Build and Deploy

```bash
make build         # Build all Docker images and pnpm packages
make deploy        # Deploy using Terraform (runs terraform apply)
docker-compose build [service-name]           # Rebuild specific service
pnpm -r build                                  # Build all workspace packages
```

### Cleanup

```bash
make clean         # Remove all build artifacts, containers, and venv
docker-compose down -v                        # Stop and remove containers/volumes
```

## Development Environment

All services are containerized but support hot reload via volume mounts:

- **Python services**: Use `uvicorn --reload` for auto-restart on file changes
- **Next.js**: `pnpm dev` provides hot module replacement
- **Shared packages**: Changes in `packages/schemas/` affect all services

The `docker-compose.yml` defines the complete development stack with proper service dependencies.

## Service Structure Patterns

Each microservice follows identical patterns:

- **Dockerfile**: Python 3.11-slim base with standardized dependencies
- **main.py**: FastAPI application with health check endpoints
- **requirements.txt**: Common FastAPI, Pydantic, SQLAlchemy stack

## Code Quality Setup

- **Virtual Environment**: All Python tooling runs in `venv/` (created by `make init`)
- **Pre-commit Hooks**: Enforced via `.pre-commit-config.yaml`
- **Python Standards**: Black formatting (88-char lines), Ruff linting, MyPy type checking
- **TypeScript Standards**: ESLint + Prettier with Next.js config
- **Testing**: Pytest with asyncio support, Jest for frontend

## Key Configuration Files

- **`pyproject.toml`**: Python project config with Black/Ruff/MyPy settings
- **`docker-compose.yml`**: Service definitions, ports, and dependencies
- **`Makefile`**: Development workflow automation with virtual environment handling
- **`.pre-commit-config.yaml`**: Automated code quality checks

## Integration Points

- **WordPress Plugin**: `integrations/wordpress/` for CMS integration
- **LTI Integration**: `integrations/lti/` for Learning Management Systems
- **Shared Schemas**: `packages/schemas/` for type definitions across services
- **Infrastructure**: `infra/terraform/` for cloud resource management

## Important Notes

- All Python commands use virtual environment paths (`./venv/bin/`)
- Services communicate through Redis for async tasks and HTTP for sync requests
- The system is designed for PDF accessibility processing with microservice specialization
- Hot reload is enabled for all services in development mode

# Technology Stack

## Backend Services

- **Python 3.9+**: Core backend services using FastAPI framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and settings management
- **SQLAlchemy 2.0+**: Database ORM with async support
- **Alembic**: Database migration tool
- **Celery**: Distributed task queue for background processing
- **Redis**: In-memory data store for caching and message broker
- **PostgreSQL**: Primary database for persistent data

## Frontend

- **Next.js 13+**: React framework with App Router
- **React 18**: Frontend UI library
- **TypeScript**: Type-safe JavaScript development
- **Node.js 18+**: JavaScript runtime

## Package Management

- **pnpm 8+**: Fast, disk space efficient package manager for Node.js
- **pip/pip-tools**: Python package management
- **pnpm workspaces**: Monorepo package management

## Infrastructure & DevOps

- **Docker & Docker Compose**: Containerization and local development
- **Terraform**: Infrastructure as Code for AWS deployment
- **GitHub Actions**: CI/CD pipelines
- **AWS**: Cloud infrastructure (ECS, RDS, ElastiCache, S3, etc.)

## Code Quality & Standards

- **Black**: Python code formatter (line length: 88)
- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking for Python
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting (2 spaces, single quotes, semicolons)
- **Pre-commit hooks**: Automated code quality checks

## Common Commands

### Development Environment

```bash
# Initialize development environment
make init

# Start all services
make dev

# Stop development environment
make dev-stop
```

### Testing

```bash
# Run all tests
make test

# Run specific service tests
docker-compose run --rm api pytest
docker-compose run --rm worker pytest
pnpm --filter web test
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Building & Deployment

```bash
# Build all services
make build

# Deploy to production
make deploy

# Clean build artifacts
make clean
```

### Docker Operations

```bash
# View service logs
docker-compose logs -f [service-name]

# Rebuild specific service
docker-compose build [service-name]

# Execute commands in running container
docker-compose exec [service-name] [command]
```

### Package Management

```bash
# Install all dependencies
pnpm install

# Add dependency to specific workspace
pnpm add [package] --filter [workspace]

# Update Python dependencies
pip-tools compile requirements.in
```

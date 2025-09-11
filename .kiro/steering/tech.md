# Technology Stack

## Backend Services

- **Python 3.9+**: Core backend services using FastAPI framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and settings management
- **SQLAlchemy 2.0+**: Database ORM with async support for PostgreSQL
- **Motor**: Async MongoDB driver for Python
- **Alembic**: Database migration tool for PostgreSQL
- **Celery**: Distributed task queue for background processing
- **Redis**: In-memory data store for caching and message broker
- **PostgreSQL**: Application data and BetterAuth authentication
- **MongoDB**: Primary document storage and job tracking

## Frontend

- **Next.js 15+**: React framework with App Router
- **React 19 RC**: Frontend UI library
- **TypeScript**: Type-safe JavaScript development
- **Node.js 18+**: JavaScript runtime
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Headless UI components
- **BetterAuth**: Modern authentication library
- **React Hook Form**: Form state management
- **Zod**: Runtime type validation
- **Lucide React**: Icon library

## Package Management

- **pnpm 8+**: Fast, disk space efficient package manager for Node.js
- **pip/pip-tools**: Python package management
- **pnpm workspaces**: Monorepo package management

## Infrastructure & DevOps

- **Docker & Docker Compose**: Containerization and local development
- **Terraform**: Infrastructure as Code for AWS deployment
- **GitHub Actions**: CI/CD pipelines
- **AWS**: Cloud infrastructure (ECS, RDS, ElastiCache, S3, etc.)
- **LocalStack**: Local AWS services for development
- **ClamAV**: Virus scanning service
- **MongoDB**: Document database with replica set support
- **PostgreSQL**: Relational database for structured data

## Authentication & Security

- **BetterAuth**: Modern authentication library with social login support
- **JWT**: JSON Web Tokens for API authentication
- **ClamAV**: Virus scanning for uploaded files
- **CORS**: Cross-origin resource sharing configuration
- **File validation**: Security validation and quarantine system
- **Rate limiting**: Request throttling and quota enforcement

## Database Configuration

### MongoDB (Primary Document Storage)

- **Connection**: `mongodb://localhost:27017/pdf_accessibility?replicaSet=rs0`
- **Usage**: Document storage, job tracking, processing metadata
- **Web Interface**: Mongo Express at http://localhost:8081 (admin/admin123)

### PostgreSQL (Application Data)

- **Main DB**: `postgresql://postgres:password@localhost:5432/app_db`
- **Auth DB**: `postgresql://postgres:password@localhost:5433/better_auth`
- **Usage**: BetterAuth user data, application metadata

## Code Quality & Standards

- **Black**: Python code formatter (line length: 88)
- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking for Python
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting (2 spaces, single quotes, semicolons)
- **Pre-commit hooks**: Automated code quality checks
- **Tailwind CSS**: Utility-first styling with consistent design system

## Common Commands

### Development Environment

```bash
# Initialize development environment
make init

# Start complete local development stack (recommended)
make up

# Stop complete development stack
make down

# Start backend services only
make dev

# Start frontend applications
make dev-frontend
make dev-dashboard  # Admin dashboard (port 3001)
make dev-web        # Public web app (port 3000)

# Stop development environment
make dev-stop

# Check development environment status
make dev-status

# View logs from all services
make dev-logs
```

### Testing

```bash
# Run all tests
make test

# Run development tests only (faster)
make test-dev

# Run specific service tests
docker-compose run --rm api pytest
docker-compose run --rm worker pytest

# Run frontend tests
pnpm --filter accesspdf-dashboard test        # Dashboard tests
pnpm --filter pdf-accessibility-web test      # Web app tests

# Run specific test types
pnpm --filter accesspdf-dashboard test:unit
pnpm --filter accesspdf-dashboard test:integration
pnpm --filter accesspdf-dashboard test:e2e
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
pnpm add [package] --filter accesspdf-dashboard
pnpm add [package] --filter pdf-accessibility-web

# Update Python dependencies
pip-tools compile requirements.in

# Database seeding and setup
make seed          # Add sample data
make seed-admin    # Create admin user from dashboard/.env.local
```

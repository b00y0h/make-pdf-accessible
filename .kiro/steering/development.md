# Development Workflow & Best Practices

## Quick Start Guide

### First Time Setup

1. **Initialize environment**:

   ```bash
   make init
   ```

2. **Start complete development stack**:

   ```bash
   make up
   ```

3. **Seed with sample data**:

   ```bash
   make seed
   make seed-admin
   ```

4. **Access applications**:
   - Admin Dashboard: http://localhost:3001
   - Public Web App: http://localhost:3000
   - API: http://localhost:8000
   - MongoDB: http://localhost:8081 (admin/admin123)

### Daily Development

- **Start everything**: `make up`
- **Stop everything**: `make down`
- **View logs**: `make dev-logs`
- **Check status**: `make dev-status`

## Frontend Development

### Dashboard (Admin Interface)

- **Location**: `dashboard/`
- **Port**: 3001
- **Start**: `make dev-dashboard` or `pnpm --filter accesspdf-dashboard dev`
- **Features**: User management, document processing, analytics
- **Auth**: BetterAuth with social login support

### Web App (Public Interface)

- **Location**: `web/`
- **Port**: 3000
- **Start**: `make dev-web` or `pnpm --filter pdf-accessibility-web dev`
- **Features**: Document upload, accessibility tools, public API

### Shared UI Components

- **Radix UI**: Headless components for accessibility
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Consistent icon library
- **React Hook Form + Zod**: Form validation

## Backend Development

### API Service

- **Location**: `services/api/`
- **Port**: 8000
- **Features**: Authentication, document management, job orchestration
- **Database**: PostgreSQL + MongoDB
- **Auth**: BetterAuth JWT integration

### Worker Service

- **Location**: `services/worker/`
- **Features**: Background job processing, document pipeline
- **Queue**: Celery with Redis broker

### Function Services

- **Location**: `services/functions/`
- **Ports**: 8001-8007
- **Pattern**: Standalone FastAPI microservices
- **Communication**: HTTP APIs, async task queues

## Database Development

### MongoDB (Documents & Jobs)

```bash
# Connect to MongoDB
docker exec -it pdf-accessibility-mongo mongosh pdf_accessibility

# View collections
show collections

# Query documents
db.documents.find().limit(5)
db.jobs.find({status: "processing"})
```

### PostgreSQL (App Data & Auth)

```bash
# Connect to main database
docker exec -it pdf-accessibility-postgres psql -U postgres -d app_db

# Connect to auth database
docker exec -it pdf-accessibility-postgres-auth psql -U postgres -d better_auth

# View tables
\dt
```

## Testing Strategy

### Unit Tests

- **Python**: pytest with fixtures
- **JavaScript**: Jest with React Testing Library
- **Location**: `tests/unit/` or alongside source files

### Integration Tests

- **API**: FastAPI TestClient with test database
- **Frontend**: Playwright for component integration
- **Location**: `tests/integration/`

### End-to-End Tests

- **Tool**: Playwright
- **Scope**: Full user workflows
- **Location**: `tests/e2e/` or `dashboard/tests/e2e/`

### Running Tests

```bash
# All tests
make test

# Development tests (faster)
make test-dev

# Specific service
docker-compose run --rm api pytest tests/unit/
pnpm --filter accesspdf-dashboard test:unit

# E2E tests
pnpm --filter accesspdf-dashboard test:e2e
```

## Code Quality

### Pre-commit Hooks

Automatically run on commit:

- Python: Black, Ruff, MyPy
- JavaScript: ESLint, Prettier
- General: File formatting, trailing whitespace

### Manual Quality Checks

```bash
# Format all code
make format

# Run all linters
make lint

# Type checking
pnpm -r type-check
```

## Environment Configuration

### Environment Files

- **Root**: `.env.local` (shared configuration)
- **Dashboard**: `dashboard/.env.local` (BetterAuth, database)
- **API**: `services/api/.env` (service-specific)

### Key Environment Variables

```bash
# Database URLs
DATABASE_URL=postgresql://postgres:password@localhost:5432/app_db
MONGODB_URI=mongodb://localhost:27017/pdf_accessibility?replicaSet=rs0

# BetterAuth
BETTER_AUTH_SECRET=your-secret-key
BETTER_AUTH_URL=http://localhost:3001

# AWS (LocalStack)
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

## Debugging

### Backend Services

```bash
# View API logs
docker-compose logs -f api

# Debug worker tasks
docker-compose logs -f worker

# Connect to running container
docker-compose exec api bash
```

### Frontend Applications

```bash
# Dashboard logs (when using make up)
tail -f dashboard.log

# Web app logs (when using make up)
tail -f web.log

# Direct development server
pnpm --filter accesspdf-dashboard dev  # with hot reload
```

### Database Debugging

```bash
# MongoDB queries
docker exec -it pdf-accessibility-mongo mongosh pdf_accessibility

# PostgreSQL queries
docker exec -it pdf-accessibility-postgres psql -U postgres -d app_db

# Redis inspection
docker exec -it pdf-accessibility-redis redis-cli
```

## Performance Optimization

### Frontend

- **Next.js**: App Router with streaming and suspense
- **Bundle analysis**: `pnpm --filter [workspace] analyze`
- **Image optimization**: Next.js Image component
- **Caching**: React Query for API state management

### Backend

- **Database**: Async operations with connection pooling
- **Caching**: Redis for frequently accessed data
- **Background jobs**: Celery for heavy processing
- **File processing**: Streaming uploads to S3

## Security Best Practices

### Authentication

- **BetterAuth**: Secure session management
- **JWT**: Short-lived tokens with refresh rotation
- **Social login**: OAuth2 with major providers
- **CSRF protection**: Built-in with BetterAuth

### File Security

- **Virus scanning**: ClamAV integration
- **File validation**: Type and signature checking
- **Quarantine system**: Suspicious file isolation
- **S3 security**: Signed URLs for file access

### API Security

- **CORS**: Configured for specific origins
- **Rate limiting**: Request throttling
- **Input validation**: Pydantic models and Zod schemas
- **SQL injection**: Parameterized queries only

## Deployment

### Local Development

- **Docker Compose**: Full stack with hot reload
- **Native frontend**: pnpm dev for optimal DX
- **LocalStack**: Local AWS services

### Production

- **Terraform**: Infrastructure as Code
- **AWS ECS**: Container orchestration
- **RDS**: Managed PostgreSQL
- **DocumentDB**: Managed MongoDB
- **ElastiCache**: Managed Redis

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check `make dev-status`
2. **Database connection**: Ensure services are healthy
3. **Frontend not loading**: Check pnpm processes
4. **API errors**: Check Docker logs
5. **Auth issues**: Verify BetterAuth configuration

### Reset Development Environment

```bash
# Clean everything
make clean

# Reinitialize
make init
make up
make seed
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Monitor database performance
docker exec -it pdf-accessibility-mongo mongosh --eval "db.runCommand({serverStatus: 1})"

# Check Redis memory
docker exec -it pdf-accessibility-redis redis-cli info memory
```

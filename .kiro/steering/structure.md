# Project Structure

## Monorepo Organization

This is a monorepo containing multiple services, integrations, and shared packages organized by domain and function.

## Top-Level Structure

```
├── infra/                  # Infrastructure as Code (Terraform)
├── services/               # Backend services and functions
├── web/                    # Public frontend application (Next.js)
├── dashboard/              # Admin dashboard application (Next.js)
├── integrations/           # Third-party integrations (WordPress, LTI)
├── packages/               # Shared libraries and schemas
├── scripts/                # Development and deployment scripts
├── docs/                   # Documentation
├── e2e/                    # End-to-end tests
├── tests/                  # Shared test utilities
└── .github/                # CI/CD workflows
```

## Services Architecture

### Core Services (`services/`)

- **`api/`**: Main API gateway - handles authentication, routing, business logic, BetterAuth integration
- **`worker/`**: Background job processor using Celery for heavy tasks
- **`shared/`**: Shared utilities, models, and authentication logic
- **`timeout-monitor/`**: Service monitoring and timeout management

### Microservices (`services/functions/`)

Each function service is a standalone FastAPI application:

- **`router/`**: Request routing and load balancing
- **`ocr/`**: Optical Character Recognition processing
- **`structure/`**: Document structure analysis
- **`tagger/`**: Content classification and metadata tagging
- **`alt_text/`**: AI-powered alt text generation
- **`exporter/`**: Export to accessible formats (HTML, EPUB, etc.)
- **`validator/`**: WCAG compliance validation
- **`notifier/`**: Notification service (email, webhooks, push)

### Service Structure Pattern

Each service follows this structure:

```
service-name/
├── Dockerfile              # Container configuration
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── packages/               # Symlinked shared packages
└── __pycache__/           # Python bytecode (ignored)
```

## Frontend Applications

### Public Web App (`web/`)

Next.js application for public-facing features:

```
web/
├── app/                  # Next.js pages (using App Router)
├── package.json           # Node.js dependencies and scripts
├── next.config.js         # Next.js configuration
├── Dockerfile             # Container configuration
└── .next/                 # Build output (ignored)
```

### Admin Dashboard (`dashboard/`)

Next.js application for administrative features with BetterAuth:

```
dashboard/
├── src/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components (UI library, auth, etc.)
│   ├── lib/              # Utilities, auth configuration, API clients
│   ├── hooks/            # Custom React hooks
│   ├── contexts/         # React contexts
│   └── types/            # TypeScript type definitions
├── auth.ts               # BetterAuth configuration
├── scripts/              # Database seeding and utility scripts
├── tests/                # Unit, integration, and E2E tests
├── package.json          # Dependencies and scripts
├── next.config.js        # Next.js configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── sqlite.db             # Local SQLite database for BetterAuth
```

## Infrastructure (`infra/`)

Terraform modules for AWS deployment:

```
infra/terraform/
├── main.tf                # Provider and common configuration
├── variables.tf           # Input variables
├── outputs.tf             # Output values
├── *.tf                   # Resource definitions by service
├── terraform.tfvars       # Environment-specific values
└── .terraform/            # Terraform state and providers
```

## Integrations (`integrations/`)

Third-party platform integrations:

- **`wordpress/`**: WordPress plugin for CMS integration
- **`lti/`**: Learning Tools Interoperability for LMS
- **`lit/`**: Additional integration (structure TBD)

## Shared Packages (`packages/`)

- **`schemas/`**: Shared data models and validation schemas used across services

## Configuration Files

### Root Level

- **`package.json`**: Monorepo configuration and scripts
- **`pnpm-workspace.yaml`**: Workspace definitions for pnpm
- **`pyproject.toml`**: Python project configuration and tool settings
- **`docker-compose.yml`**: Local development environment
- **`Makefile`**: Common development commands

### Code Quality

- **`.eslintrc.js`**: ESLint configuration for JavaScript/TypeScript
- **`.prettierrc`**: Prettier formatting rules
- **`.pre-commit-config.yaml`**: Pre-commit hook configuration
- **`.editorconfig`**: Editor configuration for consistent formatting

## Naming Conventions

### Services

- Use lowercase with hyphens for service names
- Function services prefixed with `function-` in docker-compose
- Python modules use snake_case
- FastAPI apps typically named `app` in main.py

### Files and Directories

- Python: snake_case for files and directories
- JavaScript/TypeScript: camelCase for files, kebab-case for directories
- Configuration files: lowercase with dots/hyphens

### Docker and Infrastructure

- Container names match service names
- Terraform resources use snake_case with descriptive prefixes
- Environment variables use UPPER_SNAKE_CASE

## Port Allocation

### Frontend Applications

- **3000**: Public web application (Next.js)
- **3001**: Admin dashboard (Next.js)

### Backend Services

- **8000**: Main API service (FastAPI)
- **8001-8007**: Function services (router, ocr, structure, tagger, exporter, validator, notifier)

### Infrastructure Services

- **5432**: PostgreSQL database (main app data)
- **5433**: PostgreSQL database (BetterAuth)
- **6379**: Redis cache/message broker
- **27017**: MongoDB (document storage and jobs)
- **4566**: LocalStack (local AWS services)
- **8081**: Mongo Express (MongoDB web interface)
- **3310**: ClamAV (virus scanning)

## Development Patterns

### Service Communication

- Services communicate via HTTP APIs
- Async tasks use Celery with Redis as message broker
- Shared data models defined in `packages/schemas/`

### Database Access

- **MongoDB**: Primary document storage (API and Worker services)
- **PostgreSQL**: Application data and BetterAuth (API service)
- Function services are stateless and communicate via APIs
- Use SQLAlchemy with async support for PostgreSQL operations
- Use Motor (async MongoDB driver) for MongoDB operations

### Error Handling

- Use FastAPI's built-in exception handling
- Return consistent error response formats
- Log errors with appropriate levels

### Testing

- Unit tests alongside source code
- Integration tests in separate test directories
- Use pytest for Python services
- Use Jest for JavaScript/TypeScript services

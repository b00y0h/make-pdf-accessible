# Project Structure

## Monorepo Organization

This is a monorepo containing multiple services, integrations, and shared packages organized by domain and function.

## Top-Level Structure

```
├── infra/                  # Infrastructure as Code
├── services/               # Backend services and functions
├── web/                    # Frontend application
├── integrations/           # Third-party integrations
├── packages/               # Shared libraries and schemas
└── .github/                # CI/CD workflows
```

## Services Architecture

### Core Services (`services/`)

- **`api/`**: Main API gateway - handles authentication, routing, business logic
- **`worker/`**: Background job processor using Celery for heavy tasks

### Microservices (`services/functions/`)

Each function service is a standalone FastAPI application:

- **`router/`**: Request routing and load balancing
- **`ocr/`**: Optical Character Recognition processing
- **`structure/`**: Document structure analysis
- **`tagger/`**: Content classification and metadata tagging
- **`exporter/`**: Export to accessible formats
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

## Frontend (`web/`)

Next.js application with standard structure:

```
web/
├── app/                  # Next.js pages (using App Router)
├── package.json           # Node.js dependencies and scripts
├── next.config.js         # Next.js configuration
├── Dockerfile             # Container configuration
└── .next/                 # Build output (ignored)
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

- **3000**: Web application (Next.js)
- **8000**: Main API service
- **8001-8007**: Function services (router, ocr, structure, tagger, exporter, validator, notifier)
- **5432**: PostgreSQL database
- **6379**: Redis cache/message broker

## Development Patterns

### Service Communication

- Services communicate via HTTP APIs
- Async tasks use Celery with Redis as message broker
- Shared data models defined in `packages/schemas/`

### Database Access

- Only API and Worker services access the database directly
- Function services are stateless and communicate via APIs
- Use SQLAlchemy with async support for database operations

### Error Handling

- Use FastAPI's built-in exception handling
- Return consistent error response formats
- Log errors with appropriate levels

### Testing

- Unit tests alongside source code
- Integration tests in separate test directories
- Use pytest for Python services
- Use Jest for JavaScript/TypeScript services

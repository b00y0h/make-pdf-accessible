# Directory Structure

## Root Layout

```
/workspace/
├── services/          # Backend microservices
├── web/               # Next.js main frontend
├── dashboard/         # Admin dashboard (Next.js 15)
├── packages/          # Shared packages
├── infra/             # Infrastructure as code
├── integrations/      # External integrations
├── .github/           # GitHub Actions workflows
├── docker-compose.yml # Development stack
├── Makefile           # Task automation
└── pyproject.toml     # Python project config
```

## Services Directory

```
services/
├── api/               # API Gateway (port 8000)
│   └── app/
│       ├── routes/    # API endpoints
│       ├── middleware/# Auth, CORS, rate limiting
│       ├── services/  # Business logic
│       ├── models.py  # SQLAlchemy models
│       └── main.py    # FastAPI application
├── worker/            # Celery worker
│   ├── tasks/         # Celery task definitions
│   └── celery_app.py  # Celery configuration
├── functions/         # Processing microservices
│   ├── router/        # Pipeline orchestration (8001)
│   ├── ocr/           # Text recognition (8002)
│   ├── structure/     # Document analysis (8003)
│   ├── tagger/        # Accessibility tagging (8004)
│   ├── exporter/      # PDF export (8005)
│   ├── validator/     # Compliance validation (8006)
│   └── notifier/      # Webhook delivery (8007)
├── shared/            # Shared utilities
│   ├── auth.py        # JWT authentication
│   ├── models.py      # Common data models
│   ├── persistence.py # Database connections
│   ├── security_validation.py
│   └── quota_enforcement.py
└── timeout-monitor/   # Long-running task monitor
```

## Service Structure Pattern

Each function follows identical structure:
```
services/functions/{service}/
├── main.py           # FastAPI app with health endpoint
├── models.py         # Pydantic models
├── services.py       # Business logic
├── requirements.txt  # Python dependencies
└── Dockerfile        # Container definition
```

## Frontend Applications

```
web/                   # Main web application
├── src/
│   ├── app/          # Next.js app router
│   ├── components/   # React components
│   └── lib/          # Utilities
├── package.json
└── next.config.js

dashboard/             # Admin dashboard
├── src/
│   ├── app/
│   └── components/
└── package.json
```

## Shared Packages

```
packages/
└── schemas/          # TypeScript type definitions
    └── src/          # Shared types across services
```

## Infrastructure

```
infra/
└── terraform/        # AWS infrastructure
    ├── modules/      # Reusable terraform modules
    ├── main.tf       # Root configuration
    ├── variables.tf  # Input variables
    └── outputs.tf    # Output values
```

## Integrations

```
integrations/
├── wordpress/        # WordPress plugin
│   ├── accesspdf-plugin.php
│   └── js/
├── lti/              # Learning management systems
│   └── tests/
└── html-snippets/    # Generic website integration
    └── accesspdf-snippet.js
```

## Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Development services |
| `docker-compose.test.yml` | Test environment |
| `Makefile` | Build/dev automation |
| `pyproject.toml` | Python config (Black, Ruff, MyPy) |
| `.pre-commit-config.yaml` | Git hooks |
| `pytest.ini` | Test configuration |

## Test Organization

```
tests/
├── unit/             # Fast, isolated tests
├── integration/      # Service integration tests
├── api/              # API endpoint tests
└── conftest.py       # Shared fixtures
```

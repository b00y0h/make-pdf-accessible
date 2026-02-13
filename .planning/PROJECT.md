# PDF Accessibility Microservices - Project Overview

## Vision

A comprehensive PDF accessibility processing platform that helps organizations make their PDF documents accessible to all users, including those using assistive technologies.

## System Overview

Microservices monorepo for PDF accessibility processing. The system processes PDF documents through a pipeline of specialized services to add accessibility features:

- **API Gateway** (port 8000) - Authentication, routing, rate limiting
- **Processing Functions** - Router (8001), OCR (8002), Structure (8003), Tagger (8004), Exporter (8005), Validator (8006), Notifier (8007)
- **Worker Service** - Celery-based background processing
- **Web Application** (port 3000) - Next.js frontend
- **Dashboard** (port 3001) - Admin dashboard (Next.js 15)

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.9+, FastAPI, Uvicorn, SQLAlchemy 2.0+, Celery 5.3+ |
| Frontend | Next.js (13.4.19 web, 15.5.7 dashboard), React, TypeScript |
| Database | PostgreSQL 15, MongoDB, Redis 7 |
| Infrastructure | Docker Compose (dev), Terraform (prod), AWS (S3, SQS, Cognito) |
| Integrations | WordPress plugin, LTI (LMS), HTML snippets |

## Repository Structure

```
/workspace/
├── services/          # Backend microservices
│   ├── api/           # API Gateway
│   ├── worker/        # Celery worker
│   ├── functions/     # Processing microservices (7 services)
│   └── shared/        # Common utilities
├── web/               # Main web application (Next.js 13)
├── dashboard/         # Admin dashboard (Next.js 15)
├── packages/          # Shared packages
├── integrations/      # WordPress, LTI, HTML snippets
├── infra/             # Terraform infrastructure
└── .planning/         # Planning documents
```

---

## Current Milestone

### Milestone 1: Dependabot Security Fixes

**Goal:** Resolve all open Dependabot security alerts to ensure the application has no known vulnerabilities.

**Scope:** Small (1-3 phases)

**Background:**
The repository has accumulated 82 open Dependabot security alerts across npm packages. These include critical and high severity vulnerabilities that need immediate attention.

### Alert Summary by Package

| Package | Severity | Count | Current Version | Target Version |
|---------|----------|-------|-----------------|----------------|
| next | CRITICAL/HIGH/MEDIUM/LOW | 58 | 13.4.19 (web), 15.5.7 (dashboard) | 15.5.10+ |
| better-auth | HIGH/LOW | 3 | 1.3.9 | 1.4.5+ |
| axios | HIGH | 2 | 1.5.0/1.11.0 | 1.13.5+ |
| fast-xml-parser | HIGH | 1 | (transitive) | 5.3.4+ |
| qs | HIGH/LOW | 2 | (transitive) | 6.14.2+ |
| tar-fs | HIGH | 2 | (transitive) | patched |
| jws | HIGH | 1 | (transitive) | patched |
| glob | HIGH | 1 | (transitive) | patched |
| playwright | HIGH | 1 | 1.40.1 | patched |
| js-yaml | MEDIUM | 4 | (transitive) | patched |
| lodash | MEDIUM | 1 | (transitive) | 4.17.23+ |
| postcss | MEDIUM | 2 | 8.4.29/8.4.32 | patched |
| zod | MEDIUM | 2 | 4.1.5 | patched |
| vite | MEDIUM | 1 | (transitive) | patched |
| @smithy/config-resolver | LOW | 1 | (transitive) | 4.4.0+ |

### Key Challenges

1. **Next.js Major Upgrade**: web/ uses Next.js 13.4.19, dashboard uses 15.5.7
   - Need to upgrade web/ to at least 15.x for full security coverage
   - This is a breaking change requiring code updates

2. **Transitive Dependencies**: Many vulnerabilities are in transitive dependencies
   - May require overrides/resolutions in package.json
   - Some may auto-resolve when direct dependencies are updated

3. **Testing After Upgrades**: All upgrades need verification
   - Ensure builds pass
   - Ensure tests pass
   - Check for runtime regressions

---

## Milestone History

| Version | Status | Summary |
|---------|--------|---------|
| 1.0 | In Progress | Dependabot Security Fixes |

---

## Links

- Repository: https://github.com/b00y0h/make-pdf-accessible
- Dependabot Alerts: https://github.com/b00y0h/make-pdf-accessible/security/dependabot

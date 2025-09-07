# 🚀 Development Guide

## Architecture Overview

This monorepo contains **separate Next.js applications** for optimal scalability:

- **`/web`** - Public-facing website (port 3000)
- **`/dashboard`** - Admin dashboard (port 3001)
- **`/services`** - Backend services and Lambda functions
- **`/infra`** - Infrastructure as Code (Terraform)

### Why Separate Applications?

✅ **Scaling**: Independent resource allocation and deployment  
✅ **Security**: Complete isolation between public and admin  
✅ **Teams**: Frontend and admin teams can work independently  
✅ **Performance**: Optimized bundles for each use case  

## 🏃‍♂️ Quick Start

### Prerequisites
```bash
node >= 18.0.0
pnpm >= 8.0.0
```

### Installation
```bash
pnpm install
```

## 🚀 Development Commands (Makefile)

**Universal Interface** - Always use `make` commands for consistency:

### 📋 Quick Start
```bash
# See all available commands
make help

# Start just the dashboard (recommended for dashboard development)
make dev-dashboard

# Start just the web app  
make dev-web

# Start both frontend apps
make dev-frontend

# Start backend services only
make dev

# Start everything (backend + frontend)
make dev-full
```

### 🔧 Development Utilities
```bash
# Check what's running
make dev-status

# Follow all service logs
make dev-logs

# Stop everything
make dev-stop
```

### 🏗️ Build & Test
```bash
# Build all services
make build

# Run all tests
make test

# Run development tests only  
make test-dev

# Lint code
make lint

# Format code
make format
```

### 🧹 Maintenance
```bash
# Initialize development environment
make init

# Clean everything
make clean
```

## 🌐 Application URLs

| Service | URL | Description |
|---------|-----|-------------|
| Web App | http://localhost:3000 | Public-facing website |
| Dashboard | http://localhost:3001 | Admin dashboard |
| API | http://localhost:8080 | Backend API |
| Services | Various ports | Lambda functions & services |

## 🔐 Dashboard Access

**Demo Credentials:**
- Email: `admin@example.com`
- Password: `demo123`

## 🏗️ Monorepo Structure

```
├── web/                 # Public Next.js app
├── dashboard/           # Admin Next.js app  
├── services/           
│   ├── functions/       # Lambda functions
│   └── worker/         # Shared Python package
├── infra/              # Terraform infrastructure
├── packages/           # Shared packages
└── integrations/       # Third-party integrations
```

## 🚀 Deployment Architecture

### Production Scaling Strategy

```
┌─────────────────┐    ┌─────────────────┐
│   Public Web    │    │  Admin Dashboard│
│  (High Traffic) │    │  (Low Traffic)  │
│                 │    │                 │
│ • Auto-scaling  │    │ • Fixed size    │
│ • CDN caching   │    │ • Private VPC   │
│ • Multiple AZs  │    │ • Enhanced auth │
└─────────────────┘    └─────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
            ┌───────────────┐
            │  Shared API   │
            │   Services    │
            └───────────────┘
```

### Benefits of This Architecture

1. **Independent Scaling**: Web app can handle thousands of users while dashboard serves dozens of admins
2. **Security Isolation**: Admin functions are completely separated from public traffic
3. **Development Velocity**: Teams can deploy independently without conflicts
4. **Cost Optimization**: Right-size resources for each application's needs

## 🛠️ Development Workflow

### For Dashboard Development
```bash
pnpm dev:dashboard
# Visit http://localhost:3001
```

### For Full Stack Development  
```bash
pnpm dev:full
# Starts all services + both frontend apps
```

### For Backend Only
```bash
pnpm dev
# Starts just the Docker services
```

## 📝 Common Tasks

### Adding New Dependencies
```bash
# Dashboard
pnpm --filter dashboard add <package>

# Web
pnpm --filter web add <package>

# Root (shared tooling)
pnpm add -w <package>
```

### Running Tests
```bash
pnpm test          # All tests
pnpm test:dashboard # Dashboard tests only
pnpm test:web      # Web tests only
```

### Building for Production
```bash
pnpm build         # Build all applications
```

This setup provides the **best of both worlds**: monorepo conveniences with microservice scalability! 🎯
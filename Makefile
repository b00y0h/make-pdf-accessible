.PHONY: init test test-dev build deploy clean lint format help up down seed dev dev-web dev-dashboard dev-frontend dev-full dev-stop dev-status dev-logs

# Default target
help:
	@echo "🚀 PDF Accessibility Service - Development Commands:"
	@echo ""
	@echo "🎯 Quick Start:"
	@echo "  up            - Start complete local development stack (one-command)"
	@echo "  down          - Stop all services started with 'up'"
	@echo "  seed          - Populate database with sample data"
	@echo ""
	@echo "📋 Setup & Maintenance:"
	@echo "  init          - Initialize development environment"
	@echo "  clean         - Clean build artifacts and volumes"
	@echo ""
	@echo "🏗️  Development:"
	@echo "  dev           - Start backend services only (Docker)"
	@echo "  dev-web       - Start public web app (port 3001)"
	@echo "  dev-dashboard - Start admin dashboard (port 3000)"
	@echo "  dev-frontend  - Start both frontend apps"
	@echo "  dev-full      - Start everything (backend + frontend)"
	@echo "  dev-stop      - Stop all development services"
	@echo "  dev-status    - Show development environment status"
	@echo "  dev-logs      - Follow logs from all services"
	@echo ""
	@echo "🔨 Build & Test:"
	@echo "  build         - Build all services"
	@echo "  test          - Run all tests"
	@echo "  test-dev      - Run development tests only"
	@echo ""
	@echo "✨ Code Quality:"
	@echo "  lint          - Run linters"
	@echo "  format        - Format code"
	@echo ""
	@echo "🚀 Deployment:"
	@echo "  deploy        - Deploy to production"
	@echo ""
	@echo "🌐 URLs:"
	@echo "  http://localhost:3000  - Dashboard"
	@echo "  http://localhost:3001  - Web App (if enabled)"
	@echo "  http://localhost:8000  - API"
	@echo "  http://localhost:8081  - Mongo Express (admin/admin123)"
	@echo "  http://localhost:4566  - LocalStack"

# Initialize development environment
init:
	@echo "🚀 Initializing development environment..."
	@echo "📦 Setting up Python virtual environment..."
	python3 -m venv venv
	./venv/bin/pip install -r requirements-dev.txt
	@echo "📦 Installing Node.js dependencies..."
	pnpm install
	pnpm add -g concurrently
	@echo "🔨 Building Docker services..."
	docker-compose build
	@echo "🪝 Installing pre-commit hooks..."
	git config --unset-all core.hooksPath || true
	./venv/bin/pre-commit install
	@echo "✅ Development environment initialized!"
	@echo "💡 To activate Python environment: source venv/bin/activate"

# Run all tests (should pass in CI/production)
test:
	@echo "🧪 Running all tests..."
	docker-compose -f docker-compose.test.yml run --rm api-test
	@echo "✅ All tests passed!"

# Run core/development tests only (should always pass during development)
test-dev:
	@echo "🧪 Running development tests..."
	docker-compose -f docker-compose.test.yml run --rm api-test pytest tests/test_models.py tests/test_auth.py tests/unit/ tests/api/test_endpoints.py -v
	@echo "✅ Development tests passed!"

# Build all services
build:
	@echo "🔨 Building all services..."
	docker-compose build
	pnpm -r build
	@echo "✅ All services built!"

# Deploy to production
deploy:
	@echo "🚀 Deploying to production..."
	cd infra/terraform && terraform apply -auto-approve
	@echo "✅ Deployment complete!"

# Run linters
lint:
	@echo "🔍 Running linters..."
	./venv/bin/ruff check .
	pnpm -r lint
	@echo "✅ Linting complete!"

# Format code
format:
	@echo "✨ Formatting code..."
	./venv/bin/black .
	./venv/bin/ruff check . --fix
	pnpm -r format
	@echo "✅ Code formatted!"



# Start public web app only
dev-web:
	@echo "🌐 Starting public web app..."
	pnpm --filter=pdf-accessibility-web dev --port 3000
	@echo "✅ Web app running on http://localhost:3000"

# Start admin dashboard only
dev-dashboard:
	@echo "📊 Starting admin dashboard..."
	pnpm --filter=accesspdf-dashboard dev
	@echo "✅ Dashboard running on http://localhost:3001"

# Start both frontend apps
dev-frontend:
	@echo "🎨 Starting both frontend applications..."
	npx concurrently -p "[{name}]" -n "web,dashboard" -c "cyan,magenta" \
		"pnpm --filter=pdf-accessibility-web dev --port 3000" \
		"pnpm --filter=accesspdf-dashboard dev --port 3001"

# Start everything (backend + frontend)
dev-full:
	@echo "🚀 Starting full development stack..."
	@echo "📋 Backend services..."
	docker-compose up -d
	@sleep 3
	@echo "📋 Frontend applications..."
	npx concurrently -p "[{name}]" -n "web,dashboard" -c "cyan,magenta" \
		"pnpm --filter=pdf-accessibility-web dev --port 3000" \
		"pnpm --filter=accesspdf-dashboard dev --port 3001"

# Stop all development services
dev-stop:
	@echo "⏹️  Stopping all development services..."
	@echo "🔻 Stopping frontend processes..."
	-@pkill -f "next dev" || true
	@echo "🔻 Stopping backend services..."
	docker-compose down
	@echo "✅ All development services stopped!"


# Follow logs from all services
dev-logs:
	@echo "📋 Following logs from all services..."
	@echo "💡 Press Ctrl+C to stop"
	docker-compose logs -f

# =============================================================================
# ONE-COMMAND LOCAL DEVELOPMENT STACK
# =============================================================================

# Start complete local development stack (MongoDB, LocalStack, API, Worker)
up:
	@echo "🚀 Starting complete local development stack..."
	@echo ""
	@echo "📦 Starting infrastructure services..."
	docker-compose up -d mongo localstack redis postgres
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo ""
	@echo "🔧 Starting application services..."
	docker-compose up -d api worker
	@echo ""
	@echo "⚙️  Starting processing functions..."
	docker-compose up -d function-router function-ocr function-structure function-tagger function-exporter function-validator function-notifier
	@echo ""
	@echo "🎉 Complete local development stack started successfully!"
	@echo ""
	@echo "🌐 Available services:"
	@echo "  🔌 API:           http://localhost:8000"
	@echo "  🗄️  MongoDB:       mongodb://localhost:27017/pdf_accessibility"
	@echo "  ☁️  LocalStack:   http://localhost:4566"
	@echo "  🧰 Redis:         redis://localhost:6379"
	@echo "  ⚙️  Functions:     Router, OCR, Structure, Tagger, Validator, Exporter, Notifier"
	@echo ""
	@echo "📋 Next steps:"
	@echo "  1. Run './venv/bin/python scripts/simple-seed.py' to add sample data"
	@echo "  2. Run 'make dev-dashboard' to start the frontend"
	@echo "  3. View data: docker exec pdf-accessibility-mongo mongosh pdf_accessibility"
	@echo ""
	@echo "💡 Dashboard processes may already be running in background - check ports 3000-3003"

# Bring down all services started with 'make up'
down:
	@echo "⏹️ Shutting down complete local development stack..."
	@echo ""
	@echo "🔻 Stopping all services (application services, functions, and infrastructure)..."
	docker-compose down
	@echo ""
	@echo "✅ All services have been stopped!"
	@echo ""
	@echo "💡 If you need to clean up volumes as well, use 'make clean' instead"

# Seed database with sample data
seed:
	@echo "🌱 Seeding database with sample data..."
	@echo "⏳ This may take a moment..."
	./venv/bin/python scripts/simple-seed.py
	@echo ""
	@echo "✅ Database seeded successfully!"
	@echo ""
	@echo "👥 Sample users created (for BetterAuth):"
	@echo "  - user_alice_developer"
	@echo "  - user_bob_designer"
	@echo "  - user_carol_admin"
	@echo "  - user_david_client"
	@echo "  - user_eve_tester"
	@echo ""
	@echo "📄 25 sample documents with realistic statuses"
	@echo "⚙️  Sample jobs with processing history"
	@echo "📁 Sample files in LocalStack S3"

# =============================================================================
# UPDATED TARGETS FOR LOCAL STACK
# =============================================================================

# Update dev target to use new infrastructure
dev:
	@echo "🏃 Starting backend services with local infrastructure..."
	docker-compose up -d mongo localstack redis api worker
	@echo ""
	@echo "✅ Backend services running:"
	@echo "  🔌 API: http://localhost:8000"
	@echo "  🗄️  MongoDB: localhost:27017"
	@echo "  ☁️  LocalStack: http://localhost:4566"
	@echo ""
	@echo "💡 Run 'make seed' to add sample data"
	@echo "💡 Run 'make dev-dashboard' to start the frontend"

# Update clean target to include new volumes
clean:
	@echo "🧹 Cleaning build artifacts and volumes..."
	docker-compose down -v
	docker volume prune -f
	rm -rf node_modules
	rm -rf */node_modules
	rm -rf **/__pycache__
	rm -rf **/dist
	rm -rf **/build
	rm -rf **/.next
	rm -rf venv
	pnpm store prune
	@echo "✅ Cleanup complete!"

# Updated status check for new services
dev-status:
	@echo "📊 Development Environment Status:"
	@echo ""
	@echo "🐳 Infrastructure Services:"
	@docker-compose ps mongo localstack redis 2>/dev/null || echo "  ❌ Infrastructure not running"
	@echo ""
	@echo "🔌 Application Services:"
	@docker-compose ps api worker 2>/dev/null || echo "  ❌ Applications not running"
	@echo ""
	@echo "📱 Frontend Services:"
	@docker-compose ps dashboard 2>/dev/null || echo "  ❌ Dashboard not running (use 'make up' or 'make dev-dashboard')"
	@echo ""
	@echo "🌐 Port Usage:"
	@echo "  Port 3000: $$(lsof -ti:3000 > /dev/null && echo "✅ In Use (Dashboard)" || echo "❌ Free")"
	@echo "  Port 8000: $$(lsof -ti:8000 > /dev/null && echo "✅ In Use (API)" || echo "❌ Free")"
	@echo "  Port 8081: $$(lsof -ti:8081 > /dev/null && echo "✅ In Use (Mongo Express)" || echo "❌ Free")"
	@echo "  Port 4566: $$(lsof -ti:4566 > /dev/null && echo "✅ In Use (LocalStack)" || echo "❌ Free")"
	@echo "  Port 27017: $$(lsof -ti:27017 > /dev/null && echo "✅ In Use (MongoDB)" || echo "❌ Free")"
	@echo ""
	@echo "🗄️  Database Status:"
	@echo -n "  MongoDB: "
	@docker exec pdf-accessibility-mongo mongosh --eval "db.runCommand('ping').ok" --quiet 2>/dev/null && echo "✅ Connected" || echo "❌ Not connected"
	@echo ""
	@echo "☁️  LocalStack Status:"
	@curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"s3": "available"' && echo "  ✅ S3 ready" || echo "  ❌ S3 not ready"
	@curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"sqs": "available"' && echo "  ✅ SQS ready" || echo "  ❌ SQS not ready"

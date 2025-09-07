.PHONY: init test test-dev build deploy clean lint format help dev dev-web dev-dashboard dev-frontend dev-full dev-stop dev-status dev-logs

# Default target
help:
	@echo "🚀 AccessPDF Development Commands:"
	@echo ""
	@echo "📋 Setup & Maintenance:"
	@echo "  init          - Initialize development environment"
	@echo "  clean         - Clean build artifacts"
	@echo ""
	@echo "🏗️  Development:"
	@echo "  dev           - Start backend services (Docker)"
	@echo "  dev-web       - Start public web app (port 3000)"
	@echo "  dev-dashboard - Start admin dashboard (port 3001)"
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

# Initialize development environment
init:
	@echo "🚀 Initializing development environment..."
	@echo "📦 Setting up Python virtual environment..."
	python3 -m venv venv
	./venv/bin/pip install -r requirements-dev.txt
	@echo "📦 Installing Node.js dependencies..."
	pnpm install
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

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	docker-compose down -v
	rm -rf node_modules
	rm -rf */node_modules
	rm -rf **/__pycache__
	rm -rf **/dist
	rm -rf **/build
	rm -rf **/.next
	rm -rf venv
	pnpm store prune
	@echo "✅ Cleanup complete!"

# Start backend services only
dev:
	@echo "🏃 Starting backend services..."
	docker-compose up -d
	@echo "✅ Backend services running on http://localhost:8080"

# Start public web app only
dev-web:
	@echo "🌐 Starting public web app..."
	pnpm --filter=web dev
	@echo "✅ Web app running on http://localhost:3000"

# Start admin dashboard only
dev-dashboard:
	@echo "📊 Starting admin dashboard..."
	pnpm --filter=accesspdf-dashboard dev
	@echo "✅ Dashboard running on http://localhost:3001"

# Start both frontend apps
dev-frontend:
	@echo "🎨 Starting both frontend applications..."
	concurrently -p "[{name}]" -n "web,dashboard" -c "cyan,magenta" \
		"pnpm --filter=web dev" \
		"pnpm --filter=accesspdf-dashboard dev"

# Start everything (backend + frontend)
dev-full:
	@echo "🚀 Starting full development stack..."
	@echo "📋 Backend services..."
	docker-compose up -d
	@sleep 3
	@echo "📋 Frontend applications..."
	concurrently -p "[{name}]" -n "web,dashboard" -c "cyan,magenta" \
		"pnpm --filter=web dev" \
		"pnpm --filter=accesspdf-dashboard dev"

# Stop all development services
dev-stop:
	@echo "⏹️  Stopping all development services..."
	@echo "🔻 Stopping frontend processes..."
	-@pkill -f "next dev" || true
	@echo "🔻 Stopping backend services..."
	docker-compose down
	@echo "✅ All development services stopped!"

# Quick status check
dev-status:
	@echo "📊 Development Environment Status:"
	@echo ""
	@echo "🐳 Docker Services:"
	@docker-compose ps
	@echo ""
	@echo "🌐 Port Usage:"
	@echo "  Port 3000: $$(lsof -ti:3000 > /dev/null && echo "✅ In Use (Web App)" || echo "❌ Free")"
	@echo "  Port 3001: $$(lsof -ti:3001 > /dev/null && echo "✅ In Use (Dashboard)" || echo "❌ Free")"
	@echo "  Port 8080: $$(lsof -ti:8080 > /dev/null && echo "✅ In Use (API)" || echo "❌ Free")"

# Follow logs from all services
dev-logs:
	@echo "📋 Following logs from all services..."
	@echo "💡 Press Ctrl+C to stop"
	docker-compose logs -f

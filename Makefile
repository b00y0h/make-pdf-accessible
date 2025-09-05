.PHONY: init test build deploy clean lint format help

# Default target
help:
	@echo "Available targets:"
	@echo "  init     - Initialize development environment"
	@echo "  test     - Run all tests"
	@echo "  build    - Build all services"
	@echo "  deploy   - Deploy to production"
	@echo "  lint     - Run linters"
	@echo "  format   - Format code"
	@echo "  clean    - Clean build artifacts"
	@echo "  dev      - Start development environment"

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

# Run all tests
test:
	@echo "🧪 Running tests..."
	docker-compose run --rm api pytest
	docker-compose run --rm worker pytest
	pnpm -r test
	@echo "✅ All tests passed!"

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

# Start development environment
dev:
	@echo "🏃 Starting development environment..."
	docker-compose up -d
	@echo "✅ Development environment running!"

# Stop development environment
dev-stop:
	@echo "⏹️  Stopping development environment..."
	docker-compose down
	@echo "✅ Development environment stopped!"

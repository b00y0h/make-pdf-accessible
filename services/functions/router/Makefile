.PHONY: test build push deploy clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  test     - Run tests"
	@echo "  build    - Build Docker image"
	@echo "  push     - Push image to ECR"
	@echo "  deploy   - Deploy to AWS"
	@echo "  clean    - Clean up"

# Variables (can be overridden)
AWS_REGION ?= us-east-1
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text)
ENVIRONMENT ?= dev
APP_NAME ?= pdf-accessibility
FUNCTION_NAME = $(APP_NAME)-$(ENVIRONMENT)-router
ECR_REPOSITORY = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(FUNCTION_NAME)
IMAGE_TAG ?= latest

# Install test dependencies and run tests
test:
	@echo "🧪 Running router function tests..."
	pip install -r requirements-test.txt
	python -m pytest tests/ -v --cov=. --cov-report=term-missing
	@echo "✅ Tests completed!"

# Run tests in Docker
test-docker:
	@echo "🐳 Running tests in Docker..."
	docker build -t $(FUNCTION_NAME)-test -f Dockerfile.test .
	docker run --rm $(FUNCTION_NAME)-test
	@echo "✅ Docker tests completed!"

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker build -t $(FUNCTION_NAME):$(IMAGE_TAG) .
	docker tag $(FUNCTION_NAME):$(IMAGE_TAG) $(ECR_REPOSITORY):$(IMAGE_TAG)
	@echo "✅ Image built: $(ECR_REPOSITORY):$(IMAGE_TAG)"

# Login to ECR and push image
push: build
	@echo "📦 Pushing image to ECR..."
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPOSITORY)
	docker push $(ECR_REPOSITORY):$(IMAGE_TAG)
	@echo "✅ Image pushed: $(ECR_REPOSITORY):$(IMAGE_TAG)"

# Update Lambda function with new image
update-function:
	@echo "🚀 Updating Lambda function..."
	aws lambda update-function-code \
		--function-name $(FUNCTION_NAME) \
		--image-uri $(ECR_REPOSITORY):$(IMAGE_TAG) \
		--region $(AWS_REGION)
	@echo "✅ Function updated: $(FUNCTION_NAME)"

# Deploy (build, push, and update function)
deploy: push update-function
	@echo "🎉 Deployment complete!"

# Test the function locally
test-local:
	@echo "🧪 Testing function locally..."
	python main.py
	@echo "✅ Local test completed!"

# Clean up local images
clean:
	@echo "🧹 Cleaning up..."
	docker rmi -f $(FUNCTION_NAME):$(IMAGE_TAG) 2>/dev/null || true
	docker rmi -f $(ECR_REPOSITORY):$(IMAGE_TAG) 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Lint code
lint:
	@echo "🔍 Linting code..."
	pip install ruff black
	ruff check .
	black --check .
	@echo "✅ Linting complete!"

# Format code
format:
	@echo "✨ Formatting code..."
	pip install ruff black
	ruff check . --fix
	black .
	@echo "✅ Formatting complete!"

# View function logs
logs:
	@echo "📋 Viewing function logs..."
	aws logs tail /aws/lambda/$(FUNCTION_NAME) --follow --region $(AWS_REGION)

# Invoke function for testing
invoke:
	@echo "🔧 Invoking function for testing..."
	aws lambda invoke \
		--function-name $(FUNCTION_NAME) \
		--payload file://test-payload.json \
		--region $(AWS_REGION) \
		response.json
	@cat response.json
	@rm response.json

# Show function status
status:
	@echo "📊 Function status:"
	aws lambda get-function --function-name $(FUNCTION_NAME) --region $(AWS_REGION) --query 'Configuration.{State:State,LastModified:LastModified,Runtime:Runtime,MemorySize:MemorySize,Timeout:Timeout}'
# Comprehensive Testing in GitHub Workflows

This document describes the comprehensive testing strategy implemented across all GitHub Actions workflows in this repository.

## Overview

All workflows now include comprehensive testing steps that cover:

- **Unit Testing**: Individual component testing with coverage reporting
- **Integration Testing**: Service interaction and database testing
- **Component Testing**: Frontend component and accessibility testing
- **Security Testing**: Infrastructure security scanning and validation
- **Quality Metrics**: Code coverage, test reporting, and quality gates

## Workflow Testing Details

### 1. API CI Workflow (`api-ci.yml`)

#### Test Suites

- **Unit Tests**: Python unit tests with pytest
  - Coverage threshold: 80%
  - HTML and XML coverage reports
  - Test result artifacts uploaded
- **Integration Tests**: Database and Redis integration
  - PostgreSQL and Redis test services
  - Real service interaction testing
- **API Endpoint Tests**: FastAPI endpoint testing
  - HTTP client testing
  - Authentication and authorization tests

#### Quality Gates

- Tests must pass before deployment
- Coverage must meet 80% threshold
- Linting (Black, Ruff, MyPy) must pass
- Test results published to GitHub

#### Test Configuration

```bash
# Run tests locally
cd services/api
pytest tests/unit/ --cov=app --cov-report=html
pytest tests/integration/ --tb=short
pytest tests/api/ --maxfail=5
```

### 2. Web CI Workflow (`web-ci.yml`)

#### Test Suites

- **Unit Tests**: Jest unit tests with coverage
  - Coverage threshold: 70% (branches, functions, lines, statements)
  - LCOV and JSON coverage reports
- **Component Tests**: React component testing
  - Testing Library for component interaction
  - Accessibility testing with jest-axe
- **Integration Tests**: Page and API route testing
- **Accessibility Tests**: WCAG compliance testing
  - Automated accessibility violation detection
  - Screen reader compatibility checks

#### Quality Gates

- All test suites must pass
- TypeScript compilation must succeed
- ESLint linting must pass
- Accessibility tests must pass

#### Test Configuration

```bash
# Run tests locally
cd web
pnpm test --coverage
pnpm test:ci  # CI mode with coverage
pnpm type-check
```

### 3. Lambda Functions Workflow (`build-and-deploy-lambda.yml`)

#### Test Suites

- **Function Tests**: Individual Lambda function testing
  - Automatic test file generation if none exist
  - AWS service mocking with moto
  - Lambda event structure validation
- **Integration Tests**: AWS service integration
  - S3, Textract, SQS service testing
  - Error handling and retry logic
- **Health Checks**: Deployed function validation
  - Post-deployment health verification
  - Function invocation testing

#### Quality Gates

- Function tests must pass before build
- Docker image build only proceeds after successful tests
- Health checks must pass after deployment

#### Test Configuration

```bash
# Run tests locally for a function
cd services/functions/ocr
pytest tests/ --cov=. --cov-report=xml
```

### 4. Infrastructure CI Workflow (`infra-ci.yml`)

#### Test Suites

- **Terraform Validation**: Configuration validation
  - Format checking with `terraform fmt`
  - Configuration validation with `terraform validate`
- **Infrastructure Testing**: Advanced Terraform testing
  - TFLint for best practices and errors
  - Checkov for security and compliance
  - Configuration pattern validation
- **Security Scanning**: Infrastructure security
  - Trivy security scanning
  - SARIF report generation
  - Vulnerability severity reporting

#### Quality Gates

- Terraform validation must pass
- Security scans must not have high-severity issues
- Infrastructure tests must pass before apply
- Plan review required for production

#### Test Configuration

```bash
# Run tests locally
cd infra/terraform
terraform fmt -check -recursive
terraform validate
tflint --init && tflint
checkov -d . --framework terraform
```

## Test Artifacts and Reporting

### Artifact Collection

All workflows collect and upload test artifacts:

- Test result XML files (JUnit format)
- Coverage reports (HTML, XML, LCOV)
- Security scan results (SARIF)
- Build artifacts and logs

### Test Reporting

- **GitHub Actions Summary**: Detailed test results in workflow summary
- **Pull Request Comments**: Terraform plan and test results
- **Security Tab**: SARIF uploads for security findings
- **Test Reporter**: JUnit test result visualization

### Coverage Reporting

- **API**: 80% minimum coverage threshold
- **Web**: 70% minimum coverage threshold
- **Lambda Functions**: Coverage tracking and reporting
- **Infrastructure**: Security and compliance coverage

## Test Environment Setup

### Database Services

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: testpass
      POSTGRES_USER: testuser
      POSTGRES_DB: testdb
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

  redis:
    image: redis:7
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### Environment Variables

Each test suite uses isolated environment variables:

- AWS credentials (mocked for testing)
- Database connection strings
- Service endpoints and configuration
- Feature flags and test-specific settings

## Local Development Testing

### Prerequisites

```bash
# Python services
pip install pytest pytest-cov pytest-asyncio httpx moto

# Web application
pnpm install
pnpm add -D @testing-library/jest-dom @testing-library/react jest-axe

# Infrastructure
curl -L "https://github.com/terraform-linters/tflint/releases/latest/download/tflint_linux_amd64.zip" -o tflint.zip
pip install checkov
```

### Running Tests Locally

```bash
# API tests
make test-api

# Web tests
make test-web

# Lambda function tests
make test-functions

# Infrastructure tests
make test-infra

# All tests
make test
```

## Continuous Integration Features

### Parallel Execution

- Matrix strategy for Lambda functions
- Concurrent test suite execution
- Optimized caching for dependencies

### Failure Handling

- Detailed error reporting
- Test result preservation on failure
- Rollback mechanisms for failed deployments

### Performance Optimization

- Dependency caching (pip, pnpm, Terraform)
- Docker layer caching
- Selective test execution based on changes

## Quality Metrics and Thresholds

### Code Coverage

- **API Services**: 80% minimum
- **Web Application**: 70% minimum
- **Lambda Functions**: Tracked and reported
- **Infrastructure**: Security compliance tracking

### Test Performance

- **Unit Tests**: < 30 seconds per suite
- **Integration Tests**: < 2 minutes per suite
- **End-to-End Tests**: < 5 minutes per suite

### Security Standards

- No high-severity security vulnerabilities
- WCAG 2.1 AA compliance for web components
- Infrastructure security best practices
- Dependency vulnerability scanning

## Troubleshooting

### Common Issues

1. **Test Timeouts**: Increase timeout values in test configuration
2. **Coverage Failures**: Review uncovered code paths
3. **Flaky Tests**: Add proper test isolation and cleanup
4. **Security Scan Failures**: Review and remediate security findings

### Debug Commands

```bash
# Verbose test output
pytest -v --tb=long

# Coverage debugging
pytest --cov-report=html --cov-report=term-missing

# Infrastructure debugging
terraform plan -detailed-exitcode
tflint --format=json
```

This comprehensive testing strategy ensures high code quality, security compliance, and reliable deployments across all components of the PDF Accessibility Platform.

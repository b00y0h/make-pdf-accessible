# Reusable GitHub Actions

This directory contains reusable GitHub Actions that provide common functionality across all workflows in the PDF Accessibility Platform. These actions implement best practices for error handling, retry logic, security scanning, and deployment validation.

## Available Actions

### 1. Setup AWS (`setup-aws`)

Configures AWS credentials using OIDC with standardized error handling and retry logic.

**Usage:**

```yaml
- name: Setup AWS credentials
  uses: ./.github/actions/setup-aws
  with:
    role_arn: ${{ secrets.AWS_ROLE_ARN }}
    aws_region: ${{ secrets.AWS_REGION }}
    service_name: 'my-service'
    max_retries: 3
    retry_delay: 5
```

**Inputs:**

- `role_arn` (required): AWS IAM role ARN to assume
- `aws_region` (required): AWS region (default: us-east-1)
- `service_name` (required): Service name for session naming
- `session_name` (optional): Custom role session name
- `max_retries` (optional): Maximum retry attempts (default: 3)
- `retry_delay` (optional): Delay between retries in seconds (default: 5)

**Outputs:**

- `aws_account_id`: AWS Account ID
- `aws_region`: AWS Region

### 2. Run Tests (`run-tests`)

Execute tests for Python or Node.js projects with coverage reporting and quality gates.

**Usage:**

```yaml
- name: Run tests
  uses: ./.github/actions/run-tests
  with:
    language: 'python'
    working_directory: 'services/api'
    coverage_threshold: '80'
```

**Inputs:**

- `language` (required): Programming language (python or nodejs)
- `working_directory` (required): Working directory for tests
- `test_command` (optional): Custom test command
- `coverage_threshold` (optional): Minimum coverage percentage (default: 80)
- `test_pattern` (optional): Test file pattern
- `install_dependencies` (optional): Whether to install dependencies (default: true)
- `requirements_file` (optional): Requirements file for Python (default: requirements.txt)
- `package_manager` (optional): Package manager for Node.js (default: pnpm)

**Outputs:**

- `test_results`: Test results summary
- `coverage_percentage`: Code coverage percentage
- `tests_passed`: Whether all tests passed

### 3. Security Scan (`security-scan`)

Comprehensive security scanning for code, dependencies, and containers.

**Usage:**

```yaml
- name: Run security scan
  uses: ./.github/actions/security-scan
  with:
    scan_type: 'dependencies'
    language: 'python'
    working_directory: 'services/api'
    fail_on_critical: true
```

**Inputs:**

- `scan_type` (required): Type of scan (code, dependencies, container, infrastructure)
- `language` (optional): Programming language (python, nodejs, terraform)
- `working_directory` (required): Working directory for scanning
- `container_image` (optional): Container image to scan (for container scans)
- `severity_threshold` (optional): Minimum severity to report (default: MEDIUM)
- `fail_on_critical` (optional): Fail on critical vulnerabilities (default: true)
- `fail_on_high` (optional): Fail on high severity vulnerabilities (default: false)

**Outputs:**

- `scan_results`: Security scan results summary
- `critical_count`: Number of critical vulnerabilities
- `high_count`: Number of high severity vulnerabilities
- `medium_count`: Number of medium severity vulnerabilities
- `scan_passed`: Whether the security scan passed

### 4. Health Check (`health-check`)

Perform health checks on deployed services with retry logic and comprehensive validation.

**Usage:**

```yaml
- name: Health check
  uses: ./.github/actions/health-check
  with:
    service_type: 'lambda'
    service_name: 'api'
    lambda_function_name: 'pdf-accessibility-prod-api'
    max_retries: 5
```

**Inputs:**

- `service_type` (required): Type of service (lambda, web, api)
- `service_name` (required): Name of the service
- `health_endpoint` (optional): Health check endpoint URL
- `lambda_function_name` (optional): Lambda function name (for lambda health checks)
- `expected_status_code` (optional): Expected HTTP status code (default: 200)
- `timeout_seconds` (optional): Timeout for each attempt (default: 30)
- `max_retries` (optional): Maximum retry attempts (default: 5)
- `retry_delay` (optional): Delay between retries (default: 10)
- `custom_validation` (optional): Custom validation script

**Outputs:**

- `health_status`: Health check status (healthy, unhealthy, unknown)
- `response_time`: Average response time in milliseconds
- `attempts_made`: Number of attempts made
- `last_error`: Last error message if health check failed

### 5. Retry with Backoff (`retry-with-backoff`)

Execute commands with retry logic and exponential backoff for improved reliability.

**Usage:**

```yaml
- name: Deploy with retry
  uses: ./.github/actions/retry-with-backoff
  with:
    command: 'aws lambda update-function-code --function-name my-function'
    max_attempts: 5
    initial_delay: 2
    success_condition: 'aws lambda get-function --function-name my-function'
```

**Inputs:**

- `command` (required): Command to execute with retry logic
- `max_attempts` (optional): Maximum number of attempts (default: 3)
- `initial_delay` (optional): Initial delay in seconds (default: 2)
- `max_delay` (optional): Maximum delay in seconds (default: 60)
- `backoff_multiplier` (optional): Backoff multiplier (default: 2)
- `timeout` (optional): Timeout for each attempt (default: 300)
- `success_condition` (optional): Command to check for success
- `failure_condition` (optional): Command to check for failure

**Outputs:**

- `success`: Whether the command succeeded
- `attempts_made`: Number of attempts made
- `total_time`: Total time taken in seconds
- `last_exit_code`: Exit code of the last attempt

### 6. Validate Configuration (`validate-config`)

Validate configuration files and environment settings with comprehensive checks.

**Usage:**

```yaml
- name: Validate Terraform config
  uses: ./.github/actions/validate-config
  with:
    config_type: 'terraform'
    config_path: 'infra/terraform'
    environment: 'prod'
    strict_mode: true
```

**Inputs:**

- `config_type` (required): Type of configuration (terraform, docker, kubernetes, env)
- `config_path` (required): Path to configuration files
- `validation_rules` (optional): Custom validation rules file
- `environment` (optional): Environment to validate against (default: dev)
- `strict_mode` (optional): Enable strict validation mode (default: false)
- `schema_file` (optional): Schema file for validation

**Outputs:**

- `validation_status`: Validation status (passed, failed, warning)
- `issues_found`: Number of issues found
- `warnings_count`: Number of warnings found
- `errors_count`: Number of errors found

### 7. Notify Deployment (`notify-deployment`)

Send deployment notifications to Slack/Teams with comprehensive details.

**Usage:**

```yaml
- name: Notify success
  uses: ./.github/actions/notify-deployment
  with:
    webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
    notification_type: 'success'
    service_name: 'api'
    environment: 'production'
    version: 'v1.2.3'
    deployment_url: 'https://api.example.com'
```

**Inputs:**

- `webhook_url` (required): Slack or Teams webhook URL
- `notification_type` (required): Type of notification (start, success, failure, approval_required, rollback, security_alert)
- `service_name` (required): Name of the service being deployed
- `environment` (required): Deployment environment
- `version` (optional): Version being deployed
- `commit_sha` (optional): Git commit SHA
- `deployment_url` (optional): URL of the deployed application
- `workflow_url` (optional): URL to the GitHub Actions workflow run
- `error_details` (optional): Error details for failure notifications
- `approval_url` (optional): URL for manual approval
- `security_event` (optional): Security event details
- `additional_context` (optional): Additional context as JSON

### 8. Security Monitor (`security-monitor`)

Monitor and alert on security events during deployments.

**Usage:**

```yaml
- name: Monitor security
  uses: ./.github/actions/security-monitor
  with:
    webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
    aws_region: 'us-east-1'
    monitoring_duration: '10'
    service_name: 'api'
```

**Inputs:**

- `webhook_url` (required): Slack or Teams webhook URL for security alerts
- `aws_region` (required): AWS region for CloudTrail monitoring (default: us-east-1)
- `monitoring_duration` (optional): Duration to monitor in minutes (default: 5)
- `service_name` (required): Name of the service being monitored

**Outputs:**

- `security_events_detected`: Number of security events detected
- `security_status`: Security monitoring status (clean, warning, alert)

## Workflow Templates

### Service Deployment Template

A comprehensive deployment template that uses multiple reusable actions:

```yaml
name: Deploy My Service
on:
  push:
    branches: [main]

jobs:
  deploy:
    uses: ./.github/workflow-templates/service-deployment.yml
    with:
      service_name: 'my-service'
      service_type: 'lambda'
      language: 'python'
      working_directory: 'services/my-service'
      environment: 'prod'
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
      AWS_REGION: ${{ secrets.AWS_REGION }}
      DEPLOYMENT_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Comprehensive CI/CD Template

A complete CI/CD pipeline with all features enabled:

```yaml
name: Full CI/CD Pipeline
on:
  push:
    branches: [main]

jobs:
  cicd:
    uses: ./.github/workflow-templates/comprehensive-ci-cd.yml
    with:
      service_name: 'my-service'
      service_type: 'api'
      language: 'python'
      working_directory: 'services/api'
      environment: 'prod'
      enable_security_monitoring: true
      enable_notifications: true
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
      AWS_REGION: ${{ secrets.AWS_REGION }}
      DEPLOYMENT_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Best Practices

### Error Handling

All actions implement comprehensive error handling:

1. **Input Validation**: All inputs are validated before execution
2. **Retry Logic**: Critical operations use exponential backoff retry
3. **Graceful Failures**: Actions fail gracefully with detailed error messages
4. **Artifact Preservation**: Results are uploaded as artifacts for debugging

### Security

Security is built into every action:

1. **Least Privilege**: AWS roles use minimal required permissions
2. **Secret Management**: Sensitive data is handled through GitHub Secrets
3. **Vulnerability Scanning**: Automated security scans for code and dependencies
4. **Audit Logging**: All operations are logged for audit purposes

### Performance

Actions are optimized for performance:

1. **Caching**: Dependencies and build artifacts are cached
2. **Parallel Execution**: Independent operations run in parallel
3. **Conditional Execution**: Actions only run when necessary
4. **Resource Optimization**: Efficient use of GitHub Actions resources

### Monitoring

Comprehensive monitoring and observability:

1. **Health Checks**: Automated validation of deployed services
2. **Security Monitoring**: Real-time security event detection
3. **Notifications**: Proactive alerts for deployment events
4. **Metrics Collection**: Performance and reliability metrics

## Troubleshooting

### Common Issues

1. **AWS Authentication Failures**
   - Verify OIDC provider configuration
   - Check IAM role trust policies
   - Ensure correct role ARN in secrets

2. **Test Failures**
   - Check test dependencies installation
   - Verify database/service connectivity
   - Review coverage thresholds

3. **Security Scan Failures**
   - Update vulnerable dependencies
   - Review and fix code security issues
   - Adjust severity thresholds if needed

4. **Deployment Failures**
   - Check AWS resource existence
   - Verify deployment permissions
   - Review health check configurations

### Getting Help

1. Check the workflow logs for detailed error messages
2. Review the uploaded artifacts for debugging information
3. Consult the troubleshooting guides in each action's documentation
4. Check the security and notification channels for alerts

## Contributing

When adding new reusable actions:

1. Follow the established patterns for input validation and error handling
2. Include comprehensive documentation and examples
3. Add appropriate test coverage
4. Implement retry logic for network operations
5. Include security scanning and validation
6. Add monitoring and notification capabilities
7. Update this README with the new action documentation

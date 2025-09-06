# Environment-Specific Deployment Strategies

This document describes the implementation of environment-specific deployment strategies for the Make PDF Accessible platform, addressing task 11 from the secure GitHub workflows specification.

## Overview

The implementation provides three distinct deployment environments with different approval requirements, security thresholds, and deployment strategies:

- **Development (dev)**: Fast iteration with minimal friction
- **Staging (staging)**: Production-like validation with automated testing
- **Production (prod)**: Maximum security with strict approval gates

## Implementation Components

### 1. Environment Configuration Files

Located in `.github/environments/`:

- `dev.yml` - Development environment configuration
- `staging.yml` - Staging environment configuration
- `prod.yml` - Production environment configuration

Each configuration file defines:

- Approval requirements
- Security thresholds
- Deployment strategies
- Branch restrictions
- Testing requirements
- Notification settings

### 2. Reusable Actions

#### Setup Environment Action (`.github/actions/setup-environment/`)

Loads and validates environment-specific configurations:

```yaml
- name: Setup environment configuration
  uses: ./.github/actions/setup-environment
  with:
    environment: ${{ inputs.environment }}
```

**Outputs:**

- `require_approval` - Whether manual approval is required
- `security_threshold` - Security scanning threshold (critical/high/medium)
- `deployment_strategy` - Deployment strategy (rolling/blue_green)
- `resource_prefix` - AWS resource naming prefix
- `allowed_branches` - Branches allowed to deploy to this environment

#### Environment Gate Action (`.github/actions/environment-gate/`)

Enforces environment-specific deployment gates:

```yaml
- name: Run environment gate
  uses: ./.github/actions/environment-gate
  with:
    environment: ${{ inputs.environment }}
    require_approval: ${{ needs.setup-environment.outputs.require_approval }}
    security_threshold: ${{ needs.setup-environment.outputs.security_threshold }}
    deployment_type: 'api'
    security_results: ${{ steps.security-scan.outputs.results }}
```

**Features:**

- Security vulnerability threshold enforcement
- Branch permission validation
- Deployment time window checks (production)
- Approval requirement determination

### 3. Updated Workflows

All main deployment workflows have been updated to use environment-specific configurations:

#### Infrastructure CI (`infra-ci.yml`)

- Added environment setup job
- Added environment gate validation
- Dynamic environment naming for GitHub environments
- Environment-specific approval requirements

#### API CI (`api-ci.yml`)

- Environment-specific security thresholds
- Dynamic blue/green deployment strategy
- Environment-aware resource naming
- Conditional approval gates

#### Web CI (`web-ci.yml`)

- Environment-specific build configurations
- Dynamic S3 bucket and CloudFront targeting
- Environment-aware caching strategies
- Conditional deployment validation

#### Lambda Deployment (`build-and-deploy-lambda.yml`)

- Environment-specific container configurations
- Dynamic ECR repository targeting
- Environment-aware Lambda function naming
- Conditional security scanning

### 4. Branch Protection and Environment Setup

#### Branch Protection Script (`.github/scripts/setup-branch-protection.sh`)

Automated script to configure GitHub branch protection rules:

```bash
# Run the setup script
chmod +x .github/scripts/setup-branch-protection.sh
GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }} ./.github/scripts/setup-branch-protection.sh
```

**Features:**

- Main branch protection with required status checks
- Develop branch protection (if exists)
- GitHub environment creation with appropriate reviewers
- Repository rulesets for deployment validation

#### GitHub Environments

The script creates three GitHub environments:

1. **Development**
   - No approval required
   - Flexible branch deployment
   - Immediate deployment

2. **Staging**
   - Platform team approval required
   - Protected branches only
   - Automated testing validation

3. **Production**
   - Multi-team approval required (platform + security)
   - Main branch only
   - Extended validation and monitoring

### 5. Testing and Validation

#### Environment Configuration Test (`test-environment-config.yml`)

Comprehensive test workflow to validate environment configurations:

```yaml
# Test specific environment
gh workflow run test-environment-config.yml \
-f test_environment=prod \
-f test_branch=main
```

**Test Coverage:**

- Environment configuration loading
- Environment gate validation
- Branch permission enforcement
- Security threshold behavior
- Multi-scenario security testing

## Environment-Specific Behaviors

### Development Environment

**Characteristics:**

- ✅ No manual approval required
- ✅ Allows medium severity vulnerabilities
- ✅ Supports feature branch deployments
- ✅ Fast deployment with minimal validation
- ✅ Automatic rollback on failure

**Branch Permissions:**

- `main`, `develop`, `feature/*`, `hotfix/*`

**Security Threshold:** Medium

- Blocks: Critical vulnerabilities
- Allows: High, Medium, Low vulnerabilities

**Deployment Strategy:** Rolling deployment

### Staging Environment

**Characteristics:**

- ⏳ Manual approval for infrastructure changes
- 🔒 Blocks high severity vulnerabilities
- 🧪 Full test suite including E2E tests
- 🔄 Blue/green deployment strategy
- 📊 Load testing and performance validation

**Branch Permissions:**

- `main`, `release/*`

**Security Threshold:** High

- Blocks: Critical, High vulnerabilities
- Allows: Medium, Low vulnerabilities

**Deployment Strategy:** Blue/green deployment

### Production Environment

**Characteristics:**

- 🔒 Manual approval required for ALL deployments
- 🛡️ Blocks any critical/high severity vulnerabilities
- 👥 Multiple reviewer approval required
- ⏰ Business hours deployment window (09:00-17:00 UTC)
- 🔄 Blue/green deployment with gradual traffic shift

**Branch Permissions:**

- `main` only, Git tags matching `v*`

**Security Threshold:** Critical

- Blocks: Critical, High vulnerabilities
- Allows: Medium, Low vulnerabilities (with warnings)

**Deployment Strategy:** Blue/green with gradual traffic shifting

## Configuration Examples

### Environment-Specific Resource Naming

```yaml
# Development
resource_prefix: "pdf-accessibility-dev"
lambda_function: "pdf-accessibility-dev-api"
s3_bucket: "pdf-accessibility-dev-web-assets"

# Staging
resource_prefix: "pdf-accessibility-staging"
lambda_function: "pdf-accessibility-staging-api"
s3_bucket: "pdf-accessibility-staging-web-assets"

# Production
resource_prefix: "pdf-accessibility-prod"
lambda_function: "pdf-accessibility-prod-api"
s3_bucket: "pdf-accessibility-prod-web-assets"
```

### Security Threshold Examples

```yaml
# Development - Relaxed
security_threshold: "medium"
# Allows: High (5), Medium (unlimited), Low (unlimited)
# Blocks: Critical (any)

# Staging - Balanced
security_threshold: "high"
# Allows: Medium (unlimited), Low (unlimited)
# Blocks: Critical (any), High (any)

# Production - Strict
security_threshold: "critical"
# Allows: Medium (with warnings), Low (with warnings)
# Blocks: Critical (any), High (any)
```

### Approval Configuration Examples

```yaml
# Development
require_approval: false
reviewers: []

# Staging
require_approval: true  # Infrastructure only
reviewers:
  - team: "platform-team"
    count: 1

# Production
require_approval: true  # All deployments
reviewers:
  - team: "platform-team"
    count: 1
  - team: "security-team"
    count: 1
timeout: "24h"
```

## Usage Examples

### Manual Deployment to Specific Environment

```bash
# Deploy to development
gh workflow run infra-ci.yml -f environment=dev

# Deploy to staging with approval
gh workflow run api-ci.yml -f environment=staging

# Deploy to production (requires approval)
gh workflow run web-ci.yml -f environment=prod
```

### Emergency Deployment

```bash
# Emergency deployment (bypasses some checks for non-prod)
gh workflow run api-ci.yml \
  -f environment=staging \
  -f emergency_deployment=true
```

### Testing Environment Configuration

```bash
# Test production environment configuration
gh workflow run test-environment-config.yml \
  -f test_environment=prod \
  -f test_branch=main

# Test staging with feature branch (should fail)
gh workflow run test-environment-config.yml \
  -f test_environment=staging \
  -f test_branch=feature/new-feature
```

## Monitoring and Alerting

### Environment-Specific Notifications

Each environment has different notification configurations:

```yaml
# Development
notifications:
  on_success: false
  on_failure: true
  slack_channel: "#dev-deployments"

# Staging
notifications:
  on_success: true
  on_failure: true
  on_start: true
  slack_channel: "#staging-deployments"

# Production
notifications:
  on_success: true
  on_failure: true
  on_start: true
  on_approval_required: true
  slack_channel: "#prod-alerts"
  email_notifications: true
  pagerduty_integration: true
```

### Deployment Metrics

Track environment-specific metrics:

- **Deployment Frequency**: Deployments per environment per day
- **Lead Time**: Time from commit to production deployment
- **Failure Rate**: Percentage of failed deployments by environment
- **Recovery Time**: Time to recover from deployment failures
- **Approval Time**: Time from deployment request to approval

## Security Considerations

### Environment Isolation

Each environment uses separate:

- AWS accounts or resource prefixes
- GitHub environments with different approval requirements
- Secrets and configuration values
- Monitoring and alerting channels

### Access Control

- **Development**: Open access for developers
- **Staging**: Platform team approval required
- **Production**: Multi-team approval with security review

### Audit Trail

All deployments are logged with:

- Environment target
- Approval chain
- Security scan results
- Deployment outcome
- Rollback events (if any)

## Troubleshooting

### Common Issues

#### Environment Configuration Not Loading

```bash
# Check configuration file syntax
yq eval '.settings.require_approval' .github/environments/prod.yml

# Validate YAML structure
yamllint .github/environments/
```

#### Branch Not Allowed for Environment

```bash
# Check allowed branches for environment
yq eval '.settings.allowed_branches' .github/environments/prod.yml

# Switch to allowed branch
git checkout main
```

#### Security Gate Blocking Deployment

```bash
# Check security scan results
cat security-scan-results.json | jq '.vulnerabilities[]'

# Review security threshold
yq eval '.settings.security_threshold' .github/environments/prod.yml
```

#### Approval Timeout

```bash
# Check approval status
gh run view <run-id>

# Request approval
gh pr review <pr-number> --approve
```

### Support and Documentation

- **Configuration Guide**: `.github/workflows/ENVIRONMENT_DEPLOYMENT_GUIDE.md`
- **Setup Script**: `.github/scripts/setup-branch-protection.sh`
- **Test Workflow**: `.github/workflows/test-environment-config.yml`
- **Support Channel**: #platform-support

## Requirements Compliance

This implementation addresses the following requirements from the specification:

### Requirement 1.2

✅ **Manual approval before applying Terraform changes**

- Production environment requires manual approval for all infrastructure deployments
- Staging environment requires approval for infrastructure changes
- Development environment allows automatic deployment

### Requirement 4.3

✅ **Blue/green deployment via Lambda aliases**

- Environment-specific deployment strategies configured
- Production uses blue/green with gradual traffic shifting
- Staging uses standard blue/green deployment
- Development uses rolling deployment for speed

### Requirement 5.2

✅ **Least-privilege principles for each workflow**

- Environment-specific IAM role configuration
- Resource prefix isolation between environments
- Different security thresholds per environment
- Branch-based access restrictions

## Future Enhancements

### Planned Improvements

1. **Dynamic Environment Creation**
   - Support for ephemeral environments
   - PR-based environment provisioning
   - Automatic cleanup of unused environments

2. **Advanced Approval Workflows**
   - Time-based approval windows
   - Escalation policies
   - Emergency override procedures

3. **Enhanced Monitoring**
   - Real-time deployment dashboards
   - Performance impact tracking
   - Automated rollback triggers

4. **Compliance Integration**
   - SOC 2 compliance reporting
   - Audit log integration
   - Change management workflows

### Contributing

To contribute to the environment-specific deployment strategies:

1. Review the current configuration files
2. Test changes using the test workflow
3. Update documentation as needed
4. Submit PR with environment impact assessment

For questions or support, contact the platform team via #platform-support.

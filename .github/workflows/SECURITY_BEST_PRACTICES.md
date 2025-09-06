# Security Best Practices for GitHub Actions CI/CD

This document outlines security best practices for implementing and maintaining secure CI/CD workflows with GitHub Actions and AWS OIDC integration.

## OIDC Security Configuration

### Trust Policy Best Practices

#### 1. Repository Restriction

Always restrict OIDC access to specific repositories:

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:your-org/your-repo:*"
  }
}
```

#### 2. Branch Restriction

Limit access to specific branches for production deployments:

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:your-org/your-repo:ref:refs/heads/main",
      "repo:your-org/your-repo:ref:refs/heads/release/*"
    ]
  }
}
```

#### 3. Environment-Specific Restrictions

Use different roles for different environments:

```json
{
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:environment": "production"
  }
}
```

### Session Duration Limits

Set appropriate session duration for each role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "NumericLessThan": {
          "aws:TokenIssueTime": "3600"
        }
      }
    }
  ]
}
```

## IAM Least Privilege Principles

### Infrastructure Role Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "s3:*",
        "lambda:*",
        "iam:PassRole",
        "cloudformation:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    }
  ]
}
```

### Lambda Deployment Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:PublishVersion",
        "lambda:UpdateAlias",
        "lambda:GetFunction",
        "lambda:ListVersionsByFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:pdf-accessibility-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": ["arn:aws:ecr:*:*:repository/pdf-accessibility/*"]
    }
  ]
}
```

### Web Deployment Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::pdf-accessibility-*-web",
        "arn:aws:s3:::pdf-accessibility-*-web/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "arn:aws:cloudfront::*:distribution/*"
    }
  ]
}
```

## Secrets Management Security

### Secret Naming Conventions

1. **Environment Prefixes**: Use environment-specific prefixes
   - `PROD_DATABASE_URL`
   - `STAGING_DATABASE_URL`
   - `DEV_DATABASE_URL`

2. **Service Prefixes**: Group secrets by service
   - `API_DATABASE_URL`
   - `WORKER_REDIS_URL`
   - `WEB_CDN_URL`

3. **Avoid Generic Names**: Don't use generic names like `PASSWORD` or `KEY`

### Secret Rotation Strategy

```yaml
# Example rotation workflow
name: Rotate Secrets
on:
  schedule:
    - cron: '0 2 1 * *' # Monthly rotation
  workflow_dispatch:

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Rotate API Keys
        run: |
          # Generate new API key
          NEW_KEY=$(openssl rand -hex 32)

          # Update in AWS Secrets Manager
          aws secretsmanager update-secret \
            --secret-id prod/api-key \
            --secret-string "$NEW_KEY"

          # Update GitHub secret
          gh secret set API_KEY --body "$NEW_KEY"
```

### Secret Validation

```yaml
# Validate secrets before deployment
- name: Validate Required Secrets
  run: |
    required_secrets=(
      "AWS_ACCOUNT_ID"
      "AWS_REGION"
      "DATABASE_URL"
    )

    for secret in "${required_secrets[@]}"; do
      if [ -z "${!secret}" ]; then
        echo "❌ Missing required secret: $secret"
        exit 1
      fi
    done
  env:
    AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
    AWS_REGION: ${{ secrets.AWS_REGION }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## Workflow Security

### Permissions Configuration

Always use minimal permissions in workflows:

```yaml
permissions:
  id-token: write # Required for OIDC
  contents: read # Required to checkout code
  pull-requests: write # Only if posting PR comments
  actions: read # Only if reading workflow artifacts
```

### Input Validation

Validate all workflow inputs:

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        type: choice
        options: ['dev', 'staging', 'prod']
      version:
        description: 'Version to deploy'
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Validate inputs
        run: |
          # Validate environment
          if [[ ! "${{ inputs.environment }}" =~ ^(dev|staging|prod)$ ]]; then
            echo "Invalid environment: ${{ inputs.environment }}"
            exit 1
          fi

          # Validate version format
          if [[ ! "${{ inputs.version }}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Invalid version format: ${{ inputs.version }}"
            exit 1
          fi
```

### Environment Protection

Configure environment protection rules:

1. **Required Reviewers**: Require manual approval for production
2. **Wait Timer**: Add delay before deployment
3. **Branch Restrictions**: Limit deployments to specific branches

```yaml
# Example environment configuration
environment:
  name: production
  url: https://api.pdfaccessibility.com
```

## Container Security

### Base Image Security

Use minimal, security-hardened base images:

```dockerfile
# Use specific version tags, not 'latest'
FROM python:3.11-slim-bullseye

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER appuser
```

### Vulnerability Scanning

Implement container vulnerability scanning:

```yaml
- name: Scan container image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.ECR_REGISTRY }}/pdf-accessibility/api:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy scan results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

### Image Signing

Sign container images for integrity verification:

```yaml
- name: Sign container image
  uses: sigstore/cosign-installer@v3

- name: Sign the published Docker image
  run: |
    cosign sign --yes ${{ env.ECR_REGISTRY }}/pdf-accessibility/api:${{ github.sha }}
  env:
    COSIGN_EXPERIMENTAL: 1
```

## Monitoring and Alerting

### Security Event Monitoring

Monitor for security-relevant events:

```yaml
- name: Log security event
  if: failure()
  run: |
    curl -X POST "${{ secrets.SECURITY_WEBHOOK_URL }}" \
      -H "Content-Type: application/json" \
      -d '{
        "event": "deployment_failure",
        "repository": "${{ github.repository }}",
        "workflow": "${{ github.workflow }}",
        "run_id": "${{ github.run_id }}",
        "actor": "${{ github.actor }}",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
      }'
```

### Audit Logging

Enable comprehensive audit logging:

```yaml
- name: Audit log
  run: |
    echo "AUDIT: Deployment started" >> audit.log
    echo "Repository: ${{ github.repository }}" >> audit.log
    echo "Actor: ${{ github.actor }}" >> audit.log
    echo "Commit: ${{ github.sha }}" >> audit.log
    echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> audit.log

    # Send to centralized logging
    aws logs put-log-events \
      --log-group-name "/github-actions/audit" \
      --log-stream-name "${{ github.repository }}" \
      --log-events timestamp=$(date +%s000),message="$(cat audit.log)"
```

## Compliance and Governance

### Policy as Code

Implement policy as code using tools like OPA:

```yaml
- name: Policy validation
  uses: open-policy-agent/opa-action@v2
  with:
    policy: policies/deployment.rego
    input: deployment-config.json
```

### Compliance Scanning

Scan for compliance violations:

```yaml
- name: Compliance scan
  run: |
    # Check for hardcoded secrets
    truffleHog --regex --entropy=False .

    # Check for security misconfigurations
    checkov -f Dockerfile --framework dockerfile

    # Check Terraform for compliance
    checkov -d infra/terraform --framework terraform
```

### Documentation Requirements

Maintain security documentation:

1. **Security Architecture**: Document security controls and boundaries
2. **Incident Response**: Define procedures for security incidents
3. **Access Control**: Document who has access to what resources
4. **Change Management**: Track and approve security-relevant changes

## Incident Response

### Automated Response

Implement automated incident response:

```yaml
- name: Security incident response
  if: failure()
  run: |
    # Disable compromised resources
    aws lambda put-function-concurrency \
      --function-name pdf-accessibility-api \
      --reserved-concurrent-executions 0

    # Notify security team
    curl -X POST "${{ secrets.SECURITY_ALERT_WEBHOOK }}" \
      -H "Content-Type: application/json" \
      -d '{
        "severity": "high",
        "event": "deployment_security_failure",
        "details": "${{ github.event.head_commit.message }}"
      }'
```

### Recovery Procedures

Document and automate recovery procedures:

```yaml
- name: Emergency rollback
  if: inputs.emergency_rollback == 'true'
  run: |
    # Rollback to last known good version
    aws lambda update-alias \
      --function-name pdf-accessibility-api \
      --name LIVE \
      --function-version ${{ secrets.LAST_KNOWN_GOOD_VERSION }}

    # Clear caches
    aws cloudfront create-invalidation \
      --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
      --paths "/*"
```

## Regular Security Reviews

### Automated Security Audits

Schedule regular security audits:

```yaml
name: Security Audit
on:
  schedule:
    - cron: '0 2 * * 1' # Weekly on Monday

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: IAM policy review
        run: |
          # Check for overly permissive policies
          aws iam list-roles --query 'Roles[?contains(RoleName, `GitHubActions`)]'

      - name: Secret age check
        run: |
          # Check for old secrets that need rotation
          gh secret list --json name,updated_at
```

### Security Metrics

Track security metrics:

- Failed authentication attempts
- Policy violations
- Vulnerability scan results
- Secret rotation compliance
- Incident response times

## Training and Awareness

### Developer Security Training

Ensure team members understand:

1. **OIDC Concepts**: How OIDC authentication works
2. **IAM Best Practices**: Least privilege principles
3. **Secret Management**: Proper handling of sensitive data
4. **Incident Response**: What to do when security issues arise

### Security Champions Program

Designate security champions who:

1. Review security configurations
2. Conduct security training
3. Stay updated on security best practices
4. Lead incident response efforts

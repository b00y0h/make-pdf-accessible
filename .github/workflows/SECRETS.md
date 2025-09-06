# GitHub Secrets Configuration Guide

This document outlines all required GitHub Secrets for the CI/CD workflows and their purposes.

## Repository Secrets

These secrets are required at the repository level and used across all workflows.

### AWS Configuration

| Secret Name           | Purpose                                | Example Value                                                 | Required |
| --------------------- | -------------------------------------- | ------------------------------------------------------------- | -------- |
| `AWS_ACCOUNT_ID`      | AWS account identifier                 | `123456789012`                                                | ✅       |
| `AWS_REGION`          | Primary AWS region                     | `us-east-1`                                                   | ✅       |
| `AWS_ROLE_ARN_INFRA`  | IAM role for infrastructure deployment | `arn:aws:iam::123456789012:role/GitHubActions-Infrastructure` | ✅       |
| `AWS_ROLE_ARN_LAMBDA` | IAM role for Lambda deployment         | `arn:aws:iam::123456789012:role/GitHubActions-Lambda`         | ✅       |
| `AWS_ROLE_ARN_WEB`    | IAM role for web deployment            | `arn:aws:iam::123456789012:role/GitHubActions-Web`            | ✅       |
| `AWS_ROLE_ARN_API`    | IAM role for API deployment            | `arn:aws:iam::123456789012:role/GitHubActions-API`            | ✅       |

### Infrastructure Secrets

| Secret Name                | Purpose                       | Example Value                       | Required |
| -------------------------- | ----------------------------- | ----------------------------------- | -------- |
| `TERRAFORM_BACKEND_BUCKET` | S3 bucket for Terraform state | `pdf-accessibility-terraform-state` | ✅       |
| `TERRAFORM_BACKEND_KEY`    | S3 key for state file         | `terraform.tfstate`                 | ✅       |
| `TERRAFORM_BACKEND_REGION` | Region for state bucket       | `us-east-1`                         | ✅       |

### Container Registry

| Secret Name    | Purpose          | Example Value                                  | Required |
| -------------- | ---------------- | ---------------------------------------------- | -------- |
| `ECR_REGISTRY` | ECR registry URL | `123456789012.dkr.ecr.us-east-1.amazonaws.com` | ✅       |

### Web Deployment

| Secret Name                       | Purpose                             | Example Value                | Required |
| --------------------------------- | ----------------------------------- | ---------------------------- | -------- |
| `S3_BUCKET_WEB_PROD`              | Production web assets bucket        | `pdf-accessibility-prod-web` | ✅       |
| `S3_BUCKET_WEB_DEV`               | Development web assets bucket       | `pdf-accessibility-dev-web`  | ✅       |
| `CLOUDFRONT_DISTRIBUTION_ID_PROD` | Production CloudFront distribution  | `E1234567890123`             | ✅       |
| `CLOUDFRONT_DISTRIBUTION_ID_DEV`  | Development CloudFront distribution | `E0987654321098`             | ✅       |

### Notification Configuration

| Secret Name           | Purpose                       | Example Value                            | Required |
| --------------------- | ----------------------------- | ---------------------------------------- | -------- |
| `SLACK_WEBHOOK_URL`   | Slack notifications webhook   | `https://hooks.slack.com/services/...`   | ⚠️       |
| `TEAMS_WEBHOOK_URL`   | Microsoft Teams webhook       | `https://outlook.office.com/webhook/...` | ⚠️       |
| `DISCORD_WEBHOOK_URL` | Discord notifications webhook | `https://discord.com/api/webhooks/...`   | ⚠️       |

### Monitoring and Observability

| Secret Name             | Purpose                        | Example Value                              | Required |
| ----------------------- | ------------------------------ | ------------------------------------------ | -------- |
| `DATADOG_API_KEY`       | Datadog monitoring integration | `abcd1234efgh5678ijkl9012mnop3456`         | ⚠️       |
| `NEW_RELIC_LICENSE_KEY` | New Relic monitoring           | `eu01xx66c4b8b5b4e5c7d8e9f0a1b2c3d4e5f6g7` | ⚠️       |

## Environment-Specific Secrets

Configure these secrets for each environment (development, staging, production).

### Development Environment

```yaml
# Environment: development
AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN_DEV }}
S3_BUCKET_WEB: ${{ secrets.S3_BUCKET_WEB_DEV }}
CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID_DEV }}
DATABASE_URL: ${{ secrets.DATABASE_URL_DEV }}
REDIS_URL: ${{ secrets.REDIS_URL_DEV }}
```

### Staging Environment

```yaml
# Environment: staging
AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN_STAGING }}
S3_BUCKET_WEB: ${{ secrets.S3_BUCKET_WEB_STAGING }}
CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID_STAGING }}
DATABASE_URL: ${{ secrets.DATABASE_URL_STAGING }}
REDIS_URL: ${{ secrets.REDIS_URL_STAGING }}
```

### Production Environment

```yaml
# Environment: production
AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN_PROD }}
S3_BUCKET_WEB: ${{ secrets.S3_BUCKET_WEB_PROD }}
CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID_PROD }}
DATABASE_URL: ${{ secrets.DATABASE_URL_PROD }}
REDIS_URL: ${{ secrets.REDIS_URL_PROD }}
```

## Setting Up Secrets

### Via GitHub Web Interface

1. Navigate to your repository on GitHub
2. Click on **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter the secret name and value
6. Click **Add secret**

### Via GitHub CLI

```bash
# Set repository secret
gh secret set SECRET_NAME --body "secret_value"

# Set environment secret
gh secret set SECRET_NAME --env production --body "secret_value"

# Set secret from file
gh secret set SECRET_NAME < secret_file.txt
```

### Bulk Secret Setup Script

```bash
#!/bin/bash
# setup-secrets.sh

# AWS Configuration
gh secret set AWS_ACCOUNT_ID --body "123456789012"
gh secret set AWS_REGION --body "us-east-1"

# IAM Roles
gh secret set AWS_ROLE_ARN_INFRA --body "arn:aws:iam::123456789012:role/GitHubActions-Infrastructure"
gh secret set AWS_ROLE_ARN_LAMBDA --body "arn:aws:iam::123456789012:role/GitHubActions-Lambda"
gh secret set AWS_ROLE_ARN_WEB --body "arn:aws:iam::123456789012:role/GitHubActions-Web"
gh secret set AWS_ROLE_ARN_API --body "arn:aws:iam::123456789012:role/GitHubActions-API"

# Infrastructure
gh secret set TERRAFORM_BACKEND_BUCKET --body "pdf-accessibility-terraform-state"
gh secret set ECR_REGISTRY --body "123456789012.dkr.ecr.us-east-1.amazonaws.com"

# Web Deployment
gh secret set S3_BUCKET_WEB_PROD --body "pdf-accessibility-prod-web"
gh secret set S3_BUCKET_WEB_DEV --body "pdf-accessibility-dev-web"
gh secret set CLOUDFRONT_DISTRIBUTION_ID_PROD --body "E1234567890123"
gh secret set CLOUDFRONT_DISTRIBUTION_ID_DEV --body "E0987654321098"

echo "✅ All secrets configured successfully"
```

## Secret Validation

### Validation Workflow

Create a workflow to validate all required secrets are configured:

```yaml
name: Validate Secrets
on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 0' # Weekly validation

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate AWS secrets
        run: |
          secrets=(
            "AWS_ACCOUNT_ID"
            "AWS_REGION"
            "AWS_ROLE_ARN_INFRA"
            "AWS_ROLE_ARN_LAMBDA"
            "AWS_ROLE_ARN_WEB"
            "AWS_ROLE_ARN_API"
          )

          for secret in "${secrets[@]}"; do
            if [ -z "${!secret}" ]; then
              echo "❌ Missing required secret: $secret"
              exit 1
            else
              echo "✅ Secret configured: $secret"
            fi
          done
        env:
          AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
          AWS_REGION: ${{ secrets.AWS_REGION }}
          AWS_ROLE_ARN_INFRA: ${{ secrets.AWS_ROLE_ARN_INFRA }}
          AWS_ROLE_ARN_LAMBDA: ${{ secrets.AWS_ROLE_ARN_LAMBDA }}
          AWS_ROLE_ARN_WEB: ${{ secrets.AWS_ROLE_ARN_WEB }}
          AWS_ROLE_ARN_API: ${{ secrets.AWS_ROLE_ARN_API }}
```

## Security Best Practices

### Secret Management

1. **Rotation**: Regularly rotate secrets, especially API keys
2. **Least Privilege**: Use environment-specific secrets where possible
3. **Monitoring**: Monitor secret usage and access patterns
4. **Backup**: Maintain secure backups of critical secrets

### Access Control

1. **Environment Protection**: Use environment protection rules for production
2. **Required Reviewers**: Require manual approval for production deployments
3. **Branch Protection**: Restrict secret access to specific branches
4. **Audit Logs**: Regularly review secret access logs

### Secret Naming Conventions

- Use UPPER_SNAKE_CASE for all secret names
- Include environment suffix for environment-specific secrets
- Use descriptive names that indicate purpose
- Group related secrets with common prefixes

## Troubleshooting

### Common Issues

1. **Secret Not Found**: Verify secret name matches exactly (case-sensitive)
2. **Permission Denied**: Check environment protection rules and required reviewers
3. **Invalid Role ARN**: Verify IAM role exists and trust policy is correct
4. **Region Mismatch**: Ensure AWS_REGION matches resource regions

### Debugging Commands

```bash
# List all repository secrets
gh secret list

# Check secret in workflow
- name: Debug secrets
  run: |
    echo "AWS Account: ${{ secrets.AWS_ACCOUNT_ID }}"
    echo "Region: ${{ secrets.AWS_REGION }}"
    # Never echo actual secret values in logs!
```

## Migration Guide

### From AWS Credentials to OIDC

If migrating from stored AWS credentials:

1. Remove old `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets
2. Set up OIDC provider and IAM roles (see IAM_SETUP.md)
3. Update workflows to use `aws-actions/configure-aws-credentials@v4`
4. Test authentication with a simple workflow
5. Update all workflows to use new authentication method

### Environment Migration

When adding new environments:

1. Create environment in GitHub repository settings
2. Configure environment-specific secrets
3. Set up protection rules and required reviewers
4. Update workflows to reference new environment
5. Test deployment to new environment

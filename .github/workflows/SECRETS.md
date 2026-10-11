# GitHub Secrets Configuration Guide

This document outlines all required GitHub Secrets for the CI/CD workflows and their purposes.

## Repository Secrets

These secrets are set at the repository level.

### AWS Configuration

The AWS secrets (`AWS_REGION`, `AWS_ACCOUNT_ID` and the role ARNs `AWS_INFRASTRUCTURE_CI_ROLE_ARN`, `AWS_INFRASTRUCTURE_PLAN_ROLE_ARN`, `AWS_LAMBDA_DEPLOY_ROLE_ARN`, `AWS_API_DEPLOY_ROLE_ARN` and `AWS_WEB_DEPLOY_ROLE_ARN`) are listed in one place, [GITHUB_OIDC_SETUP.md](../../infra/terraform/GITHUB_OIDC_SETUP.md#3-configure-github-secrets), with the jobs that read each one and whether it belongs on the repository, on a GitHub environment, or on both. Not all of them are repository secrets: `AWS_WEB_DEPLOY_ROLE_ARN` is set only on the `<env>-web` environments.

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

The deploy jobs run in GitHub environments named `<env>-infrastructure` (`infra-ci.yml`), `<env>-api` (`api-ci.yml`) and `<env>-web` (`web-ci.yml`, `marketing-site.yml`), where `<env>` is `dev`, `staging` or `prod`. Each environment holds its own role ARN under the same secret name as everywhere else; the environment, not a name suffix, selects the value. Which role secret goes on which environment is listed in [GITHUB_OIDC_SETUP.md](../../infra/terraform/GITHUB_OIDC_SETUP.md#3-configure-github-secrets).

A job sees an environment's secrets only if it declares that environment. Jobs without one, such as `terraform-plan` in `infra-ci.yml` and every job in `build-and-deploy-lambda.yml`, read repository secrets only.

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

# IAM roles, from each environment's `terraform output github_actions_roles_summary`.
# Scopes: infra/terraform/GITHUB_OIDC_SETUP.md. DEV_ACCOUNT_ID holds dev and staging.

# Repository secrets, for jobs that declare no environment
gh secret set AWS_INFRASTRUCTURE_CI_ROLE_ARN --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-infra-ci-role"
# AWS_INFRASTRUCTURE_PLAN_ROLE_ARN: a read-only plan role that no Terraform defines yet; see GITHUB_OIDC_SETUP.md
gh secret set AWS_LAMBDA_DEPLOY_ROLE_ARN --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-lambda-deploy-role"
gh secret set AWS_API_DEPLOY_ROLE_ARN --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-api-deploy-role"

# Environment secrets, for jobs that declare that environment
gh secret set AWS_INFRASTRUCTURE_CI_ROLE_ARN --env dev-infrastructure --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-infra-ci-role"
gh secret set AWS_INFRASTRUCTURE_CI_ROLE_ARN --env staging-infrastructure --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-staging-github-infra-ci-role"
gh secret set AWS_INFRASTRUCTURE_CI_ROLE_ARN --env prod-infrastructure --body "arn:aws:iam::PROD_ACCOUNT_ID:role/pdf-accessibility-prod-github-infra-ci-role"
gh secret set AWS_API_DEPLOY_ROLE_ARN --env dev-api --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-api-deploy-role"
gh secret set AWS_API_DEPLOY_ROLE_ARN --env staging-api --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-staging-github-api-deploy-role"
gh secret set AWS_API_DEPLOY_ROLE_ARN --env prod-api --body "arn:aws:iam::PROD_ACCOUNT_ID:role/pdf-accessibility-prod-github-api-deploy-role"
gh secret set AWS_WEB_DEPLOY_ROLE_ARN --env dev-web --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-web-deploy-role"
gh secret set AWS_WEB_DEPLOY_ROLE_ARN --env staging-web --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-staging-github-web-deploy-role"
gh secret set AWS_WEB_DEPLOY_ROLE_ARN --env prod-web --body "arn:aws:iam::PROD_ACCOUNT_ID:role/pdf-accessibility-prod-github-web-deploy-role"

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

Create a workflow to validate that the repository-level secrets are configured:

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
            "AWS_INFRASTRUCTURE_CI_ROLE_ARN"
            "AWS_LAMBDA_DEPLOY_ROLE_ARN"
            "AWS_API_DEPLOY_ROLE_ARN"
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
          AWS_INFRASTRUCTURE_CI_ROLE_ARN: ${{ secrets.AWS_INFRASTRUCTURE_CI_ROLE_ARN }}
          AWS_LAMBDA_DEPLOY_ROLE_ARN: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
          AWS_API_DEPLOY_ROLE_ARN: ${{ secrets.AWS_API_DEPLOY_ROLE_ARN }}
```

This job declares no environment, so it cannot see environment secrets such as `AWS_WEB_DEPLOY_ROLE_ARN` or the `<env>-api` copies of `AWS_API_DEPLOY_ROLE_ARN`. A job that declared `prod-web` to check them would also wait on that environment's reviewers, so check environment secrets with `gh secret list --env <name>` instead.

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
- Do not start a name with `GITHUB_`; GitHub rejects such secret names
- Use the same name on every environment that needs a secret; the environment, not a name suffix, selects the value
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

# List one environment's secrets
gh secret list --env prod-infrastructure

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
2. Set up the OIDC provider and IAM roles with Terraform (see `infra/terraform/GITHUB_OIDC_SETUP.md`)
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

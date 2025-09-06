# IAM Setup Guide for GitHub Actions OIDC

This guide provides step-by-step instructions for setting up AWS IAM roles and GitHub OIDC integration for secure CI/CD workflows.

## Overview

GitHub Actions uses OpenID Connect (OIDC) to authenticate with AWS without storing long-lived credentials. This approach provides enhanced security by using short-lived tokens that are automatically rotated.

## Prerequisites

- AWS CLI configured with administrative permissions
- GitHub repository with Actions enabled
- Terraform installed (for automated setup)

## Step 1: Create GitHub OIDC Provider in AWS

### Option A: Using Terraform (Recommended)

The OIDC provider is already configured in `infra/terraform/github_oidc.tf`. Deploy it using:

```bash
cd infra/terraform
terraform init
terraform plan -target=aws_iam_openid_connect_provider.github_actions
terraform apply -target=aws_iam_openid_connect_provider.github_actions
```

### Option B: Using AWS CLI

```bash
aws iam create-openid-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

## Step 2: Create IAM Roles for Each Workflow

### Infrastructure Deployment Role

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
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### Lambda Deployment Role

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
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": [
            "repo:OWNER/REPO:ref:refs/heads/main",
            "repo:OWNER/REPO:ref:refs/tags/*"
          ]
        }
      }
    }
  ]
}
```

### Web Deployment Role

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
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### API Deployment Role

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
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

## Step 3: Attach Policies to Roles

### Infrastructure Role Policies

```bash
# Terraform state management
aws iam attach-role-policy \
  --role-name GitHubActions-Infrastructure \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# S3 state backend access
aws iam put-role-policy \
  --role-name GitHubActions-Infrastructure \
  --policy-name TerraformStateAccess \
  --policy-document file://policies/terraform-state-policy.json
```

### Lambda Role Policies

```bash
# ECR access for container images
aws iam attach-role-policy \
  --role-name GitHubActions-Lambda \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Lambda function management
aws iam put-role-policy \
  --role-name GitHubActions-Lambda \
  --policy-name LambdaDeployment \
  --policy-document file://policies/lambda-deployment-policy.json
```

### Web Role Policies

```bash
# S3 bucket access for static assets
aws iam put-role-policy \
  --role-name GitHubActions-Web \
  --policy-name S3WebDeployment \
  --policy-document file://policies/s3-web-policy.json

# CloudFront invalidation
aws iam put-role-policy \
  --role-name GitHubActions-Web \
  --policy-name CloudFrontInvalidation \
  --policy-document file://policies/cloudfront-policy.json
```

### API Role Policies

```bash
# Lambda function deployment
aws iam put-role-policy \
  --role-name GitHubActions-API \
  --policy-name APIDeployment \
  --policy-document file://policies/api-deployment-policy.json

# API Gateway management
aws iam attach-role-policy \
  --role-name GitHubActions-API \
  --policy-arn arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator
```

## Step 4: Configure GitHub Repository

### Repository Settings

1. Navigate to your GitHub repository
2. Go to Settings → Secrets and variables → Actions
3. Add the required secrets (see SECRETS.md for details)

### Environment Configuration

1. Create environments: `development`, `staging`, `production`
2. Configure environment-specific secrets
3. Set up protection rules for production environment

## Verification

### Test OIDC Authentication

```yaml
# Test workflow to verify OIDC setup
name: Test OIDC
on: workflow_dispatch

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Test AWS access
        run: aws sts get-caller-identity
```

## Security Best Practices

1. **Least Privilege**: Grant only the minimum permissions required
2. **Branch Restrictions**: Limit role assumption to specific branches
3. **Repository Restrictions**: Restrict access to specific repositories
4. **Regular Audits**: Review and rotate IAM policies regularly
5. **Monitoring**: Enable CloudTrail logging for all role assumptions

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

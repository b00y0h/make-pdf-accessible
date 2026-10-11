# GitHub OIDC Setup Guide

This guide explains how to configure and use the GitHub OIDC provider and IAM roles for secure CI/CD workflows.

## Overview

The account layer (`account/`) creates the GitHub OIDC provider once per AWS account. This root creates five specialized IAM roles per environment, with least-privilege access for different workflow types:

1. **Infrastructure CI Role** - For Terraform operations
2. **Lambda Deploy Role** - For Lambda function deployments
3. **Web Deploy Role** - For web application deployments
4. **API Deploy Role** - For API deployments with blue/green strategy
5. **Testing Role** - For running tests in CI

## Prerequisites

1. AWS account with appropriate permissions
2. GitHub repository with Actions enabled
3. Terraform >= 1.5 installed

## Configuration

### 1. Set Required Variables

Create or update your `terraform.tfvars` file:

```hcl
# Required: Your GitHub repository in owner/repo format
github_repo = "your-org/your-repo"

# Optional: Customize session duration (default: 3600 seconds)
github_oidc_session_duration = 3600

# Other required variables
project_name = "pdf-accessibility"
environment = "prod"
aws_region = "us-east-1"
```

### 2. Deploy Infrastructure

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

### 3. Configure GitHub Secrets

After deployment, get the role ARNs from each environment's Terraform outputs:

```bash
terraform output github_actions_roles_summary
```

Each environment (`dev`, `staging`, `prod`) has its own roles, named `pdf-accessibility-<env>-github-<role>-role`, so the ARNs differ per environment.

Where a secret is stored decides which jobs can read it:

- A job that declares no `environment:` reads only repository secrets.
- A job that declares an environment reads that environment's secret first and falls back to the repository secret with the same name.
- A job that declares an environment presents `environment:<name>` to AWS as its OIDC subject instead of its branch, so the role it assumes must trust that environment.

Repository secrets live under `Settings > Secrets and variables > Actions`; environment secrets under `Settings > Environments > <name>`. GitHub rejects secret names that start with `GITHUB_`, so the role secrets use the `AWS_` prefix.

| Secret                             | Read by                                                                                                                                                                                                                                                                          | Where to set it                             | Value                                                                                                                                                                                                                                                                                  |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AWS_INFRASTRUCTURE_CI_ROLE_ARN`   | `infra-ci.yml`: `security-monitoring` (no environment), `terraform-apply` (`<env>-infrastructure`). `rollback.yml`: `rollback-infrastructure` (`<env>-infrastructure`)                                                                                                           | Repository, and each `<env>-infrastructure` | Repository: dev's `github_infrastructure_ci_role_arn`. Environment: its own.                                                                                                                                                                                                           |
| `AWS_INFRASTRUCTURE_PLAN_ROLE_ARN` | `infra-ci.yml`: `terraform-plan` (no environment)                                                                                                                                                                                                                                | Repository                                  | A role that can read dev's Terraform state and take its lock, with read-only access to everything else. No Terraform defines it yet; until it is set, pull requests skip the plan with a notice and a manual run fails. Don't use the infrastructure CI role here: it can write state. |
| `AWS_LAMBDA_DEPLOY_ROLE_ARN`       | `build-and-deploy-lambda.yml`; `rollback.yml`: `rollback-lambda-functions`; `test-rollback.yml`: `capture-baseline-lambda` and `test-deployment-state`. None of these jobs declares an environment                                                                               | Repository only                             | Dev's `github_lambda_deploy_role_arn`                                                                                                                                                                                                                                                  |
| `AWS_API_DEPLOY_ROLE_ARN`          | `api-ci.yml`: `detect-changes`, `build-package`, `cleanup` and `security-monitoring` (no environment), `blue-green-deploy` (`<env>-api`). `rollback.yml`: `rollback-api`; `test-rollback.yml`: `capture-baseline-api` and `test-cache-invalidation-apigateway` (all `<env>-api`) | Repository, and each `<env>-api`            | Repository: dev's `github_api_deploy_role_arn`. Environment: its own. Dev's role trusts `main` and, of the environments, only `dev-api`, so a `staging-api` or `prod-api` job that falls back to the repository value is rejected.                                                     |
| `AWS_WEB_DEPLOY_ROLE_ARN`          | `web-ci.yml` and `marketing-site.yml`: `deploy`; `rollback.yml`: `rollback-web`; `test-rollback.yml`: `capture-baseline-web` and `test-cache-invalidation-cloudfront` (all `<env>-web`)                                                                                          | Each `<env>-web`                            | That environment's `github_web_deploy_role_arn`. The role trusts only `environment:<env>-web`.                                                                                                                                                                                         |
| `AWS_REGION`                       | `infra-ci.yml`: `terraform-apply` and `security-monitoring` (no fallback), `terraform-plan` (falls back to `us-east-1`); `web-ci.yml` and `marketing-site.yml` (fall back to `us-east-1`)                                                                                        | Repository                                  | `us-east-1`                                                                                                                                                                                                                                                                            |
| `AWS_ACCOUNT_ID`                   | `build-and-deploy-lambda.yml`, for the ECR registry                                                                                                                                                                                                                              | Repository                                  | The account that holds the Lambda ECR repositories                                                                                                                                                                                                                                     |

Some jobs run without an environment and so assume the repository value (a dev role) even when the run is for `staging` or `prod`: `terraform-plan` on a manual run (the plan role), `security-monitoring` after an apply, and every job that uses the Lambda deploy role. The Lambda role trusts no environment, so `rollback.yml` stops with an error when asked to roll back Lambda functions outside dev.

## Role Permissions and Trusted Subjects

The trusted subjects are set per role in `github_role_subjects` in `github_oidc.tf`.

### Infrastructure CI Role

- **Trusts**: `main` and the `<env>-infrastructure` environment; in dev also `develop` and pull requests. Staging shares the dev account, so its roles accept neither.
- **Permissions**:
  - Read-only access for Terraform plan (all branches)
  - Full access for Terraform apply (main branch only)
  - Terraform state management (S3, DynamoDB)

### Lambda Deploy Role

- **Trusts**: `main`, git tags (`refs/tags/*`)
- **Permissions**:
  - ECR repository access for container images
  - Lambda function updates and versioning
  - CloudWatch Logs for monitoring

### Web Deploy Role

- **Trusts**: the `<env>-web` environment only. Limit which branches may deploy with the environment's deployment branch rule.
- **Permissions**:
  - S3 bucket access for web assets
  - CloudFront invalidation
  - CloudWatch Logs for deployment monitoring

### API Deploy Role

- **Trusts**: `main` and the `<env>-api` environment
- **Permissions**:
  - Lambda function management for blue/green deployment
  - API Gateway stage management
  - CloudWatch metrics and logs for health checks
  - Limited DynamoDB access for health checks

### Testing Role

- **Trusts**: `main`; in dev also `develop` and pull requests
- **Secret**: none; no workflow assumes this role yet
- **Permissions**:
  - Read-only access to test resources
  - Lambda function invocation for integration tests
  - S3 access for test artifacts
  - CloudWatch Logs for test results

## Usage in GitHub Actions

### Basic OIDC Authentication

```yaml
name: Example Workflow

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
          role-session-name: GitHubActions-LambdaDeploy

      - name: Deploy Lambda
        run: |
          # Your deployment commands here
          echo "Deploying Lambda functions..."
```

### Infrastructure CI Workflow

```yaml
name: Infrastructure CI

on:
  pull_request:
    paths: ['infra/terraform/**']
  push:
    branches: [main]
    paths: ['infra/terraform/**']

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_INFRASTRUCTURE_CI_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
          role-session-name: GitHubActions-InfraCI

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Plan
        run: |
          cd infra/terraform
          terraform init
          terraform plan -out=tfplan

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: |
          cd infra/terraform
          terraform apply tfplan
```

## Security Best Practices

### Trust Policy Conditions

Each role includes strict conditions that limit access to:

- Specific repository (`repo:owner/repo:*`)
- Specific branches or events
- Audience validation (`sts.amazonaws.com`)

### Least Privilege Access

- Each role has minimal permissions for its specific use case
- Cross-role access is prevented through resource-level restrictions
- Time-limited sessions (configurable, default 1 hour)

### Branch Protection

- Production deployments limited to `main` branch
- Infrastructure changes require manual approval on `main`
- Testing roles work across development branches

## Troubleshooting

### Common Issues

1. **"No identity-based policy allows the sts:AssumeRoleWithWebIdentity action"**
   - Check that the role ARN is correct in GitHub secrets, at the scope listed above
   - Verify the repository name matches the trust policy
   - Ensure the job runs on a branch or in an environment the role trusts; a job that declares an environment is matched by `environment:<name>`, not by its branch

2. **"Access denied" during resource operations**
   - Verify the role has the necessary permissions for the resource
   - Check if the resource naming matches the policy patterns
   - Ensure you're using the correct role for the workflow type

3. **"Token audience validation failed"**
   - Verify the `permissions` section includes `id-token: write`
   - Check that you're using the correct AWS region

### Debugging

Enable debug logging in your workflow:

```yaml
env:
  AWS_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

### Validation

Test role assumptions manually:

```bash
# Test role assumption (requires AWS CLI and appropriate permissions)
aws sts assume-role-with-web-identity \
  --role-arn "arn:aws:iam::ACCOUNT:role/ROLE-NAME" \
  --role-session-name "test-session" \
  --web-identity-token "$GITHUB_TOKEN"
```

## Monitoring and Auditing

### CloudTrail Events

Monitor these events for OIDC usage:

- `AssumeRoleWithWebIdentity`
- `GetCallerIdentity`
- Resource-specific actions by each role

### CloudWatch Metrics

Set up alarms for:

- Failed role assumptions
- Unusual activity patterns
- Resource access outside normal hours

### Regular Reviews

- Review role permissions quarterly
- Audit CloudTrail logs for unexpected access
- Update trust policies when repository structure changes
- Rotate OIDC thumbprints as needed

## Updates and Maintenance

### Updating Roles

To modify role permissions:

1. Update the policy in `github_oidc.tf`
2. Run `terraform plan` to review changes
3. Apply changes with `terraform apply`
4. Test the updated permissions

### Adding New Roles

To add a new workflow-specific role:

1. Define the role in `github_oidc.tf`
2. Add appropriate trust policy conditions
3. Create least-privilege policy statements
4. Add outputs in `outputs.tf`
5. Update this documentation

### Rotating OIDC Thumbprints

GitHub may update their OIDC thumbprints. To update:

1. Get new thumbprints from GitHub documentation
2. Update `thumbprint_list` in `account/github_oidc.tf`
3. Apply changes with Terraform

## References

- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [AWS IAM OIDC Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

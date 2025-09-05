# GitHub Actions Workflows

This directory contains secure CI/CD workflows for the Make PDF Accessible platform.

## Workflows

### Infrastructure CI (`infra-ci.yml`)

Manages Terraform infrastructure deployment with security and approval controls.

**Triggers:**

- Pull requests affecting `infra/terraform/**`
- Pushes to `main` branch with infrastructure changes
- Manual workflow dispatch

**Features:**

- ✅ Terraform format and validation checks
- 📋 Automated plan generation and PR comments
- 🔒 OIDC authentication (no stored credentials)
- ⚠️ Destructive change detection and warnings
- 🛡️ Security scanning with Trivy
- 🚀 Manual approval gate for production deployments
- 📊 Deployment summaries and notifications

**Required Secrets:**

- `AWS_REGION`: AWS region (e.g., `us-east-1`)
- `GITHUB_INFRASTRUCTURE_CI_ROLE_ARN`: IAM role ARN for infrastructure operations

**Environment Protection:**
The workflow uses GitHub environment protection for the `production-infrastructure` environment. Configure this in your repository settings:

1. Go to Settings → Environments
2. Create environment: `production-infrastructure`
3. Enable "Required reviewers" and add appropriate team members
4. Optionally set deployment branch rules to `main` only

## Setup Instructions

### 1. Deploy OIDC Infrastructure

First, deploy the OIDC provider and IAM roles using Terraform:

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

### 2. Configure GitHub Secrets

Add the following secrets to your repository (`Settings > Secrets and variables > Actions`):

```bash
# Get role ARNs from Terraform outputs
terraform output github_actions_roles_summary
```

Required secrets:

- `AWS_REGION`
- `GITHUB_INFRASTRUCTURE_CI_ROLE_ARN`

### 3. Set Up Environment Protection

1. Navigate to `Settings → Environments` in your GitHub repository
2. Create a new environment named `production-infrastructure`
3. Configure protection rules:
   - ✅ Required reviewers (add DevOps team members)
   - ✅ Restrict to `main` branch only
   - ⏱️ Optional: Add deployment delay

### 4. Test the Workflow

Create a test PR with infrastructure changes:

```bash
# Make a small change to trigger the workflow
echo "# Test change" >> infra/terraform/README.md
git add .
git commit -m "test: trigger infrastructure CI"
git push origin feature-branch
```

The workflow will:

1. Run format and validation checks
2. Generate a Terraform plan
3. Comment on the PR with results
4. Run security scans

## Workflow Behavior

### Pull Requests

- **Format Check**: Validates Terraform code formatting
- **Validation**: Checks Terraform syntax and configuration
- **Plan Generation**: Creates execution plan and posts summary to PR
- **Security Scan**: Runs Trivy security analysis
- **PR Comments**: Automated comments with plan results and warnings

### Main Branch (Production)

- **Manual Approval**: Requires approval from designated reviewers
- **Terraform Apply**: Executes infrastructure changes
- **Deployment Summary**: Generates summary with resource counts and URLs
- **Notifications**: Success/failure notifications (extend with Slack/Teams)

### Manual Dispatch

- **Environment Selection**: Choose target environment (dev/staging/prod)
- **Dry Run Option**: Plan-only mode for testing
- **Artifact Reuse**: Can reuse previously generated plans

## Security Features

### OIDC Authentication

- No long-lived AWS credentials stored in GitHub
- Short-lived tokens with specific permissions
- Branch and repository restrictions in trust policies

### Least Privilege Access

- Infrastructure CI role has minimal required permissions
- Read-only access for planning operations
- Full access only for apply operations on main branch

### Security Scanning

- Trivy scans for infrastructure security issues
- Results uploaded to GitHub Security tab
- Blocks deployment on critical vulnerabilities (configurable)

### Approval Gates

- Manual approval required for production changes
- Environment protection rules enforce review process
- Deployment branch restrictions prevent unauthorized changes

## Troubleshooting

### Common Issues

1. **"No identity-based policy allows the sts:AssumeRoleWithWebIdentity action"**
   - Verify the role ARN in GitHub secrets
   - Check that the repository name matches the OIDC trust policy
   - Ensure the workflow is running on an allowed branch

2. **"Access denied" during Terraform operations**
   - Verify the IAM role has necessary permissions
   - Check if resource naming matches policy patterns
   - Ensure you're using the correct role for the operation

3. **Plan generation fails**
   - Check Terraform backend configuration
   - Verify S3 bucket and DynamoDB table exist
   - Ensure proper permissions for state management

### Debug Mode

Enable debug logging by adding these secrets:

- `ACTIONS_STEP_DEBUG`: `true`
- `ACTIONS_RUNNER_DEBUG`: `true`

## Extending the Workflow

### Adding Notifications

To add Slack or Teams notifications, extend the `notify-deployment` job:

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Custom Validation

Add custom validation steps in the `terraform-validate` job:

```yaml
- name: Custom Policy Check
  run: |
    # Add your custom validation logic here
    conftest verify --policy policy/ infra/terraform/
```

### Multi-Environment Support

Extend the workflow to support multiple environments by:

1. Adding environment-specific variable files
2. Using workspace or directory-based separation
3. Implementing environment-specific approval rules

## Monitoring

Monitor workflow execution through:

- GitHub Actions dashboard
- CloudTrail logs for AWS API calls
- CloudWatch metrics for deployment frequency and success rates
- Security tab for vulnerability scan results

## Best Practices

1. **Always test changes in PRs** before merging to main
2. **Review Terraform plans carefully**, especially destructive changes
3. **Keep approval groups small** but include key stakeholders
4. **Monitor security scan results** and address issues promptly
5. **Use semantic versioning** for infrastructure changes
6. **Document significant changes** in commit messages and PR descriptions

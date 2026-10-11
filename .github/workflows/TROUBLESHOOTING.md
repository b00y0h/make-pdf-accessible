# Troubleshooting Guide for GitHub Actions CI/CD

This guide provides solutions for common issues encountered when setting up and running GitHub Actions workflows with AWS OIDC integration.

## OIDC Authentication Issues

### Error: "No OpenIDConnect provider found"

**Symptoms:**

```
Error: Could not assume role with OIDC: No OpenIDConnect provider found in your account for https://token.actions.githubusercontent.com
```

**Causes:**

- OIDC provider not created in AWS account
- OIDC provider created in wrong AWS account/region

**Solutions:**

1. **Verify OIDC Provider Exists:**

```bash
aws iam list-open-id-connect-providers
```

2. **Create OIDC Provider with the account layer:**

The provider exists once per AWS account and is managed by `infra/terraform/account`; the environment roles only look it up. Create it there rather than with the AWS CLI, or the account layer's next apply fails because the provider already exists:

```bash
cd infra/terraform/account
terraform init -reconfigure -backend-config=environments/nonprod.backend.hcl
terraform apply -var-file=environments/nonprod.tfvars -target=aws_iam_openid_connect_provider.github
```

Use `prod.backend.hcl` and `prod.tfvars` in the prod account.

### Error: "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Symptoms:**

```
Error: Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

**Causes:**

- IAM role doesn't exist
- Trust policy doesn't allow the job's subject. A job that declares an environment presents `repo:<owner>/<repo>:environment:<name>` instead of its branch, so a role that trusts only `main` rejects it, and the web role (which trusts only `environment:<env>-web`) rejects any job outside that environment.
- Role ARN is incorrect in GitHub secrets, or is the role for a different environment or account

**Solutions:**

1. **Verify Role Exists:**

```bash
aws iam get-role --role-name pdf-accessibility-dev-github-infra-ci-role
```

The roles are `pdf-accessibility-<env>-github-<role>-role`, where `<role>` is `infra-ci`, `lambda-deploy`, `web-deploy`, `api-deploy` or `testing`.

2. **Check Trust Policy:**

```bash
aws iam get-role --role-name pdf-accessibility-dev-github-infra-ci-role \
  --query 'Role.AssumeRolePolicyDocument' --output json | jq .
```

3. **Verify GitHub Secrets:**

```bash
gh secret list | grep ROLE_ARN
gh secret list --env dev-web
```

Each secret's scope (repository or environment) is listed in [GITHUB_OIDC_SETUP.md](../../infra/terraform/GITHUB_OIDC_SETUP.md#3-configure-github-secrets).

4. **Update Trust Policy:**

The trusted subjects are managed in `github_role_subjects` in `infra/terraform/github_oidc.tf`. Change them there and apply; a console edit is overwritten by the next apply.

### Error: "Token audience validation failed"

**Symptoms:**

```
Error: Could not assume role with OIDC: Token audience validation failed
```

**Causes:**

- Incorrect audience in trust policy
- Missing `id-token: write` permission in workflow

**Solutions:**

1. **Add Required Permissions:**

```yaml
permissions:
  id-token: write
  contents: read
```

2. **Verify Trust Policy Audience:**

```json
{
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
  }
}
```

## Terraform Issues

### Error: "Backend configuration changed"

**Symptoms:**

```
Error: Backend configuration changed
```

**Causes:**

- S3 bucket for state doesn't exist
- Incorrect backend configuration
- State file locked by another process

**Solutions:**

1. **Create State Bucket:**

```bash
aws s3 mb s3://pdf-accessibility-terraform-state
aws s3api put-bucket-versioning \
  --bucket pdf-accessibility-terraform-state \
  --versioning-configuration Status=Enabled
```

2. **Force Unlock State:**

```bash
terraform force-unlock LOCK_ID
```

3. **Reinitialize Backend:**

```bash
terraform init -reconfigure
```

### Error: "Access Denied" during Terraform operations

**Symptoms:**

```
Error: Error creating/updating/deleting resource: AccessDenied
```

**Causes:**

- Insufficient IAM permissions
- Resource already exists with different ownership
- Cross-region resource access issues

**Solutions:**

1. **Check IAM Permissions:**

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT_ID:role/pdf-accessibility-dev-github-infra-ci-role \
  --action-names ec2:CreateVpc \
  --resource-arns "*"
```

2. **Add Missing Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:*", "s3:*", "lambda:*", "iam:PassRole"],
      "Resource": "*"
    }
  ]
}
```

## Lambda Deployment Issues

### Error: "Function not found" during deployment

**Symptoms:**

```
Error: The resource you requested does not exist.
```

**Causes:**

- Lambda function doesn't exist yet
- Function name mismatch
- Wrong AWS region

**Solutions:**

1. **Verify Function Exists:**

```bash
aws lambda get-function --function-name pdf-accessibility-api
```

2. **Create Function First:**

```bash
aws lambda create-function \
  --function-name pdf-accessibility-api \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler main.handler \
  --zip-file fileb://function.zip
```

3. **Check Region Configuration:**

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v6
  with:
    role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
    aws-region: ${{ secrets.AWS_REGION }} # Ensure this matches function region
```

### Error: "InvalidParameterValueException" during image update

**Symptoms:**

```
Error: InvalidParameterValueException: The image URI is not valid
```

**Causes:**

- ECR image doesn't exist
- Image URI format is incorrect
- Authentication to ECR failed

**Solutions:**

1. **Verify Image Exists:**

```bash
aws ecr describe-images \
  --repository-name pdf-accessibility/api \
  --image-ids imageTag=latest
```

2. **Check Image URI Format:**

```
ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/REPOSITORY:TAG
```

3. **Authenticate to ECR:**

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

## Container Build Issues

### Error: "Docker build failed"

**Symptoms:**

```
Error: The command '/bin/sh -c pip install -r requirements.txt' returned a non-zero code: 1
```

**Causes:**

- Missing dependencies in requirements.txt
- Network issues during build
- Base image compatibility issues

**Solutions:**

1. **Test Build Locally:**

```bash
docker build -t test-image .
```

2. **Check Requirements File:**

```bash
# Verify requirements.txt exists and is valid
cat requirements.txt
pip-compile --dry-run requirements.in
```

3. **Use Build Cache:**

```yaml
- name: Build Docker image
  uses: docker/build-push-action@v7
  with:
    context: .
    push: true
    tags: ${{ env.ECR_REGISTRY }}/pdf-accessibility/api:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Error: "Push to ECR failed"

**Symptoms:**

```
Error: denied: User is not authorized to perform: ecr:BatchCheckLayerAvailability
```

**Causes:**

- Insufficient ECR permissions
- Repository doesn't exist
- Authentication token expired

**Solutions:**

1. **Create ECR Repository:**

```bash
aws ecr create-repository --repository-name pdf-accessibility/api
```

2. **Add ECR Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
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
      "Resource": "*"
    }
  ]
}
```

## Web Deployment Issues

### Error: "S3 bucket does not exist"

**Symptoms:**

```
Error: The specified bucket does not exist
```

**Causes:**

- S3 bucket not created
- Bucket name mismatch in secrets
- Wrong AWS region

**Solutions:**

1. **Create S3 Bucket:**

```bash
aws s3 mb s3://pdf-accessibility-prod-web --region us-east-1
```

2. **Verify Bucket Name:**

```bash
gh secret list | grep S3_BUCKET
aws s3 ls | grep pdf-accessibility
```

3. **Configure Bucket for Web Hosting:**

```bash
aws s3 website s3://pdf-accessibility-prod-web \
  --index-document index.html \
  --error-document error.html
```

### Error: "CloudFront invalidation failed"

**Symptoms:**

```
Error: InvalidDistributionId: The distribution ID is malformed
```

**Causes:**

- Incorrect CloudFront distribution ID
- Distribution doesn't exist
- Insufficient permissions

**Solutions:**

1. **List CloudFront Distributions:**

```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].[Id,DomainName]' \
  --output table
```

2. **Update GitHub Secret:**

```bash
gh secret set CLOUDFRONT_DISTRIBUTION_ID --body "E1234567890123"
```

3. **Add CloudFront Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "*"
    }
  ]
}
```

## Test Failures

### Error: "Tests failed to run"

**Symptoms:**

```
Error: Jest encountered an unexpected token
```

**Causes:**

- Missing test dependencies
- Incorrect Jest configuration
- Node.js version mismatch

**Solutions:**

1. **Install Dependencies:**

```bash
cd web
npm install
```

2. **Check Jest Configuration:**

```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/$1',
  },
};
```

3. **Use Correct Node Version:**

```yaml
- name: Setup Node.js
  uses: actions/setup-node@v7
  with:
    node-version: '24'
    cache: 'npm'
```

### Error: "Python tests failed"

**Symptoms:**

```
Error: ModuleNotFoundError: No module named 'pytest'
```

**Causes:**

- Missing test dependencies
- Virtual environment not activated
- Python version mismatch

**Solutions:**

1. **Install Test Dependencies:**

```bash
pip install -r requirements-dev.txt
```

2. **Use Docker for Consistent Environment:**

```yaml
- name: Run tests
  run: |
    docker-compose run --rm api pytest tests/ -v --cov
```

## Secrets and Configuration Issues

### Error: Role secret not configured

**Symptoms:**

An unset secret reads as an empty string, so the run reports the missing role rather than a missing secret:

```
AWS_API_DEPLOY_ROLE_ARN secret not configured - deployment steps will be skipped
AWS_LAMBDA_DEPLOY_ROLE_ARN secret not configured - deployment will be skipped
The web app was not deployed: AWS_WEB_DEPLOY_ROLE_ARN is not set for the dev-web environment.
Credentials could not be loaded, please check your action inputs
```

The last one comes from `aws-actions/configure-aws-credentials` in a job with no check of its own, such as `terraform-plan` in `infra-ci.yml`.

**Causes:**

- Secret not configured in GitHub
- Secret set at the wrong scope. A job that declares no environment cannot read an environment secret; `terraform-plan` needs a repository copy of `AWS_INFRASTRUCTURE_CI_ROLE_ARN`, and `AWS_WEB_DEPLOY_ROLE_ARN` belongs on each `<env>-web` environment.
- Secret set under an old name. Names starting with `GITHUB_` are rejected by GitHub, and the workflows do not read `AWS_ROLE_ARN_INFRA`, `AWS_ROLE_ARN_LAMBDA`, `AWS_ROLE_ARN_WEB` or `AWS_ROLE_ARN_API`.

**Solutions:**

1. **List Repository Secrets:**

```bash
gh secret list
```

2. **Check Environment Secrets:**

```bash
gh secret list --env prod-infrastructure
gh secret list --env prod-web
```

3. **Set Missing Secret** at the scope listed in [GITHUB_OIDC_SETUP.md](../../infra/terraform/GITHUB_OIDC_SETUP.md#3-configure-github-secrets):

```bash
# Repository secret, for jobs that declare no environment
gh secret set AWS_INFRASTRUCTURE_CI_ROLE_ARN --body "arn:aws:iam::DEV_ACCOUNT_ID:role/pdf-accessibility-dev-github-infra-ci-role"

# Environment secret
gh secret set AWS_WEB_DEPLOY_ROLE_ARN --env prod-web --body "arn:aws:iam::PROD_ACCOUNT_ID:role/pdf-accessibility-prod-github-web-deploy-role"
```

### Error: "Environment protection rule"

**Symptoms:**

```
Error: Environment protection rule prevents deployment
```

**Causes:**

- Manual approval required
- Branch protection rules
- Required reviewers not available

**Solutions:**

1. **Check Environment Settings:**
   - Go to repository Settings → Environments
   - Review protection rules for the environment

2. **Request Approval:**
   - Wait for required reviewers to approve
   - Or temporarily disable protection rules for testing

3. **Use Correct Branch:**

```yaml
on:
  push:
    branches: [main] # Ensure this matches protection rules
```

## Performance Issues

### Error: "Workflow timeout"

**Symptoms:**

```
Error: The job running on runner has exceeded the maximum execution time of 360 minutes
```

**Causes:**

- Long-running tests or builds
- Network timeouts
- Resource constraints

**Solutions:**

1. **Increase Timeout:**

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 60 # Increase from default 360
```

2. **Optimize Build Process:**

```yaml
- name: Build with cache
  uses: docker/build-push-action@v7
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

3. **Parallel Execution:**

```yaml
strategy:
  matrix:
    service: [api, worker, ocr, structure]
  max-parallel: 4
```

## Debugging Workflows

### Enable Debug Logging

1. **Set Repository Variables:**

```bash
gh variable set ACTIONS_STEP_DEBUG --body "true"
gh variable set ACTIONS_RUNNER_DEBUG --body "true"
```

2. **Add Debug Steps:**

```yaml
- name: Debug information
  run: |
    echo "GitHub Context:"
    echo "${{ toJson(github) }}"
    echo "Environment Variables:"
    env | sort
    echo "AWS CLI Version:"
    aws --version
```

### Common Debug Commands

```yaml
- name: Debug AWS credentials
  run: |
    aws sts get-caller-identity
    aws sts get-session-token --duration-seconds 900

- name: Debug Docker
  run: |
    docker version
    docker system info
    docker images

- name: Debug Network
  run: |
    curl -I https://api.github.com
    nslookup github.com
    ping -c 3 8.8.8.8
```

## Getting Help

### GitHub Support Channels

1. **GitHub Community Forum**: https://github.community/
2. **GitHub Support**: https://support.github.com/
3. **AWS Support**: https://aws.amazon.com/support/

### Useful Commands for Investigation

```bash
# Check workflow runs
gh run list --limit 10

# View workflow logs
gh run view RUN_ID --log

# Check repository settings
gh repo view --json defaultBranch,visibility,permissions

# Validate workflow syntax
gh workflow view .github/workflows/api-ci.yml

# Test secret access
gh secret list --json name,updated_at
```

### Log Analysis

Look for these patterns in workflow logs:

1. **Authentication Issues**: Search for "AssumeRole", "OIDC", "credentials"
2. **Permission Issues**: Search for "AccessDenied", "Forbidden", "unauthorized"
3. **Resource Issues**: Search for "NotFound", "does not exist", "invalid"
4. **Network Issues**: Search for "timeout", "connection", "DNS"

### Emergency Procedures

If workflows are completely broken:

1. **Disable Workflows:**

```bash
gh workflow disable .github/workflows/api-ci.yml
```

2. **Manual Deployment:**

```bash
# Deploy manually using AWS CLI
aws lambda update-function-code \
  --function-name pdf-accessibility-api \
  --image-uri ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pdf-accessibility/api:latest
```

3. **Rollback:**

```bash
# Rollback to previous version
aws lambda update-alias \
  --function-name pdf-accessibility-api \
  --name LIVE \
  --function-version $PREVIOUS_VERSION
```

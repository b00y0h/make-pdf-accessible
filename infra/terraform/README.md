# PDF Accessibility Platform - Terraform Infrastructure

This directory contains the Terraform configuration for provisioning the AWS infrastructure required for the PDF Accessibility Platform.

## Architecture Overview

The infrastructure includes:

- **VPC**: Isolated network with private subnets, NAT gateways, and VPC endpoints
- **S3 Buckets**: Secure storage for PDFs, derivatives, reports, and web assets
- **DynamoDB**: Tables for documents, jobs, and user sessions
- **SQS**: Queues for asynchronous processing with dead letter queues
- **Cognito**: User authentication with SAML IdP support
- **API Gateway**: HTTP API with JWT authorization
- **CloudFront**: CDN with WAF protection
- **ECR**: Container registries for Lambda functions
- **Step Functions**: Orchestration for PDF processing workflows
- **IAM**: Least privilege roles and policies

## Prerequisites

- [Terraform](https://terraform.io/) >= 1.8
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- An AWS account with necessary permissions

## Quick Start

### 1. Configure Variables

Copy and customize the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your specific values:

```hcl
# Required
aws_region   = "us-east-1"
project_name = "pdf-accessibility"
environment  = "dev"
github_repo  = "your-org/your-repo"

# Optional
domain_name     = "myapp.example.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
```

### 2. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

## Configuration

### Required Variables

| Variable       | Description               | Example                  |
| -------------- | ------------------------- | ------------------------ |
| `aws_region`   | AWS region for resources  | `us-east-1`              |
| `project_name` | Name prefix for resources | `pdf-accessibility`      |
| `environment`  | Environment name          | `dev`, `staging`, `prod` |
| `github_repo`  | GitHub repo for OIDC      | `owner/repository`       |

### Optional Variables

| Variable             | Description              | Default |
| -------------------- | ------------------------ | ------- |
| `domain_name`        | Custom domain name       | `""`    |
| `certificate_arn`    | ACM certificate ARN      | `""`    |
| `enable_waf`         | Enable WAF protection    | `true`  |
| `log_retention_days` | CloudWatch log retention | `30`    |

### VPC Configuration

| Variable               | Description          | Default                              |
| ---------------------- | -------------------- | ------------------------------------ |
| `vpc_cidr`             | VPC CIDR block       | `10.0.0.0/16`                        |
| `private_subnet_cidrs` | Private subnet CIDRs | `["10.0.1.0/24", "10.0.2.0/24"]`     |
| `public_subnet_cidrs`  | Public subnet CIDRs  | `["10.0.101.0/24", "10.0.102.0/24"]` |

## GitHub Actions OIDC Setup

This infrastructure includes GitHub OIDC provider configuration for secure CI/CD deployments.

### 1. Configure Repository

Update your `terraform.tfvars`:

```hcl
github_repo     = "your-org/your-repo"
github_branches = ["main", "develop"]
```

### 2. GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ['infra/terraform/**']

env:
  AWS_REGION: us-east-1

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ~1.8

      - name: Terraform Init
        run: terraform init
        working-directory: infra/terraform

      - name: Terraform Plan
        run: terraform plan
        working-directory: infra/terraform

      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: infra/terraform
```

### 3. Repository Secrets

Add the following secrets to your GitHub repository:

```
AWS_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/PROJECT-ENVIRONMENT-github-actions-role
```

You can find the exact ARN in the Terraform outputs after deployment.

## State Management

### Backend Configuration (Recommended)

Create a `backend.tf` file for remote state:

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "pdf-accessibility/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

### Local State (Development)

For development, you can use local state (not recommended for production):

```bash
# State is stored in terraform.tfstate locally
terraform init
```

## Security Features

### Encryption

- **S3**: KMS encryption for all buckets
- **DynamoDB**: KMS encryption with point-in-time recovery
- **SQS**: KMS encryption for all queues
- **CloudWatch**: Encrypted log groups

### Network Security

- **VPC**: Private subnets with NAT gateways
- **VPC Endpoints**: Secure access to AWS services
- **Security Groups**: Least privilege network access
- **WAF**: Web application firewall for CloudFront

### Access Control

- **IAM**: Least privilege roles and policies
- **Cognito**: Multi-factor authentication support
- **API Gateway**: JWT authorization
- **S3**: Bucket policies with CloudFront OAC

## Monitoring and Logging

### CloudWatch Alarms

- DynamoDB throttling
- SQS queue depth and age
- Dead letter queue messages

### Logging

- API Gateway access logs
- CloudFront access logs
- Step Functions execution logs
- WAF logs

### X-Ray Tracing

- Lambda function tracing
- Step Functions tracing

## Outputs

After deployment, Terraform provides outputs with resource identifiers:

```bash
# View all outputs
terraform output

# Get specific output
terraform output api_gateway_url
terraform output web_app_url
```

Key outputs include:

- `api_gateway_url`: API Gateway endpoint
- `web_app_url`: Web application URL
- `cognito_user_pool_id`: Cognito User Pool ID
- `github_actions_role_arn`: GitHub Actions IAM role ARN

## Customization

### Adding Custom Domains

1. Create ACM certificate in `us-east-1`:

```bash
aws acm request-certificate \
  --domain-name myapp.example.com \
  --validation-method DNS \
  --region us-east-1
```

2. Update `terraform.tfvars`:

```hcl
domain_name     = "myapp.example.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
```

3. Apply changes:

```bash
terraform apply
```

### SAML IdP Configuration

Update the SAML provider configuration in `cognito.tf`:

```hcl
provider_details = {
  MetadataURL           = "https://your-idp.com/saml/metadata"
  SLORedirectBindingURI = "https://your-idp.com/saml/slo"
  SSORedirectBindingURI = "https://your-idp.com/saml/sso"
}
```

### Step Functions Workflow

Customize the processing workflow in `state_machine_definition.json`:

1. Add new states for additional processing steps
2. Modify error handling and retry logic
3. Update DynamoDB status tracking

## Troubleshooting

### Common Issues

1. **Certificate not in us-east-1**: CloudFront requires certificates in us-east-1
2. **SAML metadata**: Replace placeholder URLs with actual IdP endpoints
3. **GitHub OIDC**: Ensure repository and branch names are correct
4. **VPC endpoints**: Some regions may not support all endpoints

### Debugging

```bash
# Enable detailed logging
export TF_LOG=DEBUG
terraform apply

# Validate configuration
terraform validate

# Format code
terraform fmt -recursive
```

### State Issues

```bash
# Import existing resources
terraform import aws_s3_bucket.example bucket-name

# Remove from state
terraform state rm aws_s3_bucket.example

# Refresh state
terraform refresh
```

## Contributing

1. Follow Terraform best practices
2. Update documentation for changes
3. Test in development environment first
4. Use meaningful commit messages

## Support

For issues and questions:

- Check AWS service limits
- Review CloudWatch logs
- Validate IAM permissions
- Consult AWS documentation

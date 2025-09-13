# AWS Resource Tagging Report

This document reports on the tagging status of all AWS resources in the PDF Accessibility Platform infrastructure.

## Tag Schema

All resources use the following standardized tag schema:

```hcl
common_tags = {
  # Required tags for dashboard filtering
  application  = "accesspdf"
  service      = "doc-processing"
  component    = "platform"
  environment  = "dev|staging|prod"
  cost_center  = "CC-DEV-001|CC-STG-002|CC-PROD-003"

  # Additional organizational tags
  owner            = "team-platform"
  business_unit    = "R&D"
  data_sensitivity = "internal|confidential"
  managed_by       = "terraform"
  repo             = "github.com/b00y0h/make-pdf-accessible"

  # Legacy tags (for backwards compatibility)
  Project     = "pdf-accessibility"
  Environment = "dev|staging|prod"
  ManagedBy   = "terraform"
}
```

## Component-Specific Tag Variations

- **API Resources**: Use `local.api_tags` with `component = "api"` and `service = "api-gateway"`
- **Lambda Functions**: Use `local.lambda_tags` with `component = "compute"` and `service = "lambda"`
- **Storage Resources**: Use `local.storage_tags` with `component = "storage"` and `service = "s3"`
- **Database Resources**: Use `local.database_tags` with `component = "database"` and `service = "documentdb"`
- **Networking Resources**: Use `local.networking_tags` with `component = "networking"` and `service = "vpc"`
- **Security Resources**: Use `local.security_tags` with `component = "security"` and `service = "iam"`
- **Monitoring Resources**: Use `local.monitoring_tags` with `component = "monitoring"` and `service = "cloudwatch"`

## Taggable Resources

✅ **Successfully Tagged**:

### Compute Resources
- ✅ `aws_lambda_function` - All Lambda functions have appropriate tags
- ✅ `aws_ecr_repository` - All ECR repositories are tagged

### Storage Resources  
- ✅ `aws_s3_bucket` - All S3 buckets have component-specific tags
- ✅ `aws_kms_key` - KMS keys for encryption are tagged

### Database Resources
- ✅ `aws_docdb_cluster` - DocumentDB cluster is tagged
- ✅ `aws_docdb_cluster_instance` - All DocumentDB instances are tagged
- ✅ `aws_docdb_subnet_group` - DocumentDB subnet group is tagged
- ✅ `aws_docdb_cluster_parameter_group` - Parameter groups are tagged
- ✅ `aws_dynamodb_table` - All DynamoDB tables are tagged

### Networking Resources
- ✅ `aws_vpc` - VPC has networking-specific tags
- ✅ `aws_subnet` - All subnets (public/private) are tagged
- ✅ `aws_internet_gateway` - Internet gateway is tagged
- ✅ `aws_nat_gateway` - NAT gateway is tagged
- ✅ `aws_route_table` - Route tables are tagged
- ✅ `aws_security_group` - Security groups are tagged

### API & Application Resources
- ✅ `aws_apigatewayv2_api` - API Gateway has API-specific tags
- ✅ `aws_apigatewayv2_stage` - API Gateway stages are tagged
- ✅ `aws_cognito_user_pool` - Cognito user pools are tagged
- ✅ `aws_cloudfront_distribution` - CloudFront distributions are tagged

### Security Resources
- ✅ `aws_iam_role` - All IAM roles have security-specific tags
- ✅ `aws_iam_policy` - Custom IAM policies are tagged
- ✅ `aws_secretsmanager_secret` - Secrets Manager secrets are tagged

### Monitoring Resources
- ✅ `aws_cloudwatch_log_group` - All log groups have monitoring-specific tags
- ✅ `aws_cloudwatch_dashboard` - CloudWatch dashboards are tagged
- ✅ `aws_cloudwatch_metric_alarm` - CloudWatch alarms are tagged

### Queue Resources
- ✅ `aws_sqs_queue` - All SQS queues are tagged

## Non-Taggable Resources

❌ **Resources that don't support tagging**:

### IAM Policy Attachments
- ❌ `aws_iam_role_policy_attachment` - **Mitigation**: Parent IAM role is tagged
- ❌ `aws_iam_policy_attachment` - **Mitigation**: Parent IAM role/policy is tagged

### API Gateway Integrations
- ❌ `aws_apigatewayv2_integration` - **Mitigation**: Parent API Gateway is tagged
- ❌ `aws_apigatewayv2_route` - **Mitigation**: Parent API Gateway is tagged

### Lambda Permissions
- ❌ `aws_lambda_permission` - **Mitigation**: Parent Lambda function is tagged

### S3 Bucket Configurations
- ❌ `aws_s3_bucket_versioning` - **Mitigation**: Parent S3 bucket is tagged
- ❌ `aws_s3_bucket_encryption` - **Mitigation**: Parent S3 bucket is tagged
- ❌ `aws_s3_bucket_public_access_block` - **Mitigation**: Parent S3 bucket is tagged
- ❌ `aws_s3_bucket_lifecycle_configuration` - **Mitigation**: Parent S3 bucket is tagged

### DocumentDB Configurations
- ❌ `aws_docdb_cluster_snapshot` - **Mitigation**: Parent DocumentDB cluster is tagged

### Route Table Associations
- ❌ `aws_route_table_association` - **Mitigation**: Parent route table and subnet are tagged
- ❌ `aws_route` - **Mitigation**: Parent route table is tagged

### ACM Certificate Validations
- ❌ `aws_acm_certificate_validation` - **Mitigation**: Parent ACM certificate is tagged

## Provider Configuration

Both AWS providers are configured with default tags:

```hcl
# Main provider (us-east-1)
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.common_tags
  }
}

# Secondary provider for CloudFront resources (us-east-1)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
  default_tags {
    tags = local.common_tags
  }
}
```

## Cost Allocation Tag Activation

The following tags must be activated in AWS Billing → Cost Allocation Tags for the costs dashboard to function:

### Required for Dashboard Filtering:
- `application`
- `service` 
- `component`
- `environment`
- `cost_center`

### Additional Organizational Tags:
- `owner`
- `business_unit`
- `data_sensitivity`
- `managed_by`
- `repo`

### Legacy Tags (backwards compatibility):
- `Project`
- `Environment`
- `ManagedBy`

## Environment-Specific Values

Tag values vary by environment as defined in `.tfvars` files:

### Development (`dev.tfvars`)
```hcl
cost_center      = "CC-DEV-001"
data_sensitivity = "internal"
environment      = "dev"
```

### Staging (`staging.tfvars`)
```hcl
cost_center      = "CC-STG-002"
data_sensitivity = "internal"
environment      = "staging"
```

### Production (`prod.tfvars`)
```hcl
cost_center      = "CC-PROD-003"
data_sensitivity = "confidential"
environment      = "prod"
```

## Validation

- ✅ All taggable resources have appropriate tags applied
- ✅ Provider-level default_tags ensure consistent tagging
- ✅ Component-specific tag variations provide granular cost allocation
- ✅ Non-taggable resources are documented with mitigation strategies
- ✅ Environment-specific tfvars files provide proper tag values per environment

## Dashboard Integration

These tags enable the Costs Dashboard to:
- Filter costs by service, environment, component, and cost center
- Group costs by business unit and owner
- Track costs across different data sensitivity levels
- Separate managed vs. manual resource costs
- Provide environment-specific cost breakdowns

**Last Updated**: December 2024  
**Review Date**: Next infrastructure audit
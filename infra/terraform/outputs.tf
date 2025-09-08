# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "List of IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "List of IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

# S3 Bucket Outputs
output "s3_bucket_pdf_originals" {
  description = "Name of the S3 bucket for PDF originals"
  value       = aws_s3_bucket.pdf_originals.id
}

output "s3_bucket_pdf_derivatives" {
  description = "Name of the S3 bucket for PDF derivatives"
  value       = aws_s3_bucket.pdf_derivatives.id
}

output "s3_bucket_pdf_temp" {
  description = "Name of the S3 bucket for temporary files"
  value       = aws_s3_bucket.pdf_temp.id
}

output "s3_bucket_pdf_reports" {
  description = "Name of the S3 bucket for reports"
  value       = aws_s3_bucket.pdf_reports.id
}

output "s3_bucket_web_assets" {
  description = "Name of the S3 bucket for web assets"
  value       = aws_s3_bucket.web_assets.id
}

# DynamoDB Outputs
output "dynamodb_documents_table_name" {
  description = "Name of the documents DynamoDB table"
  value       = aws_dynamodb_table.documents.name
}

output "dynamodb_jobs_table_name" {
  description = "Name of the jobs DynamoDB table"
  value       = aws_dynamodb_table.jobs.name
}

output "dynamodb_user_sessions_table_name" {
  description = "Name of the user sessions DynamoDB table"
  value       = aws_dynamodb_table.user_sessions.name
}

# SQS Outputs
output "sqs_ingest_queue_url" {
  description = "URL of the ingest SQS queue"
  value       = aws_sqs_queue.ingest_queue.id
}

output "sqs_process_queue_url" {
  description = "URL of the process SQS queue"
  value       = aws_sqs_queue.process_queue.id
}

output "sqs_callback_queue_url" {
  description = "URL of the callback SQS queue"
  value       = aws_sqs_queue.callback_queue.id
}

output "sqs_priority_process_queue_url" {
  description = "URL of the priority process SQS queue"
  value       = aws_sqs_queue.priority_process_queue.id
}

# Cognito Outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito user pool client"
  value       = aws_cognito_user_pool_client.web_client.id
}

output "cognito_user_pool_domain" {
  description = "Domain of the Cognito user pool"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "cognito_identity_pool_id" {
  description = "ID of the Cognito identity pool"
  value       = aws_cognito_identity_pool.main.id
}

# API Gateway Outputs
output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "api_gateway_custom_domain" {
  description = "Custom domain for API Gateway (if configured)"
  value       = var.certificate_arn != "" ? "https://api.${var.domain_name}" : null
}

# Lambda Function Outputs
output "api_lambda_function_name" {
  description = "Name of the API Lambda function"
  value       = aws_lambda_function.api.function_name
}

output "api_lambda_function_arn" {
  description = "ARN of the API Lambda function"
  value       = aws_lambda_function.api.arn
}

output "api_lambda_function_url" {
  description = "Lambda Function URL (if enabled)"
  value       = var.use_lambda_function_url ? aws_lambda_function_url.api[0].function_url : null
}

output "webhook_secret_parameter_name" {
  description = "Name of the SSM parameter storing webhook secret"
  value       = aws_ssm_parameter.webhook_secret.name
}

# CloudFront Outputs
output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.web.id
}

output "cloudfront_distribution_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.web.domain_name
}

output "web_app_url" {
  description = "URL of the web application"
  value       = var.domain_name != "" && var.certificate_arn != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.web.domain_name}"
}

# ECR Outputs
output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value = {
    for k, v in aws_ecr_repository.lambda_repos : k => v.repository_url
  }
}

# IAM Outputs
output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions role (legacy)"
  value       = aws_iam_role.github_actions.arn
}

output "step_functions_role_arn" {
  description = "ARN of the Step Functions role"
  value       = aws_iam_role.step_functions.arn
}

# Enhanced GitHub OIDC Role Outputs
output "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = var.github_repo != "" ? aws_iam_openid_connect_provider.github_enhanced[0].arn : null
}

output "github_infrastructure_ci_role_arn" {
  description = "ARN of the GitHub Actions infrastructure CI role"
  value       = var.github_repo != "" ? aws_iam_role.github_infrastructure_ci[0].arn : null
}

output "github_lambda_deploy_role_arn" {
  description = "ARN of the GitHub Actions Lambda deploy role"
  value       = var.github_repo != "" ? aws_iam_role.github_lambda_deploy[0].arn : null
}

output "github_web_deploy_role_arn" {
  description = "ARN of the GitHub Actions web deploy role"
  value       = var.github_repo != "" ? aws_iam_role.github_web_deploy[0].arn : null
}

output "github_api_deploy_role_arn" {
  description = "ARN of the GitHub Actions API deploy role"
  value       = var.github_repo != "" ? aws_iam_role.github_api_deploy[0].arn : null
}

output "github_testing_role_arn" {
  description = "ARN of the GitHub Actions testing role"
  value       = var.github_repo != "" ? aws_iam_role.github_testing[0].arn : null
}

# GitHub Actions Role Configuration Summary
output "github_actions_roles_summary" {
  description = "Summary of all GitHub Actions roles and their purposes"
  value = var.github_repo != "" ? {
    infrastructure_ci = {
      arn         = aws_iam_role.github_infrastructure_ci[0].arn
      name        = aws_iam_role.github_infrastructure_ci[0].name
      description = "Terraform infrastructure deployment (main, develop, PRs)"
      branches    = ["main", "develop", "pull_request"]
    }
    lambda_deploy = {
      arn         = aws_iam_role.github_lambda_deploy[0].arn
      name        = aws_iam_role.github_lambda_deploy[0].name
      description = "Lambda function deployment (main, tags)"
      branches    = ["main", "refs/tags/*"]
    }
    web_deploy = {
      arn         = aws_iam_role.github_web_deploy[0].arn
      name        = aws_iam_role.github_web_deploy[0].name
      description = "Web application deployment (main only)"
      branches    = ["main"]
    }
    api_deploy = {
      arn         = aws_iam_role.github_api_deploy[0].arn
      name        = aws_iam_role.github_api_deploy[0].name
      description = "API deployment with blue/green strategy (main only)"
      branches    = ["main"]
    }
    testing = {
      arn         = aws_iam_role.github_testing[0].arn
      name        = aws_iam_role.github_testing[0].name
      description = "Testing workflows (main, develop, PRs)"
      branches    = ["main", "develop", "pull_request"]
    }
  } : null
}

# Step Functions Outputs
output "step_functions_state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.pdf_processing.arn
}

# KMS Outputs
output "kms_s3_key_id" {
  description = "ID of the S3 KMS key"
  value       = aws_kms_key.s3.key_id
}

output "kms_dynamodb_key_id" {
  description = "ID of the DynamoDB KMS key"
  value       = aws_kms_key.dynamodb.key_id
}

output "kms_sqs_key_id" {
  description = "ID of the SQS KMS key"
  value       = aws_kms_key.sqs.key_id
}

# Environment Configuration
output "environment_config" {
  description = "Environment configuration for applications"
  value = {
    region                  = var.aws_region
    project_name           = var.project_name
    environment            = var.environment
    vpc_id                 = aws_vpc.main.id
    private_subnet_ids     = aws_subnet.private[*].id
    api_gateway_url        = aws_apigatewayv2_api.main.api_endpoint
    api_lambda_function    = aws_lambda_function.api.function_name
    cognito_user_pool_id   = aws_cognito_user_pool.main.id
    cognito_client_id      = aws_cognito_user_pool_client.web_client.id
    cognito_domain         = aws_cognito_user_pool_domain.main.domain
    webhook_secret_param   = aws_ssm_parameter.webhook_secret.name
    web_app_url           = var.domain_name != "" && var.certificate_arn != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.web.domain_name}"
    lambda_function_url   = var.use_lambda_function_url ? aws_lambda_function_url.api[0].function_url : null
  }
  sensitive = false
}

# Resource Names (for reference)
output "resource_names" {
  description = "Names of all created resources"
  value = {
    s3_buckets = {
      originals   = aws_s3_bucket.pdf_originals.id
      derivatives = aws_s3_bucket.pdf_derivatives.id
      temp        = aws_s3_bucket.pdf_temp.id
      reports     = aws_s3_bucket.pdf_reports.id
      web_assets  = aws_s3_bucket.web_assets.id
    }
    dynamodb_tables = {
      documents     = aws_dynamodb_table.documents.name
      jobs          = aws_dynamodb_table.jobs.name
      user_sessions = aws_dynamodb_table.user_sessions.name
    }
    sqs_queues = {
      ingest   = aws_sqs_queue.ingest_queue.name
      process  = aws_sqs_queue.process_queue.name
      callback = aws_sqs_queue.callback_queue.name
      priority = aws_sqs_queue.priority_process_queue.name
    }
    ecr_repositories = {
      for k, v in aws_ecr_repository.lambda_repos : k => v.name
    }
  }
}

# Cognito Outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_user_pool_endpoint" {
  description = "Endpoint URL of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.endpoint
}

output "cognito_app_client_id" {
  description = "ID of the Cognito User Pool App Client"
  value       = aws_cognito_user_pool_client.web_client.id
}

output "cognito_domain" {
  description = "Domain name of the Cognito User Pool Domain"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "cognito_hosted_ui_url" {
  description = "URL for Cognito Hosted UI"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com"
}

output "cognito_identity_pool_id" {
  description = "ID of the Cognito Identity Pool"
  value       = aws_cognito_identity_pool.main.id
}

# Authentication URLs
output "auth_urls" {
  description = "Authentication-related URLs for frontend configuration"
  value = {
    login_url = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com/login?client_id=${aws_cognito_user_pool_client.web_client.id}&response_type=code&scope=email+openid+profile+aws.cognito.signin.user.admin&redirect_uri="
    logout_url = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com/logout?client_id=${aws_cognito_user_pool_client.web_client.id}&logout_uri="
    token_url = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com/oauth2/token"
    jwks_url = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.main.id}/.well-known/jwks.json"
  }
}

# DocumentDB Outputs
output "documentdb_cluster_endpoint" {
  description = "DocumentDB cluster endpoint"
  value       = aws_docdb_cluster.main.endpoint
}

output "documentdb_cluster_reader_endpoint" {
  description = "DocumentDB cluster reader endpoint"
  value       = aws_docdb_cluster.main.reader_endpoint
}

output "documentdb_cluster_port" {
  description = "DocumentDB cluster port"
  value       = aws_docdb_cluster.main.port
}

output "documentdb_cluster_members" {
  description = "List of DocumentDB cluster members"
  value       = aws_docdb_cluster.main.cluster_members
}

output "documentdb_security_group_id" {
  description = "ID of the DocumentDB security group"
  value       = aws_security_group.documentdb.id
}

output "documentdb_credentials_secret_name" {
  description = "Name of the Secrets Manager secret storing DocumentDB credentials"
  value       = aws_secretsmanager_secret.documentdb_credentials.name
}

output "documentdb_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret storing DocumentDB credentials"
  value       = aws_secretsmanager_secret.documentdb_credentials.arn
}

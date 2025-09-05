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
  description = "ARN of the GitHub Actions role"
  value       = aws_iam_role.github_actions.arn
}

output "step_functions_role_arn" {
  description = "ARN of the Step Functions role"
  value       = aws_iam_role.step_functions.arn
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
    region                    = var.aws_region
    project_name             = var.project_name
    environment              = var.environment
    vpc_id                   = aws_vpc.main.id
    private_subnet_ids       = aws_subnet.private[*].id
    api_gateway_url          = aws_apigatewayv2_api.main.api_endpoint
    cognito_user_pool_id     = aws_cognito_user_pool.main.id
    cognito_client_id        = aws_cognito_user_pool_client.web_client.id
    cognito_domain          = aws_cognito_user_pool_domain.main.domain
    web_app_url             = var.domain_name != "" && var.certificate_arn != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.web.domain_name}"
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
      temp       = aws_s3_bucket.pdf_temp.id
      reports    = aws_s3_bucket.pdf_reports.id
      web_assets = aws_s3_bucket.web_assets.id
    }
    dynamodb_tables = {
      documents     = aws_dynamodb_table.documents.name
      jobs         = aws_dynamodb_table.jobs.name
      user_sessions = aws_dynamodb_table.user_sessions.name
    }
    sqs_queues = {
      ingest    = aws_sqs_queue.ingest_queue.name
      process   = aws_sqs_queue.process_queue.name
      callback  = aws_sqs_queue.callback_queue.name
      priority  = aws_sqs_queue.priority_process_queue.name
    }
    ecr_repositories = {
      for k, v in aws_ecr_repository.lambda_repos : k => v.name
    }
  }
}
# Lambda Function for API Service
resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_execution.arn
  
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda_repos["api"].repository_url}:latest"
  
  timeout     = 30
  memory_size = 512
  
  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
  
  # Environment variables
  environment {
    variables = {
      # AWS Configuration
      AWS_REGION     = var.aws_region
      AWS_ACCOUNT_ID = data.aws_caller_identity.current.account_id
      
      # DynamoDB Tables
      DOCUMENTS_TABLE      = aws_dynamodb_table.documents.name
      JOBS_TABLE          = aws_dynamodb_table.jobs.name
      USER_SESSIONS_TABLE = aws_dynamodb_table.user_sessions.name
      
      # S3 Buckets
      PDF_ORIGINALS_BUCKET   = aws_s3_bucket.pdf_originals.bucket
      PDF_DERIVATIVES_BUCKET = aws_s3_bucket.pdf_derivatives.bucket
      PDF_TEMP_BUCKET        = aws_s3_bucket.pdf_temp.bucket
      PDF_REPORTS_BUCKET     = aws_s3_bucket.pdf_reports.bucket
      
      # SQS Queues
      INGEST_QUEUE_URL           = aws_sqs_queue.ingest_queue.url
      PROCESS_QUEUE_URL          = aws_sqs_queue.process_queue.url
      CALLBACK_QUEUE_URL         = aws_sqs_queue.callback_queue.url
      PRIORITY_PROCESS_QUEUE_URL = aws_sqs_queue.priority_process_queue.url
      
      # Cognito Configuration
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.web_client.id
      COGNITO_REGION       = var.aws_region
      
      # Security
      WEBHOOK_SECRET_KEY = random_password.webhook_secret.result
      
      # Configuration
      ENVIRONMENT = var.environment
      LOG_LEVEL   = var.log_level
      
      # Powertools Configuration
      POWERTOOLS_SERVICE_NAME        = "pdf-accessibility-api"
      POWERTOOLS_METRICS_NAMESPACE   = "PDF-Accessibility"
      POWERTOOLS_LOG_LEVEL          = var.log_level
      POWERTOOLS_LOGGER_SAMPLE_RATE = "0.1"
      POWERTOOLS_LOGGER_LOG_EVENT   = "false"
      POWERTOOLS_TRACER_CAPTURE_RESPONSE = "true"
      POWERTOOLS_TRACER_CAPTURE_ERROR    = "true"
      
      # CORS Origins
      CORS_ORIGINS = jsonencode([
        "http://localhost:3000",
        "https://localhost:3000",
        var.domain_name != "" ? "https://${var.domain_name}" : "https://example.com"
      ])
      
      # DocumentDB Configuration
      DOCUMENTDB_SECRET_NAME = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT = tostring(aws_docdb_cluster.main.port)
    }
  }
  
  # Tracing configuration
  tracing_config {
    mode = "Active"
  }
  
  # Dead letter queue configuration
  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }
  
  tags = merge(local.lambda_tags, {
    Name = "${local.name_prefix}-api-lambda"
    component = "api"
  })
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy.lambda_custom,
    aws_cloudwatch_log_group.lambda_api
  ]
}

# Lambda Security Group
resource "aws_security_group" "lambda_sg" {
  name_prefix = "${local.name_prefix}-lambda-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Lambda functions"
  
  # Allow outbound HTTPS for AWS services
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound for AWS services"
  }
  
  # Allow outbound DocumentDB access
  egress {
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [aws_security_group.documentdb.id]
    description     = "DocumentDB access"
  }
  
  # Allow outbound HTTP for general internet access (if needed)
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP outbound"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-sg"
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_api" {
  name              = "/aws/lambda/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# Lambda DLQ
resource "aws_sqs_queue" "lambda_dlq" {
  name                      = "${local.name_prefix}-lambda-dlq"
  message_retention_seconds = 1209600 # 14 days
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-dlq"
  })
}

# Random password for webhook secret
resource "random_password" "webhook_secret" {
  length  = 32
  special = true
}

# Store webhook secret in AWS Systems Manager Parameter Store
resource "aws_ssm_parameter" "webhook_secret" {
  name        = "/${local.name_prefix}/api/webhook-secret"
  description = "Webhook secret key for API service"
  type        = "SecureString"
  value       = random_password.webhook_secret.result
  
  tags = local.common_tags
}

# Lambda Function URL (Alternative to API Gateway for simpler setup)
resource "aws_lambda_function_url" "api" {
  count              = var.use_lambda_function_url ? 1 : 0
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
  
  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    expose_headers    = ["keep-alive", "date"]
    max_age          = 86400
  }
}

# Update API Gateway integration to use Lambda function
resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api.invoke_arn
  
  payload_format_version = "2.0"
}

# API Gateway routes for Lambda integration
resource "aws_apigatewayv2_route" "api_proxy" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

resource "aws_apigatewayv2_route" "api_root" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Lambda permission for Function URL (if enabled)
resource "aws_lambda_permission" "function_url" {
  count         = var.use_lambda_function_url ? 1 : 0
  statement_id  = "AllowExecutionFromFunctionURL"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "*"
  source_arn    = aws_lambda_function.api.arn
}
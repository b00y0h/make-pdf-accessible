# Router function infrastructure
# Processes ingest queue messages, normalizes inputs, creates jobs

# ECR Repository for router function
resource "aws_ecr_repository" "router" {
  name                 = "${local.app_name}-${var.environment}-router"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle_policy {
    policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 10 images"
          selection = {
            tagStatus     = "tagged"
            tagPrefixList = ["latest"]
            countType     = "imageCountMoreThan"
            countNumber   = 10
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
  }

  tags = local.common_tags
}

# IAM role for router function
resource "aws_iam_role" "router_lambda_role" {
  name = "${local.app_name}-${var.environment}-router-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for router function
resource "aws_iam_role_policy" "router_lambda_policy" {
  name = "${local.app_name}-${var.environment}-router-lambda-policy"
  role = aws_iam_role.router_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.app_name}-${var.environment}-router*"
      },
      # X-Ray tracing
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      },
      # SQS permissions
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.ingest_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.process_queue.arn,
          aws_sqs_queue.priority_process_queue.arn
        ]
      },
      # DynamoDB permissions
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.documents.arn,
          aws_dynamodb_table.jobs.arn
        ]
      },
      # S3 permissions
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.pdf_originals.arn}/*",
          "${aws_s3_bucket.pdf_temp.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.pdf_originals.arn,
          aws_s3_bucket.pdf_temp.arn
        ]
      }
    ]
  })
}

# Attach AWS managed policy for VPC access (if needed)
resource "aws_iam_role_policy_attachment" "router_lambda_vpc_policy" {
  count      = var.vpc_config != null ? 1 : 0
  role       = aws_iam_role.router_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda function
resource "aws_lambda_function" "router" {
  function_name = "${local.app_name}-${var.environment}-router"
  role          = aws_iam_role.router_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.router.repository_url}:latest"

  timeout     = 300  # 5 minutes
  memory_size = 512

  environment {
    variables = {
      DOCUMENTS_TABLE             = aws_dynamodb_table.documents.name
      JOBS_TABLE                 = aws_dynamodb_table.jobs.name
      PDF_ORIGINALS_BUCKET       = aws_s3_bucket.pdf_originals.bucket
      PROCESS_QUEUE_URL          = aws_sqs_queue.process_queue.url
      PRIORITY_PROCESS_QUEUE_URL = aws_sqs_queue.priority_process_queue.url
      POWERTOOLS_SERVICE_NAME    = "pdf-router"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                  = var.log_level
      ENVIRONMENT               = var.environment
    }
  }

  # VPC configuration (optional)
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  # X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  # Dead letter queue
  dead_letter_config {
    target_arn = aws_sqs_queue.dlq.arn
  }

  depends_on = [
    aws_iam_role_policy.router_lambda_policy,
    aws_cloudwatch_log_group.router_lambda_logs
  ]

  tags = local.common_tags

  # Ignore image URI changes (handled by CI/CD)
  lifecycle {
    ignore_changes = [image_uri]
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "router_lambda_logs" {
  name              = "/aws/lambda/${local.app_name}-${var.environment}-router"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}

# SQS trigger for router function
resource "aws_lambda_event_source_mapping" "router_sqs_trigger" {
  event_source_arn                   = aws_sqs_queue.ingest_queue.arn
  function_name                      = aws_lambda_function.router.function_name
  batch_size                        = var.sqs_batch_size
  maximum_batching_window_in_seconds = var.sqs_batching_window
  
  # Error handling
  scaling_config {
    maximum_concurrency = var.router_max_concurrency
  }

  depends_on = [aws_iam_role_policy.router_lambda_policy]

  tags = local.common_tags
}

# CloudWatch Alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "router_errors" {
  alarm_name          = "${local.app_name}-${var.environment}-router-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors router function errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions         = [aws_sns_topic.alerts.arn]
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.router.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "router_duration" {
  alarm_name          = "${local.app_name}-${var.environment}-router-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "240000"  # 4 minutes (80% of timeout)
  alarm_description   = "This metric monitors router function duration"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.router.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "router_throttles" {
  alarm_name          = "${local.app_name}-${var.environment}-router-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors router function throttles"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.router.function_name
  }

  tags = local.common_tags
}

# Custom CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "router" {
  dashboard_name = "${local.app_name}-${var.environment}-router"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.router.function_name],
            [".", "Errors", ".", "."],
            [".", "Throttles", ".", "."],
            [".", "Duration", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Router Function Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["PDF-Accessibility", "DocumentsProcessed", "service", "pdf-router"],
            [".", "DocumentsSkipped", ".", "."],
            [".", "ValidationErrors", ".", "."],
            [".", "AWSServiceErrors", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Document Processing Metrics"
          period  = 300
        }
      }
    ]
  })

  tags = local.common_tags
}

# Outputs
output "router_function_name" {
  description = "Name of the router Lambda function"
  value       = aws_lambda_function.router.function_name
}

output "router_function_arn" {
  description = "ARN of the router Lambda function"
  value       = aws_lambda_function.router.arn
}

output "router_ecr_repository_url" {
  description = "URL of the router ECR repository"
  value       = aws_ecr_repository.router.repository_url
}
# Processing Lambda Functions Infrastructure
# OCR, Structure, Alt Text, Tag PDF, Exports, Validate, Notify

locals {
  lambda_functions = {
    ocr = {
      description = "OCR processing with AWS Textract"
      timeout     = 900  # 15 minutes
      memory      = 1024
    }
    structure = {
      description = "Document structure analysis with Bedrock"
      timeout     = 600  # 10 minutes
      memory      = 1024
    }
    alt_text = {
      description = "Alt text generation with Bedrock Vision"
      timeout     = 600  # 10 minutes
      memory      = 512
    }
    tag_pdf = {
      description = "PDF accessibility tagging with pikepdf"
      timeout     = 300  # 5 minutes
      memory      = 1024
    }
    exports = {
      description = "Generate accessible exports (HTML/EPUB/CSV)"
      timeout     = 600  # 10 minutes
      memory      = 1024
    }
    validate = {
      description = "Accessibility validation checks"
      timeout     = 300  # 5 minutes
      memory      = 512
    }
    notify = {
      description = "Status notifications and DynamoDB updates"
      timeout     = 60   # 1 minute
      memory      = 256
    }
  }
}

# ECR Repositories for each function
resource "aws_ecr_repository" "processing_functions" {
  for_each = local.lambda_functions

  name                 = "${local.app_name}-${var.environment}-${each.key}"
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

# IAM role for processing Lambda functions
resource "aws_iam_role" "processing_lambda_role" {
  for_each = local.lambda_functions
  
  name = "${local.app_name}-${var.environment}-${each.key}-lambda-role"

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

# IAM policy for processing Lambda functions
resource "aws_iam_role_policy" "processing_lambda_policy" {
  for_each = local.lambda_functions
  
  name = "${local.app_name}-${var.environment}-${each.key}-lambda-policy"
  role = aws_iam_role.processing_lambda_role[each.key].id

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
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.app_name}-${var.environment}-${each.key}*"
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
      # S3 permissions for all buckets
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.pdf_originals.arn}/*",
          "${aws_s3_bucket.pdf_temp.arn}/*",
          "${aws_s3_bucket.pdf_derivatives.arn}/*",
          "${aws_s3_bucket.pdf_accessible.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.pdf_originals.arn,
          aws_s3_bucket.pdf_temp.arn,
          aws_s3_bucket.pdf_derivatives.arn,
          aws_s3_bucket.pdf_accessible.arn
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
      # Textract permissions (for OCR function)
      {
        Effect = "Allow"
        Action = [
          "textract:StartDocumentAnalysis",
          "textract:GetDocumentAnalysis"
        ]
        Resource = "*"
      },
      # Bedrock permissions (for structure and alt-text functions)
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:model/anthropic.claude-3-5-sonnet-*",
          "arn:aws:bedrock:*:*:model/anthropic.claude-3-haiku-*"
        ]
      },
      # Rekognition permissions (for alt-text function)
      {
        Effect = "Allow"
        Action = [
          "rekognition:DetectLabels",
          "rekognition:DetectText"
        ]
        Resource = "*"
      },
      # SNS permissions (for notify function)
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.alerts.arn,
          aws_sns_topic.notifications.arn
        ]
      },
      # Secrets Manager permissions for DocumentDB credentials
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.documentdb_credentials.arn
        ]
      }
    ]
  })
}

# Attach AWS managed policy for VPC access (if needed)
resource "aws_iam_role_policy_attachment" "processing_lambda_vpc_policy" {
  for_each = var.vpc_config != null ? local.lambda_functions : {}
  
  role       = aws_iam_role.processing_lambda_role[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda functions
resource "aws_lambda_function" "ocr" {
  function_name = "${local.app_name}-${var.environment}-ocr"
  role          = aws_iam_role.processing_lambda_role["ocr"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["ocr"].repository_url}:latest"

  timeout     = local.lambda_functions["ocr"].timeout
  memory_size = local.lambda_functions["ocr"].memory

  environment {
    variables = {
      PDF_DERIVATIVES_BUCKET      = aws_s3_bucket.pdf_derivatives.bucket
      PDF_ORIGINALS_BUCKET        = aws_s3_bucket.pdf_originals.bucket
      POWERTOOLS_SERVICE_NAME     = "pdf-ocr"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "structure" {
  function_name = "${local.app_name}-${var.environment}-structure"
  role          = aws_iam_role.processing_lambda_role["structure"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["structure"].repository_url}:latest"

  timeout     = local.lambda_functions["structure"].timeout
  memory_size = local.lambda_functions["structure"].memory

  environment {
    variables = {
      PDF_DERIVATIVES_BUCKET      = aws_s3_bucket.pdf_derivatives.bucket
      PDF_ORIGINALS_BUCKET        = aws_s3_bucket.pdf_originals.bucket
      POWERTOOLS_SERVICE_NAME     = "pdf-structure"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "alt_text" {
  function_name = "${local.app_name}-${var.environment}-alt-text"
  role          = aws_iam_role.processing_lambda_role["alt_text"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["alt_text"].repository_url}:latest"

  timeout     = local.lambda_functions["alt_text"].timeout
  memory_size = local.lambda_functions["alt_text"].memory

  environment {
    variables = {
      PDF_DERIVATIVES_BUCKET      = aws_s3_bucket.pdf_derivatives.bucket
      PDF_ORIGINALS_BUCKET        = aws_s3_bucket.pdf_originals.bucket
      POWERTOOLS_SERVICE_NAME     = "pdf-alt-text"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "tag_pdf" {
  function_name = "${local.app_name}-${var.environment}-tag-pdf"
  role          = aws_iam_role.processing_lambda_role["tag_pdf"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["tag_pdf"].repository_url}:latest"

  timeout     = local.lambda_functions["tag_pdf"].timeout
  memory_size = local.lambda_functions["tag_pdf"].memory

  environment {
    variables = {
      PDF_DERIVATIVES_BUCKET      = aws_s3_bucket.pdf_derivatives.bucket
      PDF_ACCESSIBLE_BUCKET       = aws_s3_bucket.pdf_accessible.bucket
      POWERTOOLS_SERVICE_NAME     = "pdf-tagger"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "exports" {
  function_name = "${local.app_name}-${var.environment}-exports"
  role          = aws_iam_role.processing_lambda_role["exports"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["exports"].repository_url}:latest"

  timeout     = local.lambda_functions["exports"].timeout
  memory_size = local.lambda_functions["exports"].memory

  environment {
    variables = {
      PDF_DERIVATIVES_BUCKET      = aws_s3_bucket.pdf_derivatives.bucket
      PDF_ACCESSIBLE_BUCKET       = aws_s3_bucket.pdf_accessible.bucket
      POWERTOOLS_SERVICE_NAME     = "pdf-exports"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "validate" {
  function_name = "${local.app_name}-${var.environment}-validate"
  role          = aws_iam_role.processing_lambda_role["validate"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["validate"].repository_url}:latest"

  timeout     = local.lambda_functions["validate"].timeout
  memory_size = local.lambda_functions["validate"].memory

  environment {
    variables = {
      PDF_DERIVATIVES_BUCKET      = aws_s3_bucket.pdf_derivatives.bucket
      PDF_ACCESSIBLE_BUCKET       = aws_s3_bucket.pdf_accessible.bucket
      POWERTOOLS_SERVICE_NAME     = "pdf-validator"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "notify" {
  function_name = "${local.app_name}-${var.environment}-notify"
  role          = aws_iam_role.processing_lambda_role["notify"].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.processing_functions["notify"].repository_url}:latest"

  timeout     = local.lambda_functions["notify"].timeout
  memory_size = local.lambda_functions["notify"].memory

  environment {
    variables = {
      DOCUMENTS_TABLE             = aws_dynamodb_table.documents.name
      JOBS_TABLE                  = aws_dynamodb_table.jobs.name
      NOTIFICATIONS_TOPIC_ARN     = aws_sns_topic.notifications.arn
      POWERTOOLS_SERVICE_NAME     = "pdf-notifier"
      POWERTOOLS_METRICS_NAMESPACE = "PDF-Accessibility"
      LOG_LEVEL                   = var.log_level
      ENVIRONMENT                 = var.environment
      DOCUMENTDB_SECRET_NAME      = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT         = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT             = tostring(aws_docdb_cluster.main.port)
    }
  }

  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy.processing_lambda_policy,
    aws_cloudwatch_log_group.processing_lambda_logs
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "processing_lambda_logs" {
  for_each = local.lambda_functions
  
  name              = "/aws/lambda/${local.app_name}-${var.environment}-${each.key}"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}

# Outputs
output "processing_lambda_arns" {
  description = "ARNs of all processing Lambda functions"
  value = {
    ocr       = aws_lambda_function.ocr.arn
    structure = aws_lambda_function.structure.arn
    alt_text  = aws_lambda_function.alt_text.arn
    tag_pdf   = aws_lambda_function.tag_pdf.arn
    exports   = aws_lambda_function.exports.arn
    validate  = aws_lambda_function.validate.arn
    notify    = aws_lambda_function.notify.arn
  }
}

output "processing_ecr_repositories" {
  description = "ECR repository URLs for processing functions"
  value = {
    for k, v in aws_ecr_repository.processing_functions : k => v.repository_url
  }
}
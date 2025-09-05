# ECR Repositories for Lambda Functions
locals {
  lambda_functions = [
    "api",
    "worker",
    "router",
    "ocr",
    "structure",
    "tagger",
    "exporter",
    "validator",
    "notifier"
  ]
}

resource "aws_ecr_repository" "lambda_repos" {
  for_each = toset(local.lambda_functions)

  name                 = "${local.name_prefix}-${each.value}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-${each.value}-ecr"
    Service = each.value
    Purpose = "Container registry for ${each.value} Lambda function"
  })
}

# ECR Lifecycle Policies
resource "aws_ecr_lifecycle_policy" "lambda_repos" {
  for_each   = aws_ecr_repository.lambda_repos
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 production images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["prod", "v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 5 development images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["dev", "staging", "test"]
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECR Repository Policies (allow cross-account access if needed)
resource "aws_ecr_repository_policy" "lambda_repos" {
  for_each   = aws_ecr_repository.lambda_repos
  repository = each.value.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPull"
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
          ]
        }
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}
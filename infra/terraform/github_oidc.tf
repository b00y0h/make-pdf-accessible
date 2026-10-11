# GitHub OIDC Provider and IAM Roles for CI/CD Workflows
# This file implements secure OIDC authentication for GitHub Actions workflows
# with least-privilege IAM roles for each workflow type

# GitHub OIDC Provider (enhanced version)
resource "aws_iam_openid_connect_provider" "github_enhanced" {
  count = var.github_repo != "" ? 1 : 0

  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  # Updated thumbprints for GitHub Actions OIDC
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1", # GitHub's current thumbprint
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"  # Backup thumbprint
  ]

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-github-oidc-provider"
    Description = "OIDC provider for GitHub Actions workflows"
  })
}

# Local values for OIDC configuration
locals {
  github_oidc_provider_arn = var.github_repo != "" ? aws_iam_openid_connect_provider.github_enhanced[0].arn : ""

  # The subject (sub claim) GitHub presents depends on the job. A job that declares a GitHub
  # environment presents environment:<name> instead of its branch, so a role used by such a job
  # has to trust that environment. Who may deploy to an environment, and from which branch, is
  # then set on the environment in GitHub (required reviewers, deployment branches).
  github_subjects = {
    main         = "repo:${var.github_repo}:ref:refs/heads/main"
    develop      = "repo:${var.github_repo}:ref:refs/heads/develop"
    pull_request = "repo:${var.github_repo}:pull_request"
    tags         = "repo:${var.github_repo}:ref:refs/tags/*"
    infra_env    = "repo:${var.github_repo}:environment:${var.environment}-infrastructure"
    web_env      = "repo:${var.github_repo}:environment:${var.environment}-web"
    api_env      = "repo:${var.github_repo}:environment:${var.environment}-api"
  }

  github_role_subjects = {
    # infra-ci.yml: plans on pull requests and from main, applies in <env>-infrastructure
    infrastructure_ci = [
      local.github_subjects.main,
      local.github_subjects.develop,
      local.github_subjects.pull_request,
      local.github_subjects.infra_env,
    ]
    # build-and-deploy-lambda.yml declares no environment
    lambda_deploy = [local.github_subjects.main, local.github_subjects.tags]
    # marketing-site.yml and web-ci.yml deploy only in <env>-web, so every use of this role
    # goes through that environment's protection rules
    web_deploy = [local.github_subjects.web_env]
    # api-ci.yml packages from main and deploys in <env>-api
    api_deploy = [local.github_subjects.main, local.github_subjects.api_env]
    testing = [
      local.github_subjects.main,
      local.github_subjects.develop,
      local.github_subjects.pull_request,
    ]
  }

  # One StringLike list per role. Building these with merge() kept only the last StringLike
  # block, so each role trusted a single subject and environment-scoped jobs matched none.
  github_trust_conditions = {
    for role, subjects in local.github_role_subjects : role => {
      StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
      }
      StringLike = {
        "token.actions.githubusercontent.com:sub" = subjects
      }
    }
  }
}

# 1. Infrastructure CI Role (for Terraform operations)
resource "aws_iam_role" "github_infrastructure_ci" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-infra-ci-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = local.github_trust_conditions.infrastructure_ci
      }
    ]
  })

  max_session_duration = var.github_oidc_session_duration

  tags = merge(local.common_tags, {
    Name         = "${local.name_prefix}-github-infra-ci-role"
    Description  = "Role for GitHub Actions infrastructure CI workflows"
    WorkflowType = "infrastructure-ci"
  })
}

# Infrastructure CI Role Policy
resource "aws_iam_role_policy" "github_infrastructure_ci" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-infra-ci-policy"
  role = aws_iam_role.github_infrastructure_ci[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Terraform state management
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-terraform-state-*",
          "arn:aws:s3:::${var.project_name}-terraform-state-*/*"
        ]
      },
      # DynamoDB state locking
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = "arn:aws:dynamodb:*:*:table/${var.project_name}-terraform-locks-*"
      },
      # Read-only access for Terraform plan
      {
        Effect = "Allow"
        Action = [
          "iam:Get*",
          "iam:List*",
          "s3:Get*",
          "s3:List*",
          "lambda:Get*",
          "lambda:List*",
          "dynamodb:Describe*",
          "dynamodb:List*",
          "sqs:Get*",
          "sqs:List*",
          "ecr:Describe*",
          "ecr:List*",
          "apigateway:GET",
          "cloudfront:Get*",
          "cloudfront:List*",
          "cognito-idp:Describe*",
          "cognito-idp:List*",
          "cognito-identity:Describe*",
          "cognito-identity:List*",
          "kms:Describe*",
          "kms:List*",
          "states:Describe*",
          "states:List*",
          "vpc:Describe*",
          "ec2:Describe*"
        ]
        Resource = "*"
      },
      # Full access for Terraform apply (main branch only)
      {
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:ref" = "refs/heads/main"
          }
        }
      }
    ]
  })
}

# 2. Lambda Build and Deploy Role
resource "aws_iam_role" "github_lambda_deploy" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-lambda-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = local.github_trust_conditions.lambda_deploy
      }
    ]
  })

  max_session_duration = var.github_oidc_session_duration

  tags = merge(local.common_tags, {
    Name         = "${local.name_prefix}-github-lambda-deploy-role"
    Description  = "Role for GitHub Actions Lambda build and deploy workflows"
    WorkflowType = "lambda-deploy"
  })
}

# Lambda Deploy Role Policy
resource "aws_iam_role_policy" "github_lambda_deploy" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-lambda-deploy-policy"
  role = aws_iam_role.github_lambda_deploy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR permissions for container images
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
          "ecr:ListImages"
        ]
        Resource = [
          "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${local.name_prefix}-*"
        ]
      },
      # ECR token access (global)
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      # Lambda function updates
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:PublishVersion",
          "lambda:CreateAlias",
          "lambda:UpdateAlias",
          "lambda:GetAlias",
          "lambda:ListAliases",
          "lambda:ListVersionsByFunction",
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.name_prefix}-*"
        ]
      },
      # CloudWatch Logs for monitoring deployments
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}-*"
        ]
      }
    ]
  })
}

# 3. Web Application Deploy Role
resource "aws_iam_role" "github_web_deploy" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-web-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = local.github_trust_conditions.web_deploy
      }
    ]
  })

  max_session_duration = var.github_oidc_session_duration

  tags = merge(local.common_tags, {
    Name         = "${local.name_prefix}-github-web-deploy-role"
    Description  = "Role for GitHub Actions web application deploy workflows"
    WorkflowType = "web-deploy"
  })
}

# Web Deploy Role Policy
resource "aws_iam_role_policy" "github_web_deploy" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-web-deploy-policy"
  role = aws_iam_role.github_web_deploy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 permissions for web assets
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning"
        ]
        Resource = [
          "arn:aws:s3:::${local.name_prefix}-web-*",
          "arn:aws:s3:::${local.name_prefix}-web-*/*",
          "arn:aws:s3:::${local.name_prefix}-marketing-*",
          "arn:aws:s3:::${local.name_prefix}-marketing-*/*"
        ]
      },
      # Deploy-target discovery (bucket and distribution lookup by name/tag)
      {
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:GetBucketTagging",
          "cloudfront:ListDistributions",
          "cloudfront:ListTagsForResource"
        ]
        Resource = "*"
      },
      # CloudFront invalidation
      {
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
          "cloudfront:GetInvalidation",
          "cloudfront:ListInvalidations",
          "cloudfront:GetDistribution",
          "cloudfront:GetDistributionConfig"
        ]
        Resource = [
          "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/*"
        ]
      },
      # CloudWatch Logs for deployment monitoring
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/github-actions/web-deploy"
        ]
      }
    ]
  })
}

# 4. API Deploy Role (with blue/green deployment capabilities)
resource "aws_iam_role" "github_api_deploy" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-api-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = local.github_trust_conditions.api_deploy
      }
    ]
  })

  max_session_duration = var.github_oidc_session_duration

  tags = merge(local.common_tags, {
    Name         = "${local.name_prefix}-github-api-deploy-role"
    Description  = "Role for GitHub Actions API deploy workflows with blue/green deployment"
    WorkflowType = "api-deploy"
  })
}

# API Deploy Role Policy
resource "aws_iam_role_policy" "github_api_deploy" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-api-deploy-policy"
  role = aws_iam_role.github_api_deploy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Lambda permissions for API deployment
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:PublishVersion",
          "lambda:CreateAlias",
          "lambda:UpdateAlias",
          "lambda:GetAlias",
          "lambda:ListAliases",
          "lambda:ListVersionsByFunction",
          "lambda:InvokeFunction",
          "lambda:GetProvisionedConcurrencyConfig",
          "lambda:PutProvisionedConcurrencyConfig",
          "lambda:DeleteProvisionedConcurrencyConfig"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.name_prefix}-api*"
        ]
      },
      # API Gateway permissions for blue/green deployment
      {
        Effect = "Allow"
        Action = [
          "apigateway:GET",
          "apigateway:POST",
          "apigateway:PUT",
          "apigateway:PATCH",
          "apigateway:DELETE",
          "apigateway:UpdateStage",
          "apigateway:CreateDeployment",
          "apigateway:GetDeployment",
          "apigateway:GetDeployments",
          "apigateway:GetStage",
          "apigateway:GetStages"
        ]
        Resource = [
          "arn:aws:apigateway:${var.aws_region}::/restapis/*",
          "arn:aws:apigateway:${var.aws_region}::/apis/*"
        ]
      },
      # CloudWatch for health checks and monitoring
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData",
          "cloudwatch:ListMetrics",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:FilterLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}-api*",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/github-actions/api-deploy"
        ]
      },
      # DynamoDB access for health checks
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
          "dynamodb:GetItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-*"
        ]
      }
    ]
  })
}

# 5. Testing Role (for running tests in CI)
resource "aws_iam_role" "github_testing" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-testing-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = local.github_trust_conditions.testing
      }
    ]
  })

  max_session_duration = var.github_oidc_session_duration

  tags = merge(local.common_tags, {
    Name         = "${local.name_prefix}-github-testing-role"
    Description  = "Role for GitHub Actions testing workflows"
    WorkflowType = "testing"
  })
}

# Testing Role Policy
resource "aws_iam_role_policy" "github_testing" {
  count = var.github_repo != "" ? 1 : 0

  name = "${local.name_prefix}-github-testing-policy"
  role = aws_iam_role.github_testing[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Read-only access for testing
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-test-*"
        ]
      },
      # S3 access for test artifacts
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.name_prefix}-test-*",
          "arn:aws:s3:::${local.name_prefix}-test-*/*"
        ]
      },
      # Lambda invocation for integration tests
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:GetFunction"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.name_prefix}-*"
        ]
      },
      # CloudWatch Logs for test results
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/github-actions/testing"
        ]
      }
    ]
  })
}

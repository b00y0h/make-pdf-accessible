# Marketing site preview: the static-site module on its *.cloudfront.net address, plus a deploy
# role for .github/workflows/marketing-site.yml. It lets a non-production environment show the
# marketing site without the platform root (custom domain, certificate, WAF, logs bucket).
#
# Kept apart from the platform root and the account layer on purpose: it owns only its own state
# key, so applying it never touches shared resources. See README.md.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.common_tags
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    application      = var.application
    service          = "marketing"
    component        = "marketing"
    environment      = var.environment
    cost_center      = var.cost_center
    owner            = var.owner
    business_unit    = var.business_unit
    data_sensitivity = "public"
    managed_by       = "terraform"
    repo             = var.repo
    Project          = var.project_name
    ManagedBy        = "terraform"
  }

  # A job that declares a GitHub environment presents environment:<name> as its subject, so the
  # role trusts exactly the <env>-web environment the deploy job runs in (as in ../github_oidc.tf).
  github_web_subject = "repo:${var.github_repo}:environment:${var.environment}-web"
}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

module "marketing_site" {
  source = "../modules/static-site"

  name        = "${local.name_prefix}-marketing-preview"
  bucket_name = "${local.name_prefix}-marketing-site-${var.aws_account_id}"
  # The workflow's fallback discovery matches distributions whose comment starts with "Marketing site".
  comment = "Marketing site - preview (${var.environment})"

  tags = {
    service = "cloudfront"
  }
}

resource "aws_iam_role" "github_web_deploy" {
  name        = "${local.name_prefix}-marketing-preview-deploy"
  description = "GitHub Actions deploy role for the ${var.environment} marketing site preview"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = local.github_web_subject
          }
        }
      }
    ]
  })

  max_session_duration = 3600
}

# Only what marketing-site.yml's publish step does: sync one bucket, invalidate and read one
# distribution. Target discovery is not needed because the environment sets both ids.
resource "aws_iam_role_policy" "github_web_deploy" {
  name = "publish-marketing-site"
  role = aws_iam_role.github_web_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListSiteBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = module.marketing_site.bucket_arn
      },
      {
        Sid      = "WriteSiteObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${module.marketing_site.bucket_arn}/*"
      },
      {
        Sid    = "InvalidateAndReadDistribution"
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
          "cloudfront:GetInvalidation",
          "cloudfront:GetDistribution",
        ]
        Resource = module.marketing_site.distribution_arn
      }
    ]
  })
}

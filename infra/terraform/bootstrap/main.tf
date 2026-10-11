# One-time bootstrap per AWS account: for each environment hosted in the account, the S3 bucket
# and DynamoDB table that hold Terraform state for the platform root. Run with an administrator
# credential before the first `terraform init` of infra/terraform in that account; afterwards the
# GitHub OIDC roles created by the root take over.
#
#   cd infra/terraform/bootstrap
#   terraform init
#   terraform workspace new dev    # this root keeps local state: one workspace per account
#   AWS_PROFILE=pdf-dev terraform apply -var 'environments=["dev","staging"]'
#   terraform workspace new prod
#   AWS_PROFILE=pdf-prod terraform apply -var 'environments=["prod"]'

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Refuses to create one environment's state bucket in another environment's account
  allowed_account_ids = [local.account_id]

  default_tags {
    tags = {
      application      = "accesspdf"
      service          = "terraform-state"
      component        = "platform"
      cost_center      = var.cost_center
      owner            = "team-platform"
      business_unit    = "RnD"
      data_sensitivity = "confidential"
      managed_by       = "terraform"
      repo             = "github.com/b00y0h/make-pdf-accessible"
    }
  }
}

# Separate state per environment, even when two environments share an account, so each
# environment's deploy role can be limited to its own bucket and table.
locals {
  # The AWS account each environment lives in (ADR-0010): dev and staging share the dev account.
  # Keep in step with aws_account_id in ../environments/<env>.tfvars.
  account_ids = {
    dev     = "403030570295"
    staging = "403030570295"
    prod    = "774697187580"
  }

  # var.environments is validated to name a single account
  account_id = one(distinct([for e in var.environments : local.account_ids[e]]))

  bucket_names = { for e in var.environments : e => "${var.project_name}-terraform-state-${e}" }
  table_names  = { for e in var.environments : e => "${var.project_name}-terraform-locks-${e}" }
}

resource "aws_s3_bucket" "state" {
  for_each = local.bucket_names

  bucket = each.value

  # Object Lock (governance) protects state history from accidental deletion.
  object_lock_enabled = true

  tags = {
    Name        = each.value
    environment = each.key
  }

  # Dropping an environment from var.environments, or applying another account's set against this
  # state, must fail instead of deleting live state storage.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  for_each = aws_s3_bucket.state

  bucket = each.value.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  for_each = aws_s3_bucket.state

  bucket = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  for_each = aws_s3_bucket.state

  bucket = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_object_lock_configuration" "state" {
  for_each = aws_s3_bucket.state

  bucket = each.value.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 30
    }
  }

  depends_on = [aws_s3_bucket_versioning.state]
}

resource "aws_s3_bucket_policy" "state" {
  for_each = aws_s3_bucket.state

  bucket = each.value.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          each.value.arn,
          "${each.value.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.state]
}

resource "aws_dynamodb_table" "locks" {
  for_each = local.table_names

  name         = each.value
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = each.value
    environment = each.key
  }

  lifecycle {
    prevent_destroy = true
  }
}

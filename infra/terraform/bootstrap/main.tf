# One-time bootstrap per AWS account: the S3 bucket and DynamoDB table that hold Terraform state
# for the platform root. Run with an administrator credential before the first `terraform init`
# of infra/terraform in that account; afterwards the GitHub OIDC roles created by the root take over.
#
#   cd infra/terraform/bootstrap
#   terraform init
#   terraform apply -var environment=dev

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

  default_tags {
    tags = {
      application      = "accesspdf"
      service          = "terraform-state"
      component        = "platform"
      environment      = var.environment
      cost_center      = var.cost_center
      owner            = "team-platform"
      business_unit    = "R&D"
      data_sensitivity = "confidential"
      managed_by       = "terraform"
      repo             = "github.com/b00y0h/make-pdf-accessible"
    }
  }
}

locals {
  bucket_name = "${var.project_name}-terraform-state-${var.environment}"
  table_name  = "${var.project_name}-terraform-locks-${var.environment}"
}

resource "aws_s3_bucket" "state" {
  bucket = local.bucket_name

  # Object Lock (governance) protects state history from accidental deletion.
  object_lock_enabled = true

  tags = {
    Name = local.bucket_name
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_object_lock_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 30
    }
  }

  depends_on = [aws_s3_bucket_versioning.state]
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.state.arn,
          "${aws_s3_bucket.state.arn}/*"
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
  name         = local.table_name
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
    Name = local.table_name
  }
}

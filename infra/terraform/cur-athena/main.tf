# CUR to Athena Pipeline Infrastructure
# This module creates the necessary AWS resources for Cost and Usage Report (CUR) 
# delivery to S3 and analysis via Athena

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Local variables for resource naming and configuration
locals {
  name_prefix = var.name_prefix
  environment = var.environment
  
  # Common tags applied to all resources
  common_tags = merge(var.additional_tags, {
    Environment   = var.environment
    Project       = "AccessPDF-CostsDashboard"
    Component     = "CUR-Athena"
    ManagedBy     = "Terraform"
    Application   = "cost-analytics"
  })
  
  # CUR report configuration
  cur_report_name = "${local.name_prefix}-cur-report"
  
  # S3 bucket names (must be globally unique)
  cur_bucket_name     = "${local.name_prefix}-cur-data-${random_id.bucket_suffix.hex}"
  athena_bucket_name  = "${local.name_prefix}-athena-results-${random_id.bucket_suffix.hex}"
  
  # Glue database and table names
  glue_database_name = "${local.name_prefix}_cost_analytics"
  glue_table_name    = "${local.name_prefix}_cur_table"
  
  # Athena workgroup name
  athena_workgroup_name = "${local.name_prefix}-cost-analytics"
}

# Random suffix for S3 bucket names to ensure global uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 bucket for CUR data storage
resource "aws_s3_bucket" "cur_data" {
  bucket = local.cur_bucket_name
  tags   = local.common_tags
}

# S3 bucket versioning for CUR data
resource "aws_s3_bucket_versioning" "cur_data" {
  bucket = aws_s3_bucket.cur_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket server-side encryption for CUR data
resource "aws_s3_bucket_server_side_encryption_configuration" "cur_data" {
  bucket = aws_s3_bucket.cur_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block for CUR data
resource "aws_s3_bucket_public_access_block" "cur_data" {
  bucket = aws_s3_bucket.cur_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle configuration for CUR data
resource "aws_s3_bucket_lifecycle_configuration" "cur_data" {
  bucket = aws_s3_bucket.cur_data.id

  rule {
    id     = "cur_data_lifecycle"
    status = "Enabled"

    # Transition to IA after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete after specified retention period
    expiration {
      days = var.cur_data_retention_days
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 bucket policy for CUR delivery
resource "aws_s3_bucket_policy" "cur_data" {
  bucket = aws_s3_bucket.cur_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCURDelivery"
        Effect = "Allow"
        Principal = {
          Service = "billingreports.amazonaws.com"
        }
        Action = [
          "s3:GetBucketAcl",
          "s3:GetBucketPolicy"
        ]
        Resource = aws_s3_bucket.cur_data.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          StringLike = {
            "aws:SourceArn" = "arn:aws:cur:us-east-1:${data.aws_caller_identity.current.account_id}:definition/*"
          }
        }
      },
      {
        Sid    = "AllowCURDeliveryObjects"
        Effect = "Allow"
        Principal = {
          Service = "billingreports.amazonaws.com"
        }
        Action = "s3:PutObject"
        Resource = "${aws_s3_bucket.cur_data.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          StringLike = {
            "aws:SourceArn" = "arn:aws:cur:us-east-1:${data.aws_caller_identity.current.account_id}:definition/*"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.cur_data]
}

# S3 bucket for Athena query results
resource "aws_s3_bucket" "athena_results" {
  bucket = local.athena_bucket_name
  tags   = local.common_tags
}

# S3 bucket server-side encryption for Athena results
resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block for Athena results
resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle configuration for Athena results
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "athena_results_lifecycle"
    status = "Enabled"

    # Delete query results after 30 days
    expiration {
      days = 30
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Cost and Usage Report definition
resource "aws_cur_report_definition" "main" {
  report_name          = local.cur_report_name
  time_unit            = "HOURLY"
  format               = "Parquet"
  compression          = "GZIP"
  additional_schema_elements = ["RESOURCES"]
  s3_bucket            = aws_s3_bucket.cur_data.bucket
  s3_prefix            = "cur-data"
  s3_region            = data.aws_region.current.name
  additional_artifacts = ["ATHENA"]
  
  # Enable refresh for closed reports
  refresh_closed_reports = true
  
  # Report versioning for schema changes
  report_versioning = "OVERWRITE_REPORT"

  tags = local.common_tags
}

# Data sources for current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
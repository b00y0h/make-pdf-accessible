# KMS Key for S3 Encryption
resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-kms-key"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# S3 Bucket: PDF Originals
resource "aws_s3_bucket" "pdf_originals" {
  bucket = "${local.name_prefix}-pdf-originals-${local.name_suffix}"

  tags = merge(local.storage_tags, {
    Name      = "${local.name_prefix}-pdf-originals"
    Purpose   = "Store original PDF files"
    DataClass = "sensitive"
  })
}

# S3 Bucket: PDF Derivatives
resource "aws_s3_bucket" "pdf_derivatives" {
  bucket = "${local.name_prefix}-pdf-derivatives-${local.name_suffix}"

  tags = merge(local.storage_tags, {
    Name      = "${local.name_prefix}-pdf-derivatives"
    Purpose   = "Store processed/accessible PDF files"
    DataClass = "processed"
  })
}

# S3 Bucket: PDF Temp
resource "aws_s3_bucket" "pdf_temp" {
  bucket = "${local.name_prefix}-pdf-temp-${local.name_suffix}"

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-pdf-temp"
    Purpose   = "Temporary storage during processing"
    DataClass = "temporary"
  })
}

# S3 Bucket: PDF Reports
resource "aws_s3_bucket" "pdf_reports" {
  bucket = "${local.name_prefix}-pdf-reports-${local.name_suffix}"

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-pdf-reports"
    Purpose   = "Store accessibility reports and analysis"
    DataClass = "reports"
  })
}

# S3 Bucket: Web Assets
resource "aws_s3_bucket" "web_assets" {
  bucket = "${local.name_prefix}-web-assets-${local.name_suffix}"

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-web-assets"
    Purpose   = "Store web application assets"
    DataClass = "public"
  })
}

# S3 Bucket Configurations - PDF Originals
resource "aws_s3_bucket_server_side_encryption_configuration" "pdf_originals" {
  bucket = aws_s3_bucket.pdf_originals.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "pdf_originals" {
  bucket = aws_s3_bucket.pdf_originals.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "pdf_originals" {
  bucket = aws_s3_bucket.pdf_originals.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "pdf_originals" {
  bucket = aws_s3_bucket.pdf_originals.id

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }

  rule {
    id     = "delete_incomplete_multipart_uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 Bucket Configurations - PDF Derivatives
resource "aws_s3_bucket_server_side_encryption_configuration" "pdf_derivatives" {
  bucket = aws_s3_bucket.pdf_derivatives.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "pdf_derivatives" {
  bucket = aws_s3_bucket.pdf_derivatives.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "pdf_derivatives" {
  bucket = aws_s3_bucket.pdf_derivatives.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "pdf_derivatives" {
  bucket = aws_s3_bucket.pdf_derivatives.id

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 60
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

# S3 Bucket Configurations - PDF Temp
resource "aws_s3_bucket_server_side_encryption_configuration" "pdf_temp" {
  bucket = aws_s3_bucket.pdf_temp.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "pdf_temp" {
  bucket = aws_s3_bucket.pdf_temp.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "pdf_temp" {
  bucket = aws_s3_bucket.pdf_temp.id

  rule {
    id     = "delete_temp_files"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# S3 Bucket Configurations - PDF Reports
resource "aws_s3_bucket_server_side_encryption_configuration" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }
}

# S3 Bucket Configurations - Web Assets
resource "aws_s3_bucket_server_side_encryption_configuration" "web_assets" {
  bucket = aws_s3_bucket.web_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "web_assets" {
  bucket = aws_s3_bucket.web_assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "web_assets" {
  name                              = "${local.name_prefix}-web-assets-oac"
  description                       = "OAC for web assets bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# S3 Bucket Policy for CloudFront OAC
resource "aws_s3_bucket_policy" "web_assets" {
  bucket = aws_s3_bucket.web_assets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.web_assets.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.web.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_cloudfront_distribution.web]
}
# CloudFront Distribution
resource "aws_cloudfront_distribution" "web" {
  origin {
    domain_name              = aws_s3_bucket.web_assets.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.web_assets.id
    origin_id                = "S3-${aws_s3_bucket.web_assets.bucket}"
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "PDF Accessibility Platform - Web Distribution"
  default_root_object = "index.html"
  web_acl_id          = var.enable_waf ? aws_wafv2_web_acl.cloudfront[0].arn : null

  # Aliases (custom domain)
  aliases = var.domain_name != "" && var.certificate_arn != "" ? [var.domain_name] : []

  # Default cache behavior
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.web_assets.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600  # 1 hour
    max_ttl     = 86400 # 24 hours
  }

  # Cache behavior for API calls
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "S3-${aws_s3_bucket.web_assets.bucket}"
    compress         = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "CloudFront-Forwarded-Proto"]
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0 # No caching for API calls
    max_ttl                = 0
  }

  # Cache behavior for static assets
  ordered_cache_behavior {
    path_pattern     = "/_next/static/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.web_assets.bucket}"
    compress         = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 31536000 # 1 year
    default_ttl            = 31536000 # 1 year
    max_ttl                = 31536000 # 1 year
  }

  # Price class
  price_class = "PriceClass_100" # Use only North America and Europe

  # Restrictions
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL Certificate
  viewer_certificate {
    cloudfront_default_certificate = var.certificate_arn == ""
    acm_certificate_arn            = var.certificate_arn != "" ? var.certificate_arn : null
    ssl_support_method             = var.certificate_arn != "" ? "sni-only" : null
    minimum_protocol_version       = var.certificate_arn != "" ? "TLSv1.2_2021" : null
  }

  # Custom error responses
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  # Logging
  logging_config {
    include_cookies = false
    bucket          = aws_s3_bucket.cloudfront_logs.bucket_domain_name
    prefix          = "cloudfront-logs/"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-web-distribution"
  })
}

# S3 Bucket for CloudFront Logs
resource "aws_s3_bucket" "cloudfront_logs" {
  bucket = "${local.name_prefix}-cloudfront-logs-${local.name_suffix}"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-cloudfront-logs"
    Purpose = "Store CloudFront access logs"
  })
}

resource "aws_s3_bucket_ownership_controls" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id
  acl    = "private"

  depends_on = [aws_s3_bucket_ownership_controls.cloudfront_logs]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    id     = "delete_old_logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# WAF Web ACL for CloudFront
resource "aws_wafv2_web_acl" "cloudfront" {
  count = var.enable_waf ? 1 : 0
  name  = "${local.name_prefix}-cloudfront-waf"
  scope = "CLOUDFRONT"

  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-WebACL"
    sampled_requests_enabled   = true
  }

  # Rule 1: Block common exploits
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    override_action {
      none {}
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-CommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: Block known bad inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    override_action {
      none {}
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-BadInputsRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: Rate limiting
  rule {
    name     = "RateLimitRule"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-RateLimitMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: Block specific countries (disabled by default)
  # Uncomment and add country codes if geo-blocking is needed
  rule {
    name     = "GeoBlockRule"
    priority = 4

    action {
      block {}
    }

    statement {
      geo_match_statement {
        country_codes = ["CU", "IR", "KP", "SY", "UA"] # Replace with actual country codes
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-GeoBlockMetric"
      sampled_requests_enabled   = true
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cloudfront-waf"
  })

  # Provider must be us-east-1 for CloudFront
  provider = aws.us_east_1
}

# Provider alias for us-east-1 (required for CloudFront WAF)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# CloudWatch Log Group for WAF
resource "aws_cloudwatch_log_group" "waf" {
  count             = var.enable_waf ? 1 : 0
  name              = "/aws/wafv2/${local.name_prefix}-cloudfront"
  retention_in_days = var.log_retention_days

  provider = aws.us_east_1

  tags = local.common_tags
}

# WAF Logging Configuration (disabled due to ARN format issues)
# resource "aws_wafv2_web_acl_logging_configuration" "cloudfront" {
#   count                   = var.enable_waf ? 1 : 0
#   resource_arn            = aws_wafv2_web_acl.cloudfront[0].arn
#   log_destination_configs = [aws_cloudwatch_log_group.waf[0].arn]

#   provider = aws.us_east_1

#   redacted_fields {
#     single_header {
#       name = "authorization"
#     }
#   }

#   redacted_fields {
#     single_header {
#       name = "cookie"
#     }
#   }
# }

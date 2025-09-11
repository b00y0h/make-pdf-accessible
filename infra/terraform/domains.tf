# Domain configuration for makepdfaccessible.com
# This file manages all domain-related resources including certificates and CloudFront distributions

locals {
  domain_name = "makepdfaccessible.com"
  domains = {
    root      = local.domain_name                      # makepdfaccessible.com (marketing site)
    www       = "www.${local.domain_name}"            # www.makepdfaccessible.com (redirect to root)
    dashboard = "dashboard.${local.domain_name}"       # dashboard.makepdfaccessible.com
    api       = "api.${local.domain_name}"            # api.makepdfaccessible.com
  }
  
  # Certificate must be in us-east-1 for CloudFront
  certificate_region = "us-east-1"
}

# ACM Certificate for all domains (must be in us-east-1 for CloudFront)
resource "aws_acm_certificate" "main" {
  provider = aws.us_east_1
  
  domain_name = local.domain_name
  subject_alternative_names = [
    "*.${local.domain_name}",  # Wildcard for all subdomains
    local.domain_name           # Root domain
  ]
  
  validation_method = "DNS"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-certificate"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# Certificate validation (we'll export the DNS records for manual configuration in DNSimple)
resource "aws_acm_certificate_validation" "main" {
  provider = aws.us_east_1
  
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_acm_certificate.main.domain_validation_options : record.resource_record_name]
  
  depends_on = [aws_acm_certificate.main]
}

# CloudFront distribution for marketing website (makepdfaccessible.com)
resource "aws_cloudfront_distribution" "marketing" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Marketing site - makepdfaccessible.com"
  default_root_object = "index.html"
  
  aliases = [
    local.domains.root,
    local.domains.www
  ]
  
  # Origin for S3 bucket hosting the marketing site
  origin {
    domain_name              = aws_s3_bucket.web_assets.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.web_assets.id
    origin_id                = "S3-marketing-${aws_s3_bucket.web_assets.bucket}"
  }
  
  # Default cache behavior
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-marketing-${aws_s3_bucket.web_assets.bucket}"
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
  
  # Cache behavior for Next.js static assets
  ordered_cache_behavior {
    path_pattern     = "/_next/static/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-marketing-${aws_s3_bucket.web_assets.bucket}"
    compress         = true
    
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 31536000 # 1 year
    default_ttl            = 31536000
    max_ttl                = 31536000
  }
  
  # Custom error responses for SPA
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
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.main.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
  
  price_class = "PriceClass_100" # North America and Europe
  
  tags = merge(local.common_tags, {
    Name   = "${local.name_prefix}-marketing-distribution"
    Domain = local.domains.root
  })
}

# CloudFront distribution for dashboard (dashboard.makepdfaccessible.com)
resource "aws_cloudfront_distribution" "dashboard" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Dashboard - dashboard.makepdfaccessible.com"
  default_root_object = "index.html"
  
  aliases = [local.domains.dashboard]
  
  # Origin for S3 bucket hosting the dashboard
  origin {
    domain_name              = aws_s3_bucket.dashboard_assets.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard_assets.id
    origin_id                = "S3-dashboard-${aws_s3_bucket.dashboard_assets.bucket}"
  }
  
  # Default cache behavior
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-dashboard-${aws_s3_bucket.dashboard_assets.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
    
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type"]
      cookies {
        forward = "all"
      }
    }
    
    min_ttl     = 0
    default_ttl = 0    # No caching for dashboard by default
    max_ttl     = 86400
  }
  
  # Cache behavior for Next.js static assets
  ordered_cache_behavior {
    path_pattern     = "/_next/static/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-dashboard-${aws_s3_bucket.dashboard_assets.bucket}"
    compress         = true
    
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 31536000 # 1 year
    default_ttl            = 31536000
    max_ttl                = 31536000
  }
  
  # Cache behavior for API routes
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "S3-dashboard-${aws_s3_bucket.dashboard_assets.bucket}"
    compress         = true
    
    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }
  
  # Custom error responses for SPA
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
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.main.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
  
  price_class = "PriceClass_100" # North America and Europe
  
  tags = merge(local.common_tags, {
    Name   = "${local.name_prefix}-dashboard-distribution"
    Domain = local.domains.dashboard
  })
}

# S3 bucket for dashboard assets
resource "aws_s3_bucket" "dashboard_assets" {
  bucket = "${local.name_prefix}-dashboard-assets-${local.name_suffix}"
  
  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-dashboard-assets"
    Purpose = "Static assets for dashboard application"
  })
}

# S3 bucket policy for dashboard CloudFront access
resource "aws_s3_bucket_policy" "dashboard_assets" {
  bucket = aws_s3_bucket.dashboard_assets.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipalReadOnly"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.dashboard_assets.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.dashboard.arn
          }
        }
      }
    ]
  })
}

# CloudFront Origin Access Control for dashboard
resource "aws_cloudfront_origin_access_control" "dashboard_assets" {
  name                              = "${local.name_prefix}-dashboard-oac"
  description                       = "OAC for dashboard assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# S3 bucket configuration for dashboard
resource "aws_s3_bucket_public_access_block" "dashboard_assets" {
  bucket = aws_s3_bucket.dashboard_assets.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dashboard_assets" {
  bucket = aws_s3_bucket.dashboard_assets.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# API Gateway v2 custom domain for api.makepdfaccessible.com
resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = local.domains.api
  
  domain_name_configuration {
    certificate_arn = aws_acm_certificate.api_regional.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-domain"
  })
}

# Regional certificate for API Gateway (in the main region, not us-east-1)
resource "aws_acm_certificate" "api_regional" {
  domain_name       = local.domains.api
  validation_method = "DNS"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-certificate"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# Certificate validation for API domain
resource "aws_acm_certificate_validation" "api_regional" {
  certificate_arn         = aws_acm_certificate.api_regional.arn
  validation_record_fqdns = [for record in aws_acm_certificate.api_regional.domain_validation_options : record.resource_record_name]
}

# API mapping for HTTP API
resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = aws_apigatewayv2_stage.default.id
}

# Outputs for DNS configuration
output "dns_configuration" {
  value = {
    instructions = "Configure these DNS records in DNSimple:"
    
    marketing_site = {
      record_type = "CNAME"
      hostname    = local.domains.root
      value       = aws_cloudfront_distribution.marketing.domain_name
      ttl         = 300
    }
    
    www_redirect = {
      record_type = "CNAME"
      hostname    = "www"
      value       = aws_cloudfront_distribution.marketing.domain_name
      ttl         = 300
    }
    
    dashboard = {
      record_type = "CNAME"
      hostname    = "dashboard"
      value       = aws_cloudfront_distribution.dashboard.domain_name
      ttl         = 300
    }
    
    api = {
      record_type = "CNAME"
      hostname    = "api"
      value       = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].target_domain_name
      ttl         = 300
    }
    
    certificate_validation = {
      note = "Add these DNS records for SSL certificate validation:"
      records = [
        for dvo in aws_acm_certificate.main.domain_validation_options : {
          record_type = dvo.resource_record_type
          hostname    = trimsuffix(dvo.resource_record_name, ".${local.domain_name}.")
          value       = dvo.resource_record_value
          ttl         = 300
        }
      ]
    }
    
    api_certificate_validation = {
      note = "Add these DNS records for API SSL certificate validation:"
      records = [
        for dvo in aws_acm_certificate.api_regional.domain_validation_options : {
          record_type = dvo.resource_record_type
          hostname    = trimsuffix(dvo.resource_record_name, ".${local.domain_name}.")
          value       = dvo.resource_record_value
          ttl         = 300
        }
      ]
    }
  }
  
  description = "DNS records to configure in DNSimple"
}
# Marketing site (makepdfaccessible.com in production, <env>.makepdfaccessible.com elsewhere).
# Built from apps/marketing as a static export and deployed by .github/workflows/marketing-site.yml.

module "marketing_site" {
  source = "./modules/static-site"

  name           = "${local.name_prefix}-marketing"
  bucket_name    = "${local.name_prefix}-marketing-site-${local.name_suffix}"
  comment        = "Marketing site - ${local.domains.root} (${var.environment})"
  primary_domain = local.domains.root
  aliases        = local.marketing_aliases
  redirect_hosts = local.marketing_redirect_hosts

  certificate_arn = aws_acm_certificate_validation.main.certificate_arn
  web_acl_arn     = var.enable_waf ? aws_wafv2_web_acl.cloudfront[0].arn : null

  log_bucket_domain_name = aws_s3_bucket.cloudfront_logs.bucket_domain_name
  log_prefix             = "marketing/"

  api_origin        = "https://${local.domains.api}"
  extra_connect_src = var.marketing_extra_connect_src
  extra_frame_src   = var.marketing_extra_frame_src
  extra_script_src  = var.marketing_extra_script_src

  tags = merge(local.common_tags, {
    component = "marketing"
    service   = "cloudfront"
  })
}

output "marketing_site_bucket" {
  description = "S3 bucket that receives the exported marketing site (MARKETING_S3_BUCKET in CI)"
  value       = module.marketing_site.bucket_name
}

output "marketing_site_distribution_id" {
  description = "CloudFront distribution id for the marketing site (MARKETING_CLOUDFRONT_DISTRIBUTION_ID in CI)"
  value       = module.marketing_site.distribution_id
}

output "marketing_site_distribution_domain" {
  description = "CloudFront domain name for the marketing site (DNS ALIAS/CNAME target)"
  value       = module.marketing_site.distribution_domain_name
}

output "marketing_site_url" {
  description = "Public URL of the marketing site"
  value       = "https://${local.domains.root}"
}

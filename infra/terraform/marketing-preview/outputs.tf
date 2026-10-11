output "marketing_site_bucket" {
  description = "MARKETING_S3_BUCKET for the <environment>-web GitHub environment"
  value       = module.marketing_site.bucket_name
}

output "marketing_site_distribution_id" {
  description = "MARKETING_CLOUDFRONT_DISTRIBUTION_ID for the <environment>-web GitHub environment"
  value       = module.marketing_site.distribution_id
}

output "github_web_deploy_role_arn" {
  description = "GITHUB_WEB_DEPLOY_ROLE_ARN secret for the <environment>-web GitHub environment"
  value       = aws_iam_role.github_web_deploy.arn
}

output "marketing_site_url" {
  description = "Preview URL"
  value       = "https://${module.marketing_site.distribution_domain_name}"
}

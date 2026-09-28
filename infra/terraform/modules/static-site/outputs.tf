output "bucket_name" {
  description = "Name of the site bucket (deploy target for `aws s3 sync`)"
  value       = aws_s3_bucket.site.bucket
}

output "bucket_arn" {
  description = "ARN of the site bucket"
  value       = aws_s3_bucket.site.arn
}

output "distribution_id" {
  description = "CloudFront distribution id (invalidation target)"
  value       = aws_cloudfront_distribution.site.id
}

output "distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = aws_cloudfront_distribution.site.arn
}

output "distribution_domain_name" {
  description = "CloudFront domain name (DNS ALIAS/CNAME target)"
  value       = aws_cloudfront_distribution.site.domain_name
}

output "distribution_hosted_zone_id" {
  description = "CloudFront hosted zone id for Route 53 alias records"
  value       = aws_cloudfront_distribution.site.hosted_zone_id
}

output "viewer_request_function_arn" {
  description = "ARN of the CloudFront Function handling redirects and index rewrites"
  value       = aws_cloudfront_function.viewer_request.arn
}

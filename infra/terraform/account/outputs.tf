output "github_oidc_provider_arn" {
  description = "GitHub Actions OIDC provider ARN (the platform root looks it up by URL)"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "vpc_id" {
  description = "Platform VPC (the platform root finds it by the pdf-accessibility/network tag)"
  value       = aws_vpc.platform.id
}

output "private_subnet_ids" {
  description = "Private subnets, one per AZ"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnets, one per AZ"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_public_ips" {
  description = "Outbound IPs of the NAT gateways (give these to customers who allow-list our crawler or connectors)"
  value       = aws_eip.nat[*].public_ip
}

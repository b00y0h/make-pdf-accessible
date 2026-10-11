output "state_buckets" {
  description = "Terraform state bucket per environment (use in environments/<env>.backend.hcl)"
  value       = { for e, b in aws_s3_bucket.state : e => b.bucket }
}

output "lock_tables" {
  description = "Terraform lock table per environment (use in environments/<env>.backend.hcl)"
  value       = { for e, t in aws_dynamodb_table.locks : e => t.name }
}

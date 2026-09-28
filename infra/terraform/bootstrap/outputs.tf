output "state_bucket" {
  description = "Terraform state bucket name (use in environments/<env>.backend.hcl)"
  value       = aws_s3_bucket.state.bucket
}

output "lock_table" {
  description = "Terraform lock table name (use in environments/<env>.backend.hcl)"
  value       = aws_dynamodb_table.locks.name
}

# Backend configuration for the prod AWS account.
# Bucket and table are created by infra/terraform/bootstrap (see its README).
bucket         = "pdf-accessibility-terraform-state-prod"
key            = "platform/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "pdf-accessibility-terraform-locks-prod"
encrypt        = true

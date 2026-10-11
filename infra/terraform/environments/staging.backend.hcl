# Backend configuration for staging, which lives in the dev AWS account beside dev.
# Bucket and table are created by infra/terraform/bootstrap (see its README).
bucket         = "pdf-accessibility-terraform-state-staging"
key            = "platform/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "pdf-accessibility-terraform-locks-staging"
encrypt        = true

# Account layer state for the prod account.
bucket         = "pdf-accessibility-terraform-state-prod"
key            = "account/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "pdf-accessibility-terraform-locks-prod"
encrypt        = true

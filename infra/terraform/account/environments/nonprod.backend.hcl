# Account layer state for the non-prod account (hosts dev and staging).
# Lives beside dev's platform state, under its own key, in the bucket the bootstrap created.
bucket         = "pdf-accessibility-terraform-state-dev"
key            = "account/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "pdf-accessibility-terraform-locks-dev"
encrypt        = true

# Account layer: resources that exist once per AWS account and are shared by every environment the
# account hosts. The dev account hosts dev and staging; the prod account hosts prod (ADR-0010).
#
#   - the GitHub Actions OIDC identity provider (IAM allows one per URL per account)
#   - the platform network: VPC, subnets, NAT, gateway endpoints and optional interface endpoints
#
# The platform root (infra/terraform) looks these up rather than creating them, so it can be applied
# once per environment in the same account. Apply this layer with an administrator credential after
# infra/terraform/bootstrap and before the platform root:
#
#   cd infra/terraform/account
#   AWS_PROFILE=pdf-dev terraform init -reconfigure -backend-config=environments/nonprod.backend.hcl
#   AWS_PROFILE=pdf-dev terraform apply -var-file=environments/nonprod.tfvars

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  # Refuses to run with another account's credentials
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = {
      application      = "accesspdf"
      service          = "account"
      component        = "platform"
      environment      = var.account_name
      cost_center      = var.cost_center
      owner            = "team-platform"
      business_unit    = "RnD"
      data_sensitivity = "internal"
      managed_by       = "terraform"
      repo             = "github.com/b00y0h/make-pdf-accessible"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.account_name}"
}

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Stops a plan or apply that runs with another account's credentials, such as a default
  # AWS profile for a different organization
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.common_tags
  }
}

# Random suffix for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

# Current region (used by monitoring, OpenSearch and processing IAM policies)
data "aws_region" "current" {}

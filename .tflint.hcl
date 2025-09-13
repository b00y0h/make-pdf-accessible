# TFLint configuration for AWS cost-allocation tag enforcement

config {
  # Plugin cache directory
  plugin_dir = "~/.tflint.d/plugins"

  # Enable modules
  module = true

  # Exit with non-zero code if violations are found
  force = false

  # Disable default rules that conflict with our standards
  disabled_by_default = false
}

# AWS plugin for AWS-specific rules
plugin "aws" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"

  # Deep checking for AWS resources
  deep_check = true
}

# Terraform core plugin
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

# AWS provider rules
rule "aws_resource_missing_tags" {
  enabled = true
  tags = [
    "application",
    "service", 
    "component",
    "environment",
    "cost_center",
    "owner",
    "business_unit",
    "data_sensitivity",
    "managed_by",
    "repo"
  ]
  # Exclude resources that don't support tagging
  exclude = [
    "aws_iam_role_policy_attachment",
    "aws_iam_policy_attachment", 
    "aws_apigatewayv2_integration",
    "aws_apigatewayv2_route",
    "aws_lambda_permission",
    "aws_s3_bucket_versioning",
    "aws_s3_bucket_encryption",
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_s3_bucket_public_access_block",
    "aws_s3_bucket_lifecycle_configuration",
    "aws_s3_bucket_acl",
    "aws_s3_bucket_ownership_controls",
    "aws_docdb_cluster_snapshot",
    "aws_route_table_association",
    "aws_route",
    "aws_acm_certificate_validation",
    "aws_nat_gateway",
    "aws_eip"
  ]
}

# AWS instance type validation
rule "aws_instance_invalid_type" {
  enabled = true
}

# AWS security group rules
rule "aws_security_group_rule_invalid_protocol" {
  enabled = true
}

# Naming convention rules
rule "aws_naming_convention" {
  enabled = true
  format  = "snake_case"
}

# Terraform module standards
rule "terraform_required_version" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

# Enforce consistent naming
rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"

  # Apply to all variable and resource names
  variable {
    format = "snake_case"
  }

  resource {
    format = "snake_case"
  }

  data {
    format = "snake_case" 
  }

  locals {
    format = "snake_case"
  }
}

# Security rules
rule "aws_security_group_rule_invalid_cidr" {
  enabled = true
}

rule "aws_route_invalid_cidr" {
  enabled = true
}

# Cost optimization rules  
rule "aws_instance_previous_type" {
  enabled = true
}

rule "aws_db_instance_previous_type" {
  enabled = true
}
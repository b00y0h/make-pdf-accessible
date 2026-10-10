variable "project_name" {
  description = "Project name; must match the root module's project_name so the OIDC role policies grant access to the state bucket and lock table"
  type        = string
  default     = "pdf-accessibility"
}

variable "environment" {
  description = "Environment (dev or prod); one bootstrap per AWS account"
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod. There is no staging account yet (ADR-0010); add one to local.account_ids in main.tf when there is."
  }
}

variable "aws_region" {
  description = "Region for the state bucket and lock table"
  type        = string
  default     = "us-east-1"
}

variable "cost_center" {
  description = "Cost center tag"
  type        = string
  default     = "CC-PLATFORM-001"
}

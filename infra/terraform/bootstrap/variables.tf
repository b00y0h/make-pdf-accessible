variable "project_name" {
  description = "Project name; must match the root module's project_name so the OIDC role policies grant access to the state bucket and lock table"
  type        = string
  default     = "pdf-accessibility"
}

variable "environments" {
  description = "Environments whose Terraform state lives in this AWS account (the non-prod account holds dev and staging; the prod account holds prod)"
  type        = set(string)

  validation {
    condition     = length(var.environments) > 0 && alltrue([for e in var.environments : contains(["dev", "staging", "prod"], e)])
    error_message = "environments must be a non-empty set drawn from: dev, staging, prod."
  }

  # dev and staging share the dev account; prod has its own. One run covers one account.
  validation {
    condition     = length(setintersection(var.environments, ["prod"])) == 0 || length(var.environments) == 1
    error_message = "prod has its own account: apply it alone, from the prod workspace with prod credentials."
  }
}

variable "aws_region" {
  description = "Region for the state buckets and lock tables"
  type        = string
  default     = "us-east-1"
}

variable "cost_center" {
  description = "Cost center tag"
  type        = string
  default     = "CC-PLATFORM-001"
}

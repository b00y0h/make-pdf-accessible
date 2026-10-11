variable "environment" {
  description = "Environment this preview belongs to (dev or staging); the deploy role trusts the <environment>-web GitHub environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "Previews are for dev or staging. Production uses the platform root (../marketing.tf)."
  }
}

variable "aws_account_id" {
  description = "AWS account the preview must be created in; the provider refuses any other"
  type        = string
}

variable "aws_region" {
  description = "AWS region for the bucket (CloudFront and IAM are global)"
  type        = string
  default     = "us-east-1"
}

variable "github_repo" {
  description = "GitHub repository (owner/name) whose deploy job may assume the role"
  type        = string
  default     = "b00y0h/make-pdf-accessible"
}

variable "project_name" {
  description = "Project name used in resource names"
  type        = string
  default     = "pdf-accessibility"
}

variable "application" {
  description = "Cost-allocation tag: application"
  type        = string
  default     = "accesspdf"
}

variable "cost_center" {
  description = "Cost-allocation tag: cost center"
  type        = string
}

variable "owner" {
  description = "Cost-allocation tag: owning team"
  type        = string
  default     = "team-platform"
}

variable "business_unit" {
  description = "Cost-allocation tag: business unit (IAM and S3 reject '&' in tag values)"
  type        = string
  default     = "R and D"
}

variable "repo" {
  description = "Cost-allocation tag: source repository"
  type        = string
  default     = "github.com/b00y0h/make-pdf-accessible"
}

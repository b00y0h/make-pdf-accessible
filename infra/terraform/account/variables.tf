variable "project_name" {
  description = "Project name; must match the platform root's project_name"
  type        = string
  default     = "pdf-accessibility"
}

variable "account_name" {
  description = "Which account this is: nonprod (the dev account, hosting dev and staging) or prod"
  type        = string

  validation {
    condition     = contains(["nonprod", "prod"], var.account_name)
    error_message = "account_name must be nonprod or prod."
  }
}

variable "aws_account_id" {
  description = "AWS account this layer belongs to; the provider refuses to run against any other"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cost_center" {
  description = "Cost center tag"
  type        = string
  default     = "CC-PLATFORM-001"
}

variable "vpc_cidr" {
  description = "CIDR block for the platform VPC (use a different range per account so they can be peered later)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread subnets across"
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3."
  }
}

variable "nat_gateway_count" {
  description = "NAT gateways: 1 is cheapest (non-prod), one per AZ survives an AZ outage (prod)"
  type        = number
  default     = 1

  validation {
    condition     = var.nat_gateway_count >= 1 && var.nat_gateway_count <= 3
    error_message = "nat_gateway_count must be between 1 and 3."
  }
}

variable "interface_endpoints" {
  description = "AWS services to reach through interface VPC endpoints instead of the NAT gateway (each costs about $7 a month per AZ)"
  type        = list(string)
  default     = []
}

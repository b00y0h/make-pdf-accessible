# Input variables for CUR to Athena infrastructure

variable "name_prefix" {
  description = "Prefix for resource names to ensure uniqueness"
  type        = string
  default     = "accesspdf"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.name_prefix))
    error_message = "Name prefix must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "cur_data_retention_days" {
  description = "Number of days to retain CUR data in S3 before deletion"
  type        = number
  default     = 2555  # ~7 years for compliance
  
  validation {
    condition     = var.cur_data_retention_days >= 90 && var.cur_data_retention_days <= 3650
    error_message = "CUR data retention must be between 90 and 3650 days."
  }
}

variable "crawler_schedule" {
  description = "Cron expression for Glue crawler schedule (UTC)"
  type        = string
  default     = "cron(0 6 * * ? *)"  # Daily at 6 AM UTC
  
  validation {
    condition     = can(regex("^cron\\(", var.crawler_schedule))
    error_message = "Crawler schedule must be a valid cron expression."
  }
}

variable "athena_bytes_scanned_cutoff" {
  description = "Maximum bytes scanned per Athena query (cost control)"
  type        = number
  default     = 107374182400  # 100 GB
  
  validation {
    condition     = var.athena_bytes_scanned_cutoff >= 1073741824  # Minimum 1 GB
    error_message = "Athena bytes scanned cutoff must be at least 1 GB (1073741824 bytes)."
  }
}

variable "external_id" {
  description = "External ID for secure cross-account role assumption"
  type        = string
  default     = "accesspdf-costs-dashboard"
  sensitive   = true
}

variable "enable_detailed_billing" {
  description = "Enable detailed billing with resource-level tracking"
  type        = bool
  default     = true
}

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection integration"
  type        = bool
  default     = false
}

variable "cost_allocation_tags" {
  description = "List of cost allocation tags to include in analysis"
  type        = list(string)
  default = [
    "application",
    "environment", 
    "component",
    "cost_center",
    "service",
    "managed_by"
  ]
  
  validation {
    condition     = length(var.cost_allocation_tags) > 0
    error_message = "At least one cost allocation tag must be specified."
  }
}

variable "athena_workgroup_description" {
  description = "Description for the Athena workgroup"
  type        = string
  default     = "Workgroup for AWS cost analytics and reporting"
}

variable "enable_query_result_encryption" {
  description = "Enable encryption for Athena query results"
  type        = bool
  default     = true
}

variable "query_result_retention_days" {
  description = "Number of days to retain Athena query results"
  type        = number
  default     = 30
  
  validation {
    condition     = var.query_result_retention_days >= 1 && var.query_result_retention_days <= 365
    error_message = "Query result retention must be between 1 and 365 days."
  }
}

variable "enable_cloudwatch_metrics" {
  description = "Enable CloudWatch metrics for Athena workgroup"
  type        = bool
  default     = true
}

variable "cur_s3_prefix" {
  description = "S3 prefix for CUR data storage"
  type        = string
  default     = "cur-data"
  
  validation {
    condition     = can(regex("^[a-z0-9-/]+$", var.cur_s3_prefix))
    error_message = "S3 prefix must contain only lowercase letters, numbers, hyphens, and forward slashes."
  }
}
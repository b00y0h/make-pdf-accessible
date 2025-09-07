variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "pdf-accessibility"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (for NAT Gateway)"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "github_repo" {
  description = "GitHub repository for OIDC trust (format: owner/repo)"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", var.github_repo))
    error_message = "GitHub repository must be in the format 'owner/repo'."
  }
}

variable "github_branches" {
  description = "GitHub branches allowed for OIDC (deprecated - now handled per role)"
  type        = list(string)
  default     = ["main", "develop"]
}

# Router function configuration
variable "sqs_batch_size" {
  description = "Number of SQS messages to process in a single Lambda invocation"
  type        = number
  default     = 10
}

variable "sqs_batching_window" {
  description = "Maximum time in seconds to wait for additional messages before invoking Lambda"
  type        = number
  default     = 5
}

variable "router_max_concurrency" {
  description = "Maximum number of concurrent router function instances"
  type        = number
  default     = 100
}

variable "log_level" {
  description = "Log level for Lambda functions"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARN", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARN, ERROR."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "cloudwatch_logs_kms_key_id" {
  description = "KMS key ID for encrypting CloudWatch logs"
  type        = string
  default     = null
}

variable "vpc_config" {
  description = "VPC configuration for Lambda functions"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "github_oidc_session_duration" {
  description = "Maximum session duration for GitHub OIDC roles in seconds"
  type        = number
  default     = 3600

  validation {
    condition     = var.github_oidc_session_duration >= 900 && var.github_oidc_session_duration <= 43200
    error_message = "Session duration must be between 900 seconds (15 minutes) and 43200 seconds (12 hours)."
  }
}

variable "saml_provider_name" {
  description = "Name for SAML identity provider"
  type        = string
  default     = "ExampleSAML"
}

variable "domain_name" {
  description = "Domain name for CloudFront distribution"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for CloudFront (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "enable_waf" {
  description = "Enable WAF for CloudFront"
  type        = bool
  default     = true
}


variable "use_lambda_function_url" {
  description = "Use Lambda Function URL instead of API Gateway"
  type        = bool
  default     = false
}

# OAuth Configuration
variable "google_oauth_client_id" {
  description = "Google OAuth2 Client ID for Cognito OIDC integration"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth2 Client Secret for Cognito OIDC integration"
  type        = string
  default     = ""
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key for API authentication (will generate random if not provided)"
  type        = string
  default     = ""
  sensitive   = true
}

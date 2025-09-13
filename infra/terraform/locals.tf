# Local values for consistent naming and tagging
locals {
  # Naming convention
  name_prefix = "${var.project_name}-${var.environment}"
  name_suffix = random_id.suffix.hex

  # Common tags applied to all resources
  # These tags are required for the costs dashboard to function properly
  common_tags = {
    # Required tags for dashboard filtering
    application  = var.application
    service      = var.service
    component    = var.component
    environment  = var.environment
    cost_center  = var.cost_center

    # Additional organizational tags
    owner            = var.owner
    business_unit    = var.business_unit
    data_sensitivity = var.data_sensitivity
    managed_by       = "terraform"
    repo             = var.repo

    # Legacy tags (for backwards compatibility)
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Component-specific tag variations
  api_tags = merge(local.common_tags, {
    component = "api"
    service   = "api-gateway"
  })

  lambda_tags = merge(local.common_tags, {
    component = "compute"
    service   = "lambda"
  })

  storage_tags = merge(local.common_tags, {
    component = "storage"
    service   = "s3"
  })

  database_tags = merge(local.common_tags, {
    component = "database"
    service   = "documentdb"
  })

  networking_tags = merge(local.common_tags, {
    component = "networking"
    service   = "vpc"
  })

  security_tags = merge(local.common_tags, {
    component = "security"
    service   = "iam"
  })

  monitoring_tags = merge(local.common_tags, {
    component = "monitoring"
    service   = "cloudwatch"
  })
}
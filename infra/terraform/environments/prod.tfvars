# Production account. Domains resolve to makepdfaccessible.com, www., dashboard., api.
# Committed to git: never put secrets here (they come from AWS Secrets Manager).
project_name = "pdf-accessibility"
environment  = "prod"
aws_region   = "us-east-1"
github_repo  = "b00y0h/make-pdf-accessible"
root_domain  = "makepdfaccessible.com"

cost_center      = "CC-PRD-001"
data_sensitivity = "confidential"

enable_waf         = true
log_retention_days = 90
log_level          = "INFO"

documentdb_instance_count               = 2
documentdb_instance_class               = "db.r6g.large"
documentdb_performance_insights_enabled = true

router_max_concurrency = 100

# alerts_email = "oncall@example.com"

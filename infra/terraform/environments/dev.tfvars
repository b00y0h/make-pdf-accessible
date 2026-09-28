# Development account. Domains resolve to dev.makepdfaccessible.com, dashboard-dev., api-dev.
# Committed to git: never put secrets here (they come from AWS Secrets Manager).
project_name = "pdf-accessibility"
environment  = "dev"
aws_region   = "us-east-1"
github_repo  = "b00y0h/make-pdf-accessible"
root_domain  = "makepdfaccessible.com"

cost_center      = "CC-DEV-001"
data_sensitivity = "internal"

enable_waf         = false
log_retention_days = 14
log_level          = "DEBUG"

documentdb_instance_count = 1
documentdb_instance_class = "db.t3.medium"

router_max_concurrency = 20

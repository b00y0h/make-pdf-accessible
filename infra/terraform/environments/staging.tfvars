# Staging account. Domains resolve to staging.makepdfaccessible.com, dashboard-staging., api-staging.
# Committed to git: never put secrets here (they come from AWS Secrets Manager).
project_name = "pdf-accessibility"
environment  = "staging"
aws_region   = "us-east-1"
github_repo  = "b00y0h/make-pdf-accessible"
root_domain  = "makepdfaccessible.com"

cost_center      = "CC-STG-001"
data_sensitivity = "confidential"

enable_waf         = true
log_retention_days = 30
log_level          = "INFO"

documentdb_instance_count = 1
documentdb_instance_class = "db.t3.medium"

router_max_concurrency = 50

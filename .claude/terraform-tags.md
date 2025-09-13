Backfill & Enforce AWS Cost-Allocation Tags Across Terraform (to Power Costs Dashboard). I have this first prompt but also a stepwise GitHub issue checklist below. Use whatever approach will produce the best results.

Context
	•	Repo has an infra/ directory (Terraform configs for AWS).
	•	You already built a dashboard UI (Next.js) showing AWS costs by service, environment, component, etc.
	•	For the UI to populate correctly, Terraform-managed resources must carry consistent cost-allocation tags, and those tags must be activated in AWS Billing.

Target Tag Schema

# Example defaults (override per env/workspace)
common_tags = {
  application      = "accesspdf"
  service          = "doc-processing"
  component        = "api"
  environment      = "dev"            # dev|staging|prod
  owner            = "team-platform"
  cost_center      = "CC-12345"
  business_unit    = "R&D"
  data_sensitivity = "internal"
  managed_by       = "terraform"
  repo             = "github.com/acme/accesspdf"
}

Notes:
	•	environment, application, service, component, and cost_center are required for dashboard filtering.
	•	managed_by=terraform differentiates from console-created resources.
	•	Tag keys must be activated in Billing → Cost Allocation Tags so they appear in CUR/Cost Explorer (and thus in your UI).

⸻

Tasks

1. Global Tagging Pattern
	•	In each Terraform root module, define variables for application, service, component, environment, owner, cost_center, business_unit, data_sensitivity, repo.
	•	Add locals.tf with local.common_tags.
	•	Configure provider default_tags in providers.tf.
	•	Provide environment values via *.tfvars (dev/staging/prod).

2. Provider-Level Default Tags
	•	Add default_tags to AWS provider (applies automatically to most resources).

provider "aws" {
  region = var.region
  default_tags {
    tags = local.common_tags
  }
}

3. Propagate Tags to Modules
	•	Ensure all child modules accept a tags input (map(string)).
	•	Pass tags = local.common_tags from parent.
	•	Inside modules, merge var.tags with resource-specific tags.
	•	Wrap or patch third-party modules that don’t support tags.

4. Resource Coverage
	•	Apply tags to all supported AWS resources (EC2, ECS, EKS, VPC, S3, RDS, DynamoDB, CloudFront, Lambda, etc.).
	•	Where tagging isn’t supported, document in TAGS_REPORT.md and tag nearest parent.

5. Refactor Pass
	•	Scan all *.tf for untagged resources.
	•	Replace hardcoded tags with merge(local.common_tags, {...}).

6. Validation & CI
	•	Add tflint (with AWS plugin) and checkov/tfsec to enforce tags.
	•	Add pre-commit hooks: terraform fmt, tflint, checkov.

7. Acceptance Criteria (linked to UI)
	•	✅ default_tags defined in all root modules.
	•	✅ No Terraform plan shows missing required tag keys.
	•	✅ CI fails if a taggable resource is untagged.
	•	✅ README.md explains tag schema + how dashboard consumes them.
	•	✅ TAGS_REPORT.md lists non-taggable resources.
	•	✅ Dashboard UI can filter/group by tags (service, environment, component, cost_center) once CUR/CE data refreshes.

⸻

Output Requirements
	•	PR with:
	•	Updated provider blocks (default_tags).
	•	Module changes to propagate tags.
	•	*.tfvars for each environment.
	•	CI enforcement configs.
	•	Docs: README.md + TAGS_REPORT.md.
	•	Evidence: Terraform plan output with tags applied, screenshot of tags in AWS console, and screenshot of UI populating with correct tag filters.

⸻

Guardrails
	•	Never drop existing resource-specific tags — always merge(local.common_tags, existing).
	•	Keep key format consistent (snake_case).
	•	No secrets/PII in tag values.
	•	Ensure CUR/CE source data aligns with dashboard grouping.

⸻

Quick Snippet Examples

Child Module

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  name   = "${var.application}-${var.environment}"
  cidr   = var.vpc_cidr
  tags   = local.common_tags
}

CloudFront (no default_tags support)

resource "aws_cloudfront_distribution" "cdn" {
  # ...
  tags = merge(local.common_tags, { component = "edge" })
}

S3 + tagging block

resource "aws_s3_bucket" "data" {
  bucket = "${var.application}-${var.environment}-data"
  tags   = local.common_tags
}

resource "aws_s3_bucket_tagging" "data" {
  bucket = aws_s3_bucket.data.id
  tag_set = [
    for k, v in local.common_tags : { key = k, value = v }
  ]
}
⸻
⸻

Enforce AWS Cost-Allocation Tags in Terraform (to Power Costs Dashboard)

Our Costs Dashboard UI depends on consistent AWS cost-allocation tags. This issue ensures all Terraform-managed AWS resources carry the required tags so that Cost Explorer / CUR data flows into the dashboard.

⸻

Milestone 0 — Prep
	•	Confirm desired tag schema (application, service, component, environment, owner, cost_center, business_unit, data_sensitivity, managed_by, repo).
	•	Activate these keys as Cost Allocation Tags in AWS Billing.

⸻

Milestone 1 — Global Tagging Pattern
	•	In each Terraform root module (infra/*/), add variables.tf for all required keys.
	•	Add locals.tf with local.common_tags.
	•	Add providers.tf with AWS default_tags pointing to local.common_tags.
	•	Provide per-env values via *.tfvars (dev/staging/prod).

⸻

Milestone 2 — Provider-Level Default Tags
	•	Configure default_tags in AWS provider (applies automatically to most resources).

⸻

Milestone 3 — Propagate Tags Through Modules
	•	Ensure all child modules accept a tags variable (map(string)).
	•	Pass tags = local.common_tags from parent modules.
	•	Merge var.tags with resource-specific tags inside modules.
	•	Wrap or patch 3rd-party modules that lack tags input.

⸻

Milestone 4 — Resource Coverage
	•	Apply tags to all supported resources (EC2, ECS, EKS, VPC, S3, RDS, DynamoDB, CloudFront, Lambda, etc.).
	•	For resources that don’t support tagging, document them in TAGS_REPORT.md and ensure their parent resource is tagged.

⸻

Milestone 5 — Refactor Pass
	•	Scan all *.tf for hardcoded or missing tags.
	•	Replace with merge(local.common_tags, {...}) or rely on default_tags if supported.

⸻

Milestone 6 — Validation & CI
	•	Add terraform validate and tflint with AWS ruleset.
	•	Add checkov or tfsec with policies that fail on missing tags.
	•	Add pre-commit hooks for terraform fmt, tflint, and checkov.

⸻

Milestone 7 — Acceptance Criteria
	•	default_tags present in every root AWS provider.
	•	All child modules accept and pass tags.
	•	Terraform plan shows no missing required keys (environment, application, service, component, cost_center).
	•	CI fails if a taggable resource lacks required tags.
	•	README.md in each root explains the tag schema.
	•	TAGS_REPORT.md lists any non-taggable resources and mitigations.
	•	Dashboard UI can filter/group by tags after Cost Explorer/CUR refresh.

⸻

Milestone 8 — Reporting (Optional, Nice to Have)
	•	Generate TAGS_REPORT.md from terraform show -json plan.out.
	•	Include module path, resource address, taggable? yes/no, missing keys, notes/remediation.

⸻

Milestone 9 — Org-Level Guardrails (Optional)
	•	Create AWS Tag Policy (Org-level) to enforce required keys/values.
	•	Add AWS Config Rule to detect untagged resources.
	•	Document activation of cost allocation tags for Finance/Billing teams.

⸻

Deliverables
	•	PR with updated Terraform (providers.tf, locals.tf, variables.tf, modules).
	•	Environment-specific *.tfvars.
	•	CI configs for linting/tag enforcement.
	•	Documentation: README.md, TAGS_REPORT.md.
	•	Screenshots:
	•	Terraform plan showing tags applied.
	•	AWS console with activated cost allocation tags.
	•	Dashboard UI displaying tag-based grouping.


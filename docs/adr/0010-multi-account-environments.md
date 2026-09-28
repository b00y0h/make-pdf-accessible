# ADR-0010: Separate AWS accounts for dev, staging and prod under AWS Organizations, with per-environment Terraform state and GitHub OIDC roles

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** AWS account structure, Terraform state, CI/CD credentials
- **Related:** `docs/ENTERPRISE-READINESS-PRD.md`, `docs/AWS-DEPLOYMENT-SPECS.md`, ADR-0008

## Context

All environments share one AWS account and are distinguished by a Terraform `environment` variable and a random suffix. Terraform state is local (the README suggests creating a `backend.tf`); a binary plan file was committed to the repository. The CI workflows exist for OIDC deployment but assume a single account. Buyers ask where production data lives and whether developers can reach it. ITHAKA's lesson was that enterprise accounts run service control policies that block deployment shortcuts; we should hold ourselves to the same standard so our Terraform works in a locked-down customer account when a System-tier customer wants one.

Constraints: small team; one Terraform root today; cost of three accounts is negligible; blast radius and least privilege matter for SOC 2.

## Decision

We will create an AWS Organization with `dev`, `staging` and `prod` member accounts (plus a `security` account for CloudTrail, Config and GuardDuty aggregation when SOC 2 work starts), apply service control policies that deny public S3 access, IAM user creation and unapproved regions, and keep one Terraform root deployed three times with a partial S3 backend configured per environment (`infra/terraform/environments/<env>.backend.hcl`) and per-environment tfvars. GitHub Actions assumes a per-account OIDC role; production applies require an environment approval and run only from `main`. No long-lived AWS credentials exist anywhere.

## Alternatives Considered

- **One account with Terraform workspaces** — Cheapest, but shared IAM, shared quotas, shared blast radius; fails most security questionnaires.
- **Two accounts (non-prod, prod)** — Reasonable, but staging drift from prod is the usual outcome; three keeps staging honest.
- **Account per tenant** — Only as a System-tier option (ADR-0008), not the default.

## Consequences

**Positive**

- Hard isolation of production data; least-privilege CI roles per account; a clean answer for HECVAT and SOC 2; our Terraform is proven against SCPs.

**Negative / Trade-offs**

- Three deployments to keep in sync; certificates and DNS validation per account; more bootstrap work (state buckets, OIDC providers) before the first apply.
- Cross-account access for support and observability must be designed (roles, not shared credentials).

**Neutral / Follow-ups**

- Bootstrap module for state buckets and lock tables (`infra/terraform/bootstrap/`).
- Remove the committed `tfplan` and `.bak` files; ignore plan files in git.

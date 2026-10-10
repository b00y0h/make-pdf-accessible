# ADR-0010: Separate AWS accounts for dev and prod under AWS Organizations, with per-environment Terraform state and GitHub OIDC roles

- **Status:** Accepted
- **Date:** 2026-09-28 (amended 2026-10-10: two workload accounts, staging deferred)
- **Deciders:** Founder (product and engineering)
- **Scope:** AWS account structure, Terraform state, CI/CD credentials
- **Related:** `docs/ENTERPRISE-READINESS-PRD.md`, `docs/AWS-DEPLOYMENT-SPECS.md`, ADR-0008

## Context

All environments share one AWS account and are distinguished by a Terraform `environment` variable and a random suffix. Terraform state is local (the README suggests creating a `backend.tf`); a binary plan file was committed to the repository. The CI workflows exist for OIDC deployment but assume a single account. Buyers ask where production data lives and whether developers can reach it. ITHAKA's lesson was that enterprise accounts run service control policies that block deployment shortcuts; we should hold ourselves to the same standard so our Terraform works in a locked-down customer account when a System-tier customer wants one.

Constraints: small team; one Terraform root today; accounts cost nothing, but each copy of the platform stack carries an always-on cost (NAT gateways, DocumentDB, OpenSearch Serverless); blast radius and least privilege matter for SOC 2.

## Decision

We will run an AWS Organization (management account `reversetype`) with `dev` and `prod` member accounts, signed into through IAM Identity Center. A `staging` account, and a `security` account for CloudTrail, Config and GuardDuty aggregation when SOC 2 work starts, are added the same way when they are needed. We apply service control policies that deny public S3 access, IAM user creation and unapproved regions, and keep one Terraform root deployed once per account with a partial S3 backend configured per environment (`infra/terraform/environments/<env>.backend.hcl`) and per-environment tfvars. GitHub Actions assumes a per-account OIDC role; production applies require an environment approval and run only from `main`. No long-lived AWS credentials exist anywhere.

## Alternatives Considered

- **One account with Terraform workspaces** — Cheapest, but shared IAM, shared quotas, shared blast radius; fails most security questionnaires.
- **Three accounts (dev, staging, prod):** A separate staging account keeps staging honest, but it adds a third copy of the platform's always-on cost before there is traffic to stage. Deferred until there is.
- **Account per tenant** — Only as a System-tier option (ADR-0008), not the default.

## Consequences

**Positive**

- Hard isolation of production data; least-privilege CI roles per account; a clean answer for HECVAT and SOC 2; our Terraform is proven against SCPs.

**Negative / Trade-offs**

- Two deployments to keep in sync, and until staging exists, dev is the only place to try a change before prod; certificates and DNS validation per account; more bootstrap work (state buckets, OIDC providers) before the first apply.
- Cross-account access for support and observability must be designed (roles, not shared credentials).

**Neutral / Follow-ups**

- Bootstrap module for state buckets and lock tables (`infra/terraform/bootstrap/`).
- Remove the committed `tfplan` and `.bak` files; ignore plan files in git.

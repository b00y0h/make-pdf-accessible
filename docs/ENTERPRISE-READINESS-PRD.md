# Make PDF Accessible — Enterprise Readiness

## Identity, tenancy, permissions, audit, metering, billing, reliability and compliance so a university procurement office can say yes.

**Status:** Draft v1.0 (2026-09-28)
**Parent:** `docs/PLATFORM-PRD.md` (stage Operate)
**Implements ADRs:** ADR-0006 (Aurora PostgreSQL + DynamoDB), ADR-0007 (Cognito identity), ADR-0008 (tenant isolation), ADR-0010 (multi-account environments), ADR-0004 (evidence immutability)

---

## CONTEXT

Authentication is split three ways: the dashboard uses BetterAuth with Prisma (`dashboard/src/lib/auth-server.ts`, `dashboard/src/lib/auth-client.ts`, `dashboard/better-auth_migrations/`), the API validates BetterAuth HS256 JWTs (`services/api/app/auth.py`) and API keys (`services/api/app/middleware/api_key_auth.py`), and Terraform provisions a Cognito user pool with Google and SAML providers (`infra/terraform/cognito.tf`) that the worker's JWT code targets. Persistence is split as well: MongoDB in development (`services/shared/mongo/`), DocumentDB and DynamoDB in Terraform, PostgreSQL for BetterAuth, OpenSearch Serverless for embeddings. Quotas (`services/shared/quota_enforcement.py`, `services/api/app/routes/quotas.py`) and API keys exist; billing does not (the dashboard shows a placeholder "Professional - $99/month"). RBAC is admin/viewer. The audit log does not exist. Environments share one AWS account with an `environment` variable. There is no SLO definition, no DR runbook and no compliance program.

Higher-education procurement asks for: SSO through the campus IdP (SAML via InCommon/Shibboleth, Microsoft Entra ID, Google Workspace), a VPAT/ACR, HECVAT, SOC 2, a FERPA addendum, data residency and retention statements, an accessibility statement, and an SLA.

The motivating gaps:

1. **Three identity systems and none of them do SAML for customers.**
2. **Four data stores for one product**, with dual-write code (`services/shared/persistence.py`) to keep them in sync.
3. **No billing, no metering to invoice against, no plan enforcement beyond a counter.**
4. **No audit log, no RBAC beyond two roles, no tenant isolation guarantees in storage or keys.**
5. **No environments, SLOs, DR or compliance evidence.**

### Locked Scope Decisions

1. **Amazon Cognito is the only identity provider for humans**: hosted UI with OIDC for the dashboard, SAML 2.0 and OIDC federation per tenant (InCommon metadata, Entra ID, Google), MFA for non-federated users, RS256 JWTs validated by the API through JWKS. BetterAuth and its tables are removed. (ADR-0007)
2. **API keys and connector keys remain our own**, stored hashed, scoped, and tenant-bound (`services/api/app/routes/api_keys.py` is kept and extended).
3. **Aurora PostgreSQL Serverless v2 is the system of record**; DynamoDB holds pipeline state and the artifact index; MongoDB, DocumentDB, dual-write and OpenSearch Serverless are removed. Row-level security enforces `tenant_id` on every table. (ADR-0006)
4. **Pooled multi-tenancy with tenant-scoped encryption**: one platform, S3 prefixes per tenant, a KMS key per tenant tier (Team/Campus share a key with per-tenant encryption context; System tier gets a dedicated key, optionally a dedicated AWS account). (ADR-0008)
5. **Three AWS accounts (dev, staging, prod) under AWS Organizations**, Terraform state per account in S3 with DynamoDB locking, GitHub OIDC roles per account, no long-lived credentials anywhere. (ADR-0010)
6. **Metering is the source of truth for invoices.** Every page processed writes a usage record; Stripe Billing handles subscriptions, invoices, and tax; overages are usage-based line items.
7. **Roles are fixed for v1**: `owner`, `admin`, `editor`, `reviewer`, `viewer`, `billing`. Custom roles are out of scope.
8. **Evidence is immutable**: S3 Object Lock in compliance mode, KMS-signed manifests, retention configurable per tenant (1 to 7 years).
9. **We define SLOs before we sell an SLA**; error budgets gate releases.

### What This Is NOT

- Not a custom IdP. We federate; we do not replace campus identity.
- Not per-tenant infrastructure by default; dedicated accounts are a System-tier option, not the architecture.
- Not FedRAMP. Section 508 federal customers are a later market; we design to not preclude it (no public buckets, encryption everywhere, audit logs), but no authorization program is in scope.
- Not a data warehouse or BI tool; Reports stay operational.
- Not self-hosting or on-premises deployment.

---

## SUCCESS CRITERIA

1. A tenant admin can upload SAML metadata (or an InCommon entity id, or Entra ID/Google OIDC settings) in `/settings/sso`, test the connection, enforce SSO for the tenant's domain, and sign in through the campus IdP; JIT-provisioned users land in the `viewer` role until assigned.
2. Every API and dashboard request resolves to exactly one `tenant_id`; a test suite proves a user of tenant A cannot read, list or download any row or object of tenant B through any route, including signed URLs, search and exports.
3. Postgres row-level security is enabled on every tenant-scoped table, and the application connects with a role that cannot bypass it; a migration check in CI fails if a new table lacks the policy.
4. Every state change (documents, decisions, publications, review resolutions, roles, keys, settings, billing) writes an `audit_log` row with actor, tenant, action, target, before/after (redacted for secrets), IP and user agent; the log is exportable and retained 7 years.
5. Usage records exist per page per stage per tenant; the dashboard's usage view, the monthly Stripe invoice and the `usage_meters` table agree to the page; quotas stop new jobs at the plan limit with a clear message and an upgrade path, and overage is billed at the published rate.
6. Plans (Free, Team, Campus, System) and the Verified add-on are configured in Stripe; upgrades, downgrades, proration, failed payments and dunning work end to end in Stripe's test clock scenarios; invoices are downloadable in `/settings/billing`.
7. Dev, staging and prod are separate AWS accounts; `terraform plan` for prod runs only from `main` through the GitHub OIDC role; production applies require an environment approval; no IAM user access keys exist in any account.
8. SLOs are defined and measured: API availability 99.9% (30-day), dashboard availability 99.9%, job success rate 99% (excluding customer-caused failures), upload-to-evidence p95 10 minutes for 50-page born-digital documents; dashboards and burn-rate alerts exist; the status page reflects them.
9. Backups: Aurora point-in-time recovery (35 days) and daily snapshots copied cross-region; S3 versioning with cross-region replication for originals, accessible outputs and evidence; a documented, tested restore achieves RPO 1 hour and RTO 4 hours in a staging game day each quarter.
10. Compliance artifacts exist and are current: ACR/VPAT for the dashboard and marketing site, HECVAT Full, security whitepaper, FERPA DPA template, subprocessors list, accessibility statement, incident response plan; SOC 2 Type I report within 9 months of launch and Type II within 18.
11. Data deletion: a tenant admin can delete a document, a site or the tenant; deletion removes rows, S3 objects (except evidence under retention, which is tombstoned and expires at retention end) and search indexes within 24 hours, and a deletion certificate is issued.
12. Security controls verified in CI and periodically: dependency scanning (existing), container scanning (existing `ecr-security-scan.yml.disabled` re-enabled), secret scanning, IaC scanning (`.checkov.yaml`, `.tflint.hcl`), annual third-party penetration test, quarterly access reviews.

---

## DATA MODEL CHANGES

### New table — `tenants`

```
tenants
  - id: uuid [pk]
  - slug: text [unique]                              // used in Accessible Link
  - name, kind: enum(university, community_college, k12_district, local_government, healthcare, publisher, other)
  - plan: enum(free, team, campus, system)
  - region: text                                     // data residency; v1: us-east-1
  - kms_key_arn: text                                // tier key or dedicated key
  - compliance_date: date                            // default 2027-04-26
  - evidence_retention_years: int [1..7]
  - sso_required: bool
  - stripe_customer_id, stripe_subscription_id: text
  - status: enum(trial, active, past_due, suspended, deleted)
  - created_at, updated_at
```

### New tables — `users`, `memberships`, `sso_configs`

```
users: id, cognito_sub [unique], email, name, last_login_at, created_at
memberships: user_id, tenant_id, role: enum(owner, admin, editor, reviewer, viewer, billing), invited_by, created_at   // pk (user_id, tenant_id)
sso_configs: tenant_id [pk], kind: enum(saml, oidc), cognito_provider_name, metadata_url|metadata_xml_ref, domains: text[], jit_role, enforced: bool, tested_at
```

### New tables — `api_keys` (migrated), `audit_log`, `usage_meters`, `invoices`

```
api_keys: id, tenant_id, name, key_hash, prefix, scopes: text[], kind: enum(user, connector), created_by, last_used_at, expires_at, revoked_at
audit_log: id, tenant_id, actor_user_id|actor_key_id, action, target_type, target_id, before: jsonb, after: jsonb, ip, user_agent, at   // append-only, partitioned by month
usage_meters: id, tenant_id, job_id, document_id, stage, unit: enum(page, token_in, token_out, vcpu_second, byte), quantity, cost_cents, at   // partitioned by month
invoices: id, tenant_id, stripe_invoice_id, period_start, period_end, pages_included, pages_used, overage_pages, total_cents, status
```

### Retired

`dashboard/better-auth_migrations/`, `dashboard/prisma/schema.prisma` Placeholder model, `services/shared/mongo/*`, `services/shared/persistence.py` dual-write, `infra/terraform/documentdb.tf`, `documentdb-test.tf`, `lambda-layers.tf` (DocumentDB utilities), `opensearch.tf`.

---

## FEATURE 1 — IDENTITY AND SSO

- Cognito user pool per environment (existing `infra/terraform/cognito.tf`), hosted UI on `auth.makepdfaccessible.com`, app clients for dashboard (PKCE) and LTI tool.
- Per-tenant identity providers created through the API (`POST /v1/tenants/{id}/sso`) using Cognito's `CreateIdentityProvider` with SAML metadata or OIDC settings; identifier-first login by email domain; attribute mapping for email, name, and an optional `eduPersonAffiliation`.
- MFA (TOTP) required for non-federated `owner`/`admin`/`billing` users.
- API: validate RS256 JWTs against the pool's JWKS (replace HS256 in `services/api/app/auth.py`); short-lived access tokens; refresh handled by the dashboard.

## FEATURE 2 — TENANCY, RBAC AND AUDIT

- `tenant_id` on every row; Postgres RLS with `SET app.tenant_id` per request; S3 keys prefixed `{tenant_id}/`; IAM session tags (`tenant_id`) on Lambda invocations for S3 access with ABAC conditions.
- Role permissions matrix (v1):

| Capability                                   | owner | admin | editor | reviewer | viewer | billing |
| -------------------------------------------- | ----- | ----- | ------ | -------- | ------ | ------- |
| Manage SSO, roles, keys, deletion            | ✓     | ✓     |        |          |        |         |
| Sites, crawls, triage overrides              | ✓     | ✓     | ✓      |          |        |         |
| Submit jobs, publish back                    | ✓     | ✓     | ✓      |          |        |         |
| Resolve review items                         | ✓     | ✓     |        | ✓        |        |         |
| View inventory, documents, evidence, reports | ✓     | ✓     | ✓      | ✓        | ✓      | ✓       |
| Billing and invoices                         | ✓     |       |        |          |        | ✓       |

- Audit log writer as a shared middleware plus DB triggers for defense in depth; export to S3 monthly; dashboard viewer at `/settings/audit`.

## FEATURE 3 — METERING, QUOTAS AND BILLING

- `usage_meters` written by the pipeline's Evidence step (per page per stage) and by the crawler (pages fetched).
- Plan limits from `tenants.plan` with an override table; the ingest step checks remaining pages before starting a job; soft limit at 80% triggers an email.
- Stripe Billing: products and prices mirror the published price list; Checkout for self-serve Team; Invoicing for Campus/System (PO, net-30); usage-based overage reported nightly through Stripe's meter API; webhooks (`invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`) update `tenants.status`.
- `/settings/billing`: plan, usage this period, invoices, payment method, upgrade.

## FEATURE 4 — ENVIRONMENTS, DELIVERY AND SECRETS

- AWS Organizations with `dev`, `staging`, `prod` accounts; SCPs deny public S3, deny IAM users, restrict regions.
- Terraform: `backend.tf` partial S3 backend configured per environment (`infra/terraform/environments/*.backend.hcl`), tfvars per environment, one workspace per account; state buckets with versioning and Object Lock.
- GitHub Actions: existing OIDC roles (`infra/terraform/github_oidc.tf`) instantiated per account; `infra-ci.yml` plans on PR and applies on `main` with environment protection for `prod`.
- Secrets in AWS Secrets Manager only (engine licenses, Adobe, Stripe, CRM, LTI keys); rotation for database credentials via Aurora managed rotation.

## FEATURE 5 — RELIABILITY

- SLOs as above; CloudWatch composite alarms and burn-rate alerts to the existing `alerts` SNS topic (`infra/terraform/sns.tf`) and PagerDuty; status page (Statuspage or Instatus) fed by synthetic checks.
- Capacity: Step Functions concurrency per tenant tier; Fargate service auto-scaling on queue depth; Aurora Serverless v2 min/max ACU per environment.
- DR: cross-region replication (us-west-2) for S3 and Aurora snapshots; Terraform can rebuild the stack in the secondary region; quarterly game day.
- Change management: PR review required, CI gates (lint, tests, IaC scan, container scan), blue/green for the API Lambda (existing alias pattern), canary for the dashboard.

## FEATURE 6 — COMPLIANCE PROGRAM

- SOC 2 (Security, Availability, Confidentiality) with a compliance automation platform collecting evidence from AWS, GitHub and the HR system; policies (access control, change management, incident response, vendor management, data classification, business continuity) authored in `docs/policies/`.
- HECVAT Full and the security whitepaper maintained alongside.
- ACR (VPAT 2.5) for the dashboard, marketing site and evidence PDFs, updated each major release; accessibility statement page.
- FERPA: DPA template; course data minimization in the LTI tool; no model training on customer content; subprocessors list (AWS, Anthropic via Bedrock, Stripe, email provider, CRM).
- Privacy: retention schedule, deletion procedure and certificate, cookie policy for the marketing site.

---

## API ROUTES

| Method          | Path                     | Auth              | Purpose                                                       |
| --------------- | ------------------------ | ----------------- | ------------------------------------------------------------- |
| GET/PATCH       | `/v1/tenants/me`         | `admin`           | Tenant settings (retention, compliance date, SSO enforcement) |
| POST            | `/v1/tenants/me/sso`     | `owner`/`admin`   | Configure SAML/OIDC; `POST .../test`                          |
| GET/POST/DELETE | `/v1/tenants/me/members` | `owner`/`admin`   | Memberships and roles                                         |
| GET             | `/v1/audit`              | `admin`           | Audit log query and export                                    |
| GET             | `/v1/usage`              | any member        | Usage this period by stage                                    |
| GET             | `/v1/billing/*`          | `owner`/`billing` | Plan, invoices, portal session                                |
| POST            | `/v1/tenants/me/delete`  | `owner`           | Tenant deletion with confirmation                             |

## ENVIRONMENT VARIABLES

| Var                                                              | Purpose                                         | Example (placeholder)                                                      |
| ---------------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------- |
| `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_REGION`    | Identity (exist in `infra/terraform/lambda.tf`) | pool id, client id, region                                                 |
| `COGNITO_JWKS_URL`                                               | JWT validation                                  | `https://cognito-idp.us-east-1.amazonaws.com/<pool>/.well-known/jwks.json` |
| `DATABASE_URL`                                                   | Aurora (from Secrets Manager)                   | `postgresql://...`                                                         |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`                     | Billing (Secrets Manager)                       | `sk_live_...` placeholder                                                  |
| `STRIPE_PRICE_TEAM`, `STRIPE_PRICE_CAMPUS`, `STRIPE_METER_PAGES` | Price and meter ids                             | `price_...`, `mtr_...`                                                     |
| `AUDIT_EXPORT_BUCKET`                                            | Monthly audit exports                           | bucket name                                                                |
| `TENANT_KMS_KEY_ALIAS_PREFIX`                                    | Tier/tenant keys                                | `alias/mpa-tenant-`                                                        |
| `STATUS_PAGE_API_KEY`                                            | Status page updates (Secrets Manager)           | placeholder                                                                |

## TESTING STRATEGY

- **Tenant isolation suite:** parametrized tests over every route with two tenants; object-level checks on signed URLs; RLS policy presence check in migrations.
- **Auth:** JWKS validation, token expiry, role matrix tests, SSO login flow e2e against a SAML test IdP (SimpleSAMLphp in Docker) and an Entra ID test tenant.
- **Billing:** Stripe test clocks for upgrade, downgrade, overage, failed payment, cancellation; invoice/meter reconciliation test.
- **Reliability:** load test to 2× expected peak; chaos test killing Fargate tasks mid-page; quarterly restore drill with timing recorded.
- **Compliance:** automated evidence collection; CI gates for IaC and container scanning; annual pen test remediation tracked.

## MILESTONES / ROLLOUT PLAN

| Slice                           | Scope                                                                                       | Value delivered alone             |
| ------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------- |
| E1 — Data consolidation         | Aurora schema, migrations from Mongo, RLS, DynamoDB pipeline tables; dual-write removed     | One database to reason about      |
| E2 — Identity                   | Cognito everywhere, SAML/OIDC per tenant, RS256 in the API, BetterAuth removed, role matrix | Campus SSO works                  |
| E3 — Audit + metering + quotas  | audit_log, usage_meters, plan enforcement                                                   | Trust and invoiceable usage       |
| E4 — Billing                    | Stripe products, checkout, invoicing, overage meters, `/settings/billing`                   | Revenue                           |
| E5 — Environments + reliability | Three accounts, backends, SLOs, alarms, DR replication, status page                         | Operable and sellable with an SLA |
| E6 — Compliance                 | Policies, SOC 2 Type I, HECVAT, ACR, DPA                                                    | Procurement can say yes           |

## OPEN QUESTIONS

1. **Compliance automation vendor** (Vanta, Drata, Secureframe): choose by cost and AWS/GitHub integrations before E6.
2. **Status page vendor** and whether to expose per-tenant status.
3. **Second region** for data residency (Canada: ca-central-1?) and its timing (S7).
4. **Do System-tier dedicated accounts run our Terraform in the customer's AWS Organization or ours?** Ours is simpler to operate; theirs may be required by some state policies. Decide when the first System deal asks.

## RISKS

- **Migration off MongoDB while shipping features.** Mitigation: E1 first, feature flags on the persistence layer, one-way migration scripts with verification counts.
- **Cognito SAML quirks with InCommon metadata aggregates.** Mitigation: per-tenant metadata upload rather than the aggregate; test with two campuses early.
- **SOC 2 timeline slips.** Mitigation: start evidence collection in E3; Type I is a snapshot and can be scheduled once controls exist.

---

## SOURCES & RELATED DOCS

- `docs/PLATFORM-PRD.md` — parent
- `docs/adr/0006-aurora-postgresql-system-of-record.md`, `0007-cognito-identity-with-federation.md`, `0008-pooled-multitenancy-with-tenant-keys.md`, `0010-multi-account-environments.md`
- `docs/ENTERPRISE-READINESS-SPECS.md`, `docs/AWS-DEPLOYMENT-SPECS.md` — execution specs
- `.planning/codebase/CONCERNS.md` — known security debt this PRD retires

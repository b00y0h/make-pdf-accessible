# Make PDF Accessible — Enterprise Readiness Implementation Specs

These specs implement `docs/ENTERPRISE-READINESS-PRD.md` (ADR-0006, ADR-0007, ADR-0008, ADR-0010). Starting state: BetterAuth in the dashboard with HS256 JWTs validated by the API, a Cognito pool provisioned but unused by the dashboard, MongoDB in development with DocumentDB and DynamoDB in Terraform and a dual-write layer, quotas and API keys without billing, admin/viewer roles, no audit log, no SLOs.

Environment and state work (multi-account, backends) is in `docs/AWS-DEPLOYMENT-SPECS.md`.

---

## Spec 1 — Aurora PostgreSQL, migrations framework and core tenancy tables

### Problem

There is no relational system of record and no migration tool for the API (the dashboard has Prisma with a placeholder model). Target: Aurora Serverless v2 in Terraform, Alembic migrations in the API, and the `tenants`, `users`, `memberships`, `api_keys`, `audit_log` tables with row-level security.

### Files to touch

| File                                                                                 | Action                                                                                                                                                                       |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/aurora.tf`                                                          | Create: cluster (Serverless v2, min/max ACU per env), subnet group, security group, managed master secret with rotation, RDS Proxy, parameter group with `rds.force_ssl = 1` |
| `infra/terraform/variables.tf`                                                       | Add `aurora_min_acu`, `aurora_max_acu`                                                                                                                                       |
| `infra/terraform/lambda.tf`                                                          | Add `DATABASE_SECRET_ARN` and RDS Proxy endpoint to the API environment; security group rule to the proxy                                                                    |
| `services/api/app/db/__init__.py`, `session.py`, `rls.py`                            | Create: SQLAlchemy 2 engine, per-request `SET LOCAL app.tenant_id`, `app_rw` role that cannot bypass RLS                                                                     |
| `services/api/alembic.ini`, `services/api/app/db/migrations/env.py`, `0001_core.sql` | Create                                                                                                                                                                       |
| `services/api/app/config.py`                                                         | Add `database_url`/`database_secret_arn`; remove Mongo settings after Spec 2                                                                                                 |
| `services/api/tests/test_rls.py`                                                     | Create: two-tenant isolation over every route                                                                                                                                |
| `.github/workflows/api-ci.yml`                                                       | Add a Postgres service and a migration check (`alembic upgrade head` then a script that fails on any tenant-scoped table without an RLS policy)                              |

### Acceptance criteria

1. `alembic upgrade head` creates the tables with RLS enabled and the `app_rw` role; the CI check passes.
2. The API connects through RDS Proxy with IAM authentication from Lambda (no password in environment variables).
3. `test_rls.py` passes for every route.

### Implementation

1A. `rls.py` middleware resolves the tenant from the token or key, opens a transaction and runs `SET LOCAL app.tenant_id = :tenant_id`; background jobs call the same helper explicitly.
1B. Every tenant-scoped table: `alter table t enable row level security; create policy tenant_isolation on t using (tenant_id = current_setting('app.tenant_id', true)::uuid);` plus `force row level security`.

---

## Spec 2 — Migrate documents, jobs, alt text, API keys and demo sessions off MongoDB

### Problem

`services/shared/mongo/{documents,jobs,alt_text,api_keys,demo_sessions}.py` and `services/shared/persistence.py` (dual write) back the API and worker; the dashboard reads Mongo through `dashboard/src/lib/mongodb.ts`. Target: repositories over PostgreSQL, a one-way migration script, and removal of Mongo, DocumentDB and OpenSearch resources.

### Files to touch

| File                                                                                                                                                                  | Action                                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/db/migrations/0003_documents_jobs.sql`                                                                                                              | Create: `documents`, `jobs`, `artifacts`, `review_items`, `evidence_packs`, `document_locations` (schemas from the pipeline PRD) |
| `services/api/app/repositories/{documents,jobs,artifacts,api_keys}.py`                                                                                                | Create: SQLAlchemy implementations of the `DocumentRepository` and `JobRepository` protocols in `services/shared/persistence.py` |
| `services/shared/persistence.py`                                                                                                                                      | Reduce to a factory that returns the Postgres repositories; delete dual-write and Dynamo/Mongo branches                          |
| `services/shared/mongo/**`, `packages/schemas/mongo/**`, `scripts/mongo-init/**`, `scripts/seed-dev-data.py`, `scripts/simple-seed.py`, `test_mongodb_integration.py` | Delete after migration                                                                                                           |
| `scripts/migrate_mongo_to_postgres.py`                                                                                                                                | Create: idempotent copy with verification counts; run once per environment                                                       |
| `dashboard/src/lib/mongodb.ts`                                                                                                                                        | Delete; dashboard reads through the API only                                                                                     |
| `docker-compose.yml`, `Makefile`                                                                                                                                      | Remove `mongo`, `mongo-express`, `postgres-auth`; keep one `postgres`                                                            |
| `infra/terraform/documentdb.tf`, `documentdb-test.tf`, `lambda-layers.tf`, `opensearch.tf`                                                                            | Delete; remove references in `lambda.tf`, `processing-lambdas.tf`, `monitoring.tf`, `outputs.tf`, `vpc.tf` (OpenSearch endpoint) |
| `DOCUMENTDB_SETUP.md`                                                                                                                                                 | Delete; add a note to `infra/terraform/README.md`                                                                                |

### Acceptance criteria

1. `grep -rn "pymongo\|motor\|MONGODB" services/ dashboard/src | wc -l` is 0 after cutover.
2. The migration script reports equal counts per collection/table and a checksum over document ids.
3. `terraform plan` shows the DocumentDB cluster, its secret, the Lambda layers and the OpenSearch collection destroyed and nothing else unexpectedly changed.

---

## Spec 3 — Cognito everywhere: dashboard, API, per-tenant SSO; BetterAuth removed

### Problem

Three identity systems. Target: Cognito hosted UI (PKCE) in the dashboard, RS256 validation in the API, per-tenant SAML/OIDC providers created through the API, MFA for privileged local users.

### Files to touch

| File                                                                                                                                                                                                                                                        | Action                                                                                                                                                                                                                                                                                                                                   |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/cognito.tf`                                                                                                                                                                                                                                | Hosted UI custom domain `auth.<domain>` with the ACM cert; app clients `dashboard` (PKCE, no secret) and `lti`; `advanced_security_mode = ENFORCED`; MFA optional pool-wide (enforced per role in the app); remove the hard-coded `ExampleSAML` provider; add a `pre_token_generation` Lambda that injects `tenant_id` and `role` claims |
| `services/functions/auth_token/main.py`                                                                                                                                                                                                                     | Create: pre-token-generation trigger reading `memberships`                                                                                                                                                                                                                                                                               |
| `services/api/app/auth.py`                                                                                                                                                                                                                                  | Replace HS256 validation with JWKS RS256 (cached keys); resolve `tenant_id` and `role` from claims; keep API-key path                                                                                                                                                                                                                    |
| `services/api/app/routes/auth.py`                                                                                                                                                                                                                           | Delete sign-up/sign-in (hosted UI owns them); keep `/v1/auth/me`                                                                                                                                                                                                                                                                         |
| `services/api/app/routes/tenants.py`                                                                                                                                                                                                                        | Create: `GET/PATCH /v1/tenants/me`, `POST /v1/tenants/me/sso`, `POST /v1/tenants/me/sso/test`, members and roles                                                                                                                                                                                                                         |
| `services/api/app/services/cognito_sso.py`                                                                                                                                                                                                                  | Create: `CreateIdentityProvider`, `UpdateUserPoolClient` supported providers, domain → provider mapping                                                                                                                                                                                                                                  |
| `dashboard/src/lib/auth-server.ts`, `auth-client.ts`, `auth-middleware.ts`, `auth.ts`, `auth-unused.ts`, `dashboard/better-auth_migrations/**`, `dashboard/src/app/api/auth/**`, `dashboard/src/app/sign-in/page.tsx`, `dashboard/src/app/sign-up/page.tsx` | Delete                                                                                                                                                                                                                                                                                                                                   |
| `dashboard/src/lib/auth/cognito.ts`, `dashboard/src/middleware.ts`                                                                                                                                                                                          | Create/rewrite: PKCE login with the hosted UI, token storage in httpOnly cookies via a small route handler, refresh, logout                                                                                                                                                                                                              |
| `dashboard/src/app/(dashboard)/settings/sso/page.tsx`, `.../settings/members/page.tsx`                                                                                                                                                                      | Create                                                                                                                                                                                                                                                                                                                                   |
| `dashboard/package.json`                                                                                                                                                                                                                                    | Remove `better-auth`, `@better-auth/cli`, `prisma`, `@prisma/client`, `aws-amplify` if unused; add `oidc-client-ts` or `openid-client`                                                                                                                                                                                                   |
| `docker-compose.yml`                                                                                                                                                                                                                                        | Remove `API_JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`, `BETTER_AUTH_DASHBOARD_URL`; add `COGNITO_*` (or a local OIDC mock for dev)                                                                                                                                                                                                       |
| `services/shared/auth.py`, `services/shared/auth_README.md`                                                                                                                                                                                                 | Update to the JWKS validator shared by functions                                                                                                                                                                                                                                                                                         |
| `e2e/shared/auth.ts`, `e2e/dashboard/auth/**`                                                                                                                                                                                                               | Rewrite for the hosted UI flow (use a test user pool)                                                                                                                                                                                                                                                                                    |

### Acceptance criteria

1. Local dev: `make up` starts a mock OIDC provider (or points at a dev Cognito pool) and the dashboard signs in; no `API_JWT_SECRET` exists anywhere.
2. A tenant admin configures SAML with a SimpleSAMLphp test IdP in CI and an Entra ID test tenant in staging; JIT users get `viewer`.
3. `owner`, `admin` and `billing` local users are forced to enroll TOTP on first login.
4. The API rejects HS256 tokens and accepts RS256 tokens with the correct `aud` and `iss`.

### Implementation

3A. Token claims: `custom:tenant_id`, `custom:role` set by the pre-token trigger from `memberships`; the API treats claims as authoritative for the request and re-reads memberships on role changes (short token TTL of 15 minutes).
3B. Identifier-first login: `/sign-in` asks for e-mail, looks up `sso_configs.domains`, and redirects to the hosted UI with `identity_provider=<provider>` when enforced.

---

## Spec 4 — Audit log, usage metering and plan enforcement

### Problem

No audit trail; quotas count but do not meter; nothing to invoice against. Target: `audit_log` writes from a shared middleware and DB triggers; `usage_meters` written by the pipeline and crawler; plan limits enforced at ingest.

### Files to touch

| File                                                                                                     | Action                                                                                        |
| -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `services/api/app/db/migrations/0004_audit_usage.sql`                                                    | Create: `audit_log` (partitioned by month), `usage_meters` (partitioned), `plan_limits`       |
| `services/api/app/middleware/audit.py`                                                                   | Create: records actor, action (derived from route + method), target, before/after (redacted)  |
| `services/api/app/main.py`                                                                               | Add the middleware                                                                            |
| `services/api/app/routes/audit.py`, `services/api/app/routes/usage.py`                                   | Create                                                                                        |
| `services/shared/quota_enforcement.py`, `services/api/app/quota.py`, `services/api/app/routes/quotas.py` | Rewrite over `plan_limits` and `usage_meters`; 80% soft-limit e-mail                          |
| `services/functions/evidence/main.py`, `services/crawler/sink.py`                                        | Write `usage_meters` rows (page, tokens, vcpu seconds, bytes)                                 |
| `dashboard/src/app/(dashboard)/settings/audit/page.tsx`, `.../usage/page.tsx`                            | Create                                                                                        |
| `infra/terraform/s3.tf`                                                                                  | Add `audit_exports` bucket with Object Lock; monthly export Lambda in `processing-lambdas.tf` |

### Acceptance criteria

1. Every mutating route produces one `audit_log` row (a test iterates the OpenAPI spec and asserts coverage).
2. Usage per job matches the pipeline's cost breakdown; the usage page and `GET /v1/usage` agree.
3. A tenant at its page limit gets HTTP 402 with `upgrade_url` from `POST /v1/jobs`; the crawler stops at its page cap.

---

## Spec 5 — Stripe billing

### Problem

No billing. Target: Stripe products and prices mirroring the published list, Checkout for Team, invoicing for Campus/System, usage-based overage through Stripe meters, and the billing settings page.

### Files to touch

| File                                                      | Action                                                                                                                                    |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/routes/billing.py`                      | Create: plan, portal session, checkout session, invoices; Stripe webhook receiver with signature verification                             |
| `services/api/app/services/stripe_service.py`             | Create: customer sync, subscription state → `tenants.status`, nightly meter reporting job                                                 |
| `services/functions/billing_meter/main.py`                | Create: scheduled Lambda that reports overage from `usage_meters` to Stripe meters                                                        |
| `infra/terraform/secrets.tf`                              | Add `stripe` secret (keys, webhook secret)                                                                                                |
| `infra/terraform/eventbridge.tf`                          | Nightly schedule for the meter Lambda                                                                                                     |
| `dashboard/src/app/(dashboard)/settings/billing/page.tsx` | Create                                                                                                                                    |
| `docs/business/BUSINESS-PLAN.md` §5                       | Source of truth for prices; `services/api/tests/test_pricing_sync.py` asserts the Stripe price ids map to the listed amounts in test mode |

### Acceptance criteria

1. Stripe test-clock scenarios for upgrade, downgrade with proration, overage invoice, failed payment and dunning pass in CI (recorded fixtures).
2. `tenants.status` transitions on webhooks; suspended tenants get 402 on job creation but can still read evidence.

---

## Spec 6 — SLOs, alarms, DR and status page

### Problem

No SLO definitions or DR. Target: SLO metrics and burn-rate alarms in Terraform, cross-region replication, a tested restore runbook, and a status page.

### Files to touch

| File                                                                                         | Action                                                                                                                                                                                  |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/monitoring.tf`                                                              | Add SLO metric math (availability from API Gateway 5xx, job success from Step Functions, latency from a custom metric), composite alarms and burn-rate alarms to `aws_sns_topic.alerts` |
| `infra/terraform/replication.tf`                                                             | Create: S3 cross-region replication for originals, accessible, evidence; Aurora snapshot copy; KMS multi-region keys where needed                                                       |
| `infra/terraform/providers.tf`                                                               | Add the `aws.secondary` provider (us-west-2)                                                                                                                                            |
| `docs/runbooks/restore.md`, `docs/runbooks/incident-response.md`, `docs/runbooks/on-call.md` | Create                                                                                                                                                                                  |
| `.github/workflows/synthetics.yml`                                                           | Create: scheduled smoke checks of `/health`, dashboard and marketing site; updates the status page via API                                                                              |

### Acceptance criteria

1. Burn-rate alarms page on-call when the 30-day error budget burns at 14.4× for 1 hour or 6× for 6 hours.
2. A staging restore from the secondary region completes within 4 hours in a recorded game day.

---

## Spec 7 — Compliance program scaffolding

### Problem

No policies, ACR, HECVAT or SOC 2 evidence. Target: the documents and CI controls the PRD lists.

### Files to touch

| File                                                                                                                                                         | Action                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `docs/policies/*.md` (access-control, change-management, incident-response, vendor-management, data-classification, business-continuity, secure-development) | Create                                                   |
| `docs/compliance/HECVAT.md`, `docs/compliance/security-whitepaper.md`, `docs/compliance/subprocessors.md`, `docs/compliance/ACR.md`                          | Create                                                   |
| `.github/workflows/security-scan.yml.disabled`, `ecr-security-scan.yml.disabled`                                                                             | Rename to enable; fix whatever broke them                |
| `.github/CODEOWNERS`, `.github/pull_request_template.md`                                                                                                     | Create: review requirements and the legal/copy checklist |

### Acceptance criteria

1. Every policy has an owner, review date and version; the compliance automation platform reads them from the repo.
2. Container and dependency scans run on every PR and block on critical findings.

---

## Suggested execution order

1. Spec 1 first — everything else needs the database and RLS.
2. Spec 2 — the Mongo cutover; do it before the pipeline specs add tables, so there is one schema.
3. Spec 3 — identity; can start in parallel with Spec 2 since it touches different code, but the dashboard rewrite is large.
4. Spec 4 — audit and metering depend on Specs 1 and 3 (actor identity).
5. Spec 5 — billing depends on Spec 4's meters.
6. Spec 6 — reliability work is independent and can proceed alongside 4 and 5.
7. Spec 7 — scaffolding is documentation; start early, finish after the controls in 3, 4 and 6 exist.

Net effect: one database with enforced tenant isolation, campus SSO, an audit trail, metered usage that bills itself, defined SLOs with DR, and the documents procurement asks for.

# ADR-0008: Pooled multi-tenancy with row-level security, tenant-prefixed storage and tenant-scoped KMS keys; dedicated accounts only as a System-tier option

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Tenant isolation across database, storage, compute and keys
- **Related:** `docs/ENTERPRISE-READINESS-PRD.md`, ADR-0006, ADR-0007, ADR-0010

## Context

Today tenancy is a `tenant_id` field with no enforcement in storage or keys; the gap report lists missing data-isolation enforcement as a risk. Buyers ask how their data is separated from other institutions' data, whether keys are theirs, and sometimes whether the deployment can live in their own AWS account. Full isolation per tenant (stack per customer) is expensive to operate for a small team and slows releases; a pool with no enforcement is unsellable.

## Decision

We will run one pooled platform per environment with isolation enforced at four layers: (1) Postgres row-level security keyed on `tenant_id` set per request, with an application role that cannot bypass it; (2) S3 object keys prefixed by `tenant_id` and IAM ABAC conditions using session tags so pipeline tasks can only touch their tenant's prefix; (3) KMS encryption context including `tenant_id` on every object, with a shared key per tier for Team and Campus and a dedicated key per tenant for System; (4) per-tenant quotas and concurrency limits. A System-tier customer may buy a dedicated AWS account deployed from the same Terraform, operated by us.

## Alternatives Considered

- **Silo per tenant (stack per customer)** — Strongest isolation, but N stacks to upgrade and monitor; impossible before 2027 with the team size.
- **Pool with application-level checks only** — Cheapest, but a single missed `WHERE tenant_id` leaks data; RLS and ABAC make the failure mode a denied request instead.
- **Bridge model with a database per tenant** — Moderate isolation, but schema migrations across hundreds of databases and no faceted cross-tenant operations for us.

## Consequences

**Positive**

- Defense in depth that a security review can verify; cost stays pooled; a credible answer for procurement with a dedicated-account escape hatch.

**Negative / Trade-offs**

- RLS adds complexity to migrations and background jobs (each must set the tenant context); ABAC session tags add IAM complexity.
- Dedicated KMS keys per System tenant cost about $1 per month each plus request charges and need rotation management.

**Neutral / Follow-ups**

- A CI check must fail when a new tenant-scoped table lacks an RLS policy.
- Write the dedicated-account runbook when the first System customer requires it.

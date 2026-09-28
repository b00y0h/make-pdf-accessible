# ADR-0006: Aurora PostgreSQL as system of record with DynamoDB for pipeline state; retire MongoDB, DocumentDB and OpenSearch Serverless

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Persistence layer for API, dashboard, pipeline and inventory
- **Related:** `docs/ENTERPRISE-READINESS-PRD.md`, `docs/INVENTORY-TRIAGE-PRD.md`, ADR-0008

## Context

The platform uses MongoDB in development (`services/shared/mongo/`), provisions DocumentDB (`infra/terraform/documentdb.tf`, plus a Lambda layer for its TLS client) and DynamoDB tables (`dynamodb.tf`) in AWS, keeps a dual-write persistence manager (`services/shared/persistence.py`) to keep two stores in sync, runs PostgreSQL for BetterAuth and the dashboard's Prisma client, and provisions OpenSearch Serverless for embeddings that no marketed feature uses. Four stores for one product multiplies operational cost (DocumentDB alone is two `db.r5.large` instances in the example tfvars), complicates tenant isolation and audit, and makes analytical queries (inventory facets, triage totals, usage roll-ups, evidence reports) awkward in a document store.

Constraints: strong tenant isolation with row-level security; relational reporting; high-write, low-latency page task state; small team.

## Decision

We will use Aurora PostgreSQL Serverless v2 as the system of record for tenants, users, sites, inventory, documents, jobs, artifacts, triage decisions, review items, evidence pack manifests, publications, usage meters, audit log and billing, with row-level security keyed on `tenant_id` and `pgvector` available if semantic exports need embeddings later. DynamoDB keeps only high-write pipeline state (`page_tasks`, `artifact_index`, `crawl_frontier`, idempotency). MongoDB, DocumentDB, the dual-write layer, the DocumentDB Lambda layers and OpenSearch Serverless are removed after a one-way migration.

## Alternatives Considered

- **DocumentDB as the single store** — Weak relational reporting and RLS story, expensive at rest, and the JSON schemas in `packages/schemas/mongo` are already relational in shape.
- **DynamoDB only (single-table design)** — Excellent for pipeline state, poor for the faceted, ad-hoc reporting that inventory and evidence dashboards need without duplicating data into another store.
- **Keep all four with dual writes** — The current state; consistency bugs and cost with no benefit.
- **Managed MongoDB (Atlas)** — Adds a vendor and leaves the reporting and RLS gaps.

## Consequences

**Positive**

- One schema, migrations in CI, RLS enforced by the database, ordinary SQL reporting, lower run cost (Serverless v2 scales to near zero in dev).
- Simpler compliance story (one system of record to back up, encrypt and audit).

**Negative / Trade-offs**

- A migration while shipping features; the dashboard's Mongo client code and `packages/schemas/mongo` are rewritten.
- Aurora in a VPC means Lambda functions need VPC access (already true for DocumentDB) or RDS Proxy/Data API.

**Neutral / Follow-ups**

- Use the Aurora Data API or RDS Proxy for Lambda connection management; decide in the execution spec.
- Keep a read-only Mongo export for 90 days after cutover.

# ADR-0001: Remediate on demand and cache artifacts by content hash

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Remediation pipeline, storage layout, API job model
- **Related:** `docs/REMEDIATION-PIPELINE-PRD.md`, `docs/INTEGRATIONS-PRD.md` (Accessible Link), ADR-0002, ADR-0004

## Context

Institutions have backlogs of tens of thousands of PDFs, most of which are never opened. Remediating everything upfront is what the manual-vendor quotes price ($5 per page, about $20M for Ohio State's libraries). ITHAKA faced 156 million pages and chose to remediate a document only when a user requests it, then cache the result for everyone after; the collection grows with demand and the upfront bill disappears. Our pipeline today keys artifacts by an internal document id, so the same file uploaded twice is processed twice, and there is no entry point that takes a URL.

Constraints: per-page cost of goods must stay under $0.055; customers need predictable pricing; the same document appears at many URLs and in many systems; sources change over time.

## Decision

We will identify every document by the SHA-256 of its bytes within a tenant, key all artifacts and evidence by `(tenant, sha256, profile, engine_version)`, and serve cached artifacts whenever that key already exists. Remediation is started by demand (upload, API, connector, or the first request to an Accessible Link) and by explicit scheduling for backlogs, never by a blanket "process everything" default. An `artifact_index` table in DynamoDB provides the lookup; S3 holds the artifacts under a content-addressed prefix.

## Alternatives Considered

- **Process everything upfront (bulk mode by default)** — Simple, but it bills customers for documents nobody opens and forces capacity planning for peaks; it is also exactly what the incumbents charge for.
- **Key by document id or URL only** — Fails to deduplicate the same file at several URLs and across re-uploads; URL keys break when the source moves.
- **Cache per tenant only, without a profile in the key** — A profile or engine upgrade would silently return stale output; including profile and engine version makes cache invalidation explicit.
- **Do nothing** — Keeps the demo behavior; costs and latency stay unacceptable.

## Consequences

**Positive**

- Cost tracks real usage; duplicate uploads are free; connectors and the Accessible Link share one cache.
- Evidence is naturally versioned by content, so a changed source produces a new pack and the old one remains.

**Negative / Trade-offs**

- First-request latency on an Accessible Link is minutes, so the "preparing" experience must be good.
- Hashing large files on ingest adds a step; near-duplicates (a re-saved PDF with different bytes) are not deduplicated.

**Neutral / Follow-ups**

- Scheduled backlog runs are a policy on top (Maintain stage); the cache key must be documented in the API.
- Revisit if per-tenant deduplication across tenants (shared public documents) becomes valuable.

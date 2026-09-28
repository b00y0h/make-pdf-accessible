# ADR-0004: The signed, immutable evidence pack is the unit of delivery

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Outputs, storage, compliance posture
- **Related:** `docs/REMEDIATION-PIPELINE-PRD.md`, `docs/ENTERPRISE-READINESS-PRD.md`, ADR-0001, ADR-0003

## Context

Every vendor claims a percentage. A compliance office facing a complaint needs to show, per document, what was done, by which tool and version, what a validator said, what a person checked, and when. Today the platform stores hardcoded scores in a document record; nothing survives that a customer could hand to a regulator. The FTC's order against accessiBe shows the liability of unsupported claims. ITHAKA stores the full job event log next to the remediated PDF, which is the right instinct but not a portable, signed record.

Constraints: storage cost; retention obligations vary (1 to 7 years); packs must be verifiable without our service.

## Decision

We will produce, for every completed job, an evidence pack: `evidence.json` (versioned schema), the raw validator reports (veraPDF, axe, HTML validator), per-element semantic QA scores, the stage timeline, tool and model versions, and reviewer sign-off where applicable, plus a manifest signed with an asymmetric KMS key. Packs are written to an S3 bucket with Object Lock in compliance mode for the tenant's retention period and are exportable as JSON and as a tagged PDF. A document's status (`remediated`, `verified`) is derived from its pack, never set by hand.

## Alternatives Considered

- **Store a score and a report in the database** — Mutable, not portable, not verifiable, and what we have today.
- **Rely on the customer to run their own checker** — Puts the burden on the least-resourced party and produces no chain of custody for our work.
- **Third-party attestation service** — Adds cost and dependency; a signed manifest with a public key achieves verification.
- **Blockchain anchoring** — Unnecessary; KMS signatures plus Object Lock give integrity and immutability.

## Consequences

**Positive**

- A defensible per-document record; a differentiator no competitor offers.
- Publishing accuracy becomes a matter of aggregating packs.

**Negative / Trade-offs**

- Storage grows (raw validator output can be hundreds of KB per document); Object Lock makes accidental writes permanent, so retention defaults need legal input.
- Schema versioning discipline is required forever.

**Neutral / Follow-ups**

- Publish the schema and a verification script so customers can validate packs offline.
- Decide default retention (3 vs 7 years) before the first customer pack is written.

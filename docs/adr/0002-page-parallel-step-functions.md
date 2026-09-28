# ADR-0002: Page-parallel orchestration on Step Functions Distributed Map with Lambda and Fargate

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Remediation pipeline compute and orchestration
- **Related:** `docs/REMEDIATION-PIPELINE-PRD.md`, ADR-0001, ADR-0003

## Context

The current system has two pipelines: a Celery worker that processes whole documents in one task, and a seven-state Step Functions workflow of mostly mock Lambdas. Whole-document processing means a 300-page scan is one long task, one failure loses everything, and latency is minutes to hours. Tagging engines are CPU-bound native code that does not fit well inside Lambda size and time limits. ITHAKA's pipeline splits documents into pages, fans out with Step Functions, and merges; the ASU/AWS solution does the same with Fargate for the engine and Lambda for split and merge.

Constraints: p95 upload-to-evidence under 10 minutes for 50 pages; 1,000 concurrent page tasks per region; per-tenant fairness; a two-engineer team that cannot operate a Kubernetes cluster.

## Decision

We will orchestrate every job with one Step Functions state machine: an ingest step, a split step, a Distributed Map over pages (OCR when needed, tag, describe), then merge, validate, semantic QA, exports, evidence and notify. Light steps run on Lambda; engine and validator steps run as Fargate tasks invoked through the Step Functions ECS integration. Per-tenant-tier concurrency limits are set on the Map. The Celery worker and Redis broker are retired.

## Alternatives Considered

- **Keep Celery on ECS with our own fan-out** — We would re-implement retries, concurrency limits, timeouts and a job timeline that Step Functions provides; harder to observe.
- **Amazon MWAA (Airflow) or AWS Batch** — Good for scheduled batch, poor fit for low-latency on-demand jobs and per-page fan-out with fine-grained retries.
- **Everything on Lambda** — Engine SDKs and veraPDF need more CPU, memory and time than Lambda's limits comfortably allow; container images on Lambda still cap at 15 minutes.
- **Kubernetes (EKS) with Argo Workflows** — More control, but an operational burden the team cannot carry before 2027.

## Consequences

**Positive**

- Page-level retries and isolation; documents finish `partial` instead of failing outright.
- Built-in execution history feeds the evidence pack's timeline; cost per stage is measurable.

**Negative / Trade-offs**

- Fargate task start latency (tens of seconds) hurts single-page on-demand requests; a warm pool or Lambda-hosted engine for small pages may be needed.
- Distributed Map and Fargate pricing add cents per document; state machine definitions are harder to unit test than Python.
- Cross-page structures (tables spanning pages) require the engine's merge to be good, or a page-range Map unit.

**Neutral / Follow-ups**

- Measure PDFix merge fidelity on the eval set before committing to single-page units.
- Define per-tier Map concurrency in Terraform variables.

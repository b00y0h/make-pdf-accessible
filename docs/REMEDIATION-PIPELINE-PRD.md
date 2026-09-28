# Make PDF Accessible — Remediation Pipeline v2

## A page-parallel, engine-pluggable, independently validated pipeline that turns any PDF into a tagged PDF/UA file or semantic HTML, on demand, with an evidence pack.

**Status:** Draft v1.0 (2026-09-28)
**Parent:** `docs/PLATFORM-PRD.md` (stages Remediate or Convert, Prove, Maintain)
**Implements ADRs:** ADR-0001 (on-demand + content-hash cache), ADR-0002 (page-parallel Step Functions), ADR-0003 (pluggable engine, PDFix + veraPDF first), ADR-0004 (evidence pack), ADR-0005 (HTML first), ADR-0011 (Bedrock model strategy)

---

## CONTEXT

The current pipeline is two parallel half-implementations:

- A Celery worker (`services/worker/worker.py`, `process_pdf`) that extracts text, tables and images with pdfplumber and PyMuPDF, builds semantic HTML through `services/worker/src/semantic_html_builder.py`, uploads artifacts to S3, and then writes **hardcoded scores** (`overall: 92`) and stores the **original file** as the "accessible PDF" (`accessible/{doc_id}/accessible.pdf`, comment `# For now, same as original`).
- A Step Functions workflow (`infra/step-functions/pdf-processing-workflow.json`, seven Lambda states: OCR → Structure → AltText → TagPDF → Exports → Validate → Notify) whose Tag (`services/functions/tag_pdf/main.py`, `tags_applied = 25`), AltText (`services/functions/alt_text/main.py`) and Validate (`services/functions/validate/main.py`) handlers are mocks. The Structure function (`services/functions/structure/services.py`) makes a real Bedrock call with an outdated model id. `services/functions/validator/validation_service.py` scores the app's own JSON, never the produced PDF.

Real and reusable: upload and S3 layout, SQS ingest and the router Lambda (`services/functions/router/main.py`), Textract OCR (`services/functions/ocr/`), the Bedrock client under `services/worker/src/pdf_worker/aws/bedrock.py`, the semantic HTML builder, the chunking and Markdown exports, timeout and quota enforcement in `services/shared/`, and the dashboard's document and alt-text review screens.

ITHAKA's pipeline (`docs/research/ithaka-pipeline-analysis.md`) is the benchmark: EventBridge trigger, Lambda split, Step Functions orchestration of PDFix tagging per page and Bedrock alt text, merge, veraPDF validation, S3 cache, stage events. This PRD adopts that design and adds semantic QA, HTML conversion, the evidence pack and the review workbench.

The motivating gaps:

1. **No real tagging.** Nothing in the repo writes a PDF structure tree.
2. **No independent validation.** Scores are self-reported and hardcoded.
3. **Whole-document processing.** A 300-page scan runs as one task; failures lose everything; latency is minutes to hours.
4. **No caching.** The same file uploaded twice runs twice; there is no on-demand entry point for a URL.
5. **No evidence.** Nothing survives that a compliance office could hand to a regulator.
6. **Alt text quality is unmeasured.** Chart descriptions can satisfy a checker and say nothing.

### Locked Scope Decisions

1. **Engine adapter interface with PDFix as engine one, Adobe Auto-Tag as engine two.** No in-house tagger. Engines run in containers on Fargate; the adapter contract is per page in, tagged page out, plus a merge step. (ADR-0003)
2. **Page-level parallelism through Step Functions Distributed Map.** Split → per-page Map (OCR if needed, tag, alt text) → merge → validate → semantic QA → evidence → publish hooks. (ADR-0002)
3. **Content-addressed artifacts.** Documents are keyed by SHA-256 of the input bytes per tenant; the pipeline profile (engine, version, options) is part of the cache key. (ADR-0001)
4. **veraPDF is the validator of record for PDF output; axe-core plus an HTML validator for HTML output.** Raw reports ship in the evidence pack. (ADR-0004)
5. **Semantic QA is scored per element with confidence** by a Bedrock model, and routes low-confidence elements to the review workbench. A document is `remediated` after automated steps, `verified` only after review clears.
6. **Bedrock through the Anthropic Bedrock (Mantle) client; model ids are configuration, never literals in code.** Default `anthropic.claude-opus-5` for semantic QA and alt text; `anthropic.claude-sonnet-5` is the measured cost step-down; `anthropic.claude-haiku-4-5` for cheap classification. (ADR-0011)
7. **Textract only when a page has no usable text layer.** Born-digital pages skip OCR.
8. **The Celery worker path is retired.** One pipeline (Step Functions) serves upload, API, CMS connectors and the Accessible Link. The worker's extraction and HTML-building code moves into pipeline steps; Celery, Redis-as-broker and `services/worker/worker.py` go away.
9. **Profiles, not flags.** A job runs a named profile (`pdf_ua1_standard`, `pdf_ua2_math`, `html_first`, `forms`) that fixes engine, validator profile, output set and QA thresholds.

### What This Is NOT

- Not a new tagging algorithm. If PDFix or Adobe cannot tag a page class well, the answer is the review workbench and the eval set, not a custom tagger.
- Not a general document conversion service (no DOCX in, no PPTX in for v2; the allowed-types list in `services/api/app/config.py` narrows to PDF until conversion has its own PRD).
- Not real-time. Everything is asynchronous with webhooks and polling; the Accessible Link's first request returns a "preparing" page with a retry hint, not a blocking response.
- Not the human review operation itself (staffing, SLAs) — that is in the business plan; this PRD covers the workbench and the data model.
- Not STEM (MathML, PDF/UA-2) or fillable forms in the first two slices; the profile system reserves them and slice S6 delivers them.

---

## SUCCESS CRITERIA

1. Submitting a born-digital PDF through `POST /v1/jobs` with profile `pdf_ua1_standard` produces `tagged.pdf` whose veraPDF report (`validator/verapdf.json` in the evidence pack) has `failedChecks == 0` for ≥ 95% of the eval set, and every produced PDF has `/Lang`, `/Title`, a tagged structure tree, and `pdfuaid:part` metadata (checked by an independent script, not the engine).
2. A 200-page born-digital PDF completes upload-to-evidence in p95 ≤ 10 minutes, and no single page task runs longer than 120 seconds; a failing page retries twice and, on final failure, the document status is `partial` with the failed page numbers listed, never a silent success.
3. Resubmitting bytes with the same SHA-256 and profile returns `cache_hit: true` and the existing artifact set within 2 seconds; changing the profile or engine version creates a new job.
4. Every completed job has an evidence pack at `evidence/{tenant}/{sha256}/{profile}/{job_id}/` containing `evidence.json` (schema `evidence.v1`), `validator/verapdf.json` or `validator/axe.json` and `validator/html-validator.json`, `qa/elements.jsonl` (per-element semantic scores), `timeline.jsonl` (stage events), and `manifest.sig`; the bucket enforces Object Lock in compliance mode for the tenant's retention period.
5. For every figure, `qa/elements.jsonl` contains an alt-text entry with `confidence` in [0,1]; entries under the profile threshold (default 0.75) appear as open items in `GET /v1/review/items?document_id=`; a document reaches `verified` only when open items are zero.
6. The HTML output for profile `html_first` passes axe-core with zero violations and the Nu HTML checker with zero errors on the eval set, keeps heading hierarchy without skipped levels, marks tables with `<th scope>` and captions, and includes `lang` and a `<title>`.
7. Scanned pages (no text layer) route through Textract; the OCR confidence per page is recorded in the evidence pack and pages under 0.80 mean confidence are flagged for review.
8. Stage events (`job.started`, `page.split`, `page.tagged`, `page.described`, `document.merged`, `document.validated`, `document.qa_scored`, `document.evidence_written`, `job.completed`, `job.failed`) are published to EventBridge and mirrored to `job_events`; the dashboard's job timeline renders them.
9. Cost meters per stage (Textract pages, Bedrock input/output tokens, Fargate vCPU-seconds, storage bytes) are recorded per job and roll up to per-page cost visible to admins; the automated cost of goods on the eval set is ≤ $0.055 per page.
10. The demo endpoint returns only pipeline-produced artifacts; `services/worker/worker.py` no longer exists in the deployed system; no code path writes a literal score.

---

## DATA MODEL CHANGES

### New table — `documents` (Aurora PostgreSQL)

```
documents
  - id: uuid [pk]
  - tenant_id: uuid [fk tenants, indexed]
  - sha256: char(64) [unique with tenant_id]          // content address
  - byte_size: bigint
  - page_count: int
  - source_kind: enum(upload, url, cms, lms, api)     // first-seen origin
  - title: text                                       // best-known title
  - has_text_layer: bool
  - document_class: enum(born_digital, scanned, mixed, form, stem, unknown)
  - status: enum(inventoried, queued, processing, remediated, verified, partial, failed, exempt)
  - current_job_id: uuid [fk jobs, nullable]
  - created_at, updated_at
```

### New table — `jobs`

```
jobs
  - id: uuid [pk]
  - tenant_id, document_id [fk]
  - profile: text                                     // pdf_ua1_standard | pdf_ua2_math | html_first | forms
  - engine: text                                      // pdfix | adobe_autotag
  - engine_version, validator_version, qa_model_id: text
  - cache_key: text [indexed]                         // sha256 + profile + engine_version
  - cache_hit: bool
  - status: enum(queued, splitting, processing_pages, merging, validating, qa, evidence, completed, partial, failed, cancelled)
  - failed_pages: int[]
  - execution_arn: text                               // Step Functions
  - cost_cents: numeric, cost_breakdown: jsonb
  - requested_by: uuid, requested_via: enum(dashboard, api, connector, accessible_link, scheduler)
  - started_at, completed_at
```

### New table — `artifacts`

```
artifacts
  - id: uuid [pk]
  - job_id, document_id, tenant_id [fk]
  - kind: enum(tagged_pdf, html, markdown, csv_zip, epub, evidence_json, validator_report, qa_elements, timeline, preview)
  - s3_bucket, s3_key, content_type, byte_size, sha256
  - created_at
```

### New table — `review_items`

```
review_items
  - id: uuid [pk]
  - document_id, job_id, tenant_id [fk]
  - element_ref: text                                 // page + structure path (e.g. "p12/Figure[3]")
  - kind: enum(alt_text, reading_order, heading_level, table_header, list_structure, language, link_text, ocr_page)
  - proposed: jsonb                                   // machine output
  - confidence: numeric
  - status: enum(open, approved, edited, rejected)
  - resolution: jsonb, resolved_by: uuid, resolved_at
```

### New table — `evidence_packs`

```
evidence_packs
  - id: uuid [pk]
  - document_id, job_id, tenant_id [fk]
  - schema_version: text                              // "evidence.v1"
  - s3_prefix: text
  - manifest_sha256: char(64)
  - signature_kms_key_arn: text
  - verified_by: uuid [nullable], verified_at [nullable]
  - retention_until: timestamptz
  - created_at
```

### DynamoDB — `page_tasks` (high-write pipeline state)

```
page_tasks: pk = job_id, sk = page_number
  - stage, status, attempts, engine_ms, textract_confidence, alt_text_count, error, ttl
```

### DynamoDB — `artifact_index`

```
artifact_index: pk = tenant_id#sha256, sk = profile#engine_version
  - job_id, status, s3_prefix, updated_at
```

### Retired

`services/shared/mongo/*` collections (`documents`, `jobs`, `alt_text`, `api_keys`, `demo_sessions`) migrate to the tables above and to the Enterprise Readiness PRD's tables; see ADR-0006 and `docs/ENTERPRISE-READINESS-SPECS.md`.

---

## FEATURE 1 — INGEST AND CONTENT ADDRESSING

Entry points: dashboard upload (presigned S3 PUT, already in `services/api/app/routes/documents.py`), `POST /v1/jobs` with `source_url` or `s3_key`, connector uploads (`/v1/client/upload`), the Accessible Link, and the scheduler (Maintain stage).

Flow:

1. Bytes land in `pdf_originals` under `incoming/{tenant}/{uuid}.pdf`.
2. The ingest step (Lambda) computes SHA-256, page count, text-layer presence, byte size, and `document_class` heuristics; runs the existing file-signature and ClamAV checks (`services/shared/file_signature_validation.py`, `services/shared/security_validation.py`); rejects encrypted PDFs with a clear error; enforces quota (`services/shared/quota_enforcement.py`).
3. Looks up `artifact_index[tenant#sha256][profile#engine_version]`. On hit, creates a job with `cache_hit = true`, links artifacts, emits `job.completed`, and returns. On miss, moves the object to `originals/{tenant}/{sha256}.pdf` (idempotent) and starts the state machine.

Request shape:

```json
POST /v1/jobs
{
  "source": {"type": "s3", "key": "incoming/.../file.pdf"} | {"type": "url", "url": "https://..."},
  "profile": "pdf_ua1_standard",
  "options": {"language": "en", "title": "2026 Housing Application", "priority": "standard"},
  "callback_url": "https://customer.example/webhooks/mpa",
  "idempotency_key": "client-generated"
}
```

Response: `{ "job_id", "document_id", "status": "queued" | "completed", "cache_hit": bool, "evidence_url": null | "..." }`.

## FEATURE 2 — PAGE-PARALLEL ORCHESTRATION

State machine `pdf-remediation-v2` (replaces `infra/step-functions/pdf-processing-workflow.json`):

```
Ingest (Lambda)
 └─ Split (Lambda; pikepdf writes single-page PDFs to pdf_temp/{job}/pages/{n}.pdf; writes page_tasks rows)
     └─ Distributed Map over pages (max concurrency per tenant tier: 50 Team, 200 Campus, 500 System)
          ├─ NeedsOCR? → Textract (async, existing ocr function) → page text JSON
          ├─ Tag page (Fargate task via engine adapter; input page PDF + page text; output tagged page PDF + structure JSON)
          └─ Describe figures (Lambda → Bedrock; input figure crops + surrounding text; output alt text + confidence)
     └─ Merge (Fargate; engine adapter merge; sets /Lang, /Title, metadata, bookmarks from headings)
     └─ Validate (Fargate; veraPDF CLI with profile PDF/UA-1 or PDF/UA-2 → JSON)
     └─ Semantic QA (Lambda → Bedrock; samples reading order, headings, tables, alt text; writes qa/elements.jsonl and review_items)
     └─ Exports (Lambda; HTML via semantic_html_builder, Markdown, CSV tables, optional EPUB)
     └─ Evidence (Lambda; writes evidence.json, timeline, manifest, KMS-signs, Object Lock)
     └─ Notify (Lambda; webhooks with HMAC, EventBridge job.completed, connector publish hooks)
```

Error policy: page tasks retry twice with backoff; a page that still fails is recorded and the document continues to `partial`; engine timeouts are per page (120 s); the whole execution times out at 2 hours; every catch writes a `job.failed` event with a machine-readable `error_code`.

## FEATURE 3 — ENGINE ADAPTER

Contract (`services/pipeline/engines/base.py`):

```python
class EngineAdapter(Protocol):
    name: str
    version: str
    def tag_page(self, page_pdf: bytes, page_text: PageText | None, options: TagOptions) -> TaggedPage: ...
    def merge(self, pages: list[TaggedPage], doc_meta: DocMeta) -> bytes: ...
    def capabilities(self) -> EngineCapabilities: ...   # tables, lists, math, forms, languages
```

Engines: `pdfix` (SDK in a container image `engine-pdfix`, license from Secrets Manager `PDFIX_LICENSE_KEY`), `adobe_autotag` (PDF Services API; credentials `ADOBE_CLIENT_ID`, `ADOBE_CLIENT_SECRET`; whole-document call, so `tag_page` batches). The profile selects the engine; a tenant-level override allows A/B evaluation.

## FEATURE 4 — ALT TEXT AND SEMANTIC QA

- Figure crops are rendered at 150 dpi with the surrounding paragraph and any caption as context. The prompt asks for a description that conveys the figure's purpose and data (for charts: type, axes, trend, the takeaway), under 125 characters for `alt`, with an optional long description for complex figures, and a `decorative: true` flag when appropriate.
- Output is structured (`output_config.format`): `{ alt, long_description|null, decorative, confidence, rationale }`.
- Semantic QA samples up to 40 elements per document (all headings, all tables, all figures, reading-order runs on 5 pages) and scores each with `{ verdict: pass|fix|unsure, confidence, suggested_fix }`.
- Thresholds live in the profile; anything `fix` or under threshold becomes a `review_item`.
- Model ids are environment configuration (`BEDROCK_MODEL_ALT_TEXT`, `BEDROCK_MODEL_SEMANTIC_QA`, `BEDROCK_MODEL_CLASSIFY`), invoked through the Anthropic Bedrock client with cross-region inference profiles; prompts are versioned in `services/pipeline/prompts/` and the version is recorded in the evidence pack.

## FEATURE 5 — EVIDENCE PACK

`evidence.json` (schema `evidence.v1`):

```json
{
  "schema": "evidence.v1",
  "document": {"id": "...", "sha256": "...", "title": "...", "pages": 42, "class": "born_digital"},
  "job": {"id": "...", "profile": "pdf_ua1_standard", "engine": {"name": "pdfix", "version": "..."}, "validator": {"name": "veraPDF", "version": "...", "profile": "PDF/UA-1"}, "qa_model": "anthropic.claude-opus-5", "prompt_version": "qa.v3", "started_at": "...", "completed_at": "..."},
  "results": {"validator_failed_checks": 0, "validator_passed_checks": 133, "qa_elements": 38, "qa_flagged": 3, "ocr_pages": 0, "status": "remediated"},
  "review": {"items_total": 3, "items_resolved": 3, "verified_by": "user-uuid", "verified_at": "..."},
  "artifacts": [{"kind": "tagged_pdf", "s3_key": "...", "sha256": "..."}, ...],
  "timeline": "timeline.jsonl",
  "cost": {"cents": 187, "per_page_cents": 4.45},
  "signature": {"kms_key_arn": "...", "manifest_sha256": "...", "signed_at": "..."}
}
```

A human-readable PDF rendering of the pack (itself tagged and validated) is generated for export, plus a tenant-wide conformance report (CSV and PDF) in the dashboard.

## FEATURE 6 — REVIEW WORKBENCH

Dashboard route `/review` (replaces the alt-text-only screen at `dashboard/src/app/(dashboard)/alt-text/page.tsx`): a queue of `review_items` filterable by document, kind and confidence; a page viewer with the element highlighted; approve / edit / reject with keyboard shortcuts; batch approve for high-confidence-but-flagged classes; resolution writes back to the artifact (re-run Merge for structural fixes, patch metadata for alt text) and appends to the evidence pack. Reviewer throughput and accuracy metrics per user.

## FEATURE 7 — ACCESSIBLE LINK (on-demand entry point)

`GET /v1/links/{tenant_slug}/{hash}` (also served on `a11y.<custom domain>` through CloudFront): resolves the hash to the source URL registered during inventory, fetches the current bytes, computes SHA-256, and either redirects (302) to a short-lived signed URL for the cached tagged PDF or HTML, or starts a job and returns a 202 with an accessible "preparing your document" HTML page that polls. Cache validation: `ETag`/`Last-Modified` from the origin; if the source changed, a new job runs and the old artifacts stay until the new evidence pack exists.

---

## API ROUTES

| Method | Path                                  | Auth                                    | Purpose                            |
| ------ | ------------------------------------- | --------------------------------------- | ---------------------------------- |
| POST   | `/v1/jobs`                            | API key or session (scope `jobs:write`) | Start a remediation job            |
| GET    | `/v1/jobs/{id}`                       | `jobs:read`                             | Status, timeline, cache flag, cost |
| POST   | `/v1/jobs/{id}/cancel`                | `jobs:write`                            | Cancel a running execution         |
| GET    | `/v1/documents/{id}`                  | `documents:read`                        | Document, current job, artifacts   |
| GET    | `/v1/documents/{id}/artifacts/{kind}` | `documents:read`                        | Signed download URL                |
| GET    | `/v1/documents/{id}/evidence`         | `evidence:read`                         | Evidence pack JSON or PDF          |
| GET    | `/v1/review/items`                    | `review:read`                           | Open review items                  |
| POST   | `/v1/review/items/{id}`               | `review:write`                          | Approve / edit / reject            |
| GET    | `/v1/links/{tenant}/{hash}`           | public (rate limited)                   | Accessible Link                    |
| GET    | `/v1/profiles`                        | any                                     | Available profiles and thresholds  |

## ENVIRONMENT VARIABLES

| Var                                                                                       | Purpose                                         | Example (placeholder)                                                              |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------- |
| `PIPELINE_STATE_MACHINE_ARN`                                                              | Step Functions v2 ARN                           | `arn:aws:states:us-east-1:123456789012:stateMachine:...`                           |
| `PDF_ORIGINALS_BUCKET`, `PDF_TEMP_BUCKET`, `PDF_ACCESSIBLE_BUCKET`, `PDF_EVIDENCE_BUCKET` | Storage                                         | bucket names from Terraform outputs                                                |
| `PAGE_TASKS_TABLE`, `ARTIFACT_INDEX_TABLE`                                                | DynamoDB pipeline state                         | table names                                                                        |
| `DATABASE_URL`                                                                            | Aurora PostgreSQL                               | `postgresql://...` (from Secrets Manager)                                          |
| `BEDROCK_MODEL_ALT_TEXT`, `BEDROCK_MODEL_SEMANTIC_QA`, `BEDROCK_MODEL_CLASSIFY`           | Model ids                                       | `anthropic.claude-opus-5`, `anthropic.claude-opus-5`, `anthropic.claude-haiku-4-5` |
| `BEDROCK_REGION`                                                                          | Bedrock region for the Anthropic Bedrock client | `us-east-1`                                                                        |
| `ENGINE_DEFAULT`                                                                          | Engine for profiles without an override         | `pdfix`                                                                            |
| `PDFIX_LICENSE_KEY`                                                                       | Secrets Manager reference                       | `arn:aws:secretsmanager:...`                                                       |
| `ADOBE_CLIENT_ID`, `ADOBE_CLIENT_SECRET`                                                  | Secrets Manager references                      | `arn:aws:secretsmanager:...`                                                       |
| `VERAPDF_PROFILE_DEFAULT`                                                                 | Validator profile                               | `PDFUA_1`                                                                          |
| `EVIDENCE_SIGNING_KEY_ARN`                                                                | KMS asymmetric key for manifests                | `arn:aws:kms:...`                                                                  |
| `QA_CONFIDENCE_THRESHOLD`                                                                 | Default review threshold                        | `0.75`                                                                             |
| `EVENT_BUS_NAME`                                                                          | EventBridge bus for stage events                | `mpa-pipeline`                                                                     |

## TESTING STRATEGY

- **Unit:** adapter contract tests with a fake engine; split/merge round-trip on fixture PDFs (`e2e/fixtures/*.pdf`, `tests/fixtures/`); evidence manifest signing and verification; cache-key derivation.
- **Integration (LocalStack + Step Functions Local):** the state machine runs end to end against the fake engine; failure injection on one page yields `partial` with the right page list; cache hit path returns without execution.
- **Engine conformance:** a public eval set (`docs/eval/README.md`, 200 documents across classes) run nightly against PDFix and Adobe; veraPDF pass rate, semantic QA pass rate and cost per page recorded and published.
- **Accessibility of outputs:** axe-core and Nu HTML checker on HTML outputs; PAC-style spot checks by the QA lead; screen-reader walkthroughs (NVDA, JAWS, VoiceOver) on a sample every release.
- **Load:** 1,000 concurrent page tasks in staging; queue age and Fargate scaling alarms hold.
- **Regression must-pass:** the three fixture documents in `e2e/fixtures/` produce identical evidence pack `results` across releases unless a changelog entry explains the difference.

## MILESTONES / ROLLOUT PLAN

| Slice                                   | Scope                                                                                                                      | Value delivered alone                |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| P0 — Truth                              | Delete mock scores and the returned-original artifact; demo shows only HTML/Markdown/CSV exports the pipeline really makes | Honest demo                          |
| P1 — Engine + validate                  | PDFix adapter on Fargate for whole documents, veraPDF validate, evidence pack v1 with validator report                     | Real tagged PDFs with proof          |
| P2 — Page parallel + cache              | Split, Distributed Map, merge, page_tasks, artifact_index, Accessible Link                                                 | Speed, resilience, on-demand         |
| P3 — Alt text + semantic QA + workbench | Bedrock alt text with confidence, QA scoring, review_items, `/review`                                                      | Verified tier possible               |
| P4 — HTML-first profile                 | Hardened HTML conversion with validation in the evidence pack                                                              | Web-page output                      |
| P5 — Adobe adapter + eval publishing    | Second engine, nightly eval, public accuracy page                                                                          | Engine independence and public proof |
| P6 — Worker retirement                  | Remove Celery/Redis broker, `services/worker/worker.py`; all entry points use the state machine                            | One pipeline to operate              |

## OPEN QUESTIONS

1. **PDFix per-page merge fidelity.** Does PDFix's SDK preserve cross-page structures (tables spanning pages, running headers) when pages are tagged independently? If not, the Map unit becomes a page range. Decide during P2 with the eval set.
2. **Object Lock retention default.** 3 years vs 7 years affects storage cost; legal input needed before P1 ships to a customer.
3. **Where does OCR text go for born-digital pages with partial text layers (mixed class)?** Per-page decision using text coverage ratio; threshold to be measured.
4. **Should semantic QA sample or score every element?** Start with sampling caps for cost; measure whether flagged rates justify full scoring on Campus and above.

## RISKS

- **Engine license cost at scale.** Mitigation: Adobe adapter; per-page cost meter with alerts.
- **Bedrock throughput limits on burst.** Mitigation: cross-region inference profiles, queue-backed concurrency limits per tenant, batch API for scheduled backlog runs.
- **Fargate cold start latency for single-page on-demand requests.** Mitigation: warm pool for the Accessible Link path; Lambda-hosted engine for pages under a size threshold if the SDK permits.

---

## SOURCES & RELATED DOCS

- `docs/PLATFORM-PRD.md` — parent
- `docs/research/ithaka-pipeline-analysis.md` — architecture benchmark
- `docs/adr/0001-on-demand-remediation-with-content-hash-cache.md`, `0002-page-parallel-step-functions.md`, `0003-pluggable-engine-pdfix-first.md`, `0004-evidence-pack-as-unit-of-delivery.md`, `0005-html-first-output.md`, `0011-bedrock-model-strategy.md`
- `docs/REMEDIATION-PIPELINE-SPECS.md` — execution spec
- `PDF_PROCESSING_PIPELINE.md` — the v1 pipeline this supersedes

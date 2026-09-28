# Make PDF Accessible — Remediation Pipeline v2 Implementation Specs

These specs replace the mock tagging, hardcoded scores and whole-document worker with the page-parallel, engine-pluggable, validated pipeline defined in `docs/REMEDIATION-PIPELINE-PRD.md` (ADR-0001 to ADR-0005, ADR-0011). Starting state: `services/functions/tag_pdf/main.py`, `alt_text/main.py` and `validate/main.py` return canned values; `services/worker/worker.py` stores the original file as the accessible PDF and writes literal scores; `infra/step-functions/pdf-processing-workflow.json` chains seven Lambdas with no fan-out; artifacts are keyed by document id.

Every file path below was verified against the repository at the time of writing. New directories are marked _Create_.

---

## Spec 1 — Remove mock outputs and hardcoded scores (slice P0)

### Problem

`services/worker/worker.py` uploads `pdf_content` as `accessible/{doc_id}/accessible.pdf` with the comment `# For now, same as original` and then calls `doc_repo.update_scores` with `{"overall": 92, ...}`; `services/functions/tag_pdf/main.py` returns `tags_applied = 25`; `services/functions/validator/validation_service.py` scores the app's JSON. Any demo misrepresents the product. Target: no artifact or score exists that the pipeline did not produce.

### Files to touch

| File                                                    | Action                                                                                                                                              |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/worker/worker.py`                             | Delete the `accessible_pdf` upload entry and the `update_scores` call; set `status = "exports_only"` until Spec 3 lands                             |
| `services/functions/tag_pdf/main.py`                    | Replace the mock with a handler that raises `NotImplementedError("engine adapter not configured")` unless `ENGINE_DEFAULT` is set (Spec 3 wires it) |
| `services/functions/validate/main.py`                   | Same pattern; returns `status = "skipped"` with `reason = "validator not configured"`                                                               |
| `services/api/app/routes/documents.py`                  | Stop returning `accessible_pdf` in download listings when the artifact kind is absent                                                               |
| `dashboard/src/app/(dashboard)/documents/[id]/page.tsx` | Show "Accessible PDF: not available for this job" instead of a score badge when no evidence exists                                                  |
| `README.md`, `STATUS.md`                                | State what is implemented today; remove "95% Enterprise-Ready"                                                                                      |

### Acceptance criteria

1. `grep -rn '"overall": 92' services/` returns nothing; no code path calls `update_scores` with literals.
2. A demo upload yields HTML, Markdown, CSV and preview artifacts and no `accessible_pdf` artifact.
3. The dashboard document page renders without a score when none exists.

### Implementation

1A. In `services/worker/worker.py`, remove the tuple beginning `("accessible_pdf", f"accessible/{doc_id}/accessible.pdf", ...)` from `uploads` and delete the `scores = {...}` block and `doc_repo.update_scores(...)`.
1B. Replace the body of `lambda_handler` in `services/functions/tag_pdf/main.py` with a guard that reads `os.environ.get("ENGINE_DEFAULT")` and returns `{"doc_id": ..., "status": "failed", "error_code": "ENGINE_NOT_CONFIGURED"}` when unset.
1C. Update the README's status section to a table of implemented vs planned capabilities that links to this document.

---

## Spec 2 — Pipeline package, engine adapter contract and fake engine

### Problem

Engine calls are scattered; there is no contract. Target: a `services/pipeline` package with the `EngineAdapter` protocol, a `FakeEngine` for tests, and shared models extended from `services/shared/models.py`.

### Files to touch

| File                                                                                                      | Action                                                                                                                         |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `services/pipeline/__init__.py`, `services/pipeline/engines/base.py`, `services/pipeline/engines/fake.py` | Create                                                                                                                         |
| `services/pipeline/models.py`                                                                             | Create: `PageText`, `TagOptions`, `TaggedPage`, `DocMeta`, `EngineCapabilities`, `QAElement`, `EvidenceManifest` (Pydantic v2) |
| `services/shared/models.py`                                                                               | Add `JobStatus` enum values from the PRD; keep existing classes                                                                |
| `services/pipeline/pyproject.toml`, `services/pipeline/requirements.txt`                                  | Create (pydantic, pikepdf, boto3, aws-lambda-powertools)                                                                       |
| `services/pipeline/tests/test_engine_contract.py`                                                         | Create                                                                                                                         |

### Acceptance criteria

1. `FakeEngine` satisfies `EngineAdapter` under `mypy --strict`.
2. Contract tests run against any adapter through a fixture parameter (`fake`, later `pdfix`, `adobe_autotag`).

### Implementation

2A. `services/pipeline/engines/base.py`:

```python
from typing import Protocol
from services.pipeline.models import DocMeta, EngineCapabilities, PageText, TagOptions, TaggedPage

class EngineAdapter(Protocol):
    name: str
    version: str

    def tag_page(self, page_pdf: bytes, page_text: PageText | None, options: TagOptions) -> TaggedPage: ...
    def merge(self, pages: list[TaggedPage], doc_meta: DocMeta) -> bytes: ...
    def capabilities(self) -> EngineCapabilities: ...
```

2B. `FakeEngine.tag_page` uses pikepdf to add `/MarkInfo` and a minimal structure tree with one `/Document` element per page so downstream steps have something real to validate; `merge` concatenates pages with pikepdf and sets `/Lang` and `/Title`.

---

## Spec 3 — PDFix engine container and Fargate task

### Problem

No real tagging engine exists. Target: an `engine-pdfix` container image that implements the adapter over the PDFix SDK, runs as a Fargate task invoked by Step Functions, reads its license from Secrets Manager, and writes outputs to S3.

### Files to touch

| File                                                                                | Action                                                                                                                                      |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/pipeline/engines/pdfix.py`                                                | Create: adapter over the PDFix Python SDK                                                                                                   |
| `services/pipeline/tasks/tag_page_task.py`, `services/pipeline/tasks/merge_task.py` | Create: Fargate entrypoints (read S3 input from env/args, write output, emit stage event)                                                   |
| `services/pipeline/Dockerfile.engine-pdfix`                                         | Create                                                                                                                                      |
| `infra/terraform/ecs.tf`                                                            | Create: ECS cluster, task definitions (`engine-pdfix`, `validator-verapdf`), task role with S3 prefix ABAC, security group, log groups      |
| `infra/terraform/ecr.tf`                                                            | Add `engine-pdfix`, `validator-verapdf`, `crawler` to `service_repositories`                                                                |
| `infra/terraform/secrets.tf`                                                        | Add `pdfix_license` secret (value supplied out of band)                                                                                     |
| `.github/workflows/build-and-deploy-lambda.yml`                                     | Add the two engine images to the build matrix (they are ECS images; rename the workflow to `build-and-deploy-services.yml` in a later spec) |

### Acceptance criteria

1. `docker run engine-pdfix tag-page --input s3://.../pages/1.pdf` writes a tagged page whose structure tree has headings and paragraphs on the fixture `e2e/fixtures/test-document-with-rich.pdf` page 1.
2. The Fargate task completes in under 120 s per page on the eval set p95.
3. The license is never logged or written to the image.

### Implementation

3A. Adapter maps PDFix's tagging API to `tag_page`; `capabilities()` reports tables, lists, languages from the SDK; `merge` uses the SDK's document assembly, then sets `/Lang`, `/Title`, XMP `pdfuaid:part` per profile.
3B. Task entrypoints accept `--job-id --page --profile --input-key --output-key`, publish `page.tagged` to EventBridge and update `page_tasks` in DynamoDB.

---

## Spec 4 — veraPDF validator task and evidence pack v1

### Problem

Nothing validates the produced file; nothing durable records the result. Target: a `validator-verapdf` container that runs veraPDF CLI against the merged PDF, plus an Evidence Lambda that assembles `evidence.json`, the reports and the timeline, signs the manifest with KMS and writes to the evidence bucket with Object Lock.

### Files to touch

| File                                                                    | Action                                                                                                                            |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `services/pipeline/Dockerfile.validator-verapdf`                        | Create (veraPDF CLI, Java runtime)                                                                                                |
| `services/pipeline/tasks/validate_task.py`                              | Create: runs `verapdf --format json --flavour ua1` (or `ua2`), uploads `validator/verapdf.json`                                   |
| `services/functions/validate/main.py`                                   | Rewrite: Lambda that starts the Fargate validation task or, for HTML profiles, runs axe-core + Nu validator in a Lambda container |
| `services/functions/evidence/main.py`, `Dockerfile`, `requirements.txt` | Create: evidence assembler                                                                                                        |
| `services/pipeline/evidence/schema/evidence.v1.json`                    | Create: JSON Schema                                                                                                               |
| `infra/terraform/s3.tf`                                                 | Add `pdf_evidence` bucket with Object Lock (compliance) and retention default from `var.evidence_retention_days`                  |
| `infra/terraform/kms.tf`                                                | Create: asymmetric signing key `evidence` (RSA-3072, SIGN_VERIFY)                                                                 |
| `infra/terraform/processing-lambdas.tf`                                 | Add `evidence` function; grant `kms:Sign` on the evidence key and `s3:PutObject` with Object Lock headers on the evidence bucket  |
| `docs/eval/README.md`                                                   | Create: eval set description and how to run it                                                                                    |

### Acceptance criteria

1. For the fixture documents, `validator/verapdf.json` exists in the evidence prefix and `evidence.json` validates against `evidence.v1.json`.
2. `manifest.sig` verifies with the key's public key using a script in `services/pipeline/evidence/verify.py`.
3. Attempting to overwrite an evidence object before retention fails with `AccessDenied`.

### Implementation

4A. Evidence assembler input: job id; it lists artifacts, reads validator and QA outputs, computes SHA-256 per artifact, writes `evidence.json`, `timeline.jsonl` (from `job_events`), signs `sha256(evidence.json)` with `kms:Sign` (RSASSA_PKCS1_V1_5_SHA_256) and writes `manifest.sig`.
4B. Object Lock: bucket created with `object_lock_enabled = true` and `aws_s3_bucket_object_lock_configuration` in `COMPLIANCE` mode; per-tenant retention passed as `ObjectLockRetainUntilDate` on put.

---

## Spec 5 — Split, Distributed Map, merge, and the v2 state machine

### Problem

`infra/step-functions/pdf-processing-workflow.json` runs whole-document Lambdas serially. Target: `pdf-remediation-v2` with ingest → split → Distributed Map (OCR?, tag, describe) → merge → validate → QA → exports → evidence → notify, page state in DynamoDB, and per-tier concurrency.

### Files to touch

| File                                                                                                                                                      | Action                                                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `infra/step-functions/pdf-remediation-v2.asl.json`                                                                                                        | Create                                                                                                                                                                            |
| `infra/terraform/step_functions.tf`                                                                                                                       | Add `aws_sfn_state_machine.pdf_remediation_v2` (keep v1 until Spec 9 removes it)                                                                                                  |
| `infra/terraform/dynamodb.tf`                                                                                                                             | Add `page_tasks` (pk `job_id`, sk `page_number`, TTL) and `artifact_index` (pk `tenant_sha`, sk `profile_engine`)                                                                 |
| `services/functions/ingest/main.py`, `services/functions/split/main.py`, `services/functions/merge/main.py` (Lambda that launches the merge Fargate task) | Create                                                                                                                                                                            |
| `services/functions/ocr/main.py`                                                                                                                          | Adapt to per-page input (`pageKey`) and write `page_tasks.textract_confidence`                                                                                                    |
| `services/functions/router/main.py`                                                                                                                       | Start `pdf_remediation_v2` instead of v1; pass `profile` and `tenant_id`                                                                                                          |
| `infra/terraform/iam.tf`                                                                                                                                  | Extend the Step Functions role: `ecs:RunTask`, `iam:PassRole` for task roles, `events:PutEvents`, `dynamodb:*Item` on the two tables, Distributed Map child execution permissions |
| `infra/terraform/variables.tf`                                                                                                                            | Add `map_concurrency_by_tier` (map of number)                                                                                                                                     |
| `tests/test_pipeline_integration.py`                                                                                                                      | Extend with a Step Functions Local run of v2 using the fake engine                                                                                                                |

### Acceptance criteria

1. A 40-page fixture completes with 40 `page_tasks` rows in `succeeded`; killing one page task mid-run yields a `partial` document listing that page.
2. Two executions for the same bytes and profile produce one `artifact_index` row and the second job reports `cache_hit = true`.
3. Execution history shows the Map with `MaxConcurrency` equal to the tenant tier's value.

### Implementation

5A. Split (Lambda, pikepdf): writes `pdf_temp/{job}/pages/{n:05d}.pdf`, returns `{ "pages": n }` and a manifest object in S3 that the Distributed Map reads (`ItemReader` over S3 JSON).
5B. Map item: `Choice` on `has_text_layer` → OCR task; then `ecs:runTask.sync` for tag; then Lambda `describe_figures`; `Catch` writes `page_tasks.status = failed` and continues (`ResultPath` isolates errors).
5C. After the Map, `Choice`: if any page failed → `status = partial` but proceed to merge with the successful pages so the customer still gets output and evidence marks the gaps.

---

## Spec 6 — Bedrock alt text and semantic QA with confidence, review items and workbench API

### Problem

`services/functions/alt_text/main.py` is a mock; `services/worker/src/pdf_worker/aws/bedrock.py` has a real client but no confidence or structured output; no review model. Target: one Bedrock service used by the Map's describe step and the post-merge QA step, writing `qa/elements.jsonl` and `review_items`.

### Files to touch

| File                                                                                 | Action                                                                                                                                                                   |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `services/pipeline/llm/bedrock_client.py`                                            | Create: wrapper over the Anthropic Bedrock client (`AnthropicBedrockMantle`) reading `BEDROCK_MODEL_*` and `BEDROCK_REGION`; structured outputs; retries; token metering |
| `services/pipeline/prompts/alt_text.v1.md`, `services/pipeline/prompts/qa.v1.md`     | Create: versioned prompts                                                                                                                                                |
| `services/functions/alt_text/main.py`                                                | Rewrite: per-page figure crops (PyMuPDF) → descriptions with `confidence`, `decorative`, `long_description`                                                              |
| `services/functions/qa/main.py`, `Dockerfile`, `requirements.txt`                    | Create: semantic QA sampler and scorer                                                                                                                                   |
| `services/api/app/routes/review.py`                                                  | Create: `GET /v1/review/items`, `POST /v1/review/items/{id}`                                                                                                             |
| `services/api/app/main.py`                                                           | Mount `review.router` under `/v1`                                                                                                                                        |
| `dashboard/src/app/(dashboard)/review/page.tsx`, `dashboard/src/components/review/*` | Create: workbench (queue, viewer, approve/edit/reject, keyboard shortcuts)                                                                                               |
| `dashboard/src/app/(dashboard)/alt-text/page.tsx`                                    | Redirect to `/review?kind=alt_text`                                                                                                                                      |
| `infra/terraform/processing-lambdas.tf`                                              | Bedrock IAM: allow `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the inference-profile ARNs for the configured models; Guardrails ARN variable    |

### Acceptance criteria

1. Every figure in the fixture set has an entry in `qa/elements.jsonl` with `confidence` in [0,1]; entries under `QA_CONFIDENCE_THRESHOLD` appear in `GET /v1/review/items`.
2. Approving the last open item sets the document to `verified` and appends `review.verified_by` to the evidence pack (a new manifest version; the prior pack is retained).
3. `usage_meters` (or, before the Enterprise spec lands, `jobs.cost_breakdown`) records Bedrock input/output tokens per job.

### Implementation

6A. Model ids are read from the environment; never hard-code them. The prompt version and model id are written to `evidence.json.job`.
6B. QA sampling caps: all headings, all tables, all figures, up to 5 reading-order runs; cap 40 elements per document in the default profile.

---

## Spec 7 — Accessible Link resolver and content-hash cache path

### Problem

No on-demand entry point. Target: `GET /v1/links/{tenant}/{hash}` plus the CloudFront behavior for custom link domains.

### Files to touch

| File                                         | Action                                                                                                               |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/routes/links.py`           | Create                                                                                                               |
| `services/api/app/main.py`                   | Mount under `/v1`; exclude from the API-key middleware `excluded_paths` (public, rate limited)                       |
| `services/api/app/services/link_resolver.py` | Create: hash → source URL (from inventory), freshness check (ETag/Last-Modified), `artifact_index` lookup, job start |
| `services/api/app/templates/preparing.html`  | Create: accessible "preparing" page (no auto-refresh faster than 10 s; `aria-live` status)                           |
| `infra/terraform/api_gateway.tf`             | Add a throttled route for `/v1/links/*`                                                                              |
| `infra/terraform/domains.tf`                 | Add `a11y.` subdomain alias to the API domain (or a dedicated CloudFront distribution in a later slice)              |

### Acceptance criteria

1. First request for an inventoried PDF returns 202 with the preparing page; after completion, requests return 302 to a signed URL valid 15 minutes; p50 under 300 ms on cache hit.
2. Changing the source bytes triggers a new job on the next request while the old artifacts stay served until the new evidence exists.

---

## Spec 8 — HTML-first profile hardening and validation

### Problem

`services/worker/src/semantic_html_builder.py` produces good HTML but is only reachable through the Celery worker, and its output is not validated. Target: the builder runs in the Exports step for `html_first`, output validated with axe-core and the Nu HTML checker, reports stored in the evidence pack.

### Files to touch

| File                                                     | Action                                                                  |
| -------------------------------------------------------- | ----------------------------------------------------------------------- |
| `services/pipeline/exports/html_builder.py`              | Move from `services/worker/src/semantic_html_builder.py` (keep tests)   |
| `services/pipeline/exports/templates/accessible_html.py` | Move from `services/worker/src/pdf_worker/templates/accessible_html.py` |
| `services/functions/exports/main.py`                     | Rewrite: builds HTML, Markdown, CSV zip; calls validation               |
| `services/pipeline/Dockerfile.validator-html`            | Create: Node + axe-core (Playwright) + `vnu.jar`                        |
| `services/pipeline/tasks/validate_html_task.py`          | Create                                                                  |

### Acceptance criteria

1. HTML for the fixture set passes axe with zero violations and Nu with zero errors; reports exist at `validator/axe.json` and `validator/html-validator.json`.
2. Heading levels never skip; tables have `<th scope>`; the document has `lang` and `<title>`.

---

## Spec 9 — Retire the Celery worker and v1 state machine

### Problem

Two pipelines. Target: one.

### Files to touch

| File                                                                                                   | Action                                                                                                             |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `services/worker/worker.py`, `services/worker/celeryconfig.py`, `services/api/app/celery_app.py`       | Delete                                                                                                             |
| `services/worker/src/pdf_worker/**`                                                                    | Move reusable modules (`aws/*`, `utils/pdf.py`, `quota/*`, `timeout/*`) into `services/pipeline/`; delete the rest |
| `docker-compose.yml`                                                                                   | Remove `worker` and Redis-as-broker; keep Redis only if the API still uses it for rate limiting                    |
| `infra/step-functions/pdf-processing-workflow.json`, `infra/terraform/step_functions.tf` (v1 resource) | Delete v1                                                                                                          |
| `infra/terraform/monitoring.tf`                                                                        | Point alarms at v2 and the ECS tasks                                                                               |
| `PDF_PROCESSING_PIPELINE.md`                                                                           | Replace with a pointer to the PRD and this spec                                                                    |

### Acceptance criteria

1. `grep -rn celery services/ | wc -l` is 0; `make up` starts without a worker container.
2. All entry points (dashboard upload, `/v1/jobs`, connectors, Accessible Link, scheduler) start `pdf_remediation_v2`.

---

## Suggested execution order

1. Spec 1 first — it is small and unblocks honest demos immediately; everything else builds on a truthful baseline.
2. Spec 2 — the contract and fake engine are prerequisites for testing Specs 3 to 5 without a license.
3. Spec 4 before Spec 3 in calendar time if the PDFix license is not yet signed: validation and evidence work with the fake engine and are the moat.
4. Spec 3 — the real engine; can land whole-document first, then per page.
5. Spec 5 — page parallelism and cache; depends on Specs 2 to 4.
6. Spec 6 — alt text, QA and the workbench; depends on Spec 5's Map for per-page describe and on Spec 4 for evidence updates.
7. Spec 8 — HTML profile; independent of 6, depends on 5's Exports step.
8. Spec 7 — Accessible Link; depends on 5's cache and on the Inventory spec for hash → URL mapping.
9. Spec 9 last — only after every entry point uses v2.

Net effect: one Step Functions pipeline that produces validated, evidenced outputs from a licensed engine, with page-level resilience, content-hash caching, an on-demand link, and a review workbench.

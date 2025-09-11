# AccessPDF — Adjusted AWS Architecture & Feature Spec

This service converts PDFs into:

1. **Accessible PDFs** (PDF/UA compliant).
2. **Alternative formats** (HTML, TXT, JSON).
3. **LLM-ready corpus** (chunked, embedded, retrievable with citations).

---

## 📂 Ingestion & Preflight

- [x] S3 buckets with KMS encryption (`infra/terraform/s3.tf`).
- [x] API Gateway + CloudFront already defined (`api_gateway.tf`, `cloudfront.tf`).
- [x] Step Functions workflow defined (`infra/step-functions/pdf-processing-workflow.json`).
- [ ] Extend `services/functions/ocr` to run OCRmyPDF in ECS when PDF is image-only.
- [ ] Add Lambda in `services/functions` for preflight validation (MIME, size, page count, encryption).

---

## 📝 Structure Extraction

- [ ] Wire **Textract AnalyzeDocument** into `services/functions/structure`.
- [ ] Persist Textract JSON to S3 (`/artifacts/raw`).
- [ ] Normalize into **canonical JSON schema** in `packages/schemas`.
- [ ] Add Textract **Queries** for metadata (title, captions).

---

## 🤖 AI-Assisted Enhancements

- [ ] Use **Bedrock** client in `services/functions/alt_text` for figure alt-text + heading level inference.
- [ ] Store AI confidence in schema (extend `packages/schemas`).
- [ ] Route low-confidence items to A2I → review flow in `dashboard/src/app/review`.
- [ ] Connect `web/components/AltTextReview.tsx` with A2I outputs.

---

## 📄 Accessible PDF Remediation

- [ ] Extend `services/functions/tag_pdf` to apply PDF/UA tags:
  - Document root & Lang.
  - Headings, paragraphs, lists, figures, tables, links.
  - Reading order MCIDs.
  - Bookmarks from heading outline.
- [ ] Save tagged PDFs in S3 (`/artifacts/pdf`).

---

## ✅ Validation

- [ ] Deploy EC2 Windows AMI for **PAC 2024** validation (Terraform addition).
- [ ] Connect Step Functions state → `services/functions/validate`.
- [ ] Store PAC reports in S3 (`/artifacts/reports`).
- [ ] Notify failures via `services/functions/notifier` → SNS → `dashboard`.

---

## 🌐 Alternative Formats

- [x] Export functions already scaffolded (`services/functions/exporter`, `services/functions/exports`).
- [ ] Ensure semantic HTML builder uses canonical JSON.
- [ ] TXT exporter (reading-order aware) — extend existing exporter.
- [ ] JSON persisted in S3 (`/artifacts/json`).
- [ ] Expose via `services/api` endpoints.

---

## 📊 LLM Corpus Preparation

- [ ] Add chunking logic in `services/worker/src` (≤2k chars, metadata).
- [ ] Convert tables → Markdown + JSON.
- [ ] Include alt-text + captions with figures.

---

## 🔍 Embeddings & Indexing

- [ ] Bedrock Titan embeddings integration in `services/worker`.
- [ ] Persist chunk metadata in Aurora Postgres (replace DocumentDB).
- [ ] Index embeddings into **OpenSearch Serverless Vector Collection** (`infra/terraform/opensearch.tf` to be added).
- [ ] Define schema with `doc_id`, `version`, `page`, `bbox`, etc.

---

## 🕸️ Optional Knowledge Graph

- [ ] Entity extraction via Bedrock → `services/functions/structure`.
- [ ] Neptune cluster via Terraform.
- [ ] API layer in `services/api`.

---

## 🔎 Retrieval & Reranking

- [ ] Retrieval endpoint in `services/api`.
- [ ] Query OpenSearch → top-k chunks.
- [ ] Re-rank with **Cohere Rerank via Bedrock**.
- [ ] (Optional) Integrate with Kendra if enterprise connectors needed.

---

## 📚 Grounding & Answer Generation

- [ ] Context assembler in `services/worker`.
- [ ] Carry citation atoms (doc_id, page, bbox, section_path).
- [ ] QA generation with Titan/Anthropic on Bedrock.
- [ ] Render citations clickable in `dashboard` + `web`.

---

## 🖥️ API Surface

- [ ] `POST /qa` in `services/api` → answer + citations.
- [ ] `POST /search` → ranked chunks.
- [ ] `GET /doc/:id/chunk/:chunk_id`.
- [ ] Enforce ACLs via BetterAuth (`dashboard/auth.ts`).

---

## 🔒 Security & Compliance

- [x] S3, DynamoDB, DocumentDB already Terraform-managed.
- [ ] Replace DocumentDB with Aurora Postgres for long-term persistence.
- [ ] Comprehend PII detection → redact in exporter outputs.
- [ ] Private VPC endpoints for Textract, Bedrock, A2I.
- [ ] IAM-scoped A2I workforce.

---

## 📈 Observability & Maintenance

- [ ] Job audit trail in Aurora (migrate from Dynamo/DocDB).
- [ ] CloudWatch alarms for function errors & Step Functions DLQs.
- [ ] OpenSearch dashboards for pipeline monitoring.
- [ ] ECS autoscaling policies (`services/worker`).
- [ ] Glacier archiving after 90 days.
- [ ] Re-embed when embedding model version changes.

---

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
- [x] OCR functionality implemented with AWS Textract in `services/functions/ocr` (no ECS needed).
- [x] Preflight validation implemented in `services/api/app/security.py` (MIME, size, virus scanning ready).
- [x] Add page count and encryption detection to preflight validation.
- [x] Connect Step Functions to actual Lambda function ARNs (updated terraform configuration).

---

## 📝 Structure Extraction

- [x] Wire **Textract AnalyzeDocument** into `services/functions/ocr` (combined with OCR).
- [x] Persist Textract JSON to S3 (`/artifacts/raw`) via `services/worker` MongoDB storage.
- [x] Normalize into **canonical JSON schema** in `packages/schemas` (document models exist).
- [x] Textract integration working with structure analysis in `services/functions/structure`.
- [x] Add Textract **Queries** for metadata (title, captions, author, subject, key topics).
- [x] Enhance canonical schema for better LLM corpus preparation (TextChunk, EmbeddingVector, DocumentCorpus, RAG types).

---

## 🤖 AI-Assisted Enhancements

- [x] Use **Bedrock** client in `services/functions/alt_text` for figure alt-text (Claude + Rekognition).
- [x] Store AI results in MongoDB via `services/shared/mongo/alt_text.py`.
- [x] Alt-text review component exists in `web/components/AltTextReview.tsx`.
- [x] Add AI confidence scoring to schema (AIConfidenceScores interface with comprehensive scoring).
- [x] Route low-confidence items to A2I → review flow (comprehensive review service with confidence evaluation).
- [x] Implement heading level inference with Bedrock (Claude 3.5 Sonnet with confidence scoring).
- [ ] Connect review component with A2I workflow outputs.

---

## 📄 Accessible PDF Remediation

- [x] Extend `services/functions/tag_pdf` to apply PDF/UA tags via pikepdf:
  - [x] Document root & Lang.
  - [x] Headings, paragraphs, lists, figures, tables, links.
  - [x] Reading order MCIDs.
  - [x] Bookmarks from heading outline.
- [x] Save tagged PDFs in S3 (`/artifacts/pdf`) via tagger service.
- [x] Enhance PDF/UA compliance validation (comprehensive WCAG 2.1 + PDF/UA validation with scoring).
- [ ] Add support for complex table structures.

---

## ✅ Validation

- [x] Validation service exists in `services/functions/validator` with FastAPI.
- [x] Store validation reports in S3 (`/artifacts/reports`) - infrastructure ready.
- [x] Notification system implemented in `services/functions/notifier`.
- [ ] Deploy EC2 Windows AMI for **PAC 2024** validation (Terraform addition).
- [ ] Connect Step Functions state → `services/functions/validate`.
- [ ] Implement actual PAC 2024 validation logic.
- [ ] Add SNS → `dashboard` notification routing.

---

## 🌐 Alternative Formats

- [x] Export functions scaffolded (`services/functions/exporter`, `services/functions/exports`).
- [x] Export endpoints implemented in `services/api/app/routes/documents.py`.
- [x] Multiple formats supported: PDF, HTML, Text, CSV, Analysis, Preview.
- [x] JSON persisted in MongoDB and available via S3 (`/artifacts/json`).
- [x] Expose via `services/api` endpoints with presigned URL downloads.
- [ ] Ensure semantic HTML builder uses canonical JSON schema.
- [ ] Enhance TXT exporter to be reading-order aware.
- [ ] Add structured data export (tables as CSV/JSON).

---

## 📊 LLM Corpus Preparation

- [x] PDF content extraction implemented in `services/worker` with pdfplumber.
- [x] Table extraction and conversion capabilities exist in worker.
- [x] Image and figure extraction with alt-text integration.
- [x] Add chunking logic in `services/worker/src` (≤2k chars, metadata, smart text splitting, hierarchy building).
- [x] Convert tables → Markdown + JSON format (implemented in chunking service).
- [x] Include alt-text + captions with figures in chunks (integrated in corpus preparation).
- [x] Add document section hierarchy to chunks (hierarchy builder in chunking service).

---

## 🔍 Embeddings & Indexing

- [x] MongoDB implementation active with document storage and querying.
- [x] DynamoDB tables configured for Jobs, Documents, UserSessions.
- [x] DocumentDB cluster configured in Terraform (alternative to Aurora).
- [x] Bedrock Titan embeddings integration in `services/worker` (comprehensive embeddings service with similarity search).
- [ ] Consider Aurora Postgres migration (currently using DocumentDB + MongoDB).
- [x] Index embeddings into **OpenSearch Serverless Vector Collection** (`infra/terraform/opensearch.tf` created with VPC, security, encryption).
- [x] Define embedding schema with `doc_id`, `version`, `page`, `bbox`, etc. (EmbeddingVector interface in schemas).
- [x] Implement vector similarity search capabilities (EmbeddingsService with cosine similarity and search).

---

## 🕸️ Optional Knowledge Graph

- [x] Structure analysis capability exists in `services/functions/structure`.
- [ ] Entity extraction via Bedrock → enhance `services/functions/structure`.
- [ ] Neptune cluster via Terraform.
- [ ] API layer in `services/api` for knowledge graph queries.
- [ ] Define entity relationships schema.
- [ ] Implement graph traversal and query endpoints.

---

## 🔎 Retrieval & Reranking

- [x] Document search capabilities exist via MongoDB in `services/shared/mongo`.
- [x] API endpoints for document retrieval in `services/api/app/routes/documents.py`.
- [x] Implement semantic retrieval endpoint in `services/api` (comprehensive search API with embeddings).
- [x] Query vector embeddings → top-k chunks (implemented with Titan embeddings).
- [ ] Re-rank with **Cohere Rerank via Bedrock**.
- [ ] Add hybrid search (text + semantic).
- [ ] (Optional) Integrate with Kendra if enterprise connectors needed.

---

## 📚 Grounding & Answer Generation

- [x] Content processing capabilities exist in `services/worker`.
- [x] Document metadata tracking with doc_id, page info in MongoDB.
- [x] Bedrock Claude integration available for QA generation.
- [x] Context assembler implemented in search API for multi-document context.
- [x] Carry citation atoms (doc_id, page, bbox, section_path, chunk_id).
- [x] QA generation endpoint with Anthropic Claude on Bedrock (comprehensive RAG implementation).
- [ ] Render citations clickable in `dashboard` + `web`.
- [ ] Implement response streaming for long-form answers.

---

## 🖥️ API Surface

- [x] Document CRUD endpoints implemented in `services/api/app/routes/documents.py`.
- [x] Upload endpoints with presigned URLs.
- [x] Export endpoints for multiple formats.
- [x] Authentication integration with Cognito/BetterAuth.
- [x] `POST /search/qa` in `services/api` → answer + citations.
- [x] `POST /search/semantic` → ranked chunks.
- [x] `GET /search/documents/:id/chunks/:chunk_id` → chunk details with context.
- [ ] Enforce consistent ACLs (resolve Cognito/BetterAuth duplication).
- [ ] Add API versioning (/v1/ prefix).

---

## 🔒 Security & Compliance

- [x] S3, DynamoDB, DocumentDB already Terraform-managed.
- [x] KMS encryption enabled for all storage services.
- [x] VPC configuration for secure service communication.
- [x] Security validation framework in `services/api/app/security.py`.
- [x] Virus scanning integration ready (ClamAV placeholder).
- [ ] Replace DocumentDB with Aurora Postgres for long-term persistence.
- [ ] Comprehend PII detection → redact in exporter outputs.
- [ ] Private VPC endpoints for Textract, Bedrock, A2I.
- [ ] IAM-scoped A2I workforce.
- [ ] Resolve authentication system duplication (Cognito vs BetterAuth).

---

## 📈 Observability & Maintenance

- [x] Job tracking implemented in DynamoDB with comprehensive metadata.
- [x] Document audit trail in MongoDB with processing history.
- [x] CloudWatch configuration ready in Terraform infrastructure.
- [x] Docker containerization for all services with health checks.
- [ ] Job audit trail migration to Aurora (from Dynamo/DocDB).
- [ ] CloudWatch alarms for function errors & Step Functions DLQs.
- [ ] OpenSearch dashboards for pipeline monitoring.
- [ ] ECS autoscaling policies (`services/worker`).
- [ ] Glacier archiving after 90 days.
- [ ] Re-embed when embedding model version changes.
- [ ] Implement comprehensive logging and metrics collection.

---

## 🖥️ User Interface & Experience

- [x] **Web Application** (localhost:3000) - Fully operational:
  - [x] Landing page with professional branding and clear value proposition
  - [x] File upload with drag & drop functionality
  - [x] Real-time processing with 11-step pipeline visualization
  - [x] Progress tracking with visual progress bars and status updates
  - [x] Environment configuration properly set up
  - [x] S3 upload integration working correctly

- [x] **Dashboard Application** (localhost:3001) - Fully operational:
  - [x] Authentication system unified on BetterAuth (removed Cognito conflicts)
  - [x] Professional sign-in page with multiple OAuth options
  - [x] Admin interface ready for user management
  - [x] Environment configuration properly configured
  - [x] Database integration connected to PostgreSQL and MongoDB

---

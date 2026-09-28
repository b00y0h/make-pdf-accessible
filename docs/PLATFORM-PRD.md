# Make PDF Accessible — Enterprise Document Accessibility Platform

## Every document an institution publishes is inventoried, triaged, made accessible or defensibly exempt, published back where users find it, and backed by an evidence pack.

**Status:** Draft v1.0 (2026-09-28). Umbrella PRD; the four feature PRDs it links are the buildable units.
**Owner:** Product (founder).

---

## CONTEXT

Make PDF Accessible today is a microservices monorepo (`services/api`, `services/worker`, `services/functions/*`, `dashboard/`, `web/`, `integrations/wordpress/`, `infra/terraform/`) that can upload a PDF to S3, extract text and images, build semantic HTML (`services/worker/src/semantic_html_builder.py`), and show results in a Next.js dashboard. The WordPress plugin inventories a site's PDFs locally and serves Markdown to AI agents. The core promise, an accessible PDF with a real score, is not implemented: the tagger is a mock (`services/functions/tag_pdf/main.py`), the "accessible PDF" artifact is the original file (`services/worker/worker.py`), scores are hardcoded, and the validator never opens the output file. The market research (`docs/research/higher-ed-market-research-2026-09.md`) concluded the need is real and funded but that raw AI tagging is a commodity; the ITHAKA analysis (`docs/research/ithaka-pipeline-analysis.md`) shows the architecture to copy and the seven things it does not do.

This PRD defines the product that fills the gap: the end-to-end loop for institutions under the ADA Title II, Section 504 and Section 508 obligations, with higher education as the first market.

The motivating gaps:

1. **Institutions do not know what they have.** No inventory exists across the public website, CMS media libraries, LMS courses and shared drives. Scanners find PDFs on the website only, and they do not fix them.
2. **They should not fix everything.** The rule's exceptions (archived content, unused pre-existing documents, third-party content) mean a large share of the backlog should be deleted, archived or left alone, with the decision recorded. No tool classifies against the rule.
3. **PDF is often the wrong output, and the fixed file never gets published.** HTML-first policies are now common. Nobody publishes converted documents into WordPress or Drupal with redirects and the original kept as a download.
4. **No per-document evidence.** Vendors quote fleet averages ("90%+ automated"). A compliance office needs a record per document: what was checked, by which tool version, what a human signed off, when.
5. **The codebase overstates itself.** The README says "95% Enterprise-Ready." Any demo today would mislead a buyer.

### Locked Scope Decisions

1. **The product is the loop, not the tagger.** Inventory → Triage → Remediate or Convert → Publish → Prove → Maintain. Every feature must serve one of those stages. Rationale: tagging is commoditized (free AWS/ASU pipeline, $0.026/page at ITHAKA); the loop is unserved.
2. **We orchestrate licensed engines; we do not build a PDF tagger.** PDFix SDK plus veraPDF is the first engine; Adobe Auto-Tag is the second adapter. Rationale: two engineers cannot out-build Adobe or PDFix in seven months, and ITHAKA proved the swap-in pattern. See ADR-0003.
3. **Remediate on demand and cache by content hash; batch is a scheduling policy on top.** Rationale: ITHAKA's model; most documents are never opened. See ADR-0001.
4. **Evidence pack per document is the unit of delivery.** Nothing is "done" without one. See ADR-0004.
5. **HTML first for text-heavy web documents; PDF/UA when the document must stay a PDF.** See ADR-0005.
6. **AWS-native, Terraform-managed, multi-account.** Dev, staging and prod are separate AWS accounts. See ADR-0010.
7. **No "automatic compliance" language anywhere**, in code, UI, docs or marketing. We say "remediated and validated" and "verified by a reviewer." Rationale: FTC v. accessiBe.
8. **Higher education first**, then K-12 and local government using the same product with different packaging. Healthcare, federal and publishers are later.
9. **Cognito is the identity layer** (SAML and OIDC federation for institutions); BetterAuth is retired. See ADR-0007.
10. **Aurora PostgreSQL is the system of record; DynamoDB holds high-write pipeline state; MongoDB/DocumentDB and OpenSearch Serverless are retired.** See ADR-0006.

### What This Is NOT

- Not a website accessibility scanner. We import scanner output as inventory; we do not audit HTML pages, color contrast on web templates, or JavaScript widgets.
- Not an LMS instructor dashboard. Ally, Panorama and UDOIT own that seat through bundled contracts. Our LTI tool remediates what they flag.
- Not an overlay or a JavaScript widget that claims to fix a site. The remaining "LLM discovery" snippet (`integrations/html-snippets/`) and the disabled public embeddings endpoints are out of the product until re-scoped.
- Not a document authoring tool. We do not replace Word, InDesign or LaTeX. We accept their outputs and publish back accessible ones.
- Not a general RAG or search product. Semantic exports (Markdown, chunks) stay as an export format; `/v1/search` semantic search is not a marketed feature in this scope.
- Not a human remediation shop. The verified tier reviews flagged elements and, at the top tier, whole documents; we do not take arbitrary consulting work.
- Not a guarantee of legal compliance. We produce evidence; counsel decides.

---

## SUCCESS CRITERIA

1. A new customer can connect a WordPress site or enter a domain, and within 24 hours see every PDF the crawler and connectors found, each with page count, location, inbound links, last-modified date and usage (where analytics are connected), in the dashboard's Inventory view and as a CSV export.
2. Every inventoried document has a triage decision (`delete`, `archive`, `convert_html`, `remediate_pdf`, `review`, `exempt_third_party`) with a stored rationale and a per-document cost estimate, and the plan totals are visible on the Triage view.
3. Submitting a born-digital PDF produces a tagged PDF whose veraPDF PDF/UA-1 report (stored in the evidence pack) shows zero failed rules, for at least 95% of documents in the public eval set (`docs/eval/`), measured monthly and published.
4. Submitting the same file twice (same SHA-256) does not run the pipeline twice; the second request returns the cached artifact set and the evidence pack references the original job id.
5. Every completed document has an evidence pack: `evidence.json` (schema-versioned), the raw validator reports, the semantic QA scores per element, tool and model versions, and, for verified documents, the reviewer id and timestamp; the pack is signed and stored with S3 Object Lock in compliance mode for the retention period.
6. A text-heavy PDF converted to HTML publishes into a connected WordPress site as a page, with a 301 redirect from the old PDF URL and a link to the original PDF, within one click from the dashboard, and the published page passes axe-core with zero violations.
7. An "Accessible Link" (`https://a11y.<tenant-domain>/d/<hash>` or the API equivalent) for any inventoried PDF URL serves the remediated version; the first request remediates on demand and later requests are served from cache with p50 latency under 300 ms.
8. Elements below the semantic confidence threshold appear in the review workbench; a reviewer can approve, edit or reject each one, and the document is marked `verified` only when no open items remain.
9. An institution admin can sign in through their SAML IdP (tested with InCommon-style Shibboleth and Microsoft Entra ID), assign roles (`owner`, `admin`, `editor`, `reviewer`, `viewer`, `billing`), and see an audit log of every change to documents, triage decisions and evidence.
10. Usage is metered per page per stage and shown in the dashboard; invoices match metered usage; quotas stop processing at the plan limit with a clear message and an upgrade path.
11. The dashboard, the marketing site, and generated evidence pack PDFs pass a WCAG 2.2 AA audit with an ACR published on the marketing site.
12. The demo path (`/v1/demo/*`) and the README make no claim the pipeline cannot back: no hardcoded scores, no returned-original "accessible" PDFs.

---

## DATA MODEL (system-level; details per feature PRD)

```
tenants                 // institution or system; billing boundary; region; KMS key alias
sites                   // a crawlable domain or CMS connection belonging to a tenant
documents               // one logical document per content hash per tenant
document_locations      // where a document is found (URL, CMS attachment id, LMS file id), many per document
triage_decisions        // decision + rationale + estimated cost + decided_by + decided_at, append-only
jobs                    // one pipeline run; references document hash, engine, profile, cost meters
job_events              // stage events (EventBridge mirror) for the job timeline
artifacts               // outputs: tagged_pdf, html, markdown, csv_zip, epub, evidence_json, validator_reports
review_items            // low-confidence elements awaiting human decision
evidence_packs          // signed manifest per document version; immutable
publications            // where an artifact was published (CMS page id, redirect from, published_by)
users, memberships, roles, api_keys, audit_log, usage_meters, invoices
```

---

## FEATURES (each has its own PRD)

| Feature                                                                                                           | PRD                                | Stage(s)                              |
| ----------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------- |
| Inventory and Triage                                                                                              | `docs/INVENTORY-TRIAGE-PRD.md`     | Inventory, Triage, Maintain           |
| Remediation Pipeline v2 (engine, validation, evidence, on-demand cache, HTML conversion, review workbench)        | `docs/REMEDIATION-PIPELINE-PRD.md` | Remediate or Convert, Prove, Maintain |
| Integrations (WordPress publish-back, Drupal, LTI 1.3, scanner imports, public API and webhooks, Accessible Link) | `docs/INTEGRATIONS-PRD.md`         | Publish, Maintain                     |
| Enterprise Readiness (identity, tenancy, RBAC, audit, quotas, billing, SLOs, DR, compliance program)              | `docs/ENTERPRISE-READINESS-PRD.md` | Operate                               |
| Marketing Site                                                                                                    | `docs/MARKETING-SITE-PRD.md`       | Acquire                               |

---

## PERSONAS

- **Digital Accessibility Officer (buyer/champion).** Needs the inventory, the plan and the evidence. Lives in the dashboard's Inventory, Triage and Evidence views.
- **Web/CMS editor (daily user).** Uploads, converts, publishes back. Lives in the WordPress/Drupal plugin and the Documents view.
- **Reviewer (verified tier, ours or the customer's).** Lives in the review workbench.
- **CIO / Counsel (approver).** Reads the conformance dashboard and exported evidence packs.
- **Developer (integrator).** Uses the API, webhooks and the Accessible Link.

---

## NON-FUNCTIONAL REQUIREMENTS (summary; detail in the Enterprise Readiness PRD)

| Area          | Requirement                                                                                                                                                       |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Availability  | 99.5% (Campus), 99.9% (System) monthly for the API and dashboard; pipeline is asynchronous with queue-backed retries                                              |
| Latency       | Upload-to-evidence-pack p95 under 10 minutes for a 50-page born-digital PDF; under 30 minutes for a 50-page scanned PDF                                           |
| Throughput    | 1,000 concurrent page tasks per region without manual scaling                                                                                                     |
| Data          | Encrypted at rest with tenant-scoped KMS keys (System tier: dedicated key); TLS 1.2+ in transit; region pinning; retention configurable 1 to 7 years for evidence |
| Security      | SAML/OIDC SSO, RBAC, API keys with scopes, audit log, WAF, private subnets, no public buckets, quarterly access reviews, annual pen test                          |
| Compliance    | SOC 2 Type I by month 9, Type II by month 18; HECVAT Full; FERPA DPA; ACR/VPAT for our surfaces                                                                   |
| Observability | Stage events, per-page cost meters, SLO dashboards, alerting to on-call, per-tenant usage                                                                         |
| Cost          | Automated cost of goods under $0.055 per page                                                                                                                     |

---

## MILESTONES / ROLLOUT PLAN

| Slice                   | Scope                                                                                                                            | Value delivered alone                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| S0 — Truth              | Remove mocks and hardcoded scores; README/STATUS reflect reality; demo returns only what the pipeline produces                   | Sales can demo without misleading                          |
| S1 — Inventory & Triage | Crawler, WordPress inventory sync, classification, plan and cost estimate, exports, free website report                          | Sellable engagement; matches how institutions already work |
| S2 — Real remediation   | PDFix engine on Fargate, veraPDF validation, page-parallel Step Functions, evidence pack v1, content-hash cache, Accessible Link | The core promise is real                                   |
| S3 — HTML-first publish | Hardened conversion, WordPress publish-back with redirects, Drupal beta                                                          | Users get accessible pages, not just files                 |
| S4 — Verified tier      | Review workbench, confidence routing, reviewer sign-off in evidence                                                              | Premium tier; quality where automation is weak             |
| S5 — Enterprise         | SSO, RBAC, quotas, metering, billing, audit log, SOC 2 controls, ACR, HECVAT                                                     | Procurement can say yes                                    |
| S6 — LMS & STEM         | LTI 1.3, MathML/PDF-UA-2, forms                                                                                                  | Course content and the hardest documents                   |
| S7 — Scale              | Multi-region, dedicated-account tier, marketplace listings, K-12 and government packaging                                        | Second and third markets                                   |

---

## OPEN QUESTIONS

1. **PDFix licensing terms for SaaS use.** Per-server, per-page or revenue share? Decide before S2 procurement; the Adobe adapter is the fallback (ADR-0003).
2. **Do we run our own reviewer pool or partner with an existing remediation vendor for the verified tier?** Own pool gives control over the evidence chain; a partner gives capacity fast. Decide before S4.
3. **Data residency beyond us-east-1.** Canadian and EU institutions will ask. Decide the second region before S7.
4. **How much of the LLM-discovery work (Markdown for AI agents, chunks) stays in the product?** It is real code and some customers like it, but it dilutes positioning. Decide at S3 planning.
5. **Pricing of the free website report.** Cap at 5,000 PDFs or by crawl minutes? Decide when S1 crawler costs are measured.

## RISKS

- **Engine quality on scanned and STEM documents.** Mitigation: measured eval set by document class; verified tier; STEM deferred to S6.
- **Institutional SCPs and network policies break connectors.** Mitigation: outbound-only connectors, documented allow-lists, no inbound firewall rules required.
- **Seven-month window to the 2027 deadline.** Mitigation: S1 and S2 are the minimum; everything else can slip a quarter without losing the market.

## SUCCESS METRICS

- ≥ 95% veraPDF pass rate on the eval set by S2 exit; ≥ 98% by S4 exit.
- ≥ 5 paid pilots by December 2026; ≥ 45 paying institutions by September 2027.
- p95 upload-to-evidence under 10 minutes for 50-page born-digital documents.
- Automated cost of goods under $0.055 per page measured monthly.

---

## SOURCES & RELATED DOCS

- `docs/business/BUSINESS-PLAN.md` — commercial plan this PRD implements
- `docs/research/higher-ed-market-research-2026-09.md` — market and regulatory evidence
- `docs/research/ithaka-pipeline-analysis.md` — architectural benchmark
- `docs/REMEDIATION-PIPELINE-PRD.md`, `docs/INVENTORY-TRIAGE-PRD.md`, `docs/INTEGRATIONS-PRD.md`, `docs/ENTERPRISE-READINESS-PRD.md`, `docs/MARKETING-SITE-PRD.md` — feature PRDs
- `docs/adr/` — architecture decision records
- `docs/REMEDIATION-PIPELINE-SPECS.md`, `docs/INVENTORY-TRIAGE-SPECS.md`, `docs/ENTERPRISE-READINESS-SPECS.md`, `docs/AWS-DEPLOYMENT-SPECS.md` — execution specs

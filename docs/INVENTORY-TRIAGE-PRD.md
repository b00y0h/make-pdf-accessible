# Make PDF Accessible — Inventory & Triage

## Find every document an institution publishes, decide what the rule requires for each one, and produce a plan with a price.

**Status:** Draft v1.0 (2026-09-28)
**Parent:** `docs/PLATFORM-PRD.md` (stages Inventory, Triage, Maintain)
**Implements ADRs:** ADR-0006 (Aurora PostgreSQL system of record), ADR-0011 (Bedrock model strategy, classification)

---

## CONTEXT

The WordPress plugin (`integrations/wordpress/includes/class-make-pdf-accessible-inventory.php`, `class-make-pdf-accessible-pdf-analyzer.php`) already inventories a site's media library and linked PDFs locally: it parses the trailer and catalog to detect tags, text layer, page count, title, language, forms, encryption and a PDF/UA claim, classifies links (media library, outside the media library, another site), flags orphaned files, estimates manual remediation cost and exports CSV. Nothing equivalent exists server-side: the API has no crawler, no inventory tables and no triage concept. The dashboard has Documents and Reports views (`dashboard/src/app/(dashboard)/documents/page.tsx`, `.../reports/page.tsx`) over uploaded documents only.

Institutions do this work by hand today (UND's purge, Iowa's "Remove, Revise, Right-First", UNC's "PDFebruary"). The market research identifies inventory and triage as the wedge nobody owns.

The motivating gaps:

1. **No server-side inventory.** Only WordPress sites get a list, and only inside WordPress.
2. **No classification against the rule.** The plugin estimates cost for everything; it does not say which documents may be deleted, archived, converted or must be fixed.
3. **No usage signal.** Whether anyone opens a document decides whether the pre-existing-content exception applies. No analytics or log import exists.
4. **No plan artifact.** There is nothing to hand a CIO with counts, paths, costs and a recommended order.
5. **Nothing runs again.** After the first list there is no re-crawl, no drift detection, no intake for new uploads.

### Locked Scope Decisions

1. **Inventory is a first-class, tenant-scoped data set in Aurora PostgreSQL**, independent of whether a document has ever been processed. Documents are joined to the pipeline's `documents` table by SHA-256 when bytes are fetched.
2. **Sources are pluggable:** web crawler, WordPress plugin sync, Drupal module sync, LMS (LTI/Canvas API) listing, scanner CSV import (Siteimprove, DubBot, Pope Tech), sitemap, and analytics import (Google Analytics 4 export, server log CSV). The crawler and WordPress sync ship first.
3. **Triage rules are explicit, versioned and explainable.** A rules engine produces a decision, a rationale string and the rule id; an LLM classifier (`anthropic.claude-haiku-4-5` via Bedrock) only supplies features the rules consume (document type, currency signals, form detection), never the final decision.
4. **Every decision is recorded append-only with who or what decided and why.** Overrides by staff are decisions too.
5. **The cost estimate uses our published prices plus a manual benchmark**, shown side by side.
6. **The free website report on the marketing site is the same crawler with a cap**, not a separate implementation.

### What This Is NOT

- Not an HTML accessibility scanner. We crawl to find documents, not to audit pages.
- Not a records-management or retention system. Archive decisions are recorded; moving files is done by the CMS connector or the customer.
- Not legal advice. Rule ids cite the regulation section; the UI states that counsel makes the final call.
- Not a full-text search index over documents. Titles and metadata are indexed; content search is out of scope.
- Not LMS course-content inventory in the first slice; that arrives with the LTI tool (`docs/INTEGRATIONS-PRD.md`).

---

## SUCCESS CRITERIA

1. Entering `https://www.example.edu` and starting a crawl produces, within 24 hours for a site of up to 50,000 HTML pages, an inventory where every `.pdf` URL reachable from the home page or the sitemap appears exactly once (deduplicated by URL and by SHA-256 when fetched), with page count, byte size, text-layer flag, tagged flag, title, language, form flag, encryption flag, discovered-from pages, and last-modified.
2. Connecting the WordPress plugin syncs its local inventory into the same tenant's inventory within 5 minutes, and documents found by both the crawler and the plugin are one row with two locations.
3. Importing a Siteimprove, DubBot or Pope Tech CSV export adds documents and their issue counts without creating duplicates for URLs already known.
4. Every inventory row has a triage decision from the rules engine within one hour of discovery, with `rule_id`, `rationale` and `estimated_cost_cents` populated, and the Triage view shows totals per decision, per site and per owner.
5. Uploading a GA4 pages export or a server-log CSV attaches `views_90d` to matching documents and re-runs triage; documents with zero views and a last-modified date before the compliance date move to `archive` or `delete` candidates with rationale citing the pre-existing-content exception.
6. A staff user can override any decision with a note; the override is stored as a new decision row, the previous one is retained, and the audit log shows both.
7. The plan export (`GET /v1/inventory/plan.csv` and `.pdf`) lists every document with decision, rationale, cost estimate, recommended order and owner, and the PDF export itself passes veraPDF PDF/UA-1.
8. A scheduled re-crawl (weekly by default) detects new, changed (SHA-256 differs) and removed documents, re-triages only the changed set, and raises a dashboard notification and an optional webhook `inventory.drift`.
9. The free website report on the marketing site crawls up to 5,000 PDFs, emails a summary within 2 hours, and creates a lead record; it never stores the fetched PDFs beyond the metadata needed for the report.
10. A crawl respects `robots.txt`, identifies itself with a documented user agent, rate-limits to 4 requests per second per host by default, and can be cancelled.

---

## DATA MODEL CHANGES

### New table — `sites`

```
sites
  - id: uuid [pk]
  - tenant_id: uuid [fk]
  - kind: enum(web, wordpress, drupal, lms, import)
  - base_url: text                                  // https://www.example.edu
  - crawl_config: jsonb                             // include/exclude patterns, rate, depth, sitemap urls, auth
  - schedule: text                                  // cron; null = manual
  - last_crawl_id: uuid, last_crawled_at
  - status: enum(active, paused, error)
```

### New table — `crawls`

```
crawls
  - id: uuid [pk]
  - site_id, tenant_id [fk]
  - started_at, finished_at
  - pages_fetched, pdfs_found, pdfs_new, pdfs_changed, pdfs_removed, errors: int
  - status: enum(running, completed, cancelled, failed)
  - report_s3_key: text
```

### New table — `inventory_items`

```
inventory_items
  - id: uuid [pk]
  - tenant_id, site_id [fk]
  - url: text [unique with tenant_id]
  - document_id: uuid [fk documents, nullable]      // set when bytes fetched and hashed
  - sha256: char(64) [nullable, indexed]
  - title, language: text
  - page_count, byte_size: int
  - has_text_layer, is_tagged, is_form, is_encrypted, claims_pdfua: bool
  - last_modified: timestamptz                      // from HTTP or CMS
  - first_seen_at, last_seen_at, removed_at
  - owner: text                                     // department or user from CMS/path heuristics
  - views_90d: int [nullable]                       // from analytics import
  - inbound_page_count: int
  - source_flags: text[]                            // crawler, wordpress, drupal, siteimprove, dubbot, popetech, sitemap, analytics
  - external_issue_count: int [nullable]            // from scanner import
```

### New table — `inventory_links`

```
inventory_links
  - inventory_item_id [fk], from_url: text, anchor_text: text, seen_at
  - pk (inventory_item_id, from_url)
```

### New table — `triage_decisions` (append-only)

```
triage_decisions
  - id: uuid [pk]
  - inventory_item_id, tenant_id [fk]
  - decision: enum(delete, archive, convert_html, remediate_pdf, review, exempt_third_party, exempt_archived, keep_as_is)
  - rule_id: text                                   // e.g. "R-ARCHIVE-01"
  - rationale: text
  - features: jsonb                                 // inputs used: views_90d, last_modified, doc_type, is_form, ...
  - estimated_cost_cents: int, estimated_manual_cost_cents: int
  - priority: int                                   // 1 (highest) .. 5
  - decided_by: enum(rules, staff), decided_by_user: uuid [nullable]
  - decided_at
```

### New table — `analytics_imports`

```
analytics_imports
  - id, tenant_id, site_id, kind: enum(ga4, server_log, csv), rows, matched, imported_at, s3_key
```

---

## FEATURE 1 — WEB CRAWLER

- Implementation: a Fargate task (`services/crawler/`) using an async HTTP client, `robots.txt` compliance, sitemap parsing, link extraction from `href`, `src`, `data` attributes and PDF-looking query URLs, canonicalization (scheme, host case, trailing slash, tracking params), depth and include/exclude patterns, optional basic-auth or cookie for staging sites. PDFs are fetched with `Range` requests for metadata when the server supports it, otherwise fully; the existing PHP analyzer's checks are ported to Python (`services/crawler/pdf_probe.py`) and validated against the same fixtures (`integrations/wordpress/tests/fixtures/pdf-builder.php` cases).
- Scale: one Fargate task per crawl, frontier in DynamoDB (`crawl_frontier`), results streamed to Aurora in batches. Cap per plan: Team 20,000 pages, Campus 250,000, System unlimited.
- Politeness: 4 rps default, respects `Crawl-delay`, exponential backoff on 429/503, user agent `MakePDFAccessibleBot/1.0 (+https://makepdfaccessible.com/bot)`.

## FEATURE 2 — SOURCE CONNECTORS

- **WordPress sync:** the plugin gains `POST /v1/inventory/sync` batches (existing REST scan endpoint `POST /wp-json/make-pdf-accessible/v1/inventory/scan` is the source); rows carry attachment ids so publish-back can target them later.
- **Scanner imports:** CSV mappers for Siteimprove (PDF report export), DubBot (documents export) and Pope Tech (files report); columns mapped to URL, issue count, last crawled.
- **Sitemap-only mode** for institutions that will not permit crawling.
- **Analytics imports:** GA4 pages-and-screens export CSV (page path + views), Apache/Nginx log CSV; matched on canonical URL.

## FEATURE 3 — TRIAGE RULES ENGINE

Rules are ordered, versioned (`rules/v1.yaml`), and explainable. Initial set:

| Rule      | Condition                                                                                                                                                  | Decision                                 | Rationale template                                                                                 |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------- |
| R-3P-01   | URL host not in tenant's domains and not a CMS-hosted file                                                                                                 | `exempt_third_party`                     | Third-party content the entity does not control (28 CFR 35.201) — verify                           |
| R-DEL-01  | `inbound_page_count == 0` and `views_90d == 0` and not in media library                                                                                    | `delete` candidate                       | Orphaned and unused; removal is cheaper than remediation                                           |
| R-ARCH-01 | `last_modified` before compliance date and `views_90d == 0` and path or title matches archive patterns (minutes, agendas, superseded catalogs, past years) | `exempt_archived` candidate              | May meet the archived-content exception if moved to a labeled archive; confirm the four conditions |
| R-FORM-01 | `is_form`                                                                                                                                                  | `remediate_pdf`                          | Fillable forms stay PDF; fields need labels and tab order                                          |
| R-HTML-01 | text layer present, `page_count <= 30`, not a form, doc type in {policy, syllabus, guide, notice, faq, catalog page}                                       | `convert_html`                           | Text-heavy web document; HTML-first policy                                                         |
| R-PDF-01  | text layer present, otherwise                                                                                                                              | `remediate_pdf`                          | Print-fidelity document                                                                            |
| R-SCAN-01 | no text layer                                                                                                                                              | `review` (with `remediate_pdf` proposal) | Scanned; OCR quality must be checked                                                               |
| R-STEM-01 | doc type in {math, science paper} or LaTeX signature                                                                                                       | `review`                                 | Needs MathML/PDF-UA-2 profile                                                                      |
| R-CUR-01  | `views_90d > 0` or linked from application/aid/admissions/housing paths                                                                                    | priority 1                               | Currently used to access a program: no exception applies                                           |

Doc type comes from a Bedrock classification call (`BEDROCK_MODEL_CLASSIFY`) over the first two pages of text with a fixed label set; its output is a feature, not a decision. Rules cite section numbers so the rationale is auditable.

Cost estimate: `estimated_cost_cents = page_count × price_for(decision, plan)` using the published price list, and `estimated_manual_cost_cents = page_count × 500` (mid-range of $2.50 to $12 human rates) for comparison. Delete and exempt decisions cost zero.

## FEATURE 4 — TRIAGE AND PLAN VIEWS

Dashboard routes `/inventory` (table with facets: site, decision, owner, class, priority, source; bulk override; open document), `/triage` (totals by decision, cost by path, recommended order, "what if" toggles such as archive-all-unused), and `/plan` (export CSV/PDF, share link for the CIO). The Reports view gains inventory coverage over time.

## FEATURE 5 — MAINTAIN

Scheduled re-crawls per site; drift detection (new, changed, removed); intake hooks from connectors on upload; `inventory.drift` and `inventory.new_document` webhooks; auto-enqueue policy per site (`none`, `queue_for_review`, `auto_remediate_new`).

## FEATURE 6 — FREE WEBSITE REPORT (marketing)

`POST /v1/public/site-report` (rate limited, CAPTCHA-protected) takes a domain and an email, runs a capped crawl (5,000 PDFs or 60 minutes), stores only metadata, emails a PDF/HTML report (counts by class, estimated cost by path, top 20 heaviest documents), and creates a lead in the CRM. Details of the form live in `docs/MARKETING-SITE-PRD.md`.

---

## API ROUTES

| Method | Path                                               | Auth                  | Purpose                           |
| ------ | -------------------------------------------------- | --------------------- | --------------------------------- |
| POST   | `/v1/sites`                                        | `inventory:write`     | Register a site or connection     |
| POST   | `/v1/sites/{id}/crawls`                            | `inventory:write`     | Start a crawl                     |
| GET    | `/v1/sites/{id}/crawls/{crawl_id}`                 | `inventory:read`      | Crawl progress                    |
| GET    | `/v1/inventory/items`                              | `inventory:read`      | Paginated, filterable inventory   |
| POST   | `/v1/inventory/sync`                               | connector key         | WordPress/Drupal batch sync       |
| POST   | `/v1/inventory/imports`                            | `inventory:write`     | Scanner or analytics CSV import   |
| GET    | `/v1/inventory/items/{id}/decisions`               | `inventory:read`      | Decision history                  |
| POST   | `/v1/inventory/items/{id}/decisions`               | `triage:write`        | Staff override                    |
| POST   | `/v1/triage/run`                                   | `triage:write`        | Re-run rules for a site or filter |
| GET    | `/v1/inventory/plan.csv`, `/v1/inventory/plan.pdf` | `inventory:read`      | Plan export                       |
| POST   | `/v1/public/site-report`                           | public (rate limited) | Free website report               |

## ENVIRONMENT VARIABLES

| Var                                                  | Purpose                            | Example (placeholder)                                           |
| ---------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------- |
| `CRAWLER_TASK_DEFINITION_ARN`, `CRAWLER_CLUSTER_ARN` | Fargate crawler                    | ARNs from Terraform                                             |
| `CRAWL_FRONTIER_TABLE`                               | DynamoDB frontier                  | table name                                                      |
| `CRAWLER_USER_AGENT`                                 | Bot identity                       | `MakePDFAccessibleBot/1.0 (+https://makepdfaccessible.com/bot)` |
| `CRAWLER_DEFAULT_RPS`                                | Politeness                         | `4`                                                             |
| `TRIAGE_RULES_VERSION`                               | Rules file version                 | `v1`                                                            |
| `COMPLIANCE_DATE_DEFAULT`                            | Used by archive/pre-existing rules | `2027-04-26`                                                    |
| `BEDROCK_MODEL_CLASSIFY`                             | Doc-type classification            | `anthropic.claude-haiku-4-5`                                    |
| `SITE_REPORT_MAX_PDFS`, `SITE_REPORT_MAX_MINUTES`    | Free report caps                   | `5000`, `60`                                                    |
| `CRM_WEBHOOK_URL`                                    | Lead creation                      | `https://...` (secret)                                          |

## TESTING STRATEGY

- **Unit:** URL canonicalization, robots and sitemap parsing, PDF probe parity with the PHP analyzer fixtures, each triage rule with feature fixtures, cost math.
- **Integration:** crawl a local fixture site (Docker nginx with 200 pages and 50 PDFs including orphans and duplicates); assert counts and dedup; WordPress sync against the plugin's Playground e2e (`integrations/wordpress/tests/e2e/`).
- **E2E:** dashboard inventory → override → plan export; PDF export validated with veraPDF.
- **Must-pass regression:** the fixture site's plan totals are stable across releases unless rules version changes.

## MILESTONES / ROLLOUT PLAN

| Slice                     | Scope                                                                   | Value delivered alone                                 |
| ------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------- |
| I1 — Crawl + inventory    | Crawler, inventory tables, `/inventory` view, CSV export                | A complete list, sellable as an engagement            |
| I2 — Triage rules + plan  | Rules engine, classification feature, `/triage` and `/plan`, PDF export | The plan with a price                                 |
| I3 — Connectors + imports | WordPress sync, scanner CSV imports, analytics imports                  | Usage-aware decisions; meets customers where they are |
| I4 — Maintain             | Schedules, drift, webhooks, auto-enqueue                                | Compliance after the deadline                         |
| I5 — Free website report  | Public endpoint + email + CRM                                           | Top-of-funnel                                         |

## OPEN QUESTIONS

1. **Compliance date per tenant.** Population-based (2027 vs 2028) plus state law; store per tenant with a default. Decide at I2.
2. **Owner attribution.** Path heuristics vs CMS author vs manual mapping; measure how often heuristics are right on pilot sites.
3. **Crawling authenticated intranets.** Not in scope until a customer with an SSO-gated site asks; would need a headless browser with session cookies.
4. **Retention of fetched PDFs from the free report.** Metadata only is the current decision; confirm with counsel.

## RISKS

- **Crawler blocked by campus WAFs.** Mitigation: documented user agent and IP ranges, sitemap-only mode, WordPress/Drupal sync.
- **Mis-triage that deletes something needed.** Mitigation: decisions are recommendations until a staff user confirms; deletes are never executed by us.

---

## SOURCES & RELATED DOCS

- `docs/PLATFORM-PRD.md` — parent
- `docs/research/higher-ed-market-research-2026-09.md` — why triage is the wedge; rule exceptions
- `integrations/wordpress/README.md` — existing inventory checks to port
- `docs/INVENTORY-TRIAGE-SPECS.md` — execution spec
- `docs/MARKETING-SITE-PRD.md` — free website report form

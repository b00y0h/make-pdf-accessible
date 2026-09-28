# Make PDF Accessible — Inventory & Triage Implementation Specs

These specs implement `docs/INVENTORY-TRIAGE-PRD.md` (ADR-0006, ADR-0011). Starting state: a WordPress-only inventory in PHP (`integrations/wordpress/includes/class-make-pdf-accessible-inventory.php` and `class-make-pdf-accessible-pdf-analyzer.php`), no server-side crawler, no inventory or triage tables, and a dashboard limited to uploaded documents. They assume the Aurora PostgreSQL schema from `docs/ENTERPRISE-READINESS-SPECS.md` Spec 1 (the migration framework), and can run against the development PostgreSQL in `docker-compose.yml` before the Mongo cutover.

---

## Spec 1 — Inventory schema and API

### Problem

No tables or endpoints exist for sites, crawls, inventory items, links, triage decisions or analytics imports. Target: the schema from the PRD's data model and the read/write endpoints, tenant-scoped.

### Files to touch

| File                                                                                                            | Action                                                                                                                     |
| --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/db/migrations/0002_inventory.sql`                                                             | Create: `sites`, `crawls`, `inventory_items`, `inventory_links`, `triage_decisions`, `analytics_imports` with RLS policies |
| `services/api/app/models.py`                                                                                    | Add Pydantic response/request models for the six tables                                                                    |
| `services/api/app/routes/inventory.py`, `services/api/app/routes/sites.py`, `services/api/app/routes/triage.py` | Create                                                                                                                     |
| `services/api/app/main.py`                                                                                      | Mount the three routers under `/v1`                                                                                        |
| `services/api/tests/test_inventory_api.py`                                                                      | Create: CRUD, pagination, tenant isolation                                                                                 |

### Acceptance criteria

1. `POST /v1/sites`, `GET /v1/inventory/items?site_id=&decision=&owner=` and `POST /v1/inventory/items/{id}/decisions` behave per the PRD with cursor pagination.
2. RLS blocks cross-tenant reads (test with two tenants).

### Implementation

1A. Migration uses `tenant_id uuid not null` on every table and `create policy tenant_isolation on <table> using (tenant_id = current_setting('app.tenant_id')::uuid)`.
1B. Inventory list supports facets (`decision`, `site_id`, `owner`, `document_class`, `priority`, `source_flags`) and sort by `priority, page_count desc`.

---

## Spec 2 — Crawler service

### Problem

No crawler. Target: a Fargate task under `services/crawler/` that discovers PDFs from a base URL or sitemap, probes them, and upserts inventory rows.

### Files to touch

| File                                                                                                                            | Action                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `services/crawler/__init__.py`, `main.py`, `frontier.py`, `fetcher.py`, `extract.py`, `canonical.py`, `pdf_probe.py`, `sink.py` | Create                                                                                                    |
| `services/crawler/tests/fixtures/site/**`                                                                                       | Create: a 200-page fixture site with 50 PDFs (orphans, duplicates, query-string PDFs, encrypted, scanned) |
| `services/crawler/tests/test_crawl_fixture_site.py`                                                                             | Create: serves the fixture with a local HTTP server and asserts counts                                    |
| `services/crawler/Dockerfile`, `requirements.txt`                                                                               | Create (httpx, selectolax or lxml, pikepdf, boto3, psycopg)                                               |
| `infra/terraform/ecs.tf`                                                                                                        | Add the `crawler` task definition and role (created in the pipeline spec's Spec 3)                        |
| `infra/terraform/dynamodb.tf`                                                                                                   | Add `crawl_frontier` (pk `crawl_id`, sk `url_hash`, TTL)                                                  |
| `services/api/app/services/crawls.py`                                                                                           | Create: `start_crawl` runs the task via `ecs:RunTask` with env `CRAWL_ID`, `SITE_ID`, `TENANT_ID`         |

### Acceptance criteria

1. The fixture site yields exactly 50 unique inventory rows, 3 marked orphaned, duplicates merged by SHA-256, and no row for the external-host PDF except a `source_flags = ['external']` entry.
2. `robots.txt` disallow paths are never fetched; the user agent is `MakePDFAccessibleBot/1.0 (+https://makepdfaccessible.com/bot)`; the rate stays at or under 4 rps per host in the test.
3. A crawl can be cancelled by setting `crawls.status = cancelled`, checked between batches.

### Implementation

2A. `pdf_probe.py` ports the PHP analyzer's checks (trailer/catalog parse, `/StructTreeRoot`, fonts as text-layer proxy, `/Count`, `/Title`, `/Lang`, `/FT`, `/Encrypt`, `pdfuaid:part`) using pikepdf, with `Range` requests for the first 1 MB and the last 64 KB before falling back to a full fetch; parity tests reuse the cases in `integrations/wordpress/tests/pdf-inventory-test.php`.
2B. `canonical.py` normalizes scheme, host case, default ports, trailing slashes on directories, and strips `utm_*`, `fbclid`, `gclid`.

---

## Spec 3 — Triage rules engine

### Problem

No classification. Target: a versioned rules engine that writes `triage_decisions` with rule ids and rationales, using features from the inventory row and an optional Bedrock document-type classification.

### Files to touch

| File                                                                                                | Action                                                                                                  |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `services/triage/__init__.py`, `rules.py`, `features.py`, `classify.py`, `cost.py`, `rules/v1.yaml` | Create                                                                                                  |
| `services/triage/tests/test_rules.py`                                                               | Create: one test per rule with feature fixtures                                                         |
| `services/functions/triage/main.py`, `Dockerfile`, `requirements.txt`                               | Create: Lambda triggered by `inventory.item_upserted` events (EventBridge) and by `POST /v1/triage/run` |
| `infra/terraform/processing-lambdas.tf`                                                             | Add `triage` to `local.lambda_functions` with Bedrock permission for `BEDROCK_MODEL_CLASSIFY`           |
| `services/api/app/routes/triage.py`                                                                 | `POST /v1/triage/run` enqueues per-item events                                                          |

### Acceptance criteria

1. Every rule in the PRD table has a passing test; rule order is deterministic; the first matching decision rule wins and priority rules only adjust `priority`.
2. `classify.py` returns one of the fixed labels or `unknown` and never a decision; a Bedrock failure degrades to `unknown` and the rules still run.
3. `estimated_cost_cents` uses the price list in `services/triage/cost.py` (kept in sync with `docs/business/BUSINESS-PLAN.md` §5 by a unit test that reads both).

### Implementation

3A. `rules/v1.yaml` entries: `id`, `when` (a small expression language over features: `views_90d == 0 and inbound_page_count == 0`), `decision`, `priority`, `rationale`, `citation`.
3B. `features.py` assembles features from the row, links, analytics and classification; unknown features evaluate to `null` and rules must handle `null` explicitly.

---

## Spec 4 — Dashboard views: Inventory, Triage, Plan

### Problem

The dashboard has no inventory screens. Target: three routes with facets, overrides and exports.

### Files to touch

| File                                                                                       | Action                                                                                  |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `dashboard/src/app/(dashboard)/inventory/page.tsx`, `dashboard/src/components/inventory/*` | Create: data table (virtualized), facets, bulk override dialog, row drawer              |
| `dashboard/src/app/(dashboard)/triage/page.tsx`, `dashboard/src/components/triage/*`       | Create: totals by decision, cost by path, what-if toggles                               |
| `dashboard/src/app/(dashboard)/plan/page.tsx`                                              | Create: export buttons (CSV, PDF), share link                                           |
| `dashboard/src/lib/api.ts`                                                                 | Add inventory, sites, triage clients                                                    |
| `dashboard/src/hooks/useFilterPersistence.ts`                                              | Reuse for facet state                                                                   |
| `dashboard/src/components/layout/*`                                                        | Add navigation entries                                                                  |
| `services/api/app/routes/inventory.py`                                                     | Add `plan.csv` and `plan.pdf` (PDF via the HTML-first exporter, validated with veraPDF) |

### Acceptance criteria

1. The Inventory table handles 100,000 rows with server-side pagination and keeps keyboard operability (axe clean; roving tabindex in the grid).
2. Override writes a new decision row and the drawer shows the history.
3. `plan.pdf` passes veraPDF PDF/UA-1.

---

## Spec 5 — WordPress sync, scanner imports and analytics imports

### Problem

The plugin's inventory stays local; scanner and analytics data cannot be attached. Target: the sync endpoint used by the plugin, CSV mappers, and analytics matching.

### Files to touch

| File                                                                               | Action                                                                                                    |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `integrations/wordpress/includes/class-make-pdf-accessible-inventory.php`          | Add `sync_batch()` posting to `POST /v1/inventory/sync` after each scan batch when a connector key is set |
| `integrations/wordpress/make-pdf-accessible.php`                                   | Settings: connector key, sync toggle                                                                      |
| `services/api/app/routes/inventory.py`                                             | `POST /v1/inventory/sync` (connector key auth), `POST /v1/inventory/imports`                              |
| `services/api/app/services/imports/{siteimprove,dubbot,popetech,ga4,serverlog}.py` | Create: column mappers                                                                                    |
| `services/api/tests/test_imports.py`                                               | Create with sample CSVs under `services/api/tests/fixtures/imports/`                                      |
| `integrations/wordpress/tests/e2e/specs/inventory.spec.mjs`                        | Add a sync assertion against a mocked API                                                                 |

### Acceptance criteria

1. A plugin scan of the Playground fixture site produces matching rows in the tenant's inventory with `source_flags` containing `wordpress` and attachment ids in `document_locations`.
2. Importing each vendor's sample CSV adds or updates rows without duplicates and stores `external_issue_count`.
3. A GA4 export attaches `views_90d` to matching URLs and triggers re-triage for those rows only.

---

## Spec 6 — Scheduled re-crawls, drift and webhooks

### Problem

Nothing runs again. Target: schedules per site, drift detection and events.

### Files to touch

| File                                               | Action                                                                                                                            |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/eventbridge.tf`                   | Create: `mpa-pipeline` bus (shared with the pipeline), scheduler role, per-site schedules created via API (EventBridge Scheduler) |
| `services/api/app/services/schedules.py`           | Create: create/update/delete schedules when `sites.schedule` changes                                                              |
| `services/crawler/sink.py`                         | Compute `pdfs_new`, `pdfs_changed`, `pdfs_removed` versus the previous crawl; emit `inventory.drift`                              |
| `services/api/app/routes/webhooks.py`              | Add `inventory.drift`, `inventory.new_document` to the event catalogue                                                            |
| `dashboard/src/app/(dashboard)/inventory/page.tsx` | Drift banner                                                                                                                      |

### Acceptance criteria

1. Changing one PDF on the fixture site between two crawls yields `pdfs_changed = 1`, a re-triage of that row only, and one `inventory.drift` webhook delivery.

---

## Spec 7 — Free website report (marketing)

### Problem

The marketing site's free report needs a capped, public, abuse-resistant endpoint. Target: `POST /v1/public/site-report`.

### Files to touch

| File                                       | Action                                                                                                                                                                                               |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/routes/public.py`        | Create: `site-report`, `leads`, `pdf-check` (presign, submit, status)                                                                                                                                |
| `services/api/app/main.py`                 | Mount `public.router` under `/v1`; add `/v1/public` to the API-key middleware `excluded_paths`                                                                                                       |
| `services/api/app/services/site_report.py` | Create: starts a crawl for a system tenant `public-reports` with caps `SITE_REPORT_MAX_PDFS`, `SITE_REPORT_MAX_MINUTES`; renders the report; sends e-mail (SES); posts the lead to `CRM_WEBHOOK_URL` |
| `services/api/app/security.py`             | Add per-IP and per-e-mail rate limits for public routes and CAPTCHA verification                                                                                                                     |
| `infra/terraform/ses.tf`                   | Create: SES identity for `reports@makepdfaccessible.com`, DKIM outputs for DNSimple                                                                                                                  |
| `infra/terraform/api_gateway.tf`           | Throttle `/v1/public/*`                                                                                                                                                                              |

### Acceptance criteria

1. A request with a valid CAPTCHA token and a new domain returns 202; the same domain within 24 hours returns 429 with a friendly body.
2. The e-mailed report renders as an accessible HTML e-mail and an attached tagged PDF; only metadata is retained after the report is sent (verified by an S3 listing test).

---

## Suggested execution order

1. Spec 1 first — the schema and API are prerequisites for everything else, and the WordPress sync (Spec 5) can start as soon as it exists.
2. Spec 2 — the crawler is the largest piece and the one pilots feel first.
3. Spec 3 — rules turn a list into a plan; it only needs Spec 1 data and can be built in parallel with Spec 2 against fixture rows.
4. Spec 4 — the dashboard views follow the API; build the Inventory table while Spec 2 stabilizes.
5. Spec 5 — connectors and imports; independent of Spec 4, dependent on Spec 1.
6. Spec 7 — the free report reuses Specs 2 and 3 with caps; it is the marketing site's M2 dependency.
7. Spec 6 last — schedules and drift need at least two crawls to be meaningful.

Net effect: a tenant can register a site or connect WordPress, get a complete, triaged inventory with a priced plan, export it, keep it current on a schedule, and the marketing site can offer the same capability capped as a free report.

# Make PDF Accessible — Integrations

## Publish accessible results back where users find them: WordPress, Drupal, the LMS, the API, and any URL through the Accessible Link.

**Status:** Draft v1.0 (2026-09-28)
**Parent:** `docs/PLATFORM-PRD.md` (stages Publish, Maintain)
**Implements ADRs:** ADR-0001 (Accessible Link cache), ADR-0007 (Cognito identity; connector keys), ADR-0008 (tenant isolation for connector credentials)

---

## CONTEXT

Today's integrations are a WordPress plugin (`integrations/wordpress/`) with a real local inventory and Markdown-for-AI feature but a broken processing path (posts to `/v1/documents/client/upload` while the API mounts `/v1/client/upload`; never saves the returned document id; does not verify webhook signatures, per its README), a generic JavaScript snippet (`integrations/html-snippets/accesspdf-integration.js`) that references disabled public endpoints, an API `client` router (`services/api/app/routes/client.py`: upload, status, webhook notify) and `registration` router (`services/api/app/routes/registration.py`: domain-based integration registration), and HMAC-signed outbound webhooks (`services/api/app/routes/webhooks.py`). LTI exists only in documentation. Nothing publishes a result back into a CMS.

The motivating gaps:

1. **No publish-back.** A fixed file or an HTML page never replaces the original where users click.
2. **The WordPress processing path is broken** (wrong route, no id persistence, no signature check).
3. **No Drupal, no LMS.** Higher education runs on WordPress, Drupal, Canvas, Blackboard, D2L and Moodle.
4. **No on-demand URL entry point.** ITHAKA's model (remediate on first request, cache thereafter) needs a link any site can use.
5. **The API is document-centric and partly unversioned** (legacy unprefixed routers still mounted in `services/api/app/main.py`).

### Locked Scope Decisions

1. **Connectors are outbound-only from the customer's system to our API**, authenticated with scoped connector keys; we never require inbound firewall rules or admin credentials to a CMS beyond what the plugin itself holds.
2. **Publish-back always keeps the original** as an optional download and writes a 301 from the old URL to the new page (HTML path) or replaces the file in place with the tagged version (PDF path), recording a `publications` row either way.
3. **WordPress first, Drupal second, LTI 1.3 third.** Same API, three thin clients.
4. **LTI 1.3 with LTI Advantage (Deep Linking, Names and Roles, Assignment and Grade Services not required)**; certified against Canvas, Blackboard, D2L and Moodle in that order.
5. **The public API is versioned under `/v1` only**; the legacy unprefixed routers are removed after a deprecation window; `openapi.yaml` is generated from the app and committed.
6. **Webhooks are HMAC-SHA256 signed with a per-endpoint secret, include a timestamp, and are retried with backoff for 24 hours**; a signature verification snippet ships in each plugin.
7. **Accessible Link is a product surface**, not a demo: custom domain support (`a11y.example.edu` CNAME to CloudFront), analytics on usage, and a "preparing" page that is itself accessible.

### What This Is NOT

- Not an LMS accessibility checker or instructor dashboard (Ally, Panorama, UDOIT own that seat).
- Not a SharePoint, Google Drive or Box connector in this scope (open question below).
- Not the old "LLM discovery" snippet; `integrations/html-snippets/` is deprecated and removed from the product surface.
- Not a Zapier-style automation platform; webhooks and the API are the extension points.

---

## SUCCESS CRITERIA

1. From the WordPress media library, choosing "Make accessible" on a PDF creates a job through `POST /v1/jobs`, stores the returned `document_id` and `job_id` on the attachment, and on the `job.completed` webhook (signature verified) either replaces the attachment file with the tagged PDF (PDF path) or creates a draft page from the HTML artifact with the original PDF linked (HTML path), with the attachment's inventory row updated to `status = remediated`.
2. Publishing the draft page adds a 301 redirect from the original PDF URL to the page, recorded in `publications`, and the plugin's redirect is verified by an HTTP check from our side within 5 minutes.
3. The Drupal module does the same for media entities, with the redirect written through the Redirect module's API when present.
4. Installing the LTI 1.3 tool in Canvas lets an instructor open "Accessible files" for a course, see the course's PDFs with inventory status, request remediation, and get the accessible version linked back into the course files or module item; the tool passes the IMS certification suite for Core and Deep Linking.
5. `POST /v1/jobs`, `GET /v1/jobs/{id}`, `GET /v1/documents/{id}`, evidence and webhook endpoints are documented in a generated `openapi.yaml`, and an API key created in the dashboard with scope `jobs:write` can run the full flow from `curl` without a session.
6. A webhook endpoint that returns 5xx receives retries with exponential backoff for 24 hours, and the dashboard shows delivery attempts and lets an admin replay.
7. An Accessible Link `https://a11y.example.edu/d/{hash}` for an inventoried PDF returns the cached tagged PDF (or HTML if the profile is `html_first`) with a 302 to a 15-minute signed URL when the artifact exists, or a 202 "preparing" page that auto-refreshes and is screen-reader friendly when it does not; the custom domain is served by CloudFront with the tenant's certificate.
8. Scanner imports (Siteimprove, DubBot, Pope Tech) and analytics imports from the Inventory PRD are reachable from the dashboard and the API.
9. The legacy unprefixed routers in `services/api/app/main.py` are removed and every client in the repo (dashboard, web, WordPress, Drupal, LTI) uses `/v1`.

---

## DATA MODEL CHANGES

### New table — `connectors`

```
connectors
  - id: uuid [pk]
  - tenant_id, site_id [fk]
  - kind: enum(wordpress, drupal, lti, api)
  - external_id: text                              // site URL, platform issuer, deployment id
  - key_id: uuid [fk api_keys]                     // scoped connector key
  - config: jsonb                                  // publish policy: replace_pdf | draft_html | auto_publish, redirect: bool
  - status: enum(active, revoked), created_at, last_seen_at
```

### New table — `publications`

```
publications
  - id: uuid [pk]
  - tenant_id, document_id, job_id, connector_id [fk]
  - kind: enum(replace_pdf, html_page, lms_file, lms_module_item)
  - target_ref: text                               // attachment id, node id, file id
  - target_url, redirect_from_url: text
  - published_by: uuid, published_at
  - verified_at: timestamptz [nullable]            // our HTTP check
```

### New table — `webhook_endpoints`, `webhook_deliveries`

```
webhook_endpoints: id, tenant_id, url, secret_ref, events: text[], active
webhook_deliveries: id, endpoint_id, event, payload_sha256, attempts, last_status, next_attempt_at, delivered_at
```

### New table — `lti_platforms`, `lti_deployments`, `lti_contexts`

```
lti_platforms: id, tenant_id, issuer, client_id, auth_login_url, auth_token_url, jwks_url
lti_deployments: id, platform_id, deployment_id
lti_contexts: id, deployment_id, context_id (course), title, site_id
```

---

## FEATURE 1 — WORDPRESS PLUGIN v2

- Fix the processing path (`/v1/jobs`), persist ids on the attachment, verify webhook signatures (`X-MPA-Signature: t=..., v1=...`).
- Settings: connector key, publish policy (replace PDF in place; create draft page; auto-publish page), redirect on/off, profile default per site.
- Media library actions: single and bulk "Make accessible"; status column from inventory; "View evidence" link.
- Inventory sync (from the Inventory PRD) and publish-back: page created from the HTML artifact with a block template (title, original download link, content); redirect via the plugin's own rewrite rule or Redirection plugin API when present.
- WordPress.org release pipeline already exists (`.github/workflows/wordpress-plugin-release.yml`); keep it.

## FEATURE 2 — DRUPAL MODULE

- Composer-installable module `mpa_accessible_docs` for Drupal 10/11: media entity action, queue worker for sync, publish-back as a node of a configurable content type, Redirect module integration, Key module for the connector key.

## FEATURE 3 — LTI 1.3 TOOL

- Service `services/lti/` (FastAPI, `pylti1p3`): OIDC login, launch, Deep Linking to insert an accessible file link, Names and Roles to scope who may request remediation (instructors, designers).
- Course file listing through the platform's file API where available (Canvas), or Deep Linking only.
- Data: `lti_*` tables; FERPA note: we store course ids and titles, never rosters or grades.

## FEATURE 4 — PUBLIC API AND WEBHOOKS

- Routers: `jobs`, `documents`, `evidence`, `inventory`, `review`, `webhooks`, `links`; legacy routers removed.
- API keys (existing `services/api/app/routes/api_keys.py`) gain scopes: `jobs:read`, `jobs:write`, `documents:read`, `evidence:read`, `inventory:read`, `inventory:write`, `triage:write`, `review:read`, `review:write`, `webhooks:manage`, `connector`.
- Webhook events: `job.completed`, `job.failed`, `document.verified`, `inventory.drift`, `inventory.new_document`, `publication.verified`.
- `openapi.yaml` regenerated in CI from the FastAPI app (`services/api/app/main.py`); a drift check fails the build if the committed file differs.

## FEATURE 5 — ACCESSIBLE LINK

- Per-tenant slug and optional custom domain; CloudFront distribution with a Lambda@Edge or CloudFront Function that forwards to `GET /v1/links/{tenant}/{hash}`.
- Cache policy: artifact objects served with `Cache-Control: private, max-age=900` via signed URLs; the link resolver checks origin freshness at most once per hour.
- Usage analytics: hits, first-request remediations, cache hit rate per tenant, surfaced in Reports.

---

## API ROUTES (additions beyond the pipeline PRD)

| Method   | Path                                                       | Auth                     | Purpose                                |
| -------- | ---------------------------------------------------------- | ------------------------ | -------------------------------------- |
| POST     | `/v1/connectors`                                           | `owner`/`admin`          | Register a connector and issue its key |
| POST     | `/v1/publications`                                         | connector key            | Record a publish-back                  |
| POST     | `/v1/publications/{id}/verify`                             | connector key or `admin` | Trigger redirect verification          |
| POST     | `/v1/webhooks/endpoints`                                   | `webhooks:manage`        | Register endpoint                      |
| GET      | `/v1/webhooks/deliveries`                                  | `webhooks:manage`        | Delivery log; `POST .../{id}/replay`   |
| GET/POST | `/lti/login`, `/lti/launch`, `/lti/deep-link`, `/lti/jwks` | LTI                      | LTI 1.3 flows                          |
| GET      | `/v1/links/{tenant}/{hash}`                                | public                   | Accessible Link                        |

## ENVIRONMENT VARIABLES

| Var                                 | Purpose                                                                       | Example (placeholder)               |
| ----------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------- |
| `WEBHOOK_SECRET_KEY`                | Existing default signing key (per-endpoint secrets stored in Secrets Manager) | from SSM                            |
| `LTI_TOOL_PRIVATE_KEY_ARN`          | Tool JWKS private key                                                         | `arn:aws:secretsmanager:...`        |
| `LTI_TOOL_PUBLIC_URL`               | Tool base URL                                                                 | `https://lti.makepdfaccessible.com` |
| `ACCESSIBLE_LINK_BASE_DOMAIN`       | Default link host                                                             | `a11y.makepdfaccessible.com`        |
| `ACCESSIBLE_LINK_SIGNED_URL_TTL`    | Seconds                                                                       | `900`                               |
| `MPA_API_BASE_URL` (plugin setting) | API base for plugins                                                          | `https://api.makepdfaccessible.com` |

## TESTING STRATEGY

- WordPress: extend the Playground e2e suite (`integrations/wordpress/tests/e2e/specs/`) with job creation against a mock API, webhook signature verification, publish-back and redirect assertions.
- Drupal: DDEV-based functional tests in CI.
- LTI: IMS certification suite in staging; contract tests with recorded Canvas launches.
- API: contract tests from the generated `openapi.yaml` (Schemathesis); webhook retry tests with a failing receiver.
- Accessible Link: e2e for cache miss → preparing page → cache hit; axe on the preparing page.

## MILESTONES / ROLLOUT PLAN

| Slice                | Scope                                                                   | Value delivered alone                      |
| -------------------- | ----------------------------------------------------------------------- | ------------------------------------------ |
| G1 — API v1 clean-up | Scoped keys, generated OpenAPI, legacy routers removed, webhook retries | Integrators can build                      |
| G2 — WordPress v2    | Fixed processing, publish-back, redirects                               | Largest CMS in higher ed served end to end |
| G3 — Accessible Link | Resolver, custom domain, analytics                                      | Any site can adopt without a plugin        |
| G4 — Drupal          | Module with publish-back                                                | Second CMS                                 |
| G5 — LTI 1.3         | Canvas first, then Blackboard, D2L, Moodle                              | Course content                             |

## OPEN QUESTIONS

1. **SharePoint/OneDrive and Google Drive connectors.** Frequent in K-12 and local government; decide after the first three pilots report where their documents live.
2. **Should the WordPress plugin bundle the free tier processing (5 docs/month) to drive adoption?** Decide with pricing before G2 ships.
3. **Canvas file API access requires a developer key per institution**; is Deep Linking-only acceptable for the first LMS release?

## RISKS

- **CMS plugin review delays** (WordPress.org, Drupal.org). Mitigation: distribute directly from the dashboard as well.
- **LTI certification time.** Mitigation: start with Canvas only; certify others as customers demand.

---

## SOURCES & RELATED DOCS

- `docs/PLATFORM-PRD.md` — parent
- `docs/REMEDIATION-PIPELINE-PRD.md` — job and evidence APIs the connectors call
- `docs/INVENTORY-TRIAGE-PRD.md` — sync and import endpoints
- `integrations/wordpress/README.md` — current plugin behavior and known issues
- `docs/LLM_INTEGRATION.md` — deprecated discovery approach (retained for history)

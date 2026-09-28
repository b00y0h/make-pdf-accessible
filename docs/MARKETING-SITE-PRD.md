# Make PDF Accessible — Marketing Site

## A fast, accessible, static site at makepdfaccessible.com that turns the Title II deadline into pilots: free website report, free PDF check, published prices, and a trust center.

**Status:** Draft v1.0 (2026-09-28)
**Parent:** `docs/PLATFORM-PRD.md` (stage Acquire); `docs/business/BUSINESS-PLAN.md` §7 (go-to-market)
**Implements ADRs:** ADR-0009 (static Next.js export on S3 + CloudFront), ADR-0010 (multi-account environments)

---

## CONTEXT

There is no marketing site. `web/` is a Next.js "public web app" whose home page (`web/app/page.tsx`) is a hero plus an upload widget ("Make Your PDFs Instantly Accessible", "see the magic happen"), backed by the demo endpoints. Terraform already reserves `makepdfaccessible.com` and `www` for a marketing distribution (`infra/terraform/domains.tf`) but points it at the same S3 bucket as the web app, and a DNSimple runbook (`infra/terraform/DNSIMPLE_SETUP.md`) describes the records. The dashboard lives at `dashboard.makepdfaccessible.com` and the API at `api.makepdfaccessible.com`.

Buyers are digital accessibility officers, CIOs, web teams and counsel at institutions with a fixed deadline and a backlog they cannot size. They search for "PDF remediation", "Title II PDF", "WCAG 2.1 PDF deadline", "PDF accessibility cost per page". They need to know, in this order: does this do the whole job, what does it cost, can we trust it (evidence, security, accessibility of the product itself), and can we try it now.

The motivating gaps:

1. **No site.** The only public surface is a demo whose claims the pipeline cannot back.
2. **No lead capture.** No free website report, no pilot request, no pricing page.
3. **No trust center.** No ACR, security page, accessibility statement or accuracy report.
4. **No deployment path on AWS** for a content site: the existing web-ci workflow discovers buckets by name and assumes a Next.js standalone build.

### Locked Scope Decisions

1. **Static export of a Next.js app (`output: 'export'`) deployed to S3 behind CloudFront**, in its own bucket and distribution, in the same Terraform root as the platform (module `infra/terraform/modules/static-site`). No server runtime for the site itself. (ADR-0009)
2. **Separate app `apps/marketing` in the pnpm workspace**, not a rewrite of `web/`. `web/` is retired once the marketing site and the dashboard cover its functions.
3. **Forms post to the platform API** (`POST /v1/public/site-report`, `POST /v1/public/leads`, `POST /v1/public/pdf-check`), not to a third-party form service; the API forwards leads to the CRM.
4. **Content lives in the repo as MDX** for v1; a headless CMS is an open question, not a requirement.
5. **WCAG 2.2 AA is a release gate**: automated axe checks on every page in CI, manual audit before launch, ACR published on the site. A site that sells accessibility must be accessible.
6. **Every price is on the pricing page.** No "contact us for pricing" except the System tier's negotiated floor.
7. **No "automatic compliance" language.** Copy is reviewed against a banned-phrase list in CI.
8. **Privacy-respecting analytics** (server-side or cookieless), no third-party ad pixels, no cookie banner needed for the default configuration.

### What This Is NOT

- Not the application. No login, no dashboard, no document processing UI beyond the two capped free tools.
- Not a blog platform with comments or a community forum.
- Not a documentation site for the API (that is generated from `openapi.yaml` and hosted at `docs.makepdfaccessible.com` later; v1 links to it).
- Not localized; English only in v1, with `lang` set and the structure ready for translation.
- Not a place for customer logos or testimonials we do not have; placeholders are forbidden in production.

---

## SUCCESS CRITERIA

1. `https://makepdfaccessible.com` and `https://www.makepdfaccessible.com` (301 to the apex) serve the site from CloudFront with an ACM certificate, HTTP/2 and HTTP/3, Brotli or gzip, security headers (HSTS with preload, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) and a WAF; the S3 bucket is private with Origin Access Control.
2. Every page scores ≥ 95 on Lighthouse Performance, Accessibility, Best Practices and SEO on mobile, and Core Web Vitals in the field meet LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1.
3. Every page passes axe-core with zero violations in CI, is fully keyboard operable with visible focus, respects `prefers-reduced-motion` and `prefers-color-scheme`, has a skip link, landmarks, one `h1`, descriptive titles, and 4.5:1 text contrast; a manual audit against WCAG 2.2 AA is recorded and the ACR is published at `/accessibility`.
4. The free website report form (domain + email + consent) submits to the API, shows an accessible confirmation, and the visitor receives the report email within 2 hours; the lead appears in the CRM with source `site-report`.
5. The free PDF check (one PDF up to 25 MB, 5 per day per IP) uploads directly to S3 through a presigned URL from the API, returns within 60 seconds a summary (tagged, text layer, title, language, page count, form, PDF/UA claim, estimated cost by path) and offers the report by email; it never claims the file is or is not compliant.
6. The pricing page shows Free, Team ($6,000/year), Campus ($30,000/year), System (from $100,000/year), the Verified add-on ($2.50 to $8 per page), and the Inventory & Triage engagement ($2,500 per domain), with a page calculator and an FAQ, matching `docs/business/BUSINESS-PLAN.md` §5.
7. The trust center (`/trust`) links the accessibility statement and ACR, security overview, subprocessors, privacy policy, terms, SLA, and a status page link; the SOC 2 and HECVAT status is stated honestly (in progress with a date until complete).
8. The site builds and deploys from GitHub Actions on merge to `main` through the OIDC role, syncs to S3 with correct cache headers (immutable for hashed assets, short for HTML), invalidates CloudFront, and posts the deployed URL; a preview build runs on pull requests.
9. Structured data (Organization, Product, FAQPage, Article) validates; `sitemap.xml`, `robots.txt`, canonical URLs, Open Graph and Twitter cards exist; the "Title II countdown" and state guides are indexable.
10. A banned-phrase check in CI fails the build if copy contains "automatic compliance", "guaranteed compliant", "100% compliant", "ADA compliant PDF" (as a product claim) or "overlay".
11. The `/bot` page documents the crawler's user agent and how to allow or block it.

---

## INFORMATION ARCHITECTURE

```
/                       Home: the loop in one screen, free website report CTA, deadline countdown, how it works, evidence pack sample, prices teaser, trust strip
/product                The six stages with screenshots; Accessible Link; connectors
/product/inventory      Inventory & triage
/product/remediation    Pipeline, engines, validation, evidence pack
/product/integrations   WordPress, Drupal, LTI, API
/pricing                Published prices, calculator, FAQ, cooperative contracts
/solutions/higher-ed    Title II + 504 for universities and colleges
/solutions/k12          School districts
/solutions/government   Cities, counties, special districts
/free-report            Free website inventory report (form)
/check                  Free single-PDF check (upload)
/evidence               What an evidence pack contains, with a real sample
/accuracy               Published accuracy by document class (from the eval set), updated monthly
/resources              Guides: Title II deadline explainer, exceptions and archiving, HTML-first policy template, state laws (CO, TX, IL, CA), procurement checklist, RFP language
/resources/title-ii-countdown
/customers              Case studies (only when real)
/trust                  Trust center hub
/accessibility          Accessibility statement + ACR download
/security               Security overview, HECVAT/SOC 2 status, subprocessors
/legal/privacy, /legal/terms, /legal/sla, /legal/dpa
/about                  Team, mission, contact
/contact, /pilot        Pilot request form
/bot                    Crawler documentation
/docs -> docs.makepdfaccessible.com (external, later)
/app  -> dashboard.makepdfaccessible.com (external)
```

---

## FEATURE 1 — CONTENT AND MESSAGING

- Positioning line: "Every document on your site, made accessible, with proof."
- Home page sections, in order: headline + free report CTA; the deadline (April 26, 2027 / 2028 with a live countdown, no autoplaying motion); the six-stage loop with one sentence each; "What you get" (accessible PDF or HTML, published back, evidence pack); "Why not just tag" (commodity tagging vs the whole job, honest about engines used); pricing teaser; trust strip (ACR, security, no automatic-compliance claims); pilot CTA.
- Tone: plain, specific, numbers with sources; no exclamation marks; no "magic".
- Copy guardrails: banned phrases list in `apps/marketing/content/banned-phrases.json`; every claim about accuracy links to `/accuracy`.

## FEATURE 2 — FREE WEBSITE REPORT

- Form fields: institution website (URL), work email, institution type (select), consent checkbox, honeypot, optional Turnstile or similar CAPTCHA with an accessible fallback.
- Client posts JSON to `POST {NEXT_PUBLIC_API_BASE_URL}/v1/public/site-report`; on 202 shows "We're crawling. You'll get an email within two hours"; on 429 shows the daily cap message; on error shows a retry with the same data kept.
- Server side (Inventory PRD Feature 6) runs the capped crawl, emails the report and creates the CRM lead.

## FEATURE 3 — FREE PDF CHECK

- Drag-and-drop or file input (keyboard accessible), 25 MB cap, PDF only.
- Flow: `POST /v1/public/pdf-check/presign` → PUT to S3 → `POST /v1/public/pdf-check` → poll `GET /v1/public/pdf-check/{id}` → results table; optional email capture for the PDF report.
- Results copy explains what each check means and what it does not prove.

## FEATURE 4 — PRICING PAGE

- Plan cards, comparison table, page calculator (pages × path → estimate vs manual benchmark), Verified add-on explainer, cooperative contracts section, FAQ (overage, rollover, nonprofit, multi-year, pilots credited).

## FEATURE 5 — TRUST CENTER

- Hub with cards; ACR as a downloadable tagged PDF (validated with veraPDF in CI); security overview; subprocessors table; status page link; incident contact; responsible disclosure policy.

## FEATURE 6 — RESOURCES

- MDX articles with a consistent template (summary, last updated, sources); Title II countdown page; downloadable RFP language and HTML-first policy template as tagged PDFs and DOCX.

---

## TECHNICAL DESIGN

- **App:** `apps/marketing` (Next.js 15, React 19, TypeScript, Tailwind CSS 3.4, `output: 'export'`, `trailingSlash: true` so S3 keys map to `index.html`, `images.unoptimized: true`). MDX via `@next/mdx` in a later slice; v1 pages are TSX with content constants.
- **Design system:** tokens in `apps/marketing/src/styles/tokens.css` (color, type scale, spacing, motion), dark mode via `prefers-color-scheme`, focus ring token, minimum 44×44 px targets, system font stack (no third-party font requests) with an optional self-hosted variable font.
- **Infrastructure:** `infra/terraform/modules/static-site` creates the private S3 bucket (SSE-S3, versioning, OAC-only bucket policy), CloudFront distribution (HTTP/3, TLS 1.2_2021, compression, response headers policy with CSP/HSTS, CloudFront Function that rewrites `/path` → `/path/index.html` and redirects `www` → apex, WAF association, standard logging to the existing logs bucket), and outputs bucket name and distribution id. `infra/terraform/marketing.tf` instantiates it with the existing ACM certificate from `domains.tf`.
- **DNS:** DNSimple (existing runbook): ALIAS apex → distribution, CNAME `www` → distribution.
- **CI/CD:** `.github/workflows/marketing-site.yml`: lint, typecheck, build, axe over every exported page (Playwright + `@axe-core/playwright` against a local static server), banned-phrase check, Lighthouse CI budgets; on `main`, assume `GITHUB_WEB_DEPLOY_ROLE_ARN` via OIDC, `aws s3 sync` with cache headers, CloudFront invalidation of `/*`, deployment summary.
- **Environments:** `staging.makepdfaccessible.com` (staging account) and production; preview builds as artifacts on pull requests.
- **Analytics:** CloudFront standard logs to the logs bucket plus a cookieless analytics script (self-hosted or a privacy-focused vendor) loaded only after consent-free evaluation; no PII in analytics.
- **Forms security:** rate limits in the API, honeypot, CAPTCHA with accessible alternative, CSP `connect-src` limited to the API host.

## ENVIRONMENT VARIABLES

| Var                                                  | Purpose                              | Example (placeholder)                              |
| ---------------------------------------------------- | ------------------------------------ | -------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`                           | Platform API for forms and PDF check | `https://api.makepdfaccessible.com`                |
| `NEXT_PUBLIC_APP_URL`                                | Dashboard link                       | `https://dashboard.makepdfaccessible.com`          |
| `NEXT_PUBLIC_SITE_URL`                               | Canonical base for sitemap and OG    | `https://makepdfaccessible.com`                    |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY`                     | CAPTCHA site key (public)            | `0x...`                                            |
| `NEXT_PUBLIC_ANALYTICS_ENDPOINT`                     | Cookieless analytics collector       | `https://...`                                      |
| `MARKETING_S3_BUCKET` (CI variable)                  | Deploy target                        | Terraform output `marketing_site_bucket`           |
| `MARKETING_CLOUDFRONT_DISTRIBUTION_ID` (CI variable) | Invalidation target                  | Terraform output `marketing_site_distribution_id`  |
| `GITHUB_WEB_DEPLOY_ROLE_ARN` (CI secret)             | OIDC role (exists)                   | `arn:aws:iam::...:role/...-github-web-deploy-role` |

## TESTING STRATEGY

- **Unit:** component tests for forms (validation, error states, keyboard), calculator math, banned-phrase checker.
- **Accessibility:** axe on every exported route in CI; manual screen-reader pass (NVDA + Firefox, VoiceOver + Safari) before launch and each quarter; contrast checks in the token file's tests.
- **Performance:** Lighthouse CI with budgets (JS ≤ 120 KB gzipped on the home page, no render-blocking third-party requests).
- **E2E:** Playwright: home → free report submit (mocked API) → confirmation; PDF check happy path with a fixture PDF; pricing calculator.
- **Infra:** `terraform validate` and `tflint` in `infra-ci.yml`; a post-deploy smoke test hits `/`, `/pricing`, `/free-report` and checks headers.

## MILESTONES / ROLLOUT PLAN

| Slice                               | Scope                                                                                                                                                       | Value delivered alone                             |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| M1 — Foundation (this repo change)  | `apps/marketing` scaffold with home, product, pricing, free-report, check, trust, accessibility pages; design tokens; axe CI; Terraform module and workflow | A deployable, accessible site with the core pages |
| M2 — Lead capture live              | API endpoints for site-report, pdf-check and leads; CRM forwarding; email templates                                                                         | Pipeline of leads                                 |
| M3 — Resources and SEO              | Guides, countdown, state pages, structured data, sitemap                                                                                                    | Organic acquisition                               |
| M4 — Trust center complete          | ACR, security overview, HECVAT status, SLA, DPA                                                                                                             | Procurement-ready                                 |
| M5 — Accuracy page and case studies | Monthly eval publication, first customer stories                                                                                                            | Proof                                             |

## OPEN QUESTIONS

1. **CRM.** HubSpot (free tier is enough to start) vs Pipedrive; decide before M2.
2. **CAPTCHA vendor.** Cloudflare Turnstile has an accessible mode; confirm it works with screen readers in our tests, otherwise fall back to email verification only.
3. **Headless CMS for resources** once non-engineers write content; candidates: Keystatic (git-based), Contentful. Decide at M3.
4. **Staging domain** in the staging account: `staging.makepdfaccessible.com` requires a certificate in that account; confirm DNSimple delegation.

## RISKS

- **Claims drift in marketing copy.** Mitigation: banned-phrase CI check; legal review checklist in the PR template.
- **Free tools abused for bulk processing.** Mitigation: per-IP and per-email caps, CAPTCHA, no bulk endpoints.

---

## SOURCES & RELATED DOCS

- `docs/business/BUSINESS-PLAN.md` — pricing and go-to-market the site expresses
- `docs/INVENTORY-TRIAGE-PRD.md` — free website report backend
- `docs/adr/0009-marketing-site-static-export-on-s3-cloudfront.md`
- `docs/AWS-DEPLOYMENT-SPECS.md` — infrastructure and workflow specs (Specs 3 to 5)
- `infra/terraform/DNSIMPLE_SETUP.md` — DNS runbook

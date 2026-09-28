# ADR-0009: Marketing site as a static Next.js export on S3 and CloudFront, deployed by GitHub Actions through OIDC

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** makepdfaccessible.com marketing site hosting and delivery
- **Related:** `docs/MARKETING-SITE-PRD.md`, `docs/AWS-DEPLOYMENT-SPECS.md`, ADR-0010

## Context

The company wants the whole product, including the front-facing marketing site, on AWS. The existing `web/` app is a Next.js server-rendered application that the web-ci workflow deploys by copying a standalone build into an S3 bucket (which cannot execute it) and discovering the bucket by name. Terraform already reserves a marketing CloudFront distribution but points it at the web app's bucket. The site is content: pages, forms that call the platform API, downloads. It must be fast, accessible, cheap, and deployable by a small team without a server to patch.

Constraints: no server runtime to operate; forms need an API (which exists); preview builds for pull requests; WAF and security headers; the DNS provider is DNSimple.

## Decision

We will build the marketing site as a separate workspace app (`apps/marketing`) with Next.js `output: 'export'` and deploy the exported files to a private S3 bucket served by a CloudFront distribution with Origin Access Control, a CloudFront Function for directory-index rewrites and the `www` redirect, a response headers policy for security headers, and the existing WAF. The bucket and distribution come from a reusable Terraform module (`infra/terraform/modules/static-site`). A GitHub Actions workflow builds, runs accessibility and content checks, syncs to S3 with cache headers and invalidates CloudFront, using the existing OIDC deploy role. Forms call the platform API; there is no server-side code in the site.

## Alternatives Considered

- **AWS Amplify Hosting** — Simple, but a second deployment system with its own build image, less control over CloudFront behaviors and WAF, and preview environments that duplicate what GitHub Actions already does.
- **OpenNext on Lambda@Edge/Lambda** — Enables server rendering and API routes, but adds a runtime, cold starts and cost for a site that needs none of it.
- **Vercel** — Excellent DX, but the requirement is AWS, and it adds a vendor to the compliance program.
- **Reuse `web/` and its workflow** — The app is a demo, not a marketing site, and its deploy path is broken for server-rendered output.

## Consequences

**Positive**

- Near-zero hosting cost, no servers to patch, global caching, security headers and WAF managed as code, previews as artifacts.

**Negative / Trade-offs**

- No server-side rendering or incremental regeneration; dynamic content (accuracy numbers, countdown) is client-rendered or rebuilt on a schedule.
- Next.js static export forbids some features (image optimization, middleware, server actions); MDX content requires a build.

**Neutral / Follow-ups**

- If a headless CMS is adopted, add a scheduled rebuild workflow rather than a server.
- Remove `aws_cloudfront_distribution.marketing` from `domains.tf` in favor of the module (done in `infra/terraform/marketing.tf`).

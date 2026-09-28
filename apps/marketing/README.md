# Marketing site (`apps/marketing`)

The public site for makepdfaccessible.com: a Next.js 16 static export (`output: 'export'`) deployed to a private S3 bucket behind CloudFront by `.github/workflows/marketing-site.yml`. Product requirements: `docs/MARKETING-SITE-PRD.md`; hosting decision: `docs/adr/0009-marketing-site-static-export-on-s3-cloudfront.md`; infrastructure: `infra/terraform/marketing.tf` and `infra/terraform/modules/static-site`.

## Commands

```bash
pnpm --filter mpa-marketing dev          # http://localhost:3002
pnpm --filter mpa-marketing build        # writes out/
pnpm --filter mpa-marketing start        # serves out/ on :3100 (same layout CloudFront sees)
pnpm --filter mpa-marketing lint
pnpm --filter mpa-marketing type-check
pnpm --filter mpa-marketing check:copy   # banned-phrase check (src/ and out/)
pnpm --filter mpa-marketing test:a11y    # axe on every route + 404 + skip link (needs a build)
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to reuse a preinstalled Chromium instead of downloading one.

## Environment

| Variable                   | Purpose                                                  |
| -------------------------- | -------------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | Platform API used by the free report and PDF check forms |
| `NEXT_PUBLIC_APP_URL`      | Dashboard link in the header                             |
| `NEXT_PUBLIC_SITE_URL`     | Canonical base URL for metadata and the sitemap          |

## Rules

- Every route lives in `src/content/routes.ts` (sitemap and accessibility test read it).
- Prices and dates live in `src/content/site.ts` and must match `docs/business/BUSINESS-PLAN.md`.
- Copy must not contain phrases from `src/content/banned-phrases.json`; the build fails otherwise.
- Colors are tokens in `src/app/globals.css` (light and dark); keep 4.5:1 text contrast.

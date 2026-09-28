# static-site module

Private S3 bucket + CloudFront distribution for a Next.js `output: 'export'` site.

- Origin Access Control only; the bucket has no public access and denies non-TLS access.
- A CloudFront Function redirects secondary hosts to the canonical host, rewrites `/path/` to `/path/index.html`, and redirects `/path` to `/path/` (the trailing-slash form Next.js exports).
- A response headers policy sets HSTS (preload), CSP (generated from `api_origin` and the `extra_*` lists, or supplied verbatim), `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` and `Cross-Origin-Opener-Policy`.
- Managed `CachingOptimized` cache policy; set `Cache-Control` on upload (immutable for `_next/static/*`, short for HTML) and the CDN honors it.
- Missing objects return the exported `/404.html` with a real 404 status.

Deploy the exported `out/` directory with `aws s3 sync` and invalidate `/*`; see `.github/workflows/marketing-site.yml`.

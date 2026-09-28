# Make PDF Accessible — AWS Deployment and Marketing Site Implementation Specs

These specs make the Terraform root deployable, add the marketing site on AWS, and set up per-environment delivery. Starting state: `infra/terraform` did not pass `terraform validate` (duplicate resources, undefined locals and data sources, provider-schema errors), a binary `tfplan` and `.bak` files were committed, state was local, and the marketing distribution in `domains.tf` pointed at the web app's bucket. They implement `docs/MARKETING-SITE-PRD.md`, ADR-0009 and ADR-0010, and the environment items of `docs/ENTERPRISE-READINESS-PRD.md`.

Specs 1 to 5 were implemented in the same change that introduced this document; their status is marked. Specs 6 and 7 are follow-ups.

---

## Spec 1 — Make the Terraform root validate

**Status:** Done.

### Problem

`terraform init -backend=false && terraform validate` failed with duplicate `aws_apigatewayv2_domain_name.api` and `aws_apigatewayv2_api_mapping.api` (in `api_gateway.tf` and `domains.tf`), duplicate `locals.lambda_functions` (`ecr.tf` and `processing-lambdas.tf`), a duplicate `step_functions_state_machine_arn` output, references to undefined `local.app_name`, `data.aws_region.current`, `aws_sns_topic.alerts`, `aws_sns_topic.notifications`, `aws_s3_bucket.pdf_accessible` and `aws_sqs_queue.dlq`, an unsupported `performance_insights_enabled` argument on `aws_docdb_cluster_instance`, `tags` on `aws_lambda_layer_version` and `aws_cloudwatch_dashboard`, and inline `lifecycle_policy` blocks inside `aws_ecr_repository`. 18 files were not `terraform fmt` clean.

### Files to touch

| File                                                 | Action                                                                                                    |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `infra/terraform/api_gateway.tf`                     | Delete the optional custom-domain and mapping resources (owned by `domains.tf`)                           |
| `infra/terraform/step_functions.tf`                  | Delete outputs (moved to `outputs.tf`)                                                                    |
| `infra/terraform/outputs.tf`                         | Add `step_functions_state_machine_name`, `s3_bucket_pdf_accessible`                                       |
| `infra/terraform/locals.tf`                          | Add `app_name = var.project_name`                                                                         |
| `infra/terraform/main.tf`                            | Add `data "aws_region" "current"`                                                                         |
| `infra/terraform/ecr.tf`                             | Rename the list local to `service_repositories`; drop `ocr`, `structure`, `router` (owned elsewhere)      |
| `infra/terraform/documentdb.tf`                      | `enable_performance_insights`                                                                             |
| `infra/terraform/lambda-layers.tf`                   | Remove `tags` from layer versions                                                                         |
| `infra/terraform/processing-lambdas.tf`, `router.tf` | Move lifecycle policies to `aws_ecr_lifecycle_policy` resources; fix DLQ reference; remove dashboard tags |
| `infra/terraform/sns.tf`                             | Create: KMS key with CloudWatch grant, `alerts` and `notifications` topics, optional e-mail subscription  |
| `infra/terraform/s3.tf`                              | Add `pdf_accessible` bucket with encryption, versioning, public-access block, lifecycle                   |
| `infra/terraform/variables.tf`                       | Add `alerts_email`                                                                                        |
| all `*.tf`                                           | `terraform fmt -recursive`                                                                                |

### Acceptance criteria

1. `terraform init -backend=false && terraform validate` succeeds with the AWS provider 5.x.
2. `terraform fmt -check -recursive` reports no files.
3. No ECR repository name is declared twice (`ecr.tf` vs `processing-lambdas.tf` vs `router.tf`).

### Implementation

1A. Apply the edits in the table; each is a mechanical change verified by re-running validate until it reports success.
1B. Run `terraform fmt -recursive`.

---

## Spec 2 — Remove committed artifacts and ignore plan files

**Status:** Done.

### Problem

`infra/terraform/tfplan` (a binary plan containing resolved values), `outputs.tf.bak` and `step-functions.tf.bak` were tracked.

### Files to touch

| File                                                                                                | Action                                                               |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `infra/terraform/tfplan`, `infra/terraform/outputs.tf.bak`, `infra/terraform/step-functions.tf.bak` | Delete (git rm)                                                      |
| `.gitignore`                                                                                        | Add `*.tfplan`, `tfplan`, `plan_output.txt`, `infra/terraform/*.zip` |

### Acceptance criteria

1. `git ls-files infra/terraform` contains no `tfplan`, `.bak` or `.zip` entries.

---

## Spec 3 — Environment-aware domains and the static-site module for the marketing site

**Status:** Done.

### Problem

`domains.tf` hard-coded `makepdfaccessible.com` for every environment (CloudFront aliases must be globally unique, so dev and prod could not coexist) and defined a marketing distribution whose origin was the web app's `web_assets` bucket. The PRD requires a private bucket, OAC, security headers, a `www` redirect, real 404s and WAF.

### Files to touch

| File                                                                                                                         | Action                                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/modules/static-site/{versions,variables,main,outputs}.tf`, `functions/viewer-request.js.tftpl`, `README.md` | Create: reusable module                                                                                                               |
| `infra/terraform/marketing.tf`                                                                                               | Create: `module "marketing_site"` and its outputs                                                                                     |
| `infra/terraform/domains.tf`                                                                                                 | Replace the hard-coded locals with environment-aware ones; delete `aws_cloudfront_distribution.marketing`; update `dns_configuration` |
| `infra/terraform/outputs.tf`                                                                                                 | Point `cloudfront_distributions_domains.marketing` and `application_urls` at the module and locals                                    |
| `infra/terraform/variables.tf`                                                                                               | Add `root_domain`, `marketing_extra_connect_src`, `marketing_extra_frame_src`, `marketing_extra_script_src`                           |
| `infra/terraform/github_oidc.tf`                                                                                             | Allow the web-deploy role to write `*-marketing-*` buckets and list buckets/distributions                                             |

### Acceptance criteria

1. In `prod`, aliases are `makepdfaccessible.com` and `www.makepdfaccessible.com`; in `dev`, `dev.makepdfaccessible.com` only; dashboard and API follow `dashboard[-env].` and `api[-env].`.
2. `curl -I https://www.makepdfaccessible.com/pricing` returns 301 to `https://makepdfaccessible.com/pricing/`; `/pricing/` returns 200 with HSTS, CSP and `X-Frame-Options: DENY`; `/missing/` returns 404 with the exported `404.html`.
3. The bucket has no public access; only the distribution's ARN may `GetObject`.
4. `terraform validate` succeeds; `tflint` reports no missing tags on the bucket or distribution.

### Implementation

3A. Module `main.tf`: bucket (BucketOwnerEnforced, versioning, SSE-S3, lifecycle), OAC, CloudFront Function (`cloudfront-js-2.0`) templated with `primary_domain` and `redirect_hosts`, response headers policy (HSTS preload, generated CSP, XCTO, frame DENY, referrer policy, Permissions-Policy, COOP), distribution with managed `CachingOptimized`, 403/404 → `/404.html`, optional logging and WAF.
3B. `domains.tf` locals:

```hcl
locals {
  root_domain   = var.root_domain
  is_production = contains(["prod", "production"], var.environment)
  domain_name   = local.is_production ? local.root_domain : "${var.environment}.${local.root_domain}"
  domains = {
    root      = local.domain_name
    www       = "www.${local.root_domain}"
    dashboard = local.is_production ? "dashboard.${local.root_domain}" : "dashboard-${var.environment}.${local.root_domain}"
    api       = local.is_production ? "api.${local.root_domain}" : "api-${var.environment}.${local.root_domain}"
  }
  marketing_aliases        = local.is_production ? [local.domains.root, local.domains.www] : [local.domains.root]
  marketing_redirect_hosts = local.is_production ? [local.domains.www] : []
}
```

3C. `marketing.tf` instantiates the module with the existing ACM certificate (`aws_acm_certificate_validation.main`), the existing WAF and log bucket, and `api_origin = "https://${local.domains.api}"`.

---

## Spec 4 — Remote state per environment and CI wiring

**Status:** Done (Terraform side); the GitHub environments and account bootstrap are operator steps.

### Problem

State was local; `infra-ci.yml` ran `terraform init` and `terraform plan` with no backend or variable file, so a CI plan could not succeed (the `github_repo` variable has no default).

### Files to touch

| File                                                                 | Action                                                                                                                     |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/backend.tf`                                         | Create: partial `backend "s3" {}`                                                                                          |
| `infra/terraform/environments/{dev,staging,prod}.backend.hcl`        | Create                                                                                                                     |
| `infra/terraform/environments/{dev,staging,prod}.tfvars`             | Create                                                                                                                     |
| `infra/terraform/bootstrap/{main,variables,outputs}.tf`, `README.md` | Create: state bucket + lock table per account                                                                              |
| `.github/workflows/infra-ci.yml`                                     | `terraform init -backend-config=environments/<env>.backend.hcl`; `plan`/`apply` with `-var-file=environments/<env>.tfvars` |
| `infra/terraform/README.md`                                          | Document the flow                                                                                                          |

### Acceptance criteria

1. `terraform init -backend-config=environments/dev.backend.hcl` succeeds in the dev account after bootstrap; the state object lands at `platform/terraform.tfstate`.
2. A pull request runs `plan` against dev; a push to `main` applies to prod behind the `prod-infrastructure` environment approval.
3. The infrastructure CI role can only reach `pdf-accessibility-terraform-state-*` buckets and `pdf-accessibility-terraform-locks-*` tables (existing policy in `github_oidc.tf`).

### Implementation

4A. Operator: create the AWS Organization and the three accounts (ADR-0010); in each, run `bootstrap` with an administrator credential; run the first `terraform apply` of the root from a workstation so the OIDC roles exist; add `GITHUB_INFRASTRUCTURE_CI_ROLE_ARN`, `GITHUB_WEB_DEPLOY_ROLE_ARN`, `AWS_REGION` and `AWS_ACCOUNT_ID` as environment-scoped GitHub secrets.
4B. The workflow edits are in place; environment names follow the existing `<env>-infrastructure` convention.

---

## Spec 5 — Marketing site app and deploy workflow

**Status:** Done (scaffold with the core pages; content slices M2 to M5 follow the PRD).

### Problem

No marketing site exists; `web/` is a demo app with a deploy path that cannot run its server build.

### Files to touch

| File                                   | Action                                                                                                                                                                                         |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pnpm-workspace.yaml`                  | Add `apps/*`                                                                                                                                                                                   |
| `apps/marketing/**`                    | Create: Next.js 15 static export (home, product, pricing, free-report, check, trust, accessibility, security, bot, 404), design tokens, components, banned-phrase check, Playwright + axe test |
| `.github/workflows/marketing-site.yml` | Create: lint, typecheck, banned phrases, build, axe, deploy on `main` via OIDC to `MARKETING_S3_BUCKET`, invalidate `MARKETING_CLOUDFRONT_DISTRIBUTION_ID`                                     |
| `tsconfig.json` (root)                 | Add the project reference                                                                                                                                                                      |

### Acceptance criteria

1. `pnpm --filter mpa-marketing build` produces `apps/marketing/out/` with `index.html`, `pricing/index.html` and `404.html`.
2. `pnpm --filter mpa-marketing test:a11y` runs axe on every exported route with zero violations.
3. `pnpm --filter mpa-marketing check:copy` fails when a banned phrase is present.
4. The workflow deploys on push to `main` and posts the site URL; preview builds upload the `out/` directory as an artifact on pull requests.

### Implementation

5A. `next.config.mjs`: `output: 'export'`, `trailingSlash: true`, `images: { unoptimized: true }`, `reactStrictMode: true`.
5B. Cache headers on upload (workflow): `_next/static/**` and other hashed assets `public, max-age=31536000, immutable`; `*.html` and `*.txt`/`*.xml` `public, max-age=0, must-revalidate`.
5C. Repository variables `MARKETING_S3_BUCKET` and `MARKETING_CLOUDFRONT_DISTRIBUTION_ID` come from `terraform output marketing_site_bucket` and `marketing_site_distribution_id`; the workflow falls back to discovery by the `Name` tag when they are unset.

---

## Spec 6 — Retire `web/` and the legacy marketing distribution references

**Status:** Follow-up.

### Problem

`web/` duplicates the marketing site's purpose with a demo the pipeline cannot back; `web-ci.yml` deploys it to the `web_assets` bucket served by `aws_cloudfront_distribution.web` (`cloudfront.tf`), which is also the origin the old marketing distribution used.

### Files to touch

| File                                                                       | Action                                                                     |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `web/**`, `.github/workflows/web-ci.yml`                                   | Delete after the marketing site's `/check` replaces the demo               |
| `infra/terraform/cloudfront.tf`, `s3.tf` (`web_assets`), `outputs.tf`      | Delete the web distribution and bucket; keep `cloudfront_logs` and the WAF |
| `playwright.config.ts`, `vitest.workspace.ts`, `tsconfig.json`, `Makefile` | Remove `web` targets                                                       |

### Acceptance criteria

1. No workflow or Terraform resource references `web_assets` or `aws_cloudfront_distribution.web`.
2. The demo upload path (`/v1/demo/*`) is either removed or points at the marketing site's `/check` flow.

---

## Spec 7 — Multi-account guardrails

**Status:** Follow-up.

### Problem

ADR-0010 requires SCPs and cross-account roles that do not exist yet.

### Files to touch

| File                             | Action                                                                                                                 |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `infra/terraform/org/**`         | Create: AWS Organizations OUs, SCPs (deny public S3, deny IAM users, region allow-list), CloudTrail organization trail |
| `infra/terraform/github_oidc.tf` | Parameterize allowed branches per account (dev: `develop` and PRs; prod: `main` only)                                  |

### Acceptance criteria

1. Creating an IAM user or a public bucket in any member account is denied by SCP.
2. A CloudTrail organization trail delivers to the security account.

---

## Suggested execution order

1. Spec 1 first — nothing else can be planned or applied until the root validates.
2. Spec 2 — trivial hygiene, do it in the same change.
3. Spec 3 — the marketing site needs its own bucket and distribution; it depends on the environment-aware domains so dev and prod can coexist.
4. Spec 4 — remote state and CI wiring; independent of Spec 3 but needed before any CI apply.
5. Spec 5 — the app and workflow; depends on Spec 3's outputs for the deploy target.
6. Spec 6 — only after the marketing site's free check is live, to avoid removing the only public demo.
7. Spec 7 — when the second account is created; it hardens what Specs 4 and 5 assume.

After Specs 1 to 5 the repository has a valid Terraform root, a marketing site that builds and deploys to S3 and CloudFront on AWS, per-environment state and variables, and a documented bootstrap for new accounts.

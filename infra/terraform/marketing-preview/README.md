# Marketing site preview

Hosts the marketing site for a non-production environment on its CloudFront address (`https://<id>.cloudfront.net`), using the same `modules/static-site` module as production but without a custom domain, certificate, WAF or log bucket. It also creates the deploy role that `.github/workflows/marketing-site.yml` assumes in the `<environment>-web` GitHub environment.

Production keeps using the platform root (`../marketing.tf`). This root owns only its own state key, so applying it never touches the platform, account or bootstrap state.

## What it creates

- A private S3 bucket (versioned, encrypted, public access blocked), readable only by the distribution through origin access control.
- A CloudFront distribution with the module's security headers, the viewer-request function (directory index rewrite, trailing-slash redirect to the requested host) and a response headers policy.
- An IAM role trusted only by `repo:<github_repo>:environment:<environment>-web`, allowed to sync that bucket and invalidate that distribution.

## Apply

```bash
cd infra/terraform/marketing-preview
AWS_PROFILE=pdf-dev terraform init -backend-config=environments/dev.backend.hcl
AWS_PROFILE=pdf-dev terraform plan -var-file=environments/dev.tfvars -out=dev.tfplan
AWS_PROFILE=pdf-dev terraform apply dev.tfplan
```

## Connect the pipeline

Set these on the `<environment>-web` GitHub environment (not at repository level, where they would also reach production's deploy job):

```bash
ENV=dev-web
gh secret set GITHUB_WEB_DEPLOY_ROLE_ARN --env "$ENV" --body "$(terraform output -raw github_web_deploy_role_arn)"
gh variable set MARKETING_S3_BUCKET --env "$ENV" --body "$(terraform output -raw marketing_site_bucket)"
gh variable set MARKETING_CLOUDFRONT_DISTRIBUTION_ID --env "$ENV" --body "$(terraform output -raw marketing_site_distribution_id)"
```

Then deploy any branch to the preview:

```bash
gh workflow run marketing-site.yml --ref <branch> -f environment=dev
```

Production deploys still run only from `main`.

## Notes

- The free report and PDF check forms call the platform API, which this preview does not include, so they show an error on submit.
- The site's canonical URLs and sitemap point at `NEXT_PUBLIC_SITE_URL` (production by default), so search engines treat the preview as a copy of production rather than a separate site.

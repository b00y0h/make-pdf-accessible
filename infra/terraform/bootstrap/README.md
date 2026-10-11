# Terraform state bootstrap

Creates, once per AWS account, the S3 bucket and DynamoDB table named in `../environments/<env>.backend.hcl`.

This root keeps its state in local files, so each account gets its own workspace. The provider refuses to run when the credentials belong to a different account than the environment's (`local.account_ids` in `main.tf`).

```bash
cd infra/terraform/bootstrap
terraform init
terraform workspace new dev
AWS_PROFILE=pdf-dev terraform apply -var environment=dev
terraform workspace new prod
AWS_PROFILE=pdf-prod terraform apply -var environment=prod
```

Keep `terraform.tfstate.d/` (git-ignored): it is the only record of these resources.

Then initialize the platform root against the remote backend:

```bash
cd infra/terraform
AWS_PROFILE=pdf-dev terraform init -reconfigure -backend-config=environments/dev.backend.hcl
AWS_PROFILE=pdf-dev terraform plan -var-file=environments/dev.tfvars
```

The bucket names follow `<project_name>-terraform-state-<env>` and `<project_name>-terraform-locks-<env>`, which the GitHub OIDC infrastructure role in `../github_oidc.tf` is allowed to use.

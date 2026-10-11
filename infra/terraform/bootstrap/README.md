# Terraform state bootstrap

Creates, once per AWS account, the S3 bucket and DynamoDB table named in `../environments/<env>.backend.hcl` for every environment the account hosts. The dev account hosts `dev` and `staging`; the prod account hosts `prod` (ADR-0010). Each environment keeps its own bucket and table so its deploy role can be limited to them.

This root keeps its state in local files, so each account gets its own workspace. The provider refuses to run when the credentials belong to a different account than the environments' (`local.account_ids` in `main.tf`), and both resources carry `prevent_destroy`, so dropping an environment from the list fails instead of deleting its state storage.

```bash
cd infra/terraform/bootstrap
terraform init
terraform workspace new dev
AWS_PROFILE=pdf-dev terraform apply -var 'environments=["dev","staging"]'
terraform workspace new prod
AWS_PROFILE=pdf-prod terraform apply -var 'environments=["prod"]'
```

Keep `terraform.tfstate.d/` (git-ignored): it is the only local record of these resources. After an apply, copy the workspace's state into that account's first bucket so it survives a fresh checkout, and restore it from there before running anything on a new machine:

```bash
aws s3 cp terraform.tfstate.d/dev/terraform.tfstate s3://pdf-accessibility-terraform-state-dev/bootstrap/terraform.tfstate     # back up
aws s3 cp s3://pdf-accessibility-terraform-state-dev/bootstrap/terraform.tfstate terraform.tfstate.d/dev/terraform.tfstate     # restore
```

Then apply the account layer (`../account`) and initialize the platform root against the remote backend:

```bash
cd infra/terraform
AWS_PROFILE=pdf-dev terraform init -reconfigure -backend-config=environments/dev.backend.hcl
AWS_PROFILE=pdf-dev terraform plan -var-file=environments/dev.tfvars
```

The bucket names follow `<project_name>-terraform-state-<env>` and `<project_name>-terraform-locks-<env>`. Each environment's GitHub infrastructure role in `../github_oidc.tf` can use only its own.

# Terraform state bootstrap

Creates, once per AWS account, the S3 bucket and DynamoDB table named in `../environments/<env>.backend.hcl`.

```bash
cd infra/terraform/bootstrap
terraform init                       # local state for this tiny root
terraform apply -var environment=dev # repeat per account with that account's credentials
```

Then initialize the platform root against the remote backend:

```bash
cd infra/terraform
terraform init -backend-config=environments/dev.backend.hcl
terraform plan -var-file=environments/dev.tfvars
```

The bucket names follow `<project_name>-terraform-state-<env>` and `<project_name>-terraform-locks-<env>`, which the GitHub OIDC infrastructure role in `../github_oidc.tf` is allowed to use.

# Account layer

Resources that exist once per AWS account and are shared by every environment in it (ADR-0010):

| Account | ID | Environments | `account_name` |
| ------- | -- | ------------ | -------------- |
| pdf-accessibility-dev | 403030570295 | `dev`, `staging` | `nonprod` |
| pdf-accessibility-prod | 774697187580 | `prod` | `prod` |

- **GitHub Actions OIDC provider.** IAM allows one per URL per account. Each environment's roles (`../github_oidc.tf`) look it up by URL.
- **Platform network.** VPC, public and private subnets across two AZs, NAT gateway(s), free S3 and DynamoDB gateway endpoints, and optional interface endpoints. The platform root finds the VPC and subnets by the `pdf-accessibility/network` and `pdf-accessibility/tier` tags. Environments keep their own security groups. Private subnets are /20s because every Lambda in the VPC and every Fargate page task takes an address.

The dev account runs one NAT gateway and no interface endpoints to keep the fixed cost low (about $35 a month for the NAT gateway and its address). Prod runs a NAT gateway per AZ and interface endpoints for STS, CloudWatch Logs, Bedrock runtime, Textract and ECR. One NAT gateway also means staging's network differs from prod's.

Container image repositories stay per environment for now: the current Lambda build pushes `:latest` to `pdf-accessibility-<env>-<service>`, so a shared repository would make staging run whatever dev pushed last. Revisit when the v2 pipeline (`docs/REMEDIATION-PIPELINE-SPECS.md`) promotes images by digest.

## Order of operations in an account

```bash
# 1. State buckets and lock tables (local state, one workspace per account; see ../bootstrap/README.md)
cd infra/terraform/bootstrap && terraform init && terraform workspace select dev
AWS_PROFILE=pdf-dev terraform apply -var 'environments=["dev","staging"]'

# 2. This layer, with an administrator credential
cd ../account
AWS_PROFILE=pdf-dev terraform init -reconfigure -backend-config=environments/nonprod.backend.hcl
AWS_PROFILE=pdf-dev terraform apply -var-file=environments/nonprod.tfvars

# 3. The platform root, once per environment
cd ..
AWS_PROFILE=pdf-dev terraform init -reconfigure -backend-config=environments/dev.backend.hcl
AWS_PROFILE=pdf-dev terraform apply -var-file=environments/dev.tfvars
AWS_PROFILE=pdf-dev terraform init -reconfigure -backend-config=environments/staging.backend.hcl
AWS_PROFILE=pdf-dev terraform apply -var-file=environments/staging.tfvars
```

To deploy only the marketing site, create just the OIDC provider from this layer (`-target=aws_iam_openid_connect_provider.github`) and skip the network; see "Marketing site only" in `../README.md`.

This layer's state sits beside the first environment's platform state under the `account/` key. Environment roles can only reach their own bucket's `platform/` key, so CI can't change this layer. The provider refuses to run against any account but `aws_account_id`.

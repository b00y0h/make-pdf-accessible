# Remote state. The bucket, key, region and lock table are supplied per environment:
#   terraform init -backend-config=environments/<env>.backend.hcl
# Create the bucket and table once per AWS account with infra/terraform/bootstrap.
terraform {
  backend "s3" {}
}

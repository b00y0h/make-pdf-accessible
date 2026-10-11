# State for the dev marketing preview. Bucket and table come from infra/terraform/bootstrap;
# the key is this root's own, so it never shares state with the platform or account roots.
bucket         = "pdf-accessibility-terraform-state-dev"
key            = "marketing-preview/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "pdf-accessibility-terraform-locks-dev"
encrypt        = true

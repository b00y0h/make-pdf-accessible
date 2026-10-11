# The VPC and subnets belong to the account layer (infra/terraform/account) and are shared by every
# environment in the account; dev and staging both run in the non-prod account's network. This root
# finds them by tag and keeps only its own security groups.

data "aws_vpc" "platform" {
  tags = {
    "pdf-accessibility/network" = "platform"
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.platform.id]
  }

  tags = {
    "pdf-accessibility/tier" = "private"
  }
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.platform.id]
  }

  tags = {
    "pdf-accessibility/tier" = "public"
  }
}

locals {
  vpc_id             = data.aws_vpc.platform.id
  private_subnet_ids = sort(data.aws_subnets.private.ids)
  public_subnet_ids  = sort(data.aws_subnets.public.ids)
}

# Prod account: a NAT gateway per AZ so an AZ outage doesn't cut outbound traffic, and interface
# endpoints so calls to AWS APIs stay inside the VPC.
account_name      = "prod"
aws_account_id    = "774697187580" # pdf-accessibility-prod
cost_center       = "CC-PRD-001"
vpc_cidr          = "10.1.0.0/16"
az_count          = 2
nat_gateway_count = 2

interface_endpoints = ["sts", "logs", "bedrock-runtime", "textract", "ecr.api", "ecr.dkr"]

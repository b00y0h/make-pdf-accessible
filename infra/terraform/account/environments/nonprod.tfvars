# Dev account (403030570295): dev and staging share this network.
# One NAT gateway and no interface endpoints keep the fixed cost low; traffic to AWS APIs goes
# through the NAT gateway, and S3 and DynamoDB through the free gateway endpoints.
account_name      = "nonprod"
aws_account_id    = "403030570295" # pdf-accessibility-dev
cost_center       = "CC-DEV-001"
vpc_cidr          = "10.0.0.0/16"
az_count          = 2
nat_gateway_count = 1

interface_endpoints = []

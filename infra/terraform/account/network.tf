# Platform network, shared by every environment in the account. Environments keep their own
# security groups; the platform root finds the VPC and subnets by the pdf-accessibility/* tags.
#
# Private subnets are /20s (about 4,000 addresses each) because every Lambda in a VPC and every
# Fargate page task takes an address, and ADR-0002 targets 1,000 concurrent page tasks.

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  # 10.0.0.0/20, 10.0.16.0/20, ... for private; 10.0.240.0/24, 10.0.241.0/24, ... for public.
  private_subnet_cidrs = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnet_cidrs  = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, 240 + i)]
}

resource "aws_vpc" "platform" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name                        = "${local.name_prefix}-vpc"
    "pdf-accessibility/network" = "platform"
  }
}

resource "aws_internet_gateway" "platform" {
  vpc_id = aws_vpc.platform.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

resource "aws_subnet" "public" {
  count = var.az_count

  vpc_id                  = aws_vpc.platform.id
  cidr_block              = local.public_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name                     = "${local.name_prefix}-public-${local.azs[count.index]}"
    "pdf-accessibility/tier" = "public"
  }
}

resource "aws_subnet" "private" {
  count = var.az_count

  vpc_id            = aws_vpc.platform.id
  cidr_block        = local.private_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]

  tags = {
    Name                     = "${local.name_prefix}-private-${local.azs[count.index]}"
    "pdf-accessibility/tier" = "private"
  }
}

resource "aws_eip" "nat" {
  count = var.nat_gateway_count

  domain     = "vpc"
  depends_on = [aws_internet_gateway.platform]

  tags = {
    Name = "${local.name_prefix}-nat-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "platform" {
  count = var.nat_gateway_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${local.name_prefix}-nat-${count.index + 1}"
  }

  depends_on = [aws_internet_gateway.platform]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.platform.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.platform.id
  }

  tags = {
    Name = "${local.name_prefix}-public"
  }
}

resource "aws_route_table_association" "public" {
  count = var.az_count

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# One private route table per AZ. With fewer NAT gateways than AZs, the extra AZs share the last one.
resource "aws_route_table" "private" {
  count = var.az_count

  vpc_id = aws_vpc.platform.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.platform[min(count.index, var.nat_gateway_count - 1)].id
  }

  tags = {
    Name = "${local.name_prefix}-private-${local.azs[count.index]}"
  }
}

resource "aws_route_table_association" "private" {
  count = var.az_count

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Gateway endpoints are free and keep S3 and DynamoDB traffic off the NAT gateway.
resource "aws_vpc_endpoint" "gateway" {
  for_each = toset(["s3", "dynamodb"])

  vpc_id            = aws_vpc.platform.id
  service_name      = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = {
    Name = "${local.name_prefix}-${each.value}-endpoint"
  }
}

resource "aws_security_group" "vpc_endpoints" {
  count = length(var.interface_endpoints) > 0 ? 1 : 0

  name_prefix = "${local.name_prefix}-vpc-endpoints-"
  description = "HTTPS from inside the platform VPC to interface endpoints"
  vpc_id      = aws_vpc.platform.id

  ingress {
    description = "HTTPS from the VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.platform.cidr_block]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-vpc-endpoints"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(var.interface_endpoints)

  vpc_id              = aws_vpc.platform.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = {
    Name = "${local.name_prefix}-${each.value}-endpoint"
  }
}

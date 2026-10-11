# OpenSearch Serverless Vector Collection for embedding search

# OpenSearch Serverless names are limited to 32 characters, so these use a short prefix
locals {
  aoss_collection_name = "pdf-${var.environment}-embeddings"
}

# OpenSearch Serverless Collection for vector embeddings
resource "aws_opensearchserverless_collection" "pdf_embeddings" {
  name        = local.aoss_collection_name
  type        = "VECTORSEARCH"
  description = "Vector collection for PDF document embeddings"

  tags = merge(local.common_tags, {
    Name = "${local.app_name}-${var.environment}-embeddings-collection"
  })

  # A collection can only be created once an encryption policy covers its name
  depends_on = [
    aws_opensearchserverless_security_policy.pdf_embeddings_encryption,
    aws_opensearchserverless_security_policy.pdf_embeddings_network,
  ]
}

# Data access policy for the collection
resource "aws_opensearchserverless_access_policy" "pdf_embeddings_data" {
  name = "${local.aoss_collection_name}-data"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${local.aoss_collection_name}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/${local.aoss_collection_name}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        aws_iam_role.opensearch_role.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}

# Network access policy for the collection
resource "aws_opensearchserverless_security_policy" "pdf_embeddings_network" {
  name = "${local.aoss_collection_name}-net"
  type = "network"

  policy = jsonencode([
    {
      Description = "Network access for PDF embeddings collection"
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${local.aoss_collection_name}"
          ]
        }
      ]
      AllowFromPublic = false
      SourceVPCs      = [aws_vpc.main.id]
    }
  ])
}

# Encryption policy for the collection
resource "aws_opensearchserverless_security_policy" "pdf_embeddings_encryption" {
  name = "${local.aoss_collection_name}-enc"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/${local.aoss_collection_name}"
        ]
        AWSOwnedKey = true
      }
    ]
    AWSOwnedKey = true
  })
}

# IAM role for OpenSearch access
resource "aws_iam_role" "opensearch_role" {
  name = "${local.app_name}-${var.environment}-opensearch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["lambda.amazonaws.com", "opensearch.amazonaws.com"]
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for OpenSearch access
resource "aws_iam_role_policy" "opensearch_policy" {
  name = "${local.app_name}-${var.environment}-opensearch-policy"
  role = aws_iam_role.opensearch_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.pdf_embeddings.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# Add OpenSearch permissions to processing Lambda roles
resource "aws_iam_role_policy" "lambda_opensearch_access" {
  for_each = toset(["structure", "alt_text", "exports"]) # Functions that might need vector search

  name = "${local.app_name}-${var.environment}-${each.key}-opensearch-policy"
  role = aws_iam_role.processing_lambda_role[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.pdf_embeddings.arn
        ]
      }
    ]
  })
}

# VPC Endpoint for OpenSearch Serverless
resource "aws_vpc_endpoint" "opensearch" {
  vpc_id             = aws_vpc.main.id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.aoss"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.opensearch_sg.id]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action = [
          "aoss:*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.app_name}-${var.environment}-opensearch-endpoint"
  })
}

# Security group for OpenSearch VPC endpoint
resource "aws_security_group" "opensearch_sg" {
  name_prefix = "${local.app_name}-${var.environment}-opensearch-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for OpenSearch VPC endpoint"

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.app_name}-${var.environment}-opensearch-sg"
  })
}

# Outputs
output "opensearch_collection_arn" {
  description = "ARN of the OpenSearch collection for vector search"
  value       = aws_opensearchserverless_collection.pdf_embeddings.arn
}

output "opensearch_collection_endpoint" {
  description = "Endpoint of the OpenSearch collection"
  value       = aws_opensearchserverless_collection.pdf_embeddings.collection_endpoint
}

output "opensearch_dashboard_endpoint" {
  description = "Dashboard endpoint of the OpenSearch collection"
  value       = aws_opensearchserverless_collection.pdf_embeddings.dashboard_endpoint
}
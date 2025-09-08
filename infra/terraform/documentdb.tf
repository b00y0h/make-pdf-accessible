# DocumentDB Subnet Group
resource "aws_docdb_subnet_group" "main" {
  name       = "${local.name_prefix}-docdb-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-docdb-subnet-group"
  })
}

# DocumentDB Cluster Parameter Group
resource "aws_docdb_cluster_parameter_group" "main" {
  family      = "docdb5.0"
  name        = "${local.name_prefix}-docdb-cluster-pg"
  description = "DocumentDB cluster parameter group for ${local.name_prefix}"

  parameter {
    name  = "tls"
    value = "enabled"
  }

  parameter {
    name  = "ttl_monitor"
    value = "enabled"
  }

  tags = local.common_tags
}

# DocumentDB Security Group
resource "aws_security_group" "documentdb" {
  name_prefix = "${local.name_prefix}-documentdb-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for DocumentDB cluster"

  # Allow inbound from Lambda security group on MongoDB port
  ingress {
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
    description     = "MongoDB/DocumentDB access from Lambda functions"
  }

  # Allow inbound from processing Lambda security groups
  dynamic "ingress" {
    for_each = var.vpc_config != null ? [1] : []
    content {
      from_port       = 27017
      to_port         = 27017
      protocol        = "tcp"
      security_groups = var.vpc_config.security_group_ids
      description     = "MongoDB/DocumentDB access from processing Lambda functions"
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-documentdb-sg"
  })
}

# Random password for DocumentDB master user
resource "random_password" "documentdb_password" {
  length  = 16
  special = true
}

# DocumentDB Cluster
resource "aws_docdb_cluster" "main" {
  cluster_identifier              = "${local.name_prefix}-docdb-cluster"
  engine                         = "docdb"
  engine_version                 = "5.0.0"
  master_username                = "docdbadmin"
  master_password                = random_password.documentdb_password.result
  backup_retention_period        = 7
  preferred_backup_window        = "07:00-09:00"
  preferred_maintenance_window   = "sun:09:00-sun:10:00"
  skip_final_snapshot           = var.environment == "dev" ? true : false
  final_snapshot_identifier     = var.environment == "dev" ? null : "${local.name_prefix}-docdb-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  storage_encrypted             = true
  kms_key_id                    = var.cloudwatch_logs_kms_key_id
  db_cluster_parameter_group_name = aws_docdb_cluster_parameter_group.main.name
  db_subnet_group_name          = aws_docdb_subnet_group.main.name
  vpc_security_group_ids        = [aws_security_group.documentdb.id]
  deletion_protection           = var.environment == "dev" ? false : true
  enabled_cloudwatch_logs_exports = ["audit", "profiler"]

  # Enable backtrack for point-in-time recovery (if supported)
  apply_immediately = var.environment == "dev" ? true : false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-docdb-cluster"
  })

  depends_on = [
    aws_docdb_subnet_group.main,
    aws_docdb_cluster_parameter_group.main
  ]
}

# DocumentDB Cluster Instances
resource "aws_docdb_cluster_instance" "cluster_instances" {
  count                        = var.documentdb_instance_count
  identifier                   = "${local.name_prefix}-docdb-${count.index}"
  cluster_identifier           = aws_docdb_cluster.main.id
  instance_class               = var.documentdb_instance_class
  auto_minor_version_upgrade   = true
  performance_insights_enabled = var.documentdb_performance_insights_enabled
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-docdb-instance-${count.index}"
  })
}

# Store DocumentDB credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "documentdb_credentials" {
  name                    = "${local.name_prefix}/documentdb/credentials"
  description            = "DocumentDB cluster credentials"
  recovery_window_in_days = var.environment == "dev" ? 0 : 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "documentdb_credentials" {
  secret_id = aws_secretsmanager_secret.documentdb_credentials.id
  secret_string = jsonencode({
    username = aws_docdb_cluster.main.master_username
    password = aws_docdb_cluster.main.master_password
    endpoint = aws_docdb_cluster.main.endpoint
    port     = aws_docdb_cluster.main.port
    hosts    = aws_docdb_cluster.main.cluster_members
  })
}

# CloudWatch Log Groups for DocumentDB
resource "aws_cloudwatch_log_group" "documentdb_audit" {
  name              = "/aws/docdb/${aws_docdb_cluster.main.cluster_identifier}/audit"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "documentdb_profiler" {
  name              = "/aws/docdb/${aws_docdb_cluster.main.cluster_identifier}/profiler"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}
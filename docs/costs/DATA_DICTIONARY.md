# AWS Costs Dashboard - Data Dictionary

This document defines the tags, metrics, and data structures used in the AWS Costs Dashboard for consistent cost allocation and reporting.

## 📋 Tag Taxonomy

### Core Business Tags

These tags are **mandatory** for all AWS resources and must follow the specified format.

#### `Environment`
**Purpose**: Distinguish between different deployment environments  
**Format**: `environment:<value>`  
**Required**: ✅ Yes  
**Values**:
- `prod` - Production environment
- `staging` - Staging/pre-production environment
- `dev` - Development environment
- `test` - Testing environment
- `sandbox` - Experimental/sandbox environment

**Example**: `environment:prod`

#### `Application`
**Purpose**: Identify the application or service using the resource  
**Format**: `application:<value>`  
**Required**: ✅ Yes  
**Values**: Use kebab-case naming convention
- `pdf-accessibility` - PDF accessibility processing service
- `user-dashboard` - User-facing dashboard
- `admin-portal` - Administrative interface
- `api-gateway` - API gateway service
- `data-pipeline` - Data processing pipeline

**Example**: `application:pdf-accessibility`

#### `Team`
**Purpose**: Identify the team responsible for the resource  
**Format**: `team:<value>`  
**Required**: ✅ Yes  
**Values**:
- `platform` - Platform engineering team
- `backend` - Backend development team
- `frontend` - Frontend development team
- `data` - Data engineering team
- `security` - Security team
- `ops` - Operations team

**Example**: `team:platform`

#### `CostCenter`
**Purpose**: Assign costs to specific business units for chargeback  
**Format**: `cost-center:<value>`  
**Required**: ✅ Yes  
**Values**: Use company cost center codes
- `engineering` - Engineering department
- `product` - Product development
- `sales` - Sales and marketing
- `operations` - Business operations
- `research` - Research and development

**Example**: `cost-center:engineering`

### Operational Tags

These tags provide operational context and are **recommended** for better resource management.

#### `Owner`
**Purpose**: Identify the primary contact for the resource  
**Format**: `owner:<email>`  
**Required**: ❌ Recommended  
**Values**: Company email addresses
- Use individual email for personal resources
- Use team email for shared resources

**Example**: `owner:john.doe@company.com`

#### `Project`
**Purpose**: Associate resources with specific projects or initiatives  
**Format**: `project:<value>`  
**Required**: ❌ Recommended  
**Values**: Use project codes or names
- `pdf-v2` - PDF accessibility v2.0 project
- `dashboard-redesign` - Dashboard redesign project
- `compliance-2024` - 2024 compliance initiative

**Example**: `project:pdf-v2`

#### `Version`
**Purpose**: Track resource versions for deployment tracking  
**Format**: `version:<value>`  
**Required**: ❌ Optional  
**Values**: Use semantic versioning
- `v1.0.0` - Production version
- `v1.1.0-beta` - Beta version
- `main` - Development branch

**Example**: `version:v1.0.0`

### Financial Tags

These tags support detailed financial analysis and reporting.

#### `BudgetCategory`
**Purpose**: Categorize expenses for budget tracking  
**Format**: `budget-category:<value>`  
**Required**: ❌ Recommended  
**Values**:
- `compute` - EC2, Lambda, Fargate
- `storage` - S3, EBS, EFS
- `database` - RDS, DynamoDB
- `networking` - VPC, CloudFront, API Gateway
- `security` - WAF, Shield, KMS
- `monitoring` - CloudWatch, X-Ray

**Example**: `budget-category:compute`

#### `ChargeType`
**Purpose**: Distinguish between different charging models  
**Format**: `charge-type:<value>`  
**Required**: ❌ Optional  
**Values**:
- `reserved` - Reserved instances
- `spot` - Spot instances
- `on-demand` - On-demand instances
- `savings-plan` - Savings plan coverage

**Example**: `charge-type:reserved`

#### `FinancialOwner`
**Purpose**: Assign financial responsibility  
**Format**: `financial-owner:<value>`  
**Required**: ❌ Recommended  
**Values**: Use department or manager names
- `engineering-dept` - Engineering department budget
- `product-dept` - Product department budget
- `shared-services` - Shared services budget

**Example**: `financial-owner:engineering-dept`

### Lifecycle Tags

These tags track the lifecycle state of resources.

#### `Schedule`
**Purpose**: Define resource scheduling for cost optimization  
**Format**: `schedule:<value>`  
**Required**: ❌ Optional  
**Values**:
- `24x7` - Always on
- `business-hours` - 8 AM - 6 PM weekdays
- `dev-hours` - 9 AM - 5 PM weekdays
- `weekend-off` - Off on weekends
- `manual` - Manual start/stop

**Example**: `schedule:business-hours`

#### `Backup`
**Purpose**: Define backup requirements  
**Format**: `backup:<value>`  
**Required**: ❌ Optional  
**Values**:
- `daily` - Daily backups
- `weekly` - Weekly backups
- `monthly` - Monthly backups
- `none` - No backups required

**Example**: `backup:daily`

#### `DataClassification`
**Purpose**: Classify data sensitivity for compliance  
**Format**: `data-classification:<value>`  
**Required**: ✅ Yes (for data resources)  
**Values**:
- `public` - Public data
- `internal` - Internal use only
- `confidential` - Confidential data
- `restricted` - Restricted/sensitive data

**Example**: `data-classification:confidential`

## 🏷️ Tag Policy

### Mandatory Tagging

All AWS resources **MUST** have these tags:
```json
{
  "environment": "prod|staging|dev|test|sandbox",
  "application": "<application-name>",
  "team": "<team-name>",
  "cost-center": "<cost-center-code>"
}
```

### Tag Validation Rules

1. **Format**: All tag keys use lowercase with hyphens
2. **Values**: Use lowercase, kebab-case for consistency
3. **Length**: Tag values must be ≤ 255 characters
4. **Characters**: Only alphanumeric, hyphens, and underscores
5. **Required**: Deployment will fail without mandatory tags

### Tag Enforcement

**AWS Config Rules**:
```json
{
  "required-tags": [
    "environment",
    "application", 
    "team",
    "cost-center"
  ],
  "case-sensitive": false,
  "enforcement": "blocking"
}
```

**Terraform Validation**:
```hcl
variable "required_tags" {
  description = "Required tags for all resources"
  type = map(string)
  
  validation {
    condition = alltrue([
      can(var.required_tags.environment),
      can(var.required_tags.application),
      can(var.required_tags.team),
      can(var.required_tags["cost-center"])
    ])
    error_message = "Missing required tags: environment, application, team, cost-center"
  }
}
```

## 📊 Cost Metrics

### Primary Metrics

#### `UnblendedCost`
**Description**: The actual cost of AWS services without any discounts applied  
**Use Case**: Understanding true resource consumption  
**Currency**: USD  
**Granularity**: Hourly, Daily, Monthly  

#### `AmortizedCost`
**Description**: Cost with Reserved Instance and Savings Plan discounts applied  
**Use Case**: True cost allocation for financial planning  
**Currency**: USD  
**Granularity**: Hourly, Daily, Monthly  

#### `BlendedCost`
**Description**: Averaged cost across all accounts in consolidated billing  
**Use Case**: Organization-wide cost views  
**Currency**: USD  
**Granularity**: Daily, Monthly  

#### `NetUnblendedCost`
**Description**: UnblendedCost minus credits and refunds  
**Use Case**: Actual amount charged to credit card  
**Currency**: USD  
**Granularity**: Daily, Monthly  

### Usage Metrics

#### `UsageQuantity`
**Description**: The amount of service usage (e.g., GB-hours, requests)  
**Use Case**: Resource utilization analysis  
**Units**: Service-specific (GB, hours, requests, etc.)  
**Granularity**: Hourly, Daily, Monthly  

#### `NormalizedUsageAmount`
**Description**: Usage normalized for instance types and sizes  
**Use Case**: Comparing usage across different instance types  
**Units**: Normalized units  
**Granularity**: Hourly, Daily, Monthly  

### Reservation Metrics

#### `ReservationEffectiveUsage`
**Description**: Usage covered by Reserved Instances  
**Use Case**: RI utilization tracking  
**Units**: Hours or normalized units  

#### `ReservationUnusedQuantity`
**Description**: Unused Reserved Instance capacity  
**Use Case**: RI optimization opportunities  
**Units**: Hours or normalized units  

## 🔍 Filtering and Grouping

### Standard Dimensions

#### Service Grouping
```typescript
const serviceGroups = {
  compute: ['EC2-Instance', 'Lambda', 'ECS', 'EKS'],
  storage: ['Amazon S3', 'EBS', 'EFS'],
  database: ['RDS', 'DynamoDB', 'ElastiCache'],
  networking: ['VPC', 'CloudFront', 'API Gateway'],
  analytics: ['Athena', 'Glue', 'EMR'],
  security: ['WAF', 'Shield', 'GuardDuty']
};
```

#### Time Grouping
- **Hourly**: For detailed recent analysis (last 7 days)
- **Daily**: For trend analysis (last 3 months)
- **Monthly**: For high-level reporting (last 2 years)

#### Geographic Grouping
```typescript
const regionGroups = {
  'us-regions': ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2'],
  'eu-regions': ['eu-west-1', 'eu-west-2', 'eu-central-1'],
  'asia-regions': ['ap-southeast-1', 'ap-northeast-1', 'ap-south-1']
};
```

### Filter Combinations

#### Environment Filters
```sql
-- Production costs only
WHERE line_item_resource_id LIKE '%prod%'
   OR resource_tags_user_environment = 'prod'

-- Non-production costs
WHERE resource_tags_user_environment IN ('dev', 'staging', 'test')
```

#### Team-based Filters
```sql
-- Engineering team costs
WHERE resource_tags_user_team = 'engineering'
   OR resource_tags_user_cost_center = 'engineering'

-- Cross-team shared resources
WHERE resource_tags_user_project = 'shared-infrastructure'
```

#### Application Filters
```sql
-- PDF accessibility application
WHERE resource_tags_user_application = 'pdf-accessibility'
   OR line_item_resource_id LIKE '%pdf-accessibility%'
```

## 📈 Dashboard Views

### Executive Dashboard
**Tags Used**: `cost-center`, `environment`  
**Metrics**: `AmortizedCost`  
**Granularity**: Monthly  
**Purpose**: High-level cost overview for leadership

### Team Dashboard
**Tags Used**: `team`, `application`, `environment`  
**Metrics**: `UnblendedCost`, `UsageQuantity`  
**Granularity**: Daily  
**Purpose**: Team-specific cost tracking and optimization

### Project Dashboard
**Tags Used**: `project`, `version`, `environment`  
**Metrics**: `UnblendedCost`, `AmortizedCost`  
**Granularity**: Daily  
**Purpose**: Project-specific cost tracking

### Resource Optimization Dashboard
**Tags Used**: `schedule`, `charge-type`, `backup`  
**Metrics**: `UnblendedCost`, `ReservationUnusedQuantity`  
**Granularity**: Hourly/Daily  
**Purpose**: Cost optimization opportunities

## 🛠️ Implementation Guidelines

### Tagging Strategy

1. **Tag at Creation**: Apply tags when resources are created
2. **Inheritance**: Child resources inherit parent tags where possible
3. **Automation**: Use Infrastructure as Code for consistent tagging
4. **Validation**: Implement tag validation in CI/CD pipelines
5. **Monitoring**: Monitor tag compliance with AWS Config

### Cost Allocation

#### Shared Resources
For shared resources (e.g., VPC, security groups):
```json
{
  "cost-allocation": "shared",
  "allocation-method": "equal-split",
  "benefiting-teams": "platform,backend,frontend"
}
```

#### Multi-tenant Resources
For resources serving multiple applications:
```json
{
  "cost-allocation": "weighted",
  "allocation-weights": {
    "pdf-accessibility": 0.6,
    "user-dashboard": 0.3,
    "admin-portal": 0.1
  }
}
```

### Tag Automation

#### Terraform Example
```hcl
locals {
  common_tags = {
    environment    = var.environment
    application   = var.application_name
    team         = var.team_name
    cost-center  = var.cost_center
    project      = var.project_name
    owner        = var.resource_owner
    terraform    = "true"
    created-by   = "terraform"
  }
}

resource "aws_instance" "example" {
  # ... other configuration
  
  tags = merge(local.common_tags, {
    Name = "example-instance"
    role = "web-server"
  })
}
```

#### AWS CLI Tagging
```bash
# Tag multiple resources
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0" \
  --tags environment=prod,application=pdf-accessibility,team=platform
```

## 📊 Reporting Standards

### Monthly Reports

#### Cost by Team
```sql
SELECT 
  resource_tags_user_team as team,
  resource_tags_user_environment as environment,
  SUM(line_item_unblended_cost) as cost,
  DATE_FORMAT(line_item_usage_start_date, '%Y-%m') as month
FROM cur_table
WHERE year = '2024' AND month = '01'
GROUP BY 1, 2, 4
ORDER BY cost DESC;
```

#### Cost by Application
```sql
SELECT 
  resource_tags_user_application as application,
  resource_tags_user_cost_center as cost_center,
  SUM(line_item_unblended_cost) as cost,
  COUNT(DISTINCT line_item_resource_id) as resource_count
FROM cur_table
WHERE year = '2024' AND month = '01'
GROUP BY 1, 2
ORDER BY cost DESC;
```

### Weekly Reports

#### Environment Cost Trends
```sql
SELECT 
  resource_tags_user_environment as environment,
  DATE(line_item_usage_start_date) as date,
  SUM(line_item_unblended_cost) as daily_cost
FROM cur_table
WHERE line_item_usage_start_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Ad-hoc Queries

#### Untagged Resources
```sql
SELECT 
  line_item_product_code as service,
  line_item_resource_id as resource_id,
  SUM(line_item_unblended_cost) as cost
FROM cur_table
WHERE (resource_tags_user_environment IS NULL 
   OR resource_tags_user_application IS NULL
   OR resource_tags_user_team IS NULL)
  AND year = '2024' AND month = '01'
GROUP BY 1, 2
HAVING cost > 10
ORDER BY cost DESC;
```

## 🔗 Integration with External Systems

### FinOps Tools
- **CloudHealth**: Tag mapping for cost allocation
- **CloudCheckr**: Automated tagging recommendations
- **AWS Cost Categories**: Business logic for cost grouping

### ITSM Integration
- **ServiceNow**: Link costs to service catalog items
- **Jira**: Associate costs with project tracking
- **Confluence**: Document tag usage and policies

### BI Tools
- **Tableau**: Pre-built dashboards using tag dimensions
- **PowerBI**: Cost allocation models based on tags
- **Looker**: Self-service analytics with tag filters

## 📝 Change Management

### Tag Schema Changes

1. **Proposal**: Submit change request with business justification
2. **Review**: Technical and business stakeholder review
3. **Testing**: Validate in non-production environments
4. **Migration**: Gradual rollout with backward compatibility
5. **Documentation**: Update this data dictionary
6. **Training**: Communicate changes to all teams

### Version Control

Tag schema versions are tracked in Git:
```
docs/costs/data-dictionary/
├── v1.0.0/ (2024-01-01)
├── v1.1.0/ (2024-03-01)
└── current -> v1.1.0
```

### Deprecation Policy

1. **Notice**: 90 days advance notice for tag deprecation
2. **Migration**: Provide migration path and tools
3. **Grace Period**: 6 months of parallel support
4. **Removal**: Complete removal after grace period

---

## 📚 Resources

- **AWS Tagging Best Practices**: https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html
- **Company Tagging Policy**: [Internal Link]
- **Cost Allocation Guide**: [Internal Link]
- **Tag Compliance Dashboard**: [Internal Link]

---

*This data dictionary is reviewed quarterly and updated as needed. Last updated: $(date)*

**Document Version**: 1.1.0  
**Next Review Date**: $(date -d '+3 months' +%Y-%m-%d)  
**Owner**: Platform Engineering Team  
**Approver**: FinOps Team Lead
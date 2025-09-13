# AWS Costs Dashboard

Enterprise-grade AWS cost monitoring and analytics dashboard with multi-source data integration, comprehensive filtering, and month-over-month analytics.

## 🎯 Overview

The Costs Dashboard provides real-time insights into AWS spending across your organization with:

- **Dual Data Sources**: Cost Explorer API + Cost and Usage Reports (CUR) via Athena
- **Advanced Analytics**: Month-over-Month trends, forecasting, and anomaly detection  
- **Granular Filtering**: Services, accounts, regions, tags, custom date ranges
- **Enterprise Features**: Role-based access, data exports, caching, and audit trails

## 🚀 Quick Start

### Prerequisites

- AWS Account with Cost Explorer enabled
- Node.js 18+ and pnpm 8+
- PostgreSQL 15+ database
- Redis (optional, for caching)

### Setup Steps

1. **Install Dependencies**
   ```bash
   pnpm install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your settings
   ```

3. **Setup Database**
   ```bash
   pnpm run db:generate
   pnpm run db:push
   ```

4. **Configure AWS Credentials**
   ```bash
   # Via AWS CLI
   aws configure
   
   # Or environment variables
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   export AWS_REGION=us-east-1
   ```

5. **Start Development Server**
   ```bash
   pnpm run dev
   ```

6. **Access Dashboard**
   - Navigate to `http://localhost:3001/admin/costs`
   - Login with admin credentials

## 📊 Data Sources

### Cost Explorer API (Default)

**Use Case**: Real-time monitoring, immediate insights

**Characteristics**:
- **Freshness**: 24-48 hour delay
- **Granularity**: Daily, Monthly, Hourly (limited)
- **Retention**: 12 months of detailed data
- **Rate Limits**: 5 requests/second, burst capacity
- **Cost**: $0.01 per API request

**Best For**:
- Executive dashboards
- Real-time alerts
- Interactive analysis
- Month-over-month tracking

### Cost and Usage Reports (CUR) via Athena

**Use Case**: Deep historical analysis, custom reporting

**Characteristics**:
- **Freshness**: 6-24 hour delivery latency
- **Granularity**: Resource-level detail, hourly precision
- **Retention**: Unlimited (S3 storage)
- **Query Cost**: ~$5 per TB scanned
- **Storage**: Parquet format, compressed

**Best For**:
- Historical trend analysis
- Resource-level cost attribution
- Custom reporting
- Data warehousing integration

### Switching Between Sources

Use the **Data Source Toggle** in the dashboard header:

```typescript
// Programmatically switch data sources
const { setDataSource } = useDataSource();
setDataSource('cost-explorer'); // or 'athena'
```

## 🏗️ Architecture

### Frontend Stack
- **Framework**: Next.js 15 with App Router
- **Styling**: Tailwind CSS + shadcn/ui components
- **State**: TanStack Query for server state, React Context for UI state
- **Charts**: Recharts for data visualization
- **Authentication**: better-auth with role-based access

### Backend Services
- **API Routes**: Next.js API routes in `/app/api/costs/`
- **Data Layer**: AWS SDK clients with retry/circuit breaker patterns
- **Caching**: Redis with memory fallback, 6-12 hour TTL
- **Background Jobs**: Scheduled data refresh via cron

### Infrastructure
- **Compute**: Docker containers on AWS ECS/Fargate
- **Database**: PostgreSQL on RDS with read replicas
- **Storage**: S3 for CUR data, logs, and artifacts
- **Monitoring**: CloudWatch with custom dashboards

## 📋 Feature Matrix

| Feature | Cost Explorer | CUR/Athena | Notes |
|---------|---------------|------------|-------|
| Real-time data | ✅ 24-48h delay | ❌ 6-24h delay | CE preferred for dashboards |
| Historical data | 📅 12 months | 📅 Unlimited | CUR for long-term analysis |
| Resource details | ⚠️ Limited | ✅ Full detail | CUR has line-item data |
| Custom metrics | ❌ | ✅ SQL queries | CUR enables custom calculations |
| Rate limits | ⚠️ 5 req/sec | ✅ Athena limits | Consider caching for CE |
| Query cost | 💰 $0.01/request | 💰 ~$5/TB scanned | Monitor usage patterns |

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL="postgresql://user:pass@localhost:5432/dashboard"
AUTH_DATABASE_URL="postgresql://user:pass@localhost:5433/better_auth"

# AWS Configuration
AWS_REGION="us-east-1"
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"

# Cost Explorer Settings
COST_EXPLORER_CACHE_TTL=21600  # 6 hours in seconds
COST_EXPLORER_RATE_LIMIT=5    # requests per second

# CUR/Athena Settings
ATHENA_WORKGROUP="costs-dashboard"
ATHENA_RESULT_BUCKET="your-athena-results-bucket"
CUR_DATABASE="cur_database"
CUR_TABLE="cur_table"

# Cache Configuration
REDIS_URL="redis://localhost:6379"
MEMORY_CACHE_SIZE=1000  # Max items in memory cache

# Authentication
BETTER_AUTH_SECRET="your-secret-key-here"
BETTER_AUTH_URL="http://localhost:3001"
```

### Rate Limiting

Configure request limits to avoid throttling:

```typescript
// Cost Explorer rate limiting
const rateLimit = {
  requests: 5,          // per second
  burst: 20,           // burst capacity
  backoffMs: 1000,     // exponential backoff
};

// Athena query optimization
const athenaConfig = {
  maxConcurrentQueries: 10,
  queryTimeout: 300000,  // 5 minutes
  resultsCacheTTL: 86400,  // 24 hours
};
```

## 📊 Data Freshness & Limitations

### Cost Explorer Limitations

| Metric | Limitation | Workaround |
|--------|------------|------------|
| **Freshness** | 24-48 hour delay | Cache recent data, show freshness indicators |
| **Granularity** | Daily minimum for most metrics | Use CUR for hourly data |
| **Retention** | 12 months detailed history | Archive to S3 for longer retention |
| **Rate Limits** | 5 requests/second | Implement caching and batching |
| **Filtering** | Limited tag combinations | Use CUR for complex tag queries |

### CUR/Athena Considerations

| Aspect | Details | Best Practices |
|--------|---------|----------------|
| **Delivery** | 6-24 hour latency | Schedule overnight refreshes |
| **Partitioning** | By year/month/day | Include partitions in queries |
| **Data Size** | Can be very large | Use column pruning, date filters |
| **Query Cost** | ~$5 per TB scanned | Monitor with CloudWatch metrics |
| **Concurrency** | 10 concurrent queries | Queue long-running reports |

### Data Freshness Indicators

The dashboard shows data freshness with visual indicators:

```typescript
// Freshness calculation
const getDataFreshness = (lastUpdated: Date) => {
  const hoursOld = (Date.now() - lastUpdated.getTime()) / (1000 * 60 * 60);
  
  if (hoursOld < 6) return 'fresh';        // 🟢 Green
  if (hoursOld < 24) return 'recent';      // 🟡 Yellow  
  if (hoursOld < 48) return 'stale';       // 🟠 Orange
  return 'outdated';                       // 🔴 Red
};
```

## 🔍 Filter Behavior

### Filter Persistence

Filters are automatically saved to URL parameters for sharing and bookmarking:

```typescript
// URL structure
/admin/costs?
  dateRange=6months&
  services=EC2,S3&
  accounts=123456789012&
  regions=us-east-1,us-west-2&
  tags=environment:prod,team:backend&
  granularity=MONTHLY&
  metric=UnblendedCost
```

### Filter Combinations

| Filter Type | Behavior | Example |
|-------------|----------|---------|
| **Date Range** | Inclusive boundaries | `2024-01-01` to `2024-01-31` |
| **Services** | OR logic within services | `EC2 OR S3 OR Lambda` |
| **Accounts** | OR logic within accounts | `Account-A OR Account-B` |
| **Regions** | OR logic within regions | `us-east-1 OR us-west-2` |
| **Tags** | AND logic between keys, OR within values | `env:prod AND team:(backend OR frontend)` |

### Performance Optimization

```typescript
// Smart filtering reduces API calls
const filterStrategy = {
  // Debounce filter changes
  debounceMs: 500,
  
  // Batch multiple filter updates  
  batchUpdates: true,
  
  // Cache common filter combinations
  cacheFilterResults: true,
  
  // Prefetch adjacent time ranges
  prefetchAdjacentRanges: true,
};
```

## 📈 Metrics & KPIs

### Core Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| **UnblendedCost** | Raw usage costs | Budget tracking, resource optimization |
| **AmortizedCost** | Cost with RI/SP discounts applied | True cost allocation |
| **BlendedCost** | Weighted average across accounts | Consolidated billing views |
| **NetUnblendedCost** | After credits and refunds | Actual spend analysis |
| **UsageQuantity** | Resource utilization | Efficiency metrics |

### Month-over-Month Calculations

```typescript
// MoM calculation logic
const calculateMoM = (current: number, previous: number) => ({
  absolute: current - previous,
  percentage: previous > 0 ? ((current - previous) / previous) * 100 : 
              current > 0 ? Infinity : 0,
  trend: current > previous ? 'increase' : 
         current < previous ? 'decrease' : 'stable'
});
```

### Forecasting

Built-in AWS Cost Anomaly Detection integration:

```typescript
// Forecast configuration
const forecastConfig = {
  granularity: 'MONTHLY',
  metric: 'UNBLENDED_COST', 
  predictionIntervalLevel: 80,  // 80% confidence interval
  timeRange: '3MONTHS',        // Forecast horizon
};
```

## 🛠️ Development

### Project Structure

```
dashboard/
├── src/
│   ├── app/
│   │   ├── admin/costs/          # Main dashboard pages
│   │   └── api/costs/            # API endpoints
│   ├── components/
│   │   ├── admin/costs/          # Cost-specific components
│   │   └── ui/                   # Reusable UI components
│   ├── lib/
│   │   ├── costs/                # Cost calculation utilities
│   │   ├── cache/                # Caching layer
│   │   └── resilience/           # Error handling, retries
│   └── hooks/                    # Custom React hooks
├── tests/
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── e2e/                      # End-to-end tests
├── docs/                         # Documentation
└── infra/                        # Infrastructure code
```

### Available Scripts

```bash
# Development
pnpm dev                  # Start dev server
pnpm build               # Build for production
pnpm start               # Start production server

# Testing
pnpm test                # Run all tests
pnpm test:unit           # Unit tests only
pnpm test:integration    # Integration tests
pnpm test:e2e           # End-to-end tests
pnpm test:coverage      # Coverage report

# Code Quality
pnpm lint               # ESLint checking
pnpm type-check         # TypeScript validation
pnpm format             # Prettier formatting

# Database
pnpm db:generate        # Generate Prisma client
pnpm db:push           # Push schema changes
pnpm db:migrate        # Run migrations
```

### Testing Strategy

- **Unit Tests**: Utilities (mom.ts, topn.ts, gap-filler.ts) - 90%+ coverage required
- **Integration Tests**: API endpoints, component interactions
- **Contract Tests**: API response shape validation
- **E2E Tests**: Critical user journeys with Playwright

## 🚨 Troubleshooting

### Common Issues

#### 1. "No data available" 

**Symptoms**: Empty charts, "No cost data" message

**Causes**:
- AWS credentials not configured
- Cost Explorer API disabled
- Date range outside available data
- Insufficient IAM permissions

**Solutions**:
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify Cost Explorer access
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics UnblendedCost

# Check IAM permissions
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::ACCOUNT:user/USERNAME --action-names ce:GetCostAndUsage
```

#### 2. Slow API responses

**Symptoms**: Long loading times, timeouts

**Causes**:
- Rate limiting from AWS
- Large date ranges
- Complex filter combinations
- Missing cache configuration

**Solutions**:
```typescript
// Enable caching
REDIS_URL="redis://localhost:6379"
COST_EXPLORER_CACHE_TTL=21600

// Reduce query scope
dateRange: '3months',  // instead of '2years'
granularity: 'MONTHLY', // instead of 'DAILY'

// Use progressive loading
const { data, isLoading } = useCostData({
  enabled: !!filters.dateRange,
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

#### 3. Athena query failures

**Symptoms**: "Query failed" errors, timeout messages

**Causes**:
- Missing CUR data
- Incorrect partition filters
- Query timeout
- Athena service limits

**Solutions**:
```sql
-- Check partition availability
SHOW PARTITIONS cur_database.cur_table;

-- Optimize query with partition pruning
WHERE year = '2024' 
  AND month = '01'
  AND day BETWEEN '01' AND '31'

-- Monitor query cost
SELECT 
  query_id,
  data_scanned_in_bytes / 1024 / 1024 / 1024 AS gb_scanned,
  execution_time_millis / 1000 AS execution_seconds
FROM athena_query_results;
```

### Performance Optimization

#### 1. Caching Strategy

```typescript
// Multi-layer caching
const cacheConfig = {
  // Browser cache (immediate)
  browser: { staleTime: 60000 }, // 1 minute
  
  // Redis cache (shared)
  redis: { ttl: 21600 }, // 6 hours
  
  // Database cache (persistent)
  database: { ttl: 86400 }, // 24 hours
};
```

#### 2. Query Optimization

```typescript
// Smart query batching
const optimizedQuery = {
  // Combine multiple metrics in single call
  metrics: ['UnblendedCost', 'UsageQuantity'],
  
  // Use appropriate granularity
  granularity: dateRange > 90 ? 'MONTHLY' : 'DAILY',
  
  // Limit groupBy dimensions
  groupBy: topServices.slice(0, 10),
};
```

#### 3. UI Performance

```typescript
// Component optimization
const CostsChart = memo(({ data }) => {
  const chartData = useMemo(() => 
    processChartData(data), [data]
  );
  
  return <ResponsiveContainer>
    {/* Chart implementation */}
  </ResponsiveContainer>;
});
```

## 🔒 Security

### Authentication

- **better-auth** with session management
- Role-based access control (RBAC)
- JWT token validation
- Secure cookie handling

### Data Protection

- AWS credentials stored securely
- No sensitive data in logs
- Request sanitization
- Rate limiting protection

### IAM Permissions

Minimum required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues", 
        "ce:GetUsageReport",
        "ce:GetCostAndUsageWithResources"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow", 
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-cur-bucket/*",
        "arn:aws:s3:::your-athena-results-bucket/*"
      ]
    }
  ]
}
```

## 📚 Additional Resources

- **Runbook**: [RUNBOOK.md](./docs/costs/RUNBOOK.md) - Operational procedures
- **Data Dictionary**: [DATA_DICTIONARY.md](./docs/costs/DATA_DICTIONARY.md) - Tag definitions and policies
- **API Documentation**: [API.md](./docs/costs/API.md) - Endpoint specifications
- **Architecture Decision Records**: [/docs/adr/](./docs/adr/) - Technical decisions

## 🤝 Contributing

1. **Code Standards**: ESLint + Prettier configuration
2. **Testing**: All new features require tests (90%+ coverage)
3. **Documentation**: Update relevant docs with changes
4. **Performance**: Consider caching and optimization impact

## 📞 Support

- **Technical Issues**: Create GitHub issue with logs and reproduction steps
- **Feature Requests**: Use GitHub discussions
- **Security Issues**: Email security@company.com
- **Operational Issues**: See [RUNBOOK.md](./docs/costs/RUNBOOK.md) for escalation procedures
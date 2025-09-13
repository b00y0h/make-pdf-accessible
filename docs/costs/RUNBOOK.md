# AWS Costs Dashboard - Operations Runbook

This runbook provides operational procedures for managing the AWS Costs Dashboard in production environments.

## 🚨 Emergency Procedures

### Dashboard Down/Unresponsive

**Symptoms**: HTTP 5xx errors, timeouts, blank pages

**Immediate Actions**:
1. Check health endpoint: `curl https://dashboard.company.com/api/health`
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Check database connectivity: `pg_isready -h db-host -p 5432`
4. Review application logs: `docker logs dashboard-app`

**Escalation**: If not resolved in 15 minutes, page on-call engineer

### Data Not Loading

**Symptoms**: "No data available", empty charts, stale timestamps

**Troubleshooting Steps**:
```bash
# 1. Check AWS API health
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost

# 2. Verify IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/dashboard-role \
  --action-names ce:GetCostAndUsage

# 3. Check cache status
redis-cli -h cache-host ping
redis-cli -h cache-host info memory

# 4. Test database queries
psql -h db-host -U dashboard_user -d dashboard \
  -c "SELECT COUNT(*) FROM cost_cache WHERE created_at > NOW() - INTERVAL '1 hour';"
```

### Athena Queries Failing

**Symptoms**: "Query failed", timeout errors, high query costs

**Investigation**:
```bash
# Check Athena service health
aws athena list-query-executions \
  --work-group costs-dashboard \
  --max-items 10

# Review recent query performance
aws athena get-query-execution \
  --query-execution-id QUERY_ID

# Check S3 bucket access
aws s3 ls s3://your-cur-bucket/cur-data/ --recursive | head -20
```

**Common Fixes**:
- Verify CUR delivery: Check S3 bucket for recent files
- Update partition metadata: `MSCK REPAIR TABLE cur_database.cur_table`
- Optimize query: Add partition filters, reduce date range
- Check workgroup limits: Review concurrent query limits

## 🔄 Routine Maintenance

### Daily Operations

#### Morning Health Check (9 AM UTC)
```bash
#!/bin/bash
# daily-health-check.sh

echo "=== Daily Health Check $(date) ==="

# 1. Application health
curl -sf https://dashboard.company.com/api/health || echo "❌ App health check failed"

# 2. Database connections
psql -h db-host -U dashboard_user -d dashboard -c "SELECT 1;" > /dev/null && echo "✅ Database OK" || echo "❌ Database failed"

# 3. Cache performance
redis-cli -h cache-host info stats | grep -E "keyspace_hits|keyspace_misses"

# 4. Recent data freshness
psql -h db-host -U dashboard_user -d dashboard -c "
  SELECT 
    source,
    MAX(last_updated) as latest_data,
    NOW() - MAX(last_updated) as age
  FROM cost_cache 
  GROUP BY source;"

# 5. Error rate (last 24h)
grep -c "ERROR" /var/log/dashboard/app.log | tail -1

echo "=== Health Check Complete ==="
```

#### Cache Cleanup (Weekly - Sunday 2 AM UTC)
```bash
#!/bin/bash
# weekly-cache-cleanup.sh

echo "=== Weekly Cache Cleanup $(date) ==="

# Remove expired cache entries
redis-cli -h cache-host --scan --pattern "cost:*" | \
  xargs redis-cli -h cache-host del

# Clean old database cache entries (>7 days)
psql -h db-host -U dashboard_user -d dashboard -c "
  DELETE FROM cost_cache 
  WHERE created_at < NOW() - INTERVAL '7 days';"

# Vacuum database
psql -h db-host -U dashboard_user -d dashboard -c "VACUUM ANALYZE cost_cache;"

echo "=== Cache Cleanup Complete ==="
```

### Weekly Operations

#### Performance Review (Monday 10 AM UTC)
```bash
#!/bin/bash
# weekly-performance-review.sh

echo "=== Weekly Performance Review $(date) ==="

# 1. Query performance analysis
psql -h db-host -U dashboard_user -d dashboard -c "
  SELECT 
    endpoint,
    AVG(response_time_ms) as avg_response,
    MAX(response_time_ms) as max_response,
    COUNT(*) as request_count
  FROM api_metrics 
  WHERE created_at > NOW() - INTERVAL '7 days'
  GROUP BY endpoint
  ORDER BY avg_response DESC;"

# 2. Cache hit rates
redis-cli -h cache-host info stats | grep -E "keyspace_hits|keyspace_misses" | \
  awk -F: '{print $1 ": " $2}' | \
  python3 -c "
import sys
stats = dict(line.strip().split(': ') for line in sys.stdin)
hits = int(stats.get('keyspace_hits', 0))
misses = int(stats.get('keyspace_misses', 0))
total = hits + misses
hit_rate = (hits / total * 100) if total > 0 else 0
print(f'Cache hit rate: {hit_rate:.2f}% ({hits}/{total})')
"

# 3. AWS API usage and costs
aws cloudwatch get-metric-statistics \
  --namespace AWS/CE \
  --metric-name APIRequestCount \
  --dimensions Name=Service,Value=Cost-Explorer \
  --start-time $(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

echo "=== Performance Review Complete ==="
```

### Monthly Operations

#### Athena Workgroup Rotation (1st of month)
```bash
#!/bin/bash
# monthly-athena-rotation.sh

echo "=== Monthly Athena Workgroup Rotation $(date) ==="

CURRENT_MONTH=$(date +%Y-%m)
NEW_WORKGROUP="costs-dashboard-${CURRENT_MONTH}"
OLD_WORKGROUP="costs-dashboard-$(date -d '2 months ago' +%Y-%m)"

# 1. Create new workgroup
aws athena create-work-group \
  --name ${NEW_WORKGROUP} \
  --description "Costs dashboard workgroup for ${CURRENT_MONTH}" \
  --configuration "
    ResultConfigurationUpdates={
      OutputLocation=s3://your-athena-results-bucket/${CURRENT_MONTH}/
    },
    EnforceWorkGroupConfiguration=true,
    PublishCloudWatchMetrics=true,
    BytesScannedCutoffPerQuery=1099511627776
  "

# 2. Update application configuration
kubectl patch configmap dashboard-config \
  --type merge \
  -p '{"data":{"ATHENA_WORKGROUP":"'${NEW_WORKGROUP}'"}}'

# 3. Restart application to pick up new config
kubectl rollout restart deployment/dashboard

# 4. Verify new workgroup is working
sleep 60
curl -sf https://dashboard.company.com/api/costs/athena/timeseries?preset=1month

# 5. Delete old workgroup (after 24 hours)
echo "Remember to delete old workgroup ${OLD_WORKGROUP} after 24 hours"

echo "=== Workgroup Rotation Complete ==="
```

## 🔧 Configuration Management

### Environment Variables

**Production Configuration**:
```bash
# Application
NODE_ENV=production
PORT=3001
LOG_LEVEL=info

# Database
DATABASE_URL="postgresql://dashboard_user:${DB_PASSWORD}@prod-db:5432/dashboard"
AUTH_DATABASE_URL="postgresql://auth_user:${AUTH_PASSWORD}@prod-db:5432/better_auth"

# AWS
AWS_REGION=us-east-1
COST_EXPLORER_CACHE_TTL=21600  # 6 hours
COST_EXPLORER_RATE_LIMIT=5    # requests/second

# CUR/Athena  
ATHENA_WORKGROUP=costs-dashboard-2024-01
ATHENA_RESULT_BUCKET=your-athena-results-bucket
CUR_DATABASE=cur_database
CUR_TABLE=cur_table

# Cache
REDIS_URL="redis://prod-cache:6379"
MEMORY_CACHE_SIZE=1000

# Security
BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}
BETTER_AUTH_URL=https://dashboard.company.com
```

### Feature Flags

Control dashboard features via environment variables:

```bash
# Data sources
ENABLE_COST_EXPLORER=true
ENABLE_ATHENA=true

# Features
ENABLE_FORECASTING=true
ENABLE_ANOMALY_DETECTION=false
ENABLE_DATA_EXPORT=true

# UI Features
ENABLE_ADVANCED_FILTERS=true
ENABLE_CUSTOM_DATE_RANGES=true
SHOW_BETA_FEATURES=false
```

### Scaling Configuration

**Auto-scaling parameters**:
```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dashboard-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dashboard
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 📊 Monitoring & Alerts

### Key Metrics

#### Application Metrics
```bash
# Response time percentiles
dashboard_http_request_duration_seconds{quantile="0.5"}
dashboard_http_request_duration_seconds{quantile="0.95"}
dashboard_http_request_duration_seconds{quantile="0.99"}

# Error rates
rate(dashboard_http_requests_total{status=~"5.."}[5m])
rate(dashboard_http_requests_total[5m])

# Cache performance
dashboard_cache_hits_total / (dashboard_cache_hits_total + dashboard_cache_misses_total)

# Database connections
dashboard_database_connections_active
dashboard_database_connections_max
```

#### AWS Cost Explorer Metrics
```bash
# API usage
aws_cost_explorer_api_requests_total
aws_cost_explorer_api_errors_total
aws_cost_explorer_api_throttles_total

# Response times
aws_cost_explorer_api_duration_seconds

# Data freshness
aws_cost_explorer_data_age_hours
```

#### Athena Metrics
```bash
# Query metrics
athena_queries_total
athena_query_duration_seconds
athena_data_scanned_bytes

# Costs
athena_query_cost_usd
```

### Alerting Rules

#### Critical Alerts (Page immediately)
```yaml
# Application down
- alert: DashboardDown
  expr: up{job="dashboard"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Dashboard application is down"

# High error rate
- alert: HighErrorRate
  expr: rate(dashboard_http_requests_total{status=~"5.."}[5m]) / rate(dashboard_http_requests_total[5m]) > 0.1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate: {{ $value | humanizePercentage }}"

# Database connection failures
- alert: DatabaseConnectionFailure
  expr: dashboard_database_connection_errors_total > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Database connection failures detected"
```

#### Warning Alerts (Slack notification)
```yaml
# Slow API responses
- alert: SlowAPIResponses
  expr: histogram_quantile(0.95, dashboard_http_request_duration_seconds) > 5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "95th percentile response time > 5s"

# AWS API throttling
- alert: AWSAPIThrottling
  expr: aws_cost_explorer_api_throttles_total > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "AWS Cost Explorer API throttling detected"

# Stale data
- alert: StaleData
  expr: aws_cost_explorer_data_age_hours > 72
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Cost data is {{ $value }} hours old"
```

### Monitoring Dashboard

Key panels for operational monitoring:

1. **Application Health**
   - Request rate and error rate
   - Response time percentiles
   - Active connections

2. **AWS Integration**
   - Cost Explorer API calls and errors
   - Athena query performance
   - Data freshness indicators

3. **Infrastructure**
   - CPU and memory utilization
   - Database performance
   - Cache hit rates

4. **Business Metrics**
   - Daily active users
   - Feature usage statistics
   - Cost data volume processed

## 🔍 Troubleshooting Guide

### Common Issues

#### 1. Intermittent Data Loading Failures

**Symptoms**: Random "loading failed" errors, inconsistent data

**Root Causes**:
- AWS API rate limiting
- Network timeouts
- Cache inconsistencies

**Investigation**:
```bash
# Check recent errors
grep -A 5 -B 5 "loading failed" /var/log/dashboard/app.log | tail -50

# Verify AWS API health
for i in {1..5}; do
  aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics UnblendedCost \
    --query 'ResponseMetadata.HTTPStatusCode'
  sleep 2
done

# Check cache consistency
redis-cli -h cache-host --scan --pattern "cost:*" | \
  xargs -I{} redis-cli -h cache-host ttl {}
```

**Resolution**:
```bash
# Clear cache to force refresh
redis-cli -h cache-host flushdb

# Restart application
kubectl rollout restart deployment/dashboard

# Monitor for stability
watch -n 30 'curl -s https://dashboard.company.com/api/health | jq .status'
```

#### 2. Athena Query Performance Issues

**Symptoms**: Slow queries, high costs, timeouts

**Investigation**:
```sql
-- Check query history
SELECT 
  query_execution_id,
  query,
  status,
  data_scanned_in_bytes / 1024 / 1024 / 1024 AS gb_scanned,
  execution_time_millis / 1000 AS execution_seconds,
  creation_time
FROM athena_query_executions 
WHERE creation_time > CURRENT_DATE - INTERVAL '7' DAY
ORDER BY gb_scanned DESC
LIMIT 20;

-- Check partition health
SHOW PARTITIONS cur_database.cur_table;

-- Verify data distribution
SELECT 
  year,
  month,
  COUNT(*) as record_count,
  SUM(line_item_unblended_cost) as total_cost
FROM cur_database.cur_table
WHERE year = '2024'
GROUP BY year, month
ORDER BY year, month;
```

**Optimization**:
```sql
-- Optimized query template
SELECT 
  line_item_product_code as service,
  DATE_FORMAT(line_item_usage_start_date, '%Y-%m') as month,
  SUM(line_item_unblended_cost) as cost
FROM cur_database.cur_table
WHERE year = '2024'
  AND month = '01'
  AND line_item_usage_start_date >= DATE('2024-01-01')
  AND line_item_usage_start_date < DATE('2024-02-01')
  AND line_item_line_item_type = 'Usage'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 100;
```

#### 3. Memory Issues

**Symptoms**: OOM kills, slow performance, high memory usage

**Investigation**:
```bash
# Check current memory usage
kubectl top pods -l app=dashboard

# Review memory limits
kubectl describe pod dashboard-xxx | grep -A 10 Limits

# Check for memory leaks
curl https://dashboard.company.com/api/debug/memory | jq .

# Database connection pool status
psql -h db-host -U dashboard_user -d dashboard -c "
  SELECT 
    state,
    COUNT(*) 
  FROM pg_stat_activity 
  WHERE datname = 'dashboard' 
  GROUP BY state;"
```

**Resolution**:
```bash
# Increase memory limits
kubectl patch deployment dashboard -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "dashboard",
            "resources": {
              "limits": {
                "memory": "2Gi"
              },
              "requests": {
                "memory": "1Gi"
              }
            }
          }
        ]
      }
    }
  }
}'

# Restart application
kubectl rollout restart deployment/dashboard
```

### Query Cost Management

#### Monitor Athena Costs

```bash
#!/bin/bash
# athena-cost-monitor.sh

# Get query costs for last 7 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/Athena \
  --metric-name DataScannedInBytes \
  --dimensions Name=WorkGroup,Value=costs-dashboard \
  --start-time $(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum | \
  jq -r '.Datapoints[] | "\(.Timestamp): \(.Sum / 1024 / 1024 / 1024 | floor) GB"'

# Calculate approximate cost ($5 per TB)
TOTAL_GB=$(aws cloudwatch get-metric-statistics \
  --namespace AWS/Athena \
  --metric-name DataScannedInBytes \
  --dimensions Name=WorkGroup,Value=costs-dashboard \
  --start-time $(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 604800 \
  --statistics Sum \
  --query 'Datapoints[0].Sum' \
  --output text | \
  awk '{print $1 / 1024 / 1024 / 1024}')

COST_USD=$(echo "$TOTAL_GB / 1024 * 5" | bc -l)
echo "Estimated Athena cost (7 days): \$$(printf '%.2f' $COST_USD)"
```

#### Set Query Limits

```bash
# Update workgroup with cost controls
aws athena update-work-group \
  --work-group costs-dashboard \
  --configuration-updates "
    BytesScannedCutoffPerQuery=1099511627776,
    EnforceWorkGroupConfiguration=true,
    PublishCloudWatchMetrics=true
  "
```

## 📋 Runbook Checklist

### Incident Response

- [ ] **Acknowledge**: Respond to alert within 5 minutes
- [ ] **Assess**: Determine impact and severity
- [ ] **Investigate**: Follow troubleshooting steps
- [ ] **Mitigate**: Apply immediate fixes
- [ ] **Communicate**: Update stakeholders on status
- [ ] **Resolve**: Implement permanent solution
- [ ] **Document**: Record findings and actions
- [ ] **Review**: Conduct post-incident review

### Release Deployment

- [ ] **Pre-deploy**: Run health checks
- [ ] **Backup**: Create database backup
- [ ] **Deploy**: Execute deployment steps
- [ ] **Verify**: Test critical functionality
- [ ] **Monitor**: Watch metrics for anomalies
- [ ] **Rollback**: Revert if issues detected
- [ ] **Notify**: Inform team of completion

### Monthly Maintenance

- [ ] **Review**: Performance metrics and costs
- [ ] **Update**: Rotate Athena workgroups
- [ ] **Clean**: Remove old cache entries
- [ ] **Patch**: Apply security updates
- [ ] **Backup**: Verify backup integrity
- [ ] **Document**: Update runbook if needed

## 📞 Escalation Procedures

### Severity Levels

**P1 - Critical (Page Immediately)**
- Dashboard completely down
- Data security breach
- AWS account compromise

**P2 - High (15 min response)**
- Partial functionality loss
- High error rates
- Performance degradation

**P3 - Medium (2 hour response)**
- Minor feature issues
- Non-critical errors
- Monitoring alerts

**P4 - Low (Next business day)**
- Enhancement requests
- Documentation updates
- Non-urgent maintenance

### Contact Information

```
Primary On-Call: +1-XXX-XXX-XXXX
Secondary On-Call: +1-XXX-XXX-XXXX
Escalation Manager: +1-XXX-XXX-XXXX

Slack Channels:
#dashboard-alerts (critical)
#dashboard-ops (operational)
#dashboard-dev (development)

Email Lists:
dashboard-ops@company.com
dashboard-team@company.com
```

### External Dependencies

**AWS Support**
- Business Support: Case priority system
- Enterprise Support: Phone support available
- Account Manager: For billing/service issues

**Third-party Services**
- Database Provider: Support portal
- Monitoring Service: Status page
- CDN Provider: Support tickets

---

*This runbook should be reviewed and updated monthly. Last updated: $(date)*
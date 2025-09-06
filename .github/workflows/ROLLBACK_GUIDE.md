# Deployment Rollback and Recovery Guide

This guide covers the rollback and recovery mechanisms implemented for the Make PDF Accessible platform.

## Overview

The platform includes comprehensive rollback capabilities for all service types:

- **API Services**: Blue/green deployment with automatic rollback
- **Web Applications**: S3 deployment with CloudFront cache invalidation
- **Lambda Functions**: Version-based rollback with health checks
- **Infrastructure**: Terraform state management and rollback procedures

## Automatic Rollback System

### Health Check Monitoring

All deployments include health check monitoring that can trigger automatic rollbacks:

- **Threshold**: 2 consecutive health check failures
- **Monitoring**: Continuous health checks post-deployment
- **Response**: Automatic rollback to previous stable version

### Rollback Triggers

Automatic rollbacks are triggered by:

1. Health check failures exceeding threshold
2. Deployment process failures
3. Performance degradation detection
4. Manual emergency triggers

## Manual Rollback Procedures

### Emergency Rollback Workflow

Use the manual rollback workflow for emergency situations:

```bash
# Trigger via GitHub CLI
gh workflow run rollback.yml \
  --field service=api \
  --field environment=prod \
  --field reason="Critical bug in production" \
  --field skip_health_checks=false

# Or via GitHub UI
# Navigate to Actions > Rollback > Run workflow
```

### Rollback Options

| Parameter            | Description                         | Options                                                   |
| -------------------- | ----------------------------------- | --------------------------------------------------------- |
| `service`            | Service to rollback                 | `api`, `web`, `lambda-functions`, `infrastructure`, `all` |
| `environment`        | Target environment                  | `dev`, `staging`, `prod`                                  |
| `target_version`     | Specific version to rollback to     | Version string or empty for auto-detect                   |
| `reason`             | Rollback reason                     | Free text description                                     |
| `skip_health_checks` | Skip health checks (emergency only) | `true`/`false`                                            |

## Service-Specific Rollback Procedures

### API Service Rollback

The API service uses Lambda aliases for blue/green deployment:

1. **Current State Detection**: Identifies current LIVE alias version
2. **Target Version**: Automatically selects previous stable version
3. **Database Coordination**: Rolls back database migrations if needed
4. **Alias Update**: Updates LIVE alias to previous version
5. **Health Verification**: Runs health checks on rolled-back version
6. **Cache Invalidation**: Clears API Gateway cache

```yaml
# Example API rollback
- name: Rollback API
  uses: ./.github/workflows/rollback.yml
  with:
    service: api
    environment: prod
    reason: 'Performance regression detected'
```

### Web Application Rollback

Web applications are deployed to S3 with CloudFront distribution:

1. **Deployment History**: Retrieves previous deployment from S3
2. **File Restoration**: Syncs previous version back to S3 root
3. **Cache Invalidation**: Invalidates CloudFront cache globally
4. **Verification**: Confirms web application accessibility

```yaml
# Example web rollback
- name: Rollback Web
  uses: ./.github/workflows/rollback.yml
  with:
    service: web
    environment: prod
    reason: 'UI breaking changes'
```

### Lambda Functions Rollback

Individual Lambda functions can be rolled back independently:

1. **Version Detection**: Identifies current and previous versions
2. **Function Update**: Updates function configuration to previous version
3. **Health Check**: Invokes function to verify operation
4. **Monitoring**: Continues monitoring for stability

```yaml
# Example Lambda rollback (all functions)
- name: Rollback Lambda Functions
  uses: ./.github/workflows/rollback.yml
  with:
    service: lambda-functions
    environment: prod
    reason: 'Memory leak in OCR service'
```

### Infrastructure Rollback

Infrastructure rollbacks require careful consideration:

1. **State Analysis**: Reviews current Terraform state
2. **Manual Review**: Requires manual intervention for safety
3. **Selective Rollback**: Can target specific resources
4. **Validation**: Extensive validation before applying changes

> **⚠️ Warning**: Infrastructure rollbacks require manual review and approval.

## Database Migration Rollback

### Automatic Coordination

Database migrations are automatically coordinated during API rollbacks:

1. **Migration Detection**: Identifies current migration state
2. **Target Migration**: Determines rollback target migration
3. **Backup Creation**: Creates database backup before rollback
4. **Migration Rollback**: Executes Alembic downgrade
5. **Verification**: Confirms migration state after rollback

### Manual Database Rollback

For manual database rollbacks:

```bash
# Using the database rollback action
- name: Rollback Database
  uses: ./.github/actions/db-migration-rollback
  with:
    environment: prod
    target_migration: "abc123def456"  # Optional
    dry_run: false
    database_url: ${{ secrets.DATABASE_URL }}
    backup_before_rollback: true
```

### Migration Safety

- **Backup Required**: Always creates backup before rollback
- **Dry Run Available**: Test rollback without execution
- **Validation**: Verifies migration state after rollback
- **Data Loss Prevention**: Warns about potential data loss

## Cache Invalidation During Rollbacks

### Comprehensive Cache Clearing

All rollbacks include comprehensive cache invalidation:

1. **CloudFront**: Global cache invalidation for web assets
2. **API Gateway**: Stage cache flushing for API endpoints
3. **Redis**: Application cache clearing
4. **Application**: Internal cache invalidation

### Cache Types

| Cache Type  | Invalidation Method | Wait Time    |
| ----------- | ------------------- | ------------ |
| CloudFront  | Global invalidation | 5-15 minutes |
| API Gateway | Stage cache flush   | Immediate    |
| Redis       | FLUSHDB command     | Immediate    |
| Application | HTTP endpoint call  | Immediate    |

```yaml
# Example cache invalidation
- name: Invalidate Caches
  uses: ./.github/actions/cache-invalidation
  with:
    environment: prod
    cache_types: 'cloudfront,apigateway,redis,application'
    wait_for_completion: true
```

## Deployment State Tracking

### State Management

The system tracks deployment state using DynamoDB:

- **Service State**: Current and previous versions per service
- **Health Status**: Continuous health monitoring results
- **Failure Tracking**: Counts consecutive failures
- **Rollback History**: Complete rollback event log

### State Queries

```yaml
# Get current deployment state
- name: Get Deployment State
  uses: ./.github/actions/deployment-state
  with:
    action: get
    service: api
    environment: prod
```

### State Reset

```yaml
# Reset failure count after successful deployment
- name: Reset State
  uses: ./.github/actions/deployment-state
  with:
    action: reset
    service: api
    environment: prod
    version: 'v1.2.3'
```

## Recovery Procedures

### Post-Rollback Recovery

After a successful rollback:

1. **Root Cause Analysis**: Investigate the original failure
2. **Fix Development**: Develop and test fixes
3. **Staged Deployment**: Deploy fixes through dev → staging → prod
4. **Monitoring**: Enhanced monitoring during recovery deployment

### Rollback Failure Recovery

If a rollback itself fails:

1. **Manual Intervention**: Immediate manual investigation required
2. **Service Isolation**: Isolate affected services
3. **Emergency Contacts**: Alert on-call engineers
4. **Backup Restoration**: Consider database backup restoration
5. **Infrastructure Reset**: May require infrastructure-level recovery

## Monitoring and Alerting

### Rollback Notifications

All rollback events trigger notifications:

- **Slack/Teams**: Real-time rollback notifications
- **Email**: Detailed rollback reports
- **PagerDuty**: High-priority alerts for production rollbacks
- **Dashboard**: Visual rollback status updates

### Monitoring Dashboards

Key metrics to monitor during rollbacks:

- **Service Health**: Endpoint availability and response times
- **Error Rates**: Application and infrastructure error rates
- **Performance**: Response times and throughput
- **User Impact**: User-facing service availability

## Best Practices

### Rollback Planning

1. **Test Rollbacks**: Regularly test rollback procedures in staging
2. **Documentation**: Keep rollback procedures up-to-date
3. **Training**: Ensure team familiarity with rollback processes
4. **Automation**: Prefer automated rollbacks over manual procedures

### Prevention

1. **Comprehensive Testing**: Thorough testing before deployment
2. **Gradual Rollouts**: Use blue/green and canary deployments
3. **Health Checks**: Implement comprehensive health monitoring
4. **Rollback Testing**: Test rollback procedures with each deployment

### Communication

1. **Status Updates**: Regular communication during rollback events
2. **Post-Mortem**: Conduct post-mortem analysis after rollbacks
3. **Documentation**: Document lessons learned from rollback events
4. **Process Improvement**: Continuously improve rollback procedures

## Troubleshooting

### Common Rollback Issues

| Issue                             | Cause                            | Solution                                   |
| --------------------------------- | -------------------------------- | ------------------------------------------ |
| Health checks fail after rollback | Previous version also has issues | Manual investigation required              |
| Database rollback fails           | Migration dependencies           | Review migration history                   |
| Cache invalidation timeout        | CloudFront propagation delay     | Wait for completion or manual verification |
| Permission errors                 | IAM role issues                  | Verify AWS credentials and permissions     |

### Emergency Contacts

For rollback emergencies:

1. **On-Call Engineer**: Primary contact for immediate response
2. **DevOps Team**: Infrastructure and deployment expertise
3. **Database Admin**: Database-specific rollback issues
4. **Security Team**: Security-related rollback concerns

### Escalation Procedures

1. **Level 1**: Automatic rollback attempts
2. **Level 2**: Manual rollback procedures
3. **Level 3**: Emergency manual intervention
4. **Level 4**: Infrastructure-level recovery

## Testing Rollback Procedures

### Regular Testing

Test rollback procedures regularly:

```bash
# Test rollback in staging environment
gh workflow run rollback.yml \
  --field service=api \
  --field environment=staging \
  --field reason="Rollback procedure test" \
  --field skip_health_checks=false
```

### Rollback Drills

Conduct regular rollback drills:

1. **Monthly Drills**: Test rollback procedures monthly
2. **Scenario Testing**: Test various failure scenarios
3. **Team Training**: Ensure all team members can execute rollbacks
4. **Documentation Updates**: Update procedures based on drill results

## Compliance and Auditing

### Audit Trail

All rollback events are logged for compliance:

- **Event Logging**: Complete rollback event history
- **User Attribution**: Track who initiated rollbacks
- **Reason Documentation**: Require rollback reason documentation
- **Approval Tracking**: Log approval workflows for production rollbacks

### Compliance Requirements

- **Change Management**: Rollbacks follow change management procedures
- **Documentation**: All rollbacks must be documented
- **Approval**: Production rollbacks require appropriate approvals
- **Notification**: Stakeholders must be notified of rollback events

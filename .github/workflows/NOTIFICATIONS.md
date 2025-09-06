# Deployment Notifications and Monitoring System

This document describes the comprehensive notification and monitoring system implemented for the PDF Accessibility Platform's CI/CD workflows.

## Overview

The notification system provides real-time alerts for:

- Deployment start/completion events
- Success and failure notifications with detailed context
- Manual approval requirements
- Security event alerts
- Rollback notifications
- High-priority alerts for critical issues

## Supported Platforms

### Slack Integration

- Rich message formatting with color-coded attachments
- Interactive buttons for quick actions
- Detailed deployment context and metadata
- Thread-based conversations for related events

### Microsoft Teams Integration

- Adaptive card format with structured information
- Action buttons for deployment URLs and workflow links
- Comprehensive deployment summaries
- Integration with Teams channels and mentions

## Configuration

### Required GitHub Secrets

Add the following secrets to your GitHub repository:

```bash
# Webhook URL for notifications (Slack or Teams)
DEPLOYMENT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
# or
DEPLOYMENT_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK

# AWS credentials for security monitoring
AWS_ACCOUNT_ID=123456789012
AWS_REGION=us-east-1

# IAM role ARNs for each workflow
GITHUB_INFRASTRUCTURE_CI_ROLE_ARN=arn:aws:iam::123456789012:role/GitHubInfrastructureCI
GITHUB_LAMBDA_DEPLOY_ROLE_ARN=arn:aws:iam::123456789012:role/GitHubLambdaDeploy
GITHUB_WEB_DEPLOY_ROLE_ARN=arn:aws:iam::123456789012:role/GitHubWebDeploy
GITHUB_API_DEPLOY_ROLE_ARN=arn:aws:iam::123456789012:role/GitHubAPIDeploy
```

### Slack Webhook Setup

1. Go to your Slack workspace settings
2. Navigate to "Apps" → "Incoming Webhooks"
3. Create a new webhook for your desired channel
4. Copy the webhook URL to `DEPLOYMENT_WEBHOOK_URL` secret

### Teams Webhook Setup

1. Go to your Teams channel
2. Click "..." → "Connectors" → "Incoming Webhook"
3. Configure the webhook with a name and image
4. Copy the webhook URL to `DEPLOYMENT_WEBHOOK_URL` secret

## Notification Types

### 1. Deployment Start Notifications

Sent when a deployment begins:

```json
{
  "type": "start",
  "service": "infrastructure|lambda-functions|web-application|api",
  "environment": "dev|staging|prod",
  "version": "main-abc123-20240101-120000",
  "trigger": "push|workflow_dispatch|schedule"
}
```

### 2. Success Notifications

Sent when deployments complete successfully:

```json
{
  "type": "success",
  "service": "service-name",
  "deployment_url": "https://app.example.com",
  "test_coverage": "85.2%",
  "security_status": "clean|warning|alert"
}
```

### 3. Failure Notifications

Sent when deployments fail with detailed error information:

```json
{
  "type": "failure",
  "error_details": "Detailed error message and troubleshooting steps",
  "failure_stage": "testing|packaging|deployment",
  "rollback_status": "automatic|manual|not_required"
}
```

### 4. Manual Approval Notifications

Sent when manual approval is required:

```json
{
  "type": "approval_required",
  "approval_url": "https://github.com/repo/actions/runs/123456",
  "deployment_context": "Infrastructure changes require manual review"
}
```

### 5. Rollback Notifications

Sent when automatic or manual rollbacks occur:

```json
{
  "type": "rollback",
  "rollback_reason": "deployment_failure|health_check_failure|manual",
  "rollback_method": "blue_green_automatic|s3_restore|terraform_rollback",
  "service_availability": "maintained|interrupted"
}
```

### 6. Security Alert Notifications

Sent when security events are detected:

```json
{
  "type": "security_alert",
  "security_event": "Detailed security event description",
  "security_level": "low|medium|high|critical",
  "immediate_action_required": true
}
```

## Security Monitoring

### Monitored Events

The security monitoring system tracks:

1. **Authentication Failures**
   - Failed AWS API calls
   - Invalid credentials usage
   - Unauthorized access attempts

2. **API Security Events**
   - 401/403 HTTP responses
   - Suspicious request patterns
   - Rate limiting violations

3. **Lambda Function Security**
   - Unauthorized invocations
   - Error patterns indicating attacks
   - Unusual execution patterns

4. **Deployment Security**
   - Deployments from unexpected sources
   - Unusual deployment timing
   - Configuration changes outside CI/CD

### Security Alert Thresholds

- **Clean (0 events)**: No security concerns
- **Warning (1-5 events)**: Minor security events detected
- **Alert (6+ events)**: Significant security concerns requiring immediate attention

### Security Monitoring Duration

- **Infrastructure**: 10 minutes post-deployment
- **Lambda Functions**: 5 minutes post-deployment
- **Web Application**: 5 minutes post-deployment
- **API**: 10 minutes post-deployment (includes blue/green monitoring)

## Workflow Integration

### Infrastructure CI (`infra-ci.yml`)

- Terraform validation and planning notifications
- Manual approval alerts for production deployments
- Infrastructure security monitoring
- Rollback notifications for failed deployments

### Lambda Deployment (`build-and-deploy-lambda.yml`)

- Multi-service deployment progress
- Individual function health check results
- Container security scanning alerts
- Function-specific error notifications

### Web Application CI (`web-ci.yml`)

- Build and test result notifications
- S3 deployment and CloudFront invalidation status
- Performance and accessibility test results
- Cache invalidation and CDN propagation alerts

### API CI (`api-ci.yml`)

- Blue/green deployment progress notifications
- Traffic shifting and health check results
- Database migration status
- API performance monitoring alerts

## Customization

### Adding Custom Notification Types

1. Extend the notification action in `.github/actions/notify-deployment/action.yml`
2. Add new notification type handling in the payload preparation
3. Update color schemes and icons for the new type
4. Add appropriate fields for the notification content

### Custom Webhook Integrations

To integrate with other platforms:

1. Create a new notification action or extend the existing one
2. Add platform detection logic based on webhook URL patterns
3. Implement platform-specific payload formatting
4. Test with your platform's webhook requirements

### Environment-Specific Configurations

Configure different notification behaviors per environment:

```yaml
# In workflow files
- name: Notify deployment
  if: |
    (github.ref == 'refs/heads/main' && secrets.PROD_WEBHOOK_URL != '') ||
    (github.ref == 'refs/heads/develop' && secrets.DEV_WEBHOOK_URL != '')
  uses: ./.github/actions/notify-deployment
  with:
    webhook_url: ${{ github.ref == 'refs/heads/main' && secrets.PROD_WEBHOOK_URL || secrets.DEV_WEBHOOK_URL }}
```

## Troubleshooting

### Common Issues

1. **Notifications Not Received**
   - Verify webhook URL is correct and accessible
   - Check GitHub secrets are properly configured
   - Ensure the webhook service (Slack/Teams) is operational

2. **Security Monitoring Failures**
   - Verify AWS IAM permissions for CloudTrail and CloudWatch Logs access
   - Check AWS region configuration matches your resources
   - Ensure log groups exist and contain relevant data

3. **Incomplete Notification Data**
   - Check workflow job dependencies and outputs
   - Verify all required inputs are provided to notification actions
   - Review workflow logs for missing context data

### Debug Mode

Enable debug logging by adding to workflow environment:

```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

### Testing Notifications

Test notifications without full deployments:

```bash
# Manual workflow dispatch with test parameters
gh workflow run infra-ci.yml \
  --field environment=dev \
  --field dry_run=true
```

## Best Practices

1. **Notification Frequency**
   - Avoid notification spam by consolidating related events
   - Use thread replies for follow-up notifications
   - Implement rate limiting for high-frequency events

2. **Security Considerations**
   - Never include sensitive data in notification messages
   - Use secure webhook URLs with proper authentication
   - Regularly rotate webhook URLs and secrets

3. **Message Content**
   - Keep messages concise but informative
   - Include actionable information and next steps
   - Provide direct links to relevant resources

4. **Monitoring and Maintenance**
   - Regularly test notification delivery
   - Monitor webhook endpoint availability
   - Update notification templates as workflows evolve

## Integration Examples

### Slack Bot Commands

Create Slack bot commands for common actions:

```javascript
// Slack bot integration example
app.command('/deploy-status', async ({ command, ack, respond }) => {
  await ack();

  const workflowRuns = await github.actions.listWorkflowRuns({
    owner: 'your-org',
    repo: 'your-repo',
    workflow_id: 'infra-ci.yml',
  });

  await respond({
    text: `Latest deployment status: ${workflowRuns.data.workflow_runs[0].status}`,
  });
});
```

### Teams Adaptive Cards

Create rich Teams notifications with adaptive cards:

```json
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.2",
  "body": [
    {
      "type": "TextBlock",
      "text": "Deployment Notification",
      "weight": "Bolder",
      "size": "Medium"
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "View Deployment",
      "url": "https://app.example.com"
    }
  ]
}
```

## Monitoring Dashboard

Consider creating a monitoring dashboard that aggregates:

- Deployment frequency and success rates
- Security event trends
- Notification delivery metrics
- System performance during deployments

This can be implemented using tools like:

- Grafana with GitHub Actions metrics
- AWS CloudWatch dashboards
- Custom web dashboard with GitHub API integration

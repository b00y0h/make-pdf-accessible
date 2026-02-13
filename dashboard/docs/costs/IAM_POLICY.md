# AWS Cost Explorer IAM Policy Configuration

## Required Permissions

The application requires the following AWS Cost Explorer permissions to function properly:

### IAM Policy JSON

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues",
        "ce:GetCostForecast",
        "ce:GetUsageForecast",
        "ce:GetReservationCoverage",
        "ce:GetReservationPurchaseRecommendation",
        "ce:GetReservationUtilization",
        "ce:ListCostCategoryDefinitions",
        "ce:GetCostCategories"
      ],
      "Resource": "*"
    }
  ]
}
```

## Cost Allocation Tags

The following cost allocation tags must be activated in the AWS Billing Console:

### Required Tags

- `application` - Identifies the application or service
- `environment` - Environment type (dev, staging, prod)
- `component` - Component or service within the application
- `cost_center` - Cost center for billing attribution
- `service` - AWS service identifier
- `managed_by` - Team or person responsible for the resource

### Activation Steps

1. Navigate to AWS Billing Console → Cost allocation tags
2. Activate each of the required tags listed above
3. Wait 24 hours for tags to appear in Cost Explorer data
4. Verify tags are appearing in Cost Explorer reports

### Environment Configuration

Set the following environment variables:

```env
COST_ALLOCATION_TAGS=application,environment,component,cost_center,service,managed_by
AWS_PAYER_ACCOUNT_ID=your-payer-account-id
AWS_LINKED_ACCOUNT_IDS=account1,account2,account3
COST_SOURCE=ce
```

## Testing Access

To test that the IAM permissions are working correctly:

1. Ensure AWS credentials are configured
2. Run the Cost Explorer API test (see Testing section in README)
3. Verify that cost data is returned without errors

## Troubleshooting

### Common Issues

- **Access Denied**: Verify the IAM policy is attached to the correct role/user
- **No Data Returned**: Ensure cost allocation tags are activated and have been active for at least 24 hours
- **Tag Not Found**: Check that tags are consistently applied to resources and activated in billing console

### Rate Limits

AWS Cost Explorer has rate limits:

- GetCostAndUsage: 5 requests per second
- GetDimensionValues: 5 requests per second
- GetCostForecast: 5 requests per second

The application implements caching to stay within these limits.

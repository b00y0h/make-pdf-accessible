# DNSimple Domain Configuration Guide

This guide walks you through setting up DNS records for makepdfaccessible.com using DNSimple.

## Prerequisites

1. **Domain registered with DNSimple**: makepdfaccessible.com
2. **AWS Infrastructure deployed**: Run `terraform apply` first to create the necessary resources
3. **DNSimple API access**: Log in to your DNSimple account

## Step 1: Deploy Terraform Infrastructure

First, deploy your AWS infrastructure to get the necessary endpoints:

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

After successful deployment, Terraform will output the DNS configuration. Save this output as you'll need it for the next steps.

## Step 2: Get DNS Configuration from Terraform

Run this command to see all DNS records you need to configure:

```bash
terraform output -json dns_configuration > dns_config.json
```

## Step 3: Configure SSL Certificate Validation Records

These records are required for AWS to validate your SSL certificates. You must add these BEFORE the certificates can be issued.

### In DNSimple:

1. Go to your domain: `makepdfaccessible.com`
2. Click on "DNS" in the domain management menu
3. Add the following validation records (you'll get the exact values from Terraform output):

#### For CloudFront Certificate (covers root domain and all subdomains):
- **Type**: CNAME
- **Name**: `_[random-string].makepdfaccessible.com`
- **Content**: `_[validation-string].acm-validations.aws.`
- **TTL**: 300

#### For API Certificate:
- **Type**: CNAME  
- **Name**: `_[random-string].api.makepdfaccessible.com`
- **Content**: `_[validation-string].acm-validations.aws.`
- **TTL**: 300

**Important**: Wait 5-10 minutes after adding these records for DNS propagation before proceeding.

## Step 4: Add Application DNS Records

Once certificates are validated, add these records in DNSimple:

### 1. Root Domain (Marketing Site)
- **Type**: ALIAS (or ANAME if ALIAS not available)
- **Name**: `@` (or leave blank for root)
- **Content**: `[cloudfront-distribution-id].cloudfront.net`
- **TTL**: 300

### 2. WWW Redirect
- **Type**: CNAME
- **Name**: `www`
- **Content**: `[cloudfront-distribution-id].cloudfront.net`
- **TTL**: 300

### 3. Dashboard Subdomain
- **Type**: CNAME
- **Name**: `dashboard`
- **Content**: `[cloudfront-distribution-id].cloudfront.net`
- **TTL**: 300

### 4. API Subdomain
- **Type**: CNAME
- **Name**: `api`
- **Content**: `[api-gateway-id].execute-api.[region].amazonaws.com`
- **TTL**: 300

## Step 5: Using DNSimple API (Optional)

If you prefer to automate this, you can use the DNSimple API:

### Install DNSimple CLI:
```bash
gem install dnsimple
```

### Set up authentication:
```bash
export DNSIMPLE_TOKEN="your-api-token"
export DNSIMPLE_ACCOUNT="your-account-id"
```

### Add records via API:
```bash
# Example script to add records
cat > add_dns_records.sh << 'EOF'
#!/bin/bash

DOMAIN="makepdfaccessible.com"
ACCOUNT_ID="your-account-id"
API_TOKEN="your-api-token"

# Function to add DNS record
add_record() {
  local name=$1
  local type=$2
  local content=$3
  local ttl=${4:-300}
  
  curl -H "Authorization: Bearer $API_TOKEN" \
       -H "Content-Type: application/json" \
       -X POST \
       -d "{\"name\":\"$name\",\"type\":\"$type\",\"content\":\"$content\",\"ttl\":$ttl}" \
       "https://api.dnsimple.com/v2/$ACCOUNT_ID/zones/$DOMAIN/records"
}

# Add your records here (get values from Terraform output)
# add_record "" "ALIAS" "d1234567890.cloudfront.net"
# add_record "www" "CNAME" "d1234567890.cloudfront.net"
# add_record "dashboard" "CNAME" "d0987654321.cloudfront.net"
# add_record "api" "CNAME" "abc123.execute-api.us-east-1.amazonaws.com"

EOF

chmod +x add_dns_records.sh
```

## Step 6: Verify DNS Configuration

After adding all records, verify they're working:

### Check DNS propagation:
```bash
# Check root domain
dig makepdfaccessible.com

# Check www
dig www.makepdfaccessible.com

# Check dashboard
dig dashboard.makepdfaccessible.com

# Check API
dig api.makepdfaccessible.com
```

### Test with curl:
```bash
# Test marketing site
curl -I https://makepdfaccessible.com

# Test dashboard
curl -I https://dashboard.makepdfaccessible.com

# Test API health check
curl https://api.makepdfaccessible.com/health
```

## Step 7: Update Application Configuration

Update your application environment variables:

### For Web (marketing site):
```env
NEXT_PUBLIC_API_URL=https://api.makepdfaccessible.com
NEXT_PUBLIC_SITE_URL=https://makepdfaccessible.com
```

### For Dashboard:
```env
NEXT_PUBLIC_API_URL=https://api.makepdfaccessible.com
NEXT_PUBLIC_APP_URL=https://dashboard.makepdfaccessible.com
BETTER_AUTH_URL=https://dashboard.makepdfaccessible.com
```

### For API:
```env
ALLOWED_ORIGINS=https://makepdfaccessible.com,https://dashboard.makepdfaccessible.com
API_DOMAIN=https://api.makepdfaccessible.com
```

## Step 8: Enable DNSSEC (Optional but Recommended)

In DNSimple:
1. Go to your domain settings
2. Click on "DNSSEC"
3. Click "Enable DNSSEC"
4. DNSimple will handle the DS record configuration automatically

## Troubleshooting

### Certificate Validation Failing
- Ensure validation CNAME records are exactly as provided by AWS
- Wait at least 10 minutes for DNS propagation
- Check records with: `dig _validation-string.makepdfaccessible.com CNAME`

### Site Not Loading
- Verify CloudFront distribution is deployed: Check AWS Console
- Ensure S3 bucket has content uploaded
- Check CloudFront origin settings

### API Not Responding
- Verify API Gateway is deployed
- Check API Gateway custom domain configuration
- Ensure Lambda functions are deployed

### DNS Not Resolving
- Use DNSimple's DNS check tool
- Verify nameservers are set to DNSimple:
  - ns1.dnsimple.com
  - ns2.dnsimple-edge.net
  - ns3.dnsimple.com
  - ns4.dnsimple-edge.org

## Rollback Procedure

If you need to rollback:

1. **Keep DNS records** - They won't affect anything if infrastructure is not deployed
2. **In Terraform**: 
   ```bash
   terraform destroy -target=aws_cloudfront_distribution.marketing
   terraform destroy -target=aws_cloudfront_distribution.dashboard
   terraform destroy -target=aws_apigatewayv2_domain_name.api
   ```
3. **Update DNS** to point to backup/previous infrastructure if needed

## Security Considerations

1. **Enable DNSSEC** for protection against DNS spoofing
2. **Use DNSimple's 2FA** for account security
3. **Rotate API tokens** regularly if using API access
4. **Monitor DNS query logs** for unusual activity
5. **Set up DNS monitoring** alerts for record changes

## Support

- **DNSimple Support**: https://dnsimple.com/support
- **DNSimple API Docs**: https://developer.dnsimple.com/
- **AWS Certificate Manager**: Check certificate status in AWS Console
- **CloudFront Issues**: Check CloudFront logs in S3 bucket

## Next Steps

After DNS is configured:
1. Deploy your applications to S3
2. Set up CI/CD pipelines with the new domains
3. Configure monitoring and alerting
4. Set up backup and disaster recovery procedures
5. Document the infrastructure for your team
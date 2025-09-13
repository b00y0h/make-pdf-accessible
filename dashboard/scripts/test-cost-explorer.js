#!/usr/bin/env node

/**
 * Test script to verify AWS Cost Explorer API access
 * Run: node scripts/test-cost-explorer.js
 */

import { CostExplorerClient, GetCostAndUsageCommand } from '@aws-sdk/client-cost-explorer';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

async function testCostExplorerAccess() {
  console.log('Testing AWS Cost Explorer API access...\n');

  try {
    // Configure AWS client
    const config = {
      region: process.env.AWS_REGION || 'us-east-1',
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      },
    };

    // Add endpoint URL if provided (for LocalStack)
    if (process.env.AWS_ENDPOINT_URL) {
      config.endpoint = process.env.AWS_ENDPOINT_URL;
      console.log(`Using custom endpoint: ${process.env.AWS_ENDPOINT_URL}`);
    }

    const client = new CostExplorerClient(config);

    // Calculate date range (last 3 months)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 3);

    const params = {
      TimePeriod: {
        Start: startDate.toISOString().split('T')[0],
        End: endDate.toISOString().split('T')[0],
      },
      Granularity: 'MONTHLY',
      Metrics: ['UnblendedCost'],
      GroupBy: [
        {
          Type: 'DIMENSION',
          Key: 'SERVICE',
        },
      ],
    };

    console.log('Request parameters:');
    console.log(JSON.stringify(params, null, 2));
    console.log('\\nSending GetCostAndUsage request...');

    const command = new GetCostAndUsageCommand(params);
    const response = await client.send(command);

    console.log('\\n✅ Success! Cost Explorer API is accessible');
    console.log(`Returned ${response.ResultsByTime?.length || 0} time periods`);
    
    if (response.ResultsByTime && response.ResultsByTime.length > 0) {
      const latestPeriod = response.ResultsByTime[response.ResultsByTime.length - 1];
      console.log(`\\nLatest period: ${latestPeriod.TimePeriod?.Start} to ${latestPeriod.TimePeriod?.End}`);
      console.log(`Number of services: ${latestPeriod.Groups?.length || 0}`);
      
      if (latestPeriod.Groups && latestPeriod.Groups.length > 0) {
        console.log('\\nTop 3 services by cost:');
        latestPeriod.Groups
          .sort((a, b) => parseFloat(b.Metrics?.UnblendedCost?.Amount || '0') - parseFloat(a.Metrics?.UnblendedCost?.Amount || '0'))
          .slice(0, 3)
          .forEach((group, index) => {
            const service = group.Keys?.[0] || 'Unknown';
            const amount = parseFloat(group.Metrics?.UnblendedCost?.Amount || '0').toFixed(2);
            const currency = group.Metrics?.UnblendedCost?.Unit || 'USD';
            console.log(`  ${index + 1}. ${service}: ${currency} ${amount}`);
          });
      }
    }

    // Test dimension values
    console.log('\\n--- Testing GetDimensionValues ---');
    const { GetDimensionValuesCommand } = await import('@aws-sdk/client-cost-explorer');
    
    const dimensionCommand = new GetDimensionValuesCommand({
      TimePeriod: {
        Start: startDate.toISOString().split('T')[0],
        End: endDate.toISOString().split('T')[0],
      },
      Dimension: 'SERVICE',
    });

    const dimensionResponse = await client.send(dimensionCommand);
    console.log(`✅ GetDimensionValues successful! Found ${dimensionResponse.DimensionValues?.length || 0} services`);

  } catch (error) {
    console.error('\\n❌ Error testing Cost Explorer API:');
    console.error('Error code:', error.name);
    console.error('Error message:', error.message);
    
    if (error.name === 'AccessDenied') {
      console.error('\\n💡 Troubleshooting tips:');
      console.error('1. Verify IAM permissions include ce:GetCostAndUsage and ce:GetDimensionValues');
      console.error('2. Check that AWS credentials are correctly configured');
      console.error('3. Ensure the AWS region is correct');
    }
    
    process.exit(1);
  }
}

// Run the test
testCostExplorerAccess();
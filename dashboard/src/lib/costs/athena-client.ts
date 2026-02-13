import {
  AthenaClient,
  StartQueryExecutionCommand,
  GetQueryExecutionCommand,
  GetQueryResultsCommand,
  QueryExecutionState,
  type QueryExecution,
  type Row,
} from '@aws-sdk/client-athena';
import {
  type CostFilters,
  type TimeSeriesResponse,
  type ServiceCostResponse,
  type TagCostResponse,
  type ServiceDimension,
  type CostDataPoint,
  type ServiceCostDataPoint,
  type TagCostDataPoint,
} from './types';

export interface AthenaQueryConfig {
  workgroup: string;
  database: string;
  tableName: string;
  resultsBucket: string;
}

export class AthenaQueryService {
  private client: AthenaClient;
  private config: AthenaQueryConfig;

  constructor(config: AthenaQueryConfig) {
    this.client = new AthenaClient({
      region: process.env.AWS_REGION || 'us-east-1',
    });
    this.config = config;
  }

  /**
   * Execute a query and wait for results
   */
  private async executeQuery(sql: string): Promise<Row[]> {
    // Start query execution
    const startCommand = new StartQueryExecutionCommand({
      QueryString: sql,
      WorkGroup: this.config.workgroup,
      ResultConfiguration: {
        OutputLocation: `s3://${this.config.resultsBucket}/query-results/`,
      },
    });

    const startResult = await this.client.send(startCommand);
    const executionId = startResult.QueryExecutionId;

    if (!executionId) {
      throw new Error('Failed to start query execution');
    }

    // Poll for completion
    let execution: QueryExecution | undefined;
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes at 5-second intervals

    while (attempts < maxAttempts) {
      const statusCommand = new GetQueryExecutionCommand({
        QueryExecutionId: executionId,
      });

      const statusResult = await this.client.send(statusCommand);
      execution = statusResult.QueryExecution;

      if (!execution?.Status?.State) {
        throw new Error('Query execution status not available');
      }

      const state = execution.Status.State;

      if (state === QueryExecutionState.SUCCEEDED) {
        break;
      }

      if (
        state === QueryExecutionState.FAILED ||
        state === QueryExecutionState.CANCELLED
      ) {
        const reason = execution.Status.StateChangeReason || 'Unknown error';
        throw new Error(`Query failed: ${reason}`);
      }

      // Wait 5 seconds before next poll
      await new Promise((resolve) => setTimeout(resolve, 5000));
      attempts++;
    }

    if (attempts >= maxAttempts) {
      throw new Error('Query execution timed out');
    }

    // Get query results
    const resultsCommand = new GetQueryResultsCommand({
      QueryExecutionId: executionId,
      MaxResults: 1000, // Adjust as needed
    });

    const resultsResult = await this.client.send(resultsCommand);
    return resultsResult.ResultSet?.Rows || [];
  }

  /**
   * Get monthly cost timeseries from CUR data
   */
  async getTimeseries(filters: CostFilters): Promise<TimeSeriesResponse> {
    const { startDate, endDate } = this.getDateRange(filters);

    const sql = `
      SELECT 
        date_format(line_item_usage_start_date, '%Y-%m') as month,
        SUM(line_item_unblended_cost) as unblended_cost,
        SUM(line_item_blended_cost) as blended_cost,
        line_item_currency_code as currency
      FROM ${this.config.database}.${this.config.tableName}
      WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
        AND line_item_usage_start_date >= date('${startDate}')
        AND line_item_usage_start_date < date('${endDate}')
        ${this.buildAccountFilter(filters)}
        ${this.buildServiceFilter(filters)}
        ${this.buildTagFilter(filters)}
      GROUP BY 
        date_format(line_item_usage_start_date, '%Y-%m'),
        line_item_currency_code
      ORDER BY month ASC
    `;

    const rows = await this.executeQuery(sql);
    const dataPoints = this.parseTimeseriesRows(rows);

    return {
      timePeriod: {
        start: startDate,
        end: endDate,
      },
      dataPoints,
      total: dataPoints.reduce((sum, point) => sum + point.amount, 0),
    };
  }

  /**
   * Get costs grouped by service from CUR data
   */
  async getServiceCosts(filters: CostFilters): Promise<ServiceCostResponse> {
    const { startDate, endDate } = this.getDateRange(filters);

    const sql = `
      SELECT 
        date_format(line_item_usage_start_date, '%Y-%m') as month,
        line_item_product_code as service,
        SUM(line_item_unblended_cost) as unblended_cost,
        SUM(line_item_blended_cost) as blended_cost,
        line_item_currency_code as currency
      FROM ${this.config.database}.${this.config.tableName}
      WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
        AND line_item_usage_start_date >= date('${startDate}')
        AND line_item_usage_start_date < date('${endDate}')
        ${this.buildAccountFilter(filters)}
        ${this.buildServiceFilter(filters)}
        ${this.buildTagFilter(filters)}
      GROUP BY 
        date_format(line_item_usage_start_date, '%Y-%m'),
        line_item_product_code,
        line_item_currency_code
      ORDER BY month ASC, unblended_cost DESC
    `;

    const rows = await this.executeQuery(sql);
    const dataPoints = this.parseServiceCostRows(rows);

    return {
      timePeriod: {
        start: startDate,
        end: endDate,
      },
      dataPoints,
      services: this.extractUniqueServices(dataPoints),
    };
  }

  /**
   * Get costs grouped by tags from CUR data
   */
  async getTagCosts(filters: CostFilters): Promise<TagCostResponse> {
    const { startDate, endDate } = this.getDateRange(filters);

    const tagColumns = Object.keys(filters.tags || {})
      .map((tag) => `COALESCE(resource_tags_${tag}, 'untagged') as ${tag}`)
      .join(', ');

    const groupByTags = Object.keys(filters.tags || {})
      .map((tag) => `COALESCE(resource_tags_${tag}, 'untagged')`)
      .join(', ');

    if (!tagColumns) {
      // Default to environment tag if no specific tags requested
      const sql = `
        SELECT 
          date_format(line_item_usage_start_date, '%Y-%m') as month,
          COALESCE(resource_tags_environment, 'untagged') as environment,
          SUM(line_item_unblended_cost) as unblended_cost,
          SUM(line_item_blended_cost) as blended_cost,
          line_item_currency_code as currency
        FROM ${this.config.database}.${this.config.tableName}
        WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
          AND line_item_usage_start_date >= date('${startDate}')
          AND line_item_usage_start_date < date('${endDate}')
          ${this.buildAccountFilter(filters)}
          ${this.buildServiceFilter(filters)}
        GROUP BY 
          date_format(line_item_usage_start_date, '%Y-%m'),
          COALESCE(resource_tags_environment, 'untagged'),
          line_item_currency_code
        ORDER BY month ASC, unblended_cost DESC
      `;

      const rows = await this.executeQuery(sql);
      const dataPoints = this.parseTagCostRows(rows, ['environment']);

      return {
        timePeriod: {
          start: startDate,
          end: endDate,
        },
        dataPoints,
        tags: ['environment'],
      };
    }

    const sql = `
      SELECT 
        date_format(line_item_usage_start_date, '%Y-%m') as month,
        ${tagColumns},
        SUM(line_item_unblended_cost) as unblended_cost,
        SUM(line_item_blended_cost) as blended_cost,
        line_item_currency_code as currency
      FROM ${this.config.database}.${this.config.tableName}
      WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
        AND line_item_usage_start_date >= date('${startDate}')
        AND line_item_usage_start_date < date('${endDate}')
        ${this.buildAccountFilter(filters)}
        ${this.buildServiceFilter(filters)}
      GROUP BY 
        date_format(line_item_usage_start_date, '%Y-%m'),
        ${groupByTags},
        line_item_currency_code
      ORDER BY month ASC, unblended_cost DESC
    `;

    const rows = await this.executeQuery(sql);
    const requestedTags = Object.keys(filters.tags || {});
    const dataPoints = this.parseTagCostRows(rows, requestedTags);

    return {
      timePeriod: {
        start: startDate,
        end: endDate,
      },
      dataPoints,
      tags: requestedTags,
    };
  }

  /**
   * Get available services from CUR data
   */
  async getAvailableServices(): Promise<ServiceDimension[]> {
    const sql = `
      SELECT DISTINCT 
        line_item_product_code as service,
        COUNT(*) as usage_count
      FROM ${this.config.database}.${this.config.tableName}
      WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage')
        AND line_item_product_code IS NOT NULL
        AND line_item_product_code != ''
      GROUP BY line_item_product_code
      ORDER BY usage_count DESC
      LIMIT 100
    `;

    const rows = await this.executeQuery(sql);

    return rows
      .slice(1)
      .map((row) => ({
        // Skip header row
        value: row.Data?.[0]?.VarCharValue || '',
        displayName: this.formatServiceName(row.Data?.[0]?.VarCharValue || ''),
      }))
      .filter((service) => service.value);
  }

  // Helper methods

  private getDateRange(filters: CostFilters): {
    startDate: string;
    endDate: string;
  } {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth();

    let startDate: Date;
    let endDate: Date;

    if (filters.dateRange.preset) {
      switch (filters.dateRange.preset) {
        case '3months':
          startDate = new Date(currentYear, currentMonth - 3, 1);
          endDate = new Date(currentYear, currentMonth, 1);
          break;
        case '6months':
          startDate = new Date(currentYear, currentMonth - 6, 1);
          endDate = new Date(currentYear, currentMonth, 1);
          break;
        case '12months':
        default:
          startDate = new Date(currentYear - 1, currentMonth, 1);
          endDate = new Date(currentYear, currentMonth, 1);
          break;
      }
    } else if (filters.dateRange.custom) {
      startDate = new Date(filters.dateRange.custom.start);
      endDate = new Date(filters.dateRange.custom.end);
    } else {
      // Default to 12 months
      startDate = new Date(currentYear - 1, currentMonth, 1);
      endDate = new Date(currentYear, currentMonth, 1);
    }

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    };
  }

  private buildAccountFilter(filters: CostFilters): string {
    if (!filters.accounts?.length) return '';

    const accountList = filters.accounts
      .map((account) => `'${account}'`)
      .join(', ');
    return `AND line_item_usage_account_id IN (${accountList})`;
  }

  private buildServiceFilter(filters: CostFilters): string {
    if (!filters.services?.length) return '';

    const serviceList = filters.services
      .map((service) => `'${service}'`)
      .join(', ');
    return `AND line_item_product_code IN (${serviceList})`;
  }

  private buildTagFilter(filters: CostFilters): string {
    if (!filters.tags || Object.keys(filters.tags).length === 0) return '';

    const conditions = Object.entries(filters.tags)
      .map(([key, values]) => {
        if (!values?.length) return '';
        const valueList = values.map((value) => `'${value}'`).join(', ');
        return `resource_tags_${key} IN (${valueList})`;
      })
      .filter(Boolean);

    return conditions.length > 0 ? `AND (${conditions.join(' AND ')})` : '';
  }

  private parseTimeseriesRows(rows: Row[]): CostDataPoint[] {
    return rows
      .slice(1)
      .map((row) => {
        // Skip header row
        const data = row.Data || [];
        return {
          month: data[0]?.VarCharValue || '',
          amount: parseFloat(data[1]?.VarCharValue || '0'),
          currency: data[3]?.VarCharValue || 'USD',
        };
      })
      .filter((point) => point.month && point.amount > 0);
  }

  private parseServiceCostRows(rows: Row[]): ServiceCostDataPoint[] {
    return rows
      .slice(1)
      .map((row) => {
        // Skip header row
        const data = row.Data || [];
        return {
          month: data[0]?.VarCharValue || '',
          service: data[1]?.VarCharValue || '',
          amount: parseFloat(data[2]?.VarCharValue || '0'),
          currency: data[4]?.VarCharValue || 'USD',
        };
      })
      .filter((point) => point.month && point.service && point.amount > 0);
  }

  private parseTagCostRows(rows: Row[], tagKeys: string[]): TagCostDataPoint[] {
    return rows
      .slice(1)
      .map((row) => {
        // Skip header row
        const data = row.Data || [];
        const tags: Record<string, string> = {};

        // Extract tag values (columns 1 to 1+tagKeys.length)
        tagKeys.forEach((key, index) => {
          tags[key] = data[1 + index]?.VarCharValue || 'untagged';
        });

        return {
          month: data[0]?.VarCharValue || '',
          tags,
          amount: parseFloat(data[1 + tagKeys.length]?.VarCharValue || '0'),
          currency: data[1 + tagKeys.length + 2]?.VarCharValue || 'USD',
        };
      })
      .filter((point) => point.month && point.amount > 0);
  }

  private extractUniqueServices(
    dataPoints: ServiceCostDataPoint[]
  ): ServiceDimension[] {
    const serviceMap = new Map<string, number>();

    dataPoints.forEach((point) => {
      const current = serviceMap.get(point.service) || 0;
      serviceMap.set(point.service, current + point.amount);
    });

    return Array.from(serviceMap.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([service]) => ({
        value: service,
        displayName: this.formatServiceName(service),
      }));
  }

  private formatServiceName(serviceCode: string): string {
    const serviceNames: Record<string, string> = {
      AmazonEC2: 'EC2 - Compute',
      AmazonS3: 'S3 - Storage',
      AmazonRDS: 'RDS - Database',
      AWSLambda: 'Lambda - Functions',
      AmazonCloudFront: 'CloudFront - CDN',
      AmazonRoute53: 'Route 53 - DNS',
      AmazonVPC: 'VPC - Networking',
      AmazonSNS: 'SNS - Notifications',
      AmazonSQS: 'SQS - Queues',
      AmazonDynamoDB: 'DynamoDB - NoSQL',
      AmazonRedshift: 'Redshift - Data Warehouse',
      AmazonElastiCache: 'ElastiCache - Caching',
      AmazonCloudWatch: 'CloudWatch - Monitoring',
      AmazonKinesis: 'Kinesis - Streaming',
      AWSGlue: 'Glue - ETL',
      AmazonAthena: 'Athena - Analytics',
    };

    return serviceNames[serviceCode] || serviceCode;
  }
}

// Default configuration factory
export function createAthenaQueryService(): AthenaQueryService {
  const config: AthenaQueryConfig = {
    workgroup: process.env.ATHENA_WORKGROUP || 'accesspdf-cost-analytics',
    database: process.env.ATHENA_DATABASE || 'accesspdf_cost_analytics',
    tableName: process.env.ATHENA_TABLE || 'accesspdf_cur_table',
    resultsBucket:
      process.env.ATHENA_RESULTS_BUCKET || 'accesspdf-athena-results',
  };

  return new AthenaQueryService(config);
}

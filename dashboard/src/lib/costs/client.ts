import {
  CostExplorerClient,
  GetCostAndUsageCommand,
  GetDimensionValuesCommand,
  GetCostForecastCommand,
  type GetCostAndUsageCommandInput,
  type GetDimensionValuesCommandInput,
  type GetCostForecastCommandInput,
} from '@aws-sdk/client-cost-explorer';

import {
  CostExplorerConfig,
  CostSeries,
  CostPoint,
  ResultByTime,
  ServiceDimension,
  ForecastResult,
  CostExplorerError,
  TimePeriod,
} from './types';
import { MoMCalculator } from '../mom';
import { GapFiller } from './gap-filler';
import { getCacheInstance } from '../cache/redis-cache';
import {
  withCostExplorerRetry,
  costExplorerCircuitBreaker,
  RetryableError,
} from '../resilience/retry';

export class CostExplorerService {
  private client: CostExplorerClient;
  private config: CostExplorerConfig;
  private cache = getCacheInstance();

  constructor(config?: Partial<CostExplorerConfig>) {
    this.config = {
      source: 'ce',
      region: process.env.AWS_REGION || 'us-east-1',
      payerAccountId: process.env.AWS_PAYER_ACCOUNT_ID,
      linkedAccountIds: process.env.AWS_LINKED_ACCOUNT_IDS?.split(','),
      costAllocationTags: process.env.COST_ALLOCATION_TAGS?.split(',') || [],
      cacheConfig: {
        ttl: 6 * 60 * 60, // 6 hours in seconds
        keyPrefix: 'costs:ce:',
      },
      ...config,
    };

    // Configure AWS client
    const clientConfig: any = {
      region: this.config.region,
    };

    // Use environment credentials
    if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY) {
      clientConfig.credentials = {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      };
    }

    // Add endpoint for LocalStack or custom endpoints
    if (process.env.AWS_ENDPOINT_URL) {
      clientConfig.endpoint = process.env.AWS_ENDPOINT_URL;
    }

    this.client = new CostExplorerClient(clientConfig);
  }

  /**
   * Get cost and usage data with normalization
   */
  async getCostAndUsage(params: {
    timePeriod: TimePeriod;
    granularity: 'MONTHLY' | 'DAILY';
    metrics: ('UnblendedCost' | 'AmortizedCost')[];
    groupBy?: Array<{ type: 'DIMENSION' | 'TAG'; key: string }>;
    filter?: any;
    bypassCache?: boolean;
  }): Promise<CostSeries> {
    // Generate cache key from parameters
    const cacheKey = 'cost-and-usage';
    const cacheParams = {
      timePeriod: params.timePeriod,
      granularity: params.granularity,
      metrics: params.metrics,
      groupBy: params.groupBy,
      filter: params.filter,
    };

    // Try to get from cache first (unless bypassing)
    if (!params.bypassCache) {
      try {
        const cached = await this.cache.get<CostSeries>(cacheKey, cacheParams);
        if (cached) {
          console.log('Cache hit for cost and usage data');
          return cached;
        }
      } catch (error) {
        console.warn('Cache retrieval error:', error);
      }
    }

    try {
      const command = new GetCostAndUsageCommand({
        TimePeriod: {
          Start: params.timePeriod.start,
          End: params.timePeriod.end,
        },
        Granularity: params.granularity,
        Metrics: params.metrics,
        GroupBy: params.groupBy?.map((g) => ({ Type: g.type, Key: g.key })),
        Filter: params.filter,
      });

      // Execute with circuit breaker and retry logic
      const { result: response } = await costExplorerCircuitBreaker.execute(
        async () => {
          return await withCostExplorerRetry(async () => {
            console.log('Fetching cost data from AWS Cost Explorer...');
            return await this.client.send(command);
          });
        }
      );

      // Normalize response to CostSeries format
      const series: CostPoint[] = [];

      if (response.ResultsByTime) {
        for (const result of response.ResultsByTime) {
          const date = result.TimePeriod?.Start || '';

          if (params.groupBy && params.groupBy.length > 0) {
            // Handle grouped results
            if (result.Groups) {
              for (const group of result.Groups) {
                const key = group.Keys?.[0] || 'Unknown';
                for (const metric of params.metrics) {
                  const metricData = group.Metrics?.[metric];
                  if (metricData) {
                    series.push({
                      date,
                      amount: parseFloat(metricData.Amount || '0'),
                      unit: metricData.Unit || 'USD',
                      estimated: result.Estimated || false,
                    });
                  }
                }
              }
            }
          } else {
            // Handle ungrouped results (total)
            for (const metric of params.metrics) {
              const metricData = result.Total?.[metric];
              if (metricData) {
                series.push({
                  date,
                  amount: parseFloat(metricData.Amount || '0'),
                  unit: metricData.Unit || 'USD',
                  estimated: result.Estimated || false,
                });
              }
            }
          }
        }
      }

      // Convert to standardized format for gap filling
      const costDataPoints = series.map((point) => ({
        month: point.date,
        time: point.date,
        amount: point.amount,
        currency: point.unit,
      }));

      // Fill gaps to ensure consistent data
      const filledDataPoints = GapFiller.fillTimeSeriesGaps(
        costDataPoints,
        params.timePeriod.start,
        params.timePeriod.end,
        {
          granularity: params.granularity,
          fillValue: 0,
          currency: 'USD',
        }
      );

      // Convert back to original format
      const filledSeries = filledDataPoints.map((point) => ({
        date: point.month,
        amount: point.amount,
        unit: point.currency,
        estimated: false,
      }));

      const result: CostSeries = {
        metric: params.metrics[0],
        groupBy: params.groupBy?.[0]?.key,
        series: filledSeries,
        metadata: {
          source: 'ce',
          requestId: response.$metadata.requestId || '',
          cached: false,
          gapsFilled: filledDataPoints.length > series.length,
        },
      };

      // Cache the result
      try {
        await this.cache.set(cacheKey, result, cacheParams, {
          ttl: this.config.cacheConfig?.ttl || 6 * 60 * 60, // 6 hours
        });
        console.log('Cached cost and usage data');
      } catch (error) {
        console.warn('Cache storage error:', error);
      }

      return result;
    } catch (error: any) {
      throw new CostExplorerError(
        `Failed to get cost and usage: ${error.message}`,
        error.name,
        error.$metadata?.httpStatusCode,
        error.$metadata?.requestId
      );
    }
  }

  /**
   * Get timeseries data (total costs without grouping)
   */
  async getTimeseries(params: {
    timePeriod: TimePeriod;
    granularity?: 'MONTHLY' | 'DAILY';
    metric?: 'UnblendedCost' | 'AmortizedCost';
  }): Promise<CostSeries> {
    return this.getCostAndUsage({
      timePeriod: params.timePeriod,
      granularity: params.granularity || 'MONTHLY',
      metrics: [params.metric || 'UnblendedCost'],
      // No groupBy for total timeseries
    });
  }

  /**
   * Get costs grouped by service
   */
  async getCostsByService(params: {
    timePeriod: TimePeriod;
    granularity?: 'MONTHLY' | 'DAILY';
    metric?: 'UnblendedCost' | 'AmortizedCost';
  }): Promise<CostSeries> {
    return this.getCostAndUsage({
      timePeriod: params.timePeriod,
      granularity: params.granularity || 'MONTHLY',
      metrics: [params.metric || 'UnblendedCost'],
      groupBy: [{ type: 'DIMENSION', key: 'SERVICE' }],
    });
  }

  /**
   * Get costs grouped by tag
   */
  async getCostsByTag(params: {
    timePeriod: TimePeriod;
    tag: string;
    granularity?: 'MONTHLY' | 'DAILY';
    metric?: 'UnblendedCost' | 'AmortizedCost';
  }): Promise<CostSeries> {
    // Validate tag is supported
    if (!this.config.costAllocationTags.includes(params.tag)) {
      throw new CostExplorerError(
        `Unsupported cost allocation tag: ${params.tag}. Supported tags: ${this.config.costAllocationTags.join(', ')}`
      );
    }

    return this.getCostAndUsage({
      timePeriod: params.timePeriod,
      granularity: params.granularity || 'MONTHLY',
      metrics: [params.metric || 'UnblendedCost'],
      groupBy: [{ type: 'TAG', key: params.tag }],
    });
  }

  /**
   * Get available service dimension values
   */
  async getServiceDimensions(params: {
    timePeriod: TimePeriod;
  }): Promise<ServiceDimension[]> {
    try {
      const command = new GetDimensionValuesCommand({
        TimePeriod: {
          Start: params.timePeriod.start,
          End: params.timePeriod.end,
        },
        Dimension: 'SERVICE',
        Context: 'COST_AND_USAGE',
      });

      const response = await this.client.send(command);

      return (response.DimensionValues || []).map((dim) => ({
        value: dim.Value || '',
        attributes: dim.Attributes,
      }));
    } catch (error: any) {
      throw new CostExplorerError(
        `Failed to get service dimensions: ${error.message}`,
        error.name,
        error.$metadata?.httpStatusCode,
        error.$metadata?.requestId
      );
    }
  }

  /**
   * Get cost forecast
   */
  async getCostForecast(params: {
    granularity?: 'MONTHLY' | 'DAILY';
    metric?: 'UNBLENDED_COST' | 'BLENDED_COST';
    predictionIntervalLevel?: number;
  }): Promise<{
    forecastResults: ForecastResult[];
    total: { amount: string; unit: string };
    metadata: { source: string; requestId: string };
  }> {
    try {
      // Calculate forecast period (next 3 months)
      const today = new Date();
      const startDate = today.toISOString().split('T')[0];
      const endDate = new Date(
        today.getFullYear(),
        today.getMonth() + 3,
        today.getDate()
      )
        .toISOString()
        .split('T')[0];

      const command = new GetCostForecastCommand({
        TimePeriod: {
          Start: startDate,
          End: endDate,
        },
        Granularity: params.granularity || 'MONTHLY',
        Metric: params.metric || 'UNBLENDED_COST',
        PredictionIntervalLevel: params.predictionIntervalLevel || 80,
      });

      const response = await this.client.send(command);

      const forecastResults: ForecastResult[] = (
        response.ForecastResultsByTime || []
      ).map((result) => ({
        timePeriod: {
          start: result.TimePeriod?.Start || '',
          end: result.TimePeriod?.End || '',
        },
        meanValue: result.MeanValue || '0',
        predictionIntervalLowerBound:
          result.PredictionIntervalLowerBound || '0',
        predictionIntervalUpperBound:
          result.PredictionIntervalUpperBound || '0',
      }));

      return {
        forecastResults,
        total: {
          amount: response.Total?.Amount || '0',
          unit: response.Total?.Unit || 'USD',
        },
        metadata: {
          source: 'ce',
          requestId: response.$metadata.requestId || '',
        },
      };
    } catch (error: any) {
      throw new CostExplorerError(
        `Failed to get cost forecast: ${error.message}`,
        error.name,
        error.$metadata?.httpStatusCode,
        error.$metadata?.requestId
      );
    }
  }

  /**
   * Calculate default date ranges for common presets
   */
  static getDateRange(
    preset: '3months' | '6months' | '12months' | '18months'
  ): TimePeriod {
    const today = new Date();
    const endDate = today.toISOString().split('T')[0];

    const startDate = new Date(today);
    switch (preset) {
      case '3months':
        startDate.setMonth(startDate.getMonth() - 3);
        break;
      case '6months':
        startDate.setMonth(startDate.getMonth() - 6);
        break;
      case '12months':
        startDate.setMonth(startDate.getMonth() - 12);
        break;
      case '18months':
        startDate.setMonth(startDate.getMonth() - 18);
        break;
    }

    return {
      start: startDate.toISOString().split('T')[0],
      end: endDate,
    };
  }
}

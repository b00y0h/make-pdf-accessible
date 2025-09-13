/**
 * Contract tests for Cost API endpoints
 * These tests ensure API responses maintain expected shape and data contracts
 */

import { NextRequest } from 'next/server';
import { GET as timeseriesHandler } from '../costs/timeseries/route';
import { GET as summaryHandler } from '../costs/summary/route';
import { GET as servicesHandler } from '../costs/services/route';
import { GET as forecastHandler } from '../costs/forecast/route';

// Mock better-auth for testing
jest.mock('better-auth', () => ({
  betterAuth: () => ({
    api: {
      getSession: jest.fn(() =>
        Promise.resolve({
          user: { role: 'admin', id: 'test-user' },
          session: { id: 'test-session', userId: 'test-user' },
        })
      ),
    },
  }),
}));

describe('Cost API Contract Tests', () => {
  const createMockRequest = (searchParams: Record<string, string> = {}) => {
    const url = new URL('http://localhost/api/costs/test');
    Object.entries(searchParams).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });

    return new NextRequest(url);
  };

  describe('/api/costs/timeseries', () => {
    it('should return ascending months with no gaps', async () => {
      const request = createMockRequest({
        preset: '6months',
        metric: 'UnblendedCost',
        granularity: 'MONTHLY',
      });

      const response = await timeseriesHandler(request);
      const data = await response.json();

      // Check response structure
      expect(data).toHaveProperty('ok');
      expect(data).toHaveProperty('data');
      expect(data.data).toHaveProperty('series');
      expect(data.data).toHaveProperty('total');

      // Check series is array
      expect(Array.isArray(data.data.series)).toBe(true);

      if (data.data.series.length > 0) {
        // Check each data point has required fields
        data.data.series.forEach((point: any, index: number) => {
          expect(point).toHaveProperty('time');
          expect(point).toHaveProperty('amount');
          expect(point).toHaveProperty('unit');

          // Check data types
          expect(typeof point.time).toBe('string');
          expect(typeof point.amount).toBe('number');
          expect(typeof point.unit).toBe('string');

          // Amount should be non-negative for costs
          expect(point.amount).toBeGreaterThanOrEqual(0);

          // Check ascending order
          if (index > 0) {
            const currentDate = new Date(point.time);
            const previousDate = new Date(data.data.series[index - 1].time);
            expect(currentDate.getTime()).toBeGreaterThan(
              previousDate.getTime()
            );
          }
        });

        // Check for gaps in monthly data
        if (data.data.series.length > 1) {
          for (let i = 1; i < data.data.series.length; i++) {
            const current = new Date(data.data.series[i].time);
            const previous = new Date(data.data.series[i - 1].time);

            // For monthly data, should be exactly 1 month apart
            const monthDiff =
              (current.getFullYear() - previous.getFullYear()) * 12 +
              (current.getMonth() - previous.getMonth());
            expect(monthDiff).toBe(1);
          }
        }
      }

      // Check total is numeric
      expect(typeof data.data.total).toBe('number');
      expect(data.data.total).toBeGreaterThanOrEqual(0);
    });

    it('should handle different granularities correctly', async () => {
      const monthlyRequest = createMockRequest({
        preset: '3months',
        granularity: 'MONTHLY',
      });

      const dailyRequest = createMockRequest({
        preset: '3months',
        granularity: 'DAILY',
      });

      const [monthlyResponse, dailyResponse] = await Promise.all([
        timeseriesHandler(monthlyRequest),
        timeseriesHandler(dailyRequest),
      ]);

      const monthlyData = await monthlyResponse.json();
      const dailyData = await dailyResponse.json();

      // Both should have valid structure
      expect(monthlyData.ok).toBe(true);
      expect(dailyData.ok).toBe(true);

      // Daily data should have more points than monthly for same period
      if (
        monthlyData.data.series.length > 0 &&
        dailyData.data.series.length > 0
      ) {
        expect(dailyData.data.series.length).toBeGreaterThan(
          monthlyData.data.series.length
        );
      }
    });

    it('should validate date formats', async () => {
      const request = createMockRequest({
        preset: '6months',
      });

      const response = await timeseriesHandler(request);
      const data = await response.json();

      if (data.ok && data.data.series.length > 0) {
        data.data.series.forEach((point: any) => {
          // Should be valid ISO date string or YYYY-MM format
          const dateRegex = /^\d{4}-\d{2}(-\d{2})?$/;
          expect(point.time).toMatch(dateRegex);
        });
      }
    });
  });

  describe('/api/costs/summary', () => {
    it('should return grouped data with consistent structure', async () => {
      const request = createMockRequest({
        preset: '6months',
        groupBy: 'SERVICE',
      });

      const response = await summaryHandler(request);
      const data = await response.json();

      expect(data).toHaveProperty('ok');
      expect(data).toHaveProperty('data');
      expect(data.data).toHaveProperty('series');

      if (data.data.series.length > 0) {
        data.data.series.forEach((point: any) => {
          expect(point).toHaveProperty('time');
          expect(point).toHaveProperty('amount');
          expect(point).toHaveProperty('service'); // For SERVICE grouping

          expect(typeof point.time).toBe('string');
          expect(typeof point.amount).toBe('number');
          expect(typeof point.service).toBe('string');

          expect(point.amount).toBeGreaterThanOrEqual(0);
        });
      }
    });

    it('should handle different groupBy values', async () => {
      const serviceRequest = createMockRequest({
        preset: '3months',
        groupBy: 'SERVICE',
      });

      const regionRequest = createMockRequest({
        preset: '3months',
        groupBy: 'REGION',
      });

      const [serviceResponse, regionResponse] = await Promise.all([
        summaryHandler(serviceRequest),
        summaryHandler(regionRequest),
      ]);

      const serviceData = await serviceResponse.json();
      const regionData = await regionResponse.json();

      expect(serviceData.ok).toBe(true);
      expect(regionData.ok).toBe(true);

      // Check that groupBy field is present in response
      if (serviceData.data.series.length > 0) {
        expect(serviceData.data.series[0]).toHaveProperty('service');
      }

      if (regionData.data.series.length > 0) {
        expect(regionData.data.series[0]).toHaveProperty('region');
      }
    });
  });

  describe('/api/costs/services', () => {
    it('should return available services list', async () => {
      const request = createMockRequest();
      const response = await servicesHandler(request);
      const data = await response.json();

      expect(data).toHaveProperty('ok');
      expect(data).toHaveProperty('data');
      expect(data.data).toHaveProperty('dimensionValues');
      expect(Array.isArray(data.data.dimensionValues)).toBe(true);

      if (data.data.dimensionValues.length > 0) {
        data.data.dimensionValues.forEach((service: any) => {
          expect(service).toHaveProperty('value');
          expect(service).toHaveProperty('displayName');
          expect(typeof service.value).toBe('string');
          expect(typeof service.displayName).toBe('string');
          expect(service.value.length).toBeGreaterThan(0);
        });
      }
    });
  });

  describe('/api/costs/forecast', () => {
    it('should return forecast data with prediction intervals', async () => {
      const request = createMockRequest({
        metric: 'UNBLENDED_COST',
        granularity: 'MONTHLY',
      });

      const response = await forecastHandler(request);
      const data = await response.json();

      expect(data).toHaveProperty('ok');
      expect(data).toHaveProperty('data');
      expect(data.data).toHaveProperty('forecastResultsByTime');
      expect(Array.isArray(data.data.forecastResultsByTime)).toBe(true);

      if (data.data.forecastResultsByTime.length > 0) {
        data.data.forecastResultsByTime.forEach((forecast: any) => {
          expect(forecast).toHaveProperty('timePeriod');
          expect(forecast).toHaveProperty('meanValue');
          expect(forecast).toHaveProperty('predictionIntervalLowerBound');
          expect(forecast).toHaveProperty('predictionIntervalUpperBound');

          expect(typeof forecast.meanValue).toBe('string'); // AWS returns as string
          expect(typeof forecast.predictionIntervalLowerBound).toBe('string');
          expect(typeof forecast.predictionIntervalUpperBound).toBe('string');

          // Check that bounds make sense
          const mean = parseFloat(forecast.meanValue);
          const lower = parseFloat(forecast.predictionIntervalLowerBound);
          const upper = parseFloat(forecast.predictionIntervalUpperBound);

          expect(lower).toBeLessThanOrEqual(mean);
          expect(mean).toBeLessThanOrEqual(upper);
        });
      }
    });
  });

  describe('Error handling and validation', () => {
    it('should return proper error structure for invalid requests', async () => {
      const invalidRequest = createMockRequest({
        preset: 'invalid-preset',
      });

      const response = await timeseriesHandler(invalidRequest);
      const data = await response.json();

      if (!data.ok) {
        expect(data).toHaveProperty('error');
        expect(typeof data.error).toBe('string');
        expect(data.error.length).toBeGreaterThan(0);
      }
    });

    it('should handle missing required parameters gracefully', async () => {
      const emptyRequest = createMockRequest({});
      const response = await timeseriesHandler(emptyRequest);

      // Should either succeed with defaults or return proper error
      expect(response.status).toBeLessThan(500);
    });
  });

  describe('Performance and caching headers', () => {
    it('should include appropriate cache headers', async () => {
      const request = createMockRequest({
        preset: '6months',
      });

      const response = await timeseriesHandler(request);

      // Check for cache-related headers
      const cacheControl = response.headers.get('Cache-Control');
      if (cacheControl) {
        expect(cacheControl).toMatch(/max-age=\d+/);
      }
    });

    it('should handle concurrent requests without errors', async () => {
      const request = createMockRequest({
        preset: '3months',
      });

      // Make multiple concurrent requests
      const promises = Array(5)
        .fill(null)
        .map(() => timeseriesHandler(request));
      const responses = await Promise.all(promises);

      // All should succeed
      responses.forEach((response) => {
        expect(response.status).toBeLessThan(400);
      });
    });
  });

  describe('Data consistency across endpoints', () => {
    it('should have consistent data types across endpoints', async () => {
      const timeseriesRequest = createMockRequest({
        preset: '3months',
        metric: 'UnblendedCost',
      });

      const summaryRequest = createMockRequest({
        preset: '3months',
        groupBy: 'SERVICE',
      });

      const [timeseriesResponse, summaryResponse] = await Promise.all([
        timeseriesHandler(timeseriesRequest),
        summaryHandler(summaryRequest),
      ]);

      const timeseriesData = await timeseriesResponse.json();
      const summaryData = await summaryResponse.json();

      if (timeseriesData.ok && summaryData.ok) {
        // Both should use same amount data type
        if (
          timeseriesData.data.series.length > 0 &&
          summaryData.data.series.length > 0
        ) {
          expect(typeof timeseriesData.data.series[0].amount).toBe('number');
          expect(typeof summaryData.data.series[0].amount).toBe('number');
        }
      }
    });

    it('should maintain currency consistency', async () => {
      const request = createMockRequest({
        preset: '6months',
      });

      const response = await timeseriesHandler(request);
      const data = await response.json();

      if (data.ok && data.data.series.length > 0) {
        const firstCurrency = data.data.series[0].unit;

        // All data points should have same currency
        data.data.series.forEach((point: any) => {
          expect(point.unit).toBe(firstCurrency);
        });
      }
    });
  });
});

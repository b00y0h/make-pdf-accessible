import { GapFiller } from '../costs/gap-filler';
import {
  CostDataPoint,
  ServiceCostDataPoint,
  TagCostDataPoint,
} from '../costs/types';

describe('GapFiller', () => {
  describe('fillTimeSeriesGaps', () => {
    const sampleData: CostDataPoint[] = [
      { month: '2024-01', time: '2024-01', amount: 1000, currency: 'USD' },
      { month: '2024-03', time: '2024-03', amount: 1200, currency: 'USD' }, // Missing Feb
      { month: '2024-05', time: '2024-05', amount: 800, currency: 'USD' }, // Missing Apr
    ];

    it('should fill missing months with zero values', () => {
      const result = GapFiller.fillTimeSeriesGaps(
        sampleData,
        '2024-01-01',
        '2024-05-31',
        { granularity: 'MONTHLY' }
      );

      expect(result).toHaveLength(5);

      // Check existing data is preserved
      expect(result[0]).toEqual(sampleData[0]);
      expect(result[2]).toEqual(sampleData[1]);
      expect(result[4]).toEqual(sampleData[2]);

      // Check gaps are filled
      expect(result[1]).toEqual({
        month: '2024-02',
        time: '2024-02',
        amount: 0,
        currency: 'USD',
      });

      expect(result[3]).toEqual({
        month: '2024-04',
        time: '2024-04',
        amount: 0,
        currency: 'USD',
      });
    });

    it('should handle empty data by creating all zero values', () => {
      const result = GapFiller.fillTimeSeriesGaps(
        [],
        '2024-01-01',
        '2024-03-31',
        { granularity: 'MONTHLY' }
      );

      expect(result).toHaveLength(3);
      expect(result[0]).toEqual({
        month: '2024-01',
        time: '2024-01',
        amount: 0,
        currency: 'USD',
      });
      expect(result[1]).toEqual({
        month: '2024-02',
        time: '2024-02',
        amount: 0,
        currency: 'USD',
      });
      expect(result[2]).toEqual({
        month: '2024-03',
        time: '2024-03',
        amount: 0,
        currency: 'USD',
      });
    });

    it('should handle daily granularity', () => {
      const dailyData: CostDataPoint[] = [
        {
          month: '2024-01-01',
          time: '2024-01-01',
          amount: 100,
          currency: 'USD',
        },
        {
          month: '2024-01-03',
          time: '2024-01-03',
          amount: 150,
          currency: 'USD',
        },
      ];

      const result = GapFiller.fillTimeSeriesGaps(
        dailyData,
        '2024-01-01',
        '2024-01-03',
        { granularity: 'DAILY' }
      );

      expect(result).toHaveLength(3);
      expect(result[1]).toEqual({
        month: '2024-01-02',
        time: '2024-01-02',
        amount: 0,
        currency: 'USD',
      });
    });

    it('should use custom fill value and currency', () => {
      const result = GapFiller.fillTimeSeriesGaps(
        [],
        '2024-01-01',
        '2024-02-29',
        {
          granularity: 'MONTHLY',
          fillValue: -1,
          currency: 'EUR',
        }
      );

      expect(result).toHaveLength(2);
      expect(result[0].amount).toBe(-1);
      expect(result[0].currency).toBe('EUR');
    });
  });

  describe('fillServiceCostGaps', () => {
    const serviceData: ServiceCostDataPoint[] = [
      { month: '2024-01', service: 'EC2', amount: 1000, currency: 'USD' },
      { month: '2024-01', service: 'S3', amount: 500, currency: 'USD' },
      { month: '2024-03', service: 'EC2', amount: 1200, currency: 'USD' }, // Missing Feb for EC2
      // Missing all of Feb for S3, and all of Mar for S3
    ];

    it('should fill gaps for all services across all months', () => {
      const result = GapFiller.fillServiceCostGaps(
        serviceData,
        '2024-01-01',
        '2024-03-31',
        { granularity: 'MONTHLY' }
      );

      expect(result).toHaveLength(6); // 2 services × 3 months

      // Check that all service-month combinations exist
      const combinations = result.map((r) => `${r.service}-${r.month}`);
      expect(combinations).toContain('EC2-2024-01');
      expect(combinations).toContain('EC2-2024-02');
      expect(combinations).toContain('EC2-2024-03');
      expect(combinations).toContain('S3-2024-01');
      expect(combinations).toContain('S3-2024-02');
      expect(combinations).toContain('S3-2024-03');

      // Check that missing data points are filled with zeros
      const s3Feb = result.find(
        (r) => r.service === 'S3' && r.month === '2024-02'
      );
      expect(s3Feb?.amount).toBe(0);

      const s3Mar = result.find(
        (r) => r.service === 'S3' && r.month === '2024-03'
      );
      expect(s3Mar?.amount).toBe(0);
    });

    it('should preserve existing data while filling gaps', () => {
      const result = GapFiller.fillServiceCostGaps(
        serviceData,
        '2024-01-01',
        '2024-03-31',
        { granularity: 'MONTHLY' }
      );

      // Check existing data is preserved
      const ec2Jan = result.find(
        (r) => r.service === 'EC2' && r.month === '2024-01'
      );
      expect(ec2Jan?.amount).toBe(1000);

      const ec2Mar = result.find(
        (r) => r.service === 'EC2' && r.month === '2024-03'
      );
      expect(ec2Mar?.amount).toBe(1200);

      const s3Jan = result.find(
        (r) => r.service === 'S3' && r.month === '2024-01'
      );
      expect(s3Jan?.amount).toBe(500);
    });

    it('should handle empty service data', () => {
      const result = GapFiller.fillServiceCostGaps(
        [],
        '2024-01-01',
        '2024-02-29',
        { granularity: 'MONTHLY' }
      );

      expect(result).toEqual([]);
    });

    it('should sort results chronologically and alphabetically', () => {
      const result = GapFiller.fillServiceCostGaps(
        serviceData,
        '2024-01-01',
        '2024-03-31',
        { granularity: 'MONTHLY' }
      );

      // Should be sorted by month, then by service
      expect(result[0]).toMatchObject({ month: '2024-01', service: 'EC2' });
      expect(result[1]).toMatchObject({ month: '2024-01', service: 'S3' });
      expect(result[2]).toMatchObject({ month: '2024-02', service: 'EC2' });
      expect(result[3]).toMatchObject({ month: '2024-02', service: 'S3' });
      expect(result[4]).toMatchObject({ month: '2024-03', service: 'EC2' });
      expect(result[5]).toMatchObject({ month: '2024-03', service: 'S3' });
    });
  });

  describe('fillTagCostGaps', () => {
    const tagData: TagCostDataPoint[] = [
      {
        month: '2024-01',
        tags: { environment: 'prod', application: 'web' },
        amount: 1000,
        currency: 'USD',
      },
      {
        month: '2024-01',
        tags: { environment: 'dev', application: 'api' },
        amount: 500,
        currency: 'USD',
      },
      {
        month: '2024-03',
        tags: { environment: 'prod', application: 'web' },
        amount: 1200,
        currency: 'USD',
      },
      // Missing Feb for prod-web, missing all months for dev-api except Jan
    ];

    it('should fill gaps for all tag combinations across all months', () => {
      const result = GapFiller.fillTagCostGaps(
        tagData,
        '2024-01-01',
        '2024-03-31',
        { granularity: 'MONTHLY' }
      );

      expect(result).toHaveLength(6); // 2 tag combinations × 3 months

      // Check that all tag combination-month pairs exist
      const prodWebFeb = result.find(
        (r) =>
          r.month === '2024-02' &&
          r.tags.environment === 'prod' &&
          r.tags.application === 'web'
      );
      expect(prodWebFeb?.amount).toBe(0);

      const devApiFeb = result.find(
        (r) =>
          r.month === '2024-02' &&
          r.tags.environment === 'dev' &&
          r.tags.application === 'api'
      );
      expect(devApiFeb?.amount).toBe(0);
    });

    it('should preserve existing tag data', () => {
      const result = GapFiller.fillTagCostGaps(
        tagData,
        '2024-01-01',
        '2024-03-31',
        { granularity: 'MONTHLY' }
      );

      const prodWebJan = result.find(
        (r) =>
          r.month === '2024-01' &&
          r.tags.environment === 'prod' &&
          r.tags.application === 'web'
      );
      expect(prodWebJan?.amount).toBe(1000);
    });

    it('should handle complex tag structures', () => {
      const complexTagData: TagCostDataPoint[] = [
        {
          month: '2024-01',
          tags: {
            environment: 'prod',
            application: 'web',
            team: 'frontend',
            costCenter: 'engineering',
          },
          amount: 1000,
          currency: 'USD',
        },
      ];

      const result = GapFiller.fillTagCostGaps(
        complexTagData,
        '2024-01-01',
        '2024-02-29',
        { granularity: 'MONTHLY' }
      );

      expect(result).toHaveLength(2);
      expect(result[1].tags).toEqual({
        environment: 'prod',
        application: 'web',
        team: 'frontend',
        costCenter: 'engineering',
      });
      expect(result[1].amount).toBe(0);
    });
  });

  describe('validateContinuity', () => {
    const continuousData: CostDataPoint[] = [
      { month: '2024-01', time: '2024-01', amount: 1000, currency: 'USD' },
      { month: '2024-02', time: '2024-02', amount: 1100, currency: 'USD' },
      { month: '2024-03', time: '2024-03', amount: 1200, currency: 'USD' },
    ];

    const gappyData: CostDataPoint[] = [
      { month: '2024-01', time: '2024-01', amount: 1000, currency: 'USD' },
      { month: '2024-03', time: '2024-03', amount: 1200, currency: 'USD' }, // Missing Feb
    ];

    it('should validate continuous data correctly', () => {
      const result = GapFiller.validateContinuity(
        continuousData,
        '2024-01-01',
        '2024-03-31',
        'MONTHLY'
      );

      expect(result.isComplete).toBe(true);
      expect(result.missingPeriods).toEqual([]);
      expect(result.totalPeriods).toBe(3);
      expect(result.existingPeriods).toBe(3);
    });

    it('should identify missing periods', () => {
      const result = GapFiller.validateContinuity(
        gappyData,
        '2024-01-01',
        '2024-03-31',
        'MONTHLY'
      );

      expect(result.isComplete).toBe(false);
      expect(result.missingPeriods).toEqual(['2024-02']);
      expect(result.totalPeriods).toBe(3);
      expect(result.existingPeriods).toBe(2);
    });

    it('should handle daily granularity validation', () => {
      const dailyData: CostDataPoint[] = [
        {
          month: '2024-01-01',
          time: '2024-01-01',
          amount: 100,
          currency: 'USD',
        },
        {
          month: '2024-01-03',
          time: '2024-01-03',
          amount: 150,
          currency: 'USD',
        },
      ];

      const result = GapFiller.validateContinuity(
        dailyData,
        '2024-01-01',
        '2024-01-03',
        'DAILY'
      );

      expect(result.isComplete).toBe(false);
      expect(result.missingPeriods).toEqual(['2024-01-02']);
      expect(result.totalPeriods).toBe(3);
      expect(result.existingPeriods).toBe(2);
    });

    it('should handle empty data', () => {
      const result = GapFiller.validateContinuity(
        [],
        '2024-01-01',
        '2024-02-29',
        'MONTHLY'
      );

      expect(result.isComplete).toBe(false);
      expect(result.missingPeriods).toEqual(['2024-01', '2024-02']);
      expect(result.totalPeriods).toBe(2);
      expect(result.existingPeriods).toBe(0);
    });
  });

  describe('edge cases and error handling', () => {
    it('should handle single day ranges', () => {
      const result = GapFiller.fillTimeSeriesGaps(
        [],
        '2024-01-01',
        '2024-01-01',
        { granularity: 'DAILY' }
      );

      expect(result).toHaveLength(1);
      expect(result[0].month).toBe('2024-01-01');
    });

    it('should handle leap year correctly', () => {
      const result = GapFiller.fillTimeSeriesGaps(
        [],
        '2024-02-01',
        '2024-02-29', // 2024 is a leap year
        { granularity: 'DAILY' }
      );

      expect(result).toHaveLength(29);
      expect(result[result.length - 1].month).toBe('2024-02-29');
    });

    it('should handle year boundaries', () => {
      const result = GapFiller.fillTimeSeriesGaps(
        [],
        '2023-12-01',
        '2024-01-31',
        { granularity: 'MONTHLY' }
      );

      expect(result).toHaveLength(2);
      expect(result[0].month).toBe('2023-12');
      expect(result[1].month).toBe('2024-01');
    });

    it('should handle invalid date ranges gracefully', () => {
      // End date before start date
      const result = GapFiller.fillTimeSeriesGaps(
        [],
        '2024-02-01',
        '2024-01-01',
        { granularity: 'MONTHLY' }
      );

      expect(result).toEqual([]);
    });
  });
});

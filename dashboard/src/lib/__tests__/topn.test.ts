import { TopNProcessor } from '../topn';
import { ServiceCostData } from '../costs/types';

describe('TopNProcessor', () => {
  const sampleServiceData: ServiceCostData[] = [
    { service: 'EC2', cost: 1000, percentage: 40, unit: 'USD' },
    { service: 'S3', cost: 500, percentage: 20, unit: 'USD' },
    { service: 'Lambda', cost: 300, percentage: 12, unit: 'USD' },
    { service: 'RDS', cost: 200, percentage: 8, unit: 'USD' },
    { service: 'CloudWatch', cost: 150, percentage: 6, unit: 'USD' },
    { service: 'API Gateway', cost: 100, percentage: 4, unit: 'USD' },
    { service: 'SNS', cost: 75, percentage: 3, unit: 'USD' },
    { service: 'SQS', cost: 50, percentage: 2, unit: 'USD' },
    { service: 'DynamoDB', cost: 25, percentage: 1, unit: 'USD' },
    { service: 'ElastiCache', cost: 100, percentage: 4, unit: 'USD' },
  ];

  describe('processTopN', () => {
    it('should return top N items with "Other" aggregation', () => {
      const result = TopNProcessor.processTopN(sampleServiceData, 5);

      expect(result).toHaveLength(6); // 5 + "Other"

      // Check top 5 are preserved
      expect(result[0].service).toBe('EC2');
      expect(result[1].service).toBe('S3');
      expect(result[2].service).toBe('Lambda');
      expect(result[3].service).toBe('RDS');
      expect(result[4].service).toBe('CloudWatch');

      // Check "Other" aggregation
      const otherItem = result[5];
      expect(otherItem.service).toBe('Other Services');
      expect(otherItem.cost).toBe(350); // 100 + 75 + 50 + 25 + 100
      expect(otherItem.percentage).toBe(14); // 4 + 3 + 2 + 1 + 4
      expect(otherItem.unit).toBe('USD');
    });

    it('should handle N greater than data length', () => {
      const result = TopNProcessor.processTopN(sampleServiceData, 15);

      expect(result).toHaveLength(10); // Original length, no "Other"
      expect(
        result.find((item) => item.service === 'Other Services')
      ).toBeUndefined();
    });

    it('should handle N equal to data length', () => {
      const result = TopNProcessor.processTopN(sampleServiceData, 10);

      expect(result).toHaveLength(10);
      expect(
        result.find((item) => item.service === 'Other Services')
      ).toBeUndefined();
    });

    it('should handle empty data', () => {
      const result = TopNProcessor.processTopN([], 5);
      expect(result).toEqual([]);
    });

    it('should handle N = 0', () => {
      const result = TopNProcessor.processTopN(sampleServiceData, 0);

      expect(result).toHaveLength(1);
      expect(result[0].service).toBe('Other Services');
      expect(result[0].cost).toBe(2500); // Sum of all costs
    });

    it('should preserve original data order for top N items', () => {
      const result = TopNProcessor.processTopN(sampleServiceData, 3);

      expect(result[0].service).toBe('EC2');
      expect(result[1].service).toBe('S3');
      expect(result[2].service).toBe('Lambda');
      expect(result[3].service).toBe('Other Services');
    });
  });

  describe('aggregateOthers', () => {
    it('should correctly aggregate remaining items', () => {
      const remaining = sampleServiceData.slice(5); // Last 5 items
      const result = TopNProcessor.aggregateOthers(remaining);

      expect(result.service).toBe('Other Services');
      expect(result.cost).toBe(350); // 100 + 75 + 50 + 25 + 100
      expect(result.percentage).toBe(14); // 4 + 3 + 2 + 1 + 4
      expect(result.unit).toBe('USD');
    });

    it('should handle single item aggregation', () => {
      const singleItem = [sampleServiceData[0]];
      const result = TopNProcessor.aggregateOthers(singleItem);

      expect(result.service).toBe('Other Services');
      expect(result.cost).toBe(1000);
      expect(result.percentage).toBe(40);
      expect(result.unit).toBe('USD');
    });

    it('should handle empty array', () => {
      const result = TopNProcessor.aggregateOthers([]);

      expect(result.service).toBe('Other Services');
      expect(result.cost).toBe(0);
      expect(result.percentage).toBe(0);
      expect(result.unit).toBe('USD');
    });
  });

  describe('sortByValue', () => {
    it('should sort by cost in descending order', () => {
      const unsortedData = [...sampleServiceData].reverse();
      const result = TopNProcessor.sortByValue(unsortedData, 'cost');

      expect(result[0].cost).toBe(1000);
      expect(result[1].cost).toBe(500);
      expect(result[2].cost).toBe(300);
      expect(result[result.length - 1].cost).toBe(25);
    });

    it('should sort by percentage in descending order', () => {
      const result = TopNProcessor.sortByValue(sampleServiceData, 'percentage');

      expect(result[0].percentage).toBe(40);
      expect(result[1].percentage).toBe(20);
      expect(result[2].percentage).toBe(12);
    });

    it('should handle identical values', () => {
      const dataWithDuplicates = [
        { service: 'A', cost: 100, percentage: 10, unit: 'USD' },
        { service: 'B', cost: 100, percentage: 10, unit: 'USD' },
        { service: 'C', cost: 200, percentage: 20, unit: 'USD' },
      ];

      const result = TopNProcessor.sortByValue(dataWithDuplicates, 'cost');

      expect(result[0].cost).toBe(200);
      expect(result[1].cost).toBe(100);
      expect(result[2].cost).toBe(100);
    });
  });

  describe('generic type support', () => {
    interface CustomData {
      name: string;
      value: number;
      category: string;
    }

    const customData: CustomData[] = [
      { name: 'Item1', value: 100, category: 'A' },
      { name: 'Item2', value: 200, category: 'B' },
      { name: 'Item3', value: 50, category: 'A' },
      { name: 'Item4', value: 300, category: 'C' },
      { name: 'Item5', value: 25, category: 'B' },
    ];

    it('should work with generic data types', () => {
      const result = TopNProcessor.sortByValue(customData, 'value');

      expect(result[0].value).toBe(300);
      expect(result[1].value).toBe(200);
      expect(result[2].value).toBe(100);
      expect(result[3].value).toBe(50);
      expect(result[4].value).toBe(25);
    });
  });

  describe('edge cases and error handling', () => {
    it('should handle data with zero values', () => {
      const dataWithZeros = [
        { service: 'A', cost: 100, percentage: 50, unit: 'USD' },
        { service: 'B', cost: 0, percentage: 0, unit: 'USD' },
        { service: 'C', cost: 100, percentage: 50, unit: 'USD' },
      ];

      const result = TopNProcessor.processTopN(dataWithZeros, 2);

      expect(result).toHaveLength(3); // 2 + "Other"
      expect(result[2].service).toBe('Other Services');
      expect(result[2].cost).toBe(0);
    });

    it('should handle negative values correctly', () => {
      const dataWithNegatives = [
        { service: 'A', cost: 100, percentage: 60, unit: 'USD' },
        { service: 'B', cost: -20, percentage: -20, unit: 'USD' },
        { service: 'C', cost: 50, percentage: 60, unit: 'USD' },
      ];

      const result = TopNProcessor.processTopN(dataWithNegatives, 2);

      expect(result).toHaveLength(3);
      expect(result[0].cost).toBe(100); // Highest positive
      expect(result[1].cost).toBe(50);
      expect(result[2].cost).toBe(-20); // Negative in "Other"
    });

    it('should handle very large numbers', () => {
      const dataWithLargeNumbers = [
        { service: 'A', cost: 1e12, percentage: 50, unit: 'USD' },
        { service: 'B', cost: 5e11, percentage: 25, unit: 'USD' },
        { service: 'C', cost: 2.5e11, percentage: 25, unit: 'USD' },
      ];

      const result = TopNProcessor.processTopN(dataWithLargeNumbers, 2);

      expect(result[0].cost).toBe(1e12);
      expect(result[1].cost).toBe(5e11);
      expect(result[2].cost).toBe(2.5e11);
    });
  });

  describe('deterministic behavior', () => {
    it('should produce consistent results across multiple runs', () => {
      const results = [];

      for (let i = 0; i < 5; i++) {
        results.push(TopNProcessor.processTopN(sampleServiceData, 5));
      }

      // All results should be identical
      for (let i = 1; i < results.length; i++) {
        expect(results[i]).toEqual(results[0]);
      }
    });

    it('should maintain stable sort for identical values', () => {
      const dataWithIdenticalValues = [
        { service: 'First', cost: 100, percentage: 10, unit: 'USD' },
        { service: 'Second', cost: 100, percentage: 10, unit: 'USD' },
        { service: 'Third', cost: 100, percentage: 10, unit: 'USD' },
      ];

      const result1 = TopNProcessor.sortByValue(
        dataWithIdenticalValues,
        'cost'
      );
      const result2 = TopNProcessor.sortByValue(
        dataWithIdenticalValues,
        'cost'
      );

      expect(result1).toEqual(result2);
    });
  });
});

import { MoMCalculator } from '../mom';
import { CostPoint } from '../costs/types';

describe('MoMCalculator', () => {
  const sampleData: CostPoint[] = [
    { date: '2024-01-01', amount: 1000, unit: 'USD', estimated: false },
    { date: '2024-02-01', amount: 1200, unit: 'USD', estimated: false },
    { date: '2024-03-01', amount: 900, unit: 'USD', estimated: false },
    { date: '2024-04-01', amount: 1100, unit: 'USD', estimated: false },
    { date: '2024-05-01', amount: 0, unit: 'USD', estimated: false }, // Zero value
  ];

  describe('calculateMoM', () => {
    it('should calculate positive month-over-month change', () => {
      const result = MoMCalculator.calculateMoM(1200, 1000);
      expect(result).toEqual({
        absolute: 200,
        percentage: 20,
        direction: 'increase',
      });
    });

    it('should calculate negative month-over-month change', () => {
      const result = MoMCalculator.calculateMoM(900, 1200);
      expect(result).toEqual({
        absolute: -300,
        percentage: -25,
        direction: 'decrease',
      });
    });

    it('should handle zero current value', () => {
      const result = MoMCalculator.calculateMoM(0, 1000);
      expect(result).toEqual({
        absolute: -1000,
        percentage: -100,
        direction: 'decrease',
      });
    });

    it('should handle zero previous value', () => {
      const result = MoMCalculator.calculateMoM(1000, 0);
      expect(result).toEqual({
        absolute: 1000,
        percentage: Infinity,
        direction: 'increase',
      });
    });

    it('should handle both values being zero', () => {
      const result = MoMCalculator.calculateMoM(0, 0);
      expect(result).toEqual({
        absolute: 0,
        percentage: 0,
        direction: 'stable',
      });
    });

    it('should handle negative values correctly', () => {
      const result = MoMCalculator.calculateMoM(-500, -1000);
      expect(result).toEqual({
        absolute: 500,
        percentage: 50, // Improvement from -1000 to -500
        direction: 'increase',
      });
    });
  });

  describe('processTimeSeries', () => {
    it('should process time series data correctly', () => {
      const result = MoMCalculator.processTimeSeries(sampleData);

      expect(result).toHaveLength(5);

      // First month should have no MoM data
      expect(result[0]).toEqual({
        ...sampleData[0],
        mom: null,
      });

      // Second month should show 20% increase
      expect(result[1]).toEqual({
        ...sampleData[1],
        mom: {
          absolute: 200,
          percentage: 20,
          direction: 'increase',
        },
      });

      // Third month should show 25% decrease
      expect(result[2]).toEqual({
        ...sampleData[2],
        mom: {
          absolute: -300,
          percentage: -25,
          direction: 'decrease',
        },
      });
    });

    it('should handle empty data', () => {
      const result = MoMCalculator.processTimeSeries([]);
      expect(result).toEqual([]);
    });

    it('should handle single data point', () => {
      const singlePoint = [sampleData[0]];
      const result = MoMCalculator.processTimeSeries(singlePoint);

      expect(result).toHaveLength(1);
      expect(result[0].mom).toBeNull();
    });
  });

  describe('getLatestMoM', () => {
    it('should return the most recent MoM calculation', () => {
      const processed = MoMCalculator.processTimeSeries(sampleData);
      const latestMoM = MoMCalculator.getLatestMoM(processed);

      // Latest should be May vs April (0 vs 1100)
      expect(latestMoM).toEqual({
        absolute: -1100,
        percentage: -100,
        direction: 'decrease',
      });
    });

    it('should return null for empty data', () => {
      const latestMoM = MoMCalculator.getLatestMoM([]);
      expect(latestMoM).toBeNull();
    });

    it('should return null for single data point', () => {
      const singlePoint = [{ ...sampleData[0], mom: null }];
      const latestMoM = MoMCalculator.getLatestMoM(singlePoint);
      expect(latestMoM).toBeNull();
    });
  });

  describe('formatMoMChange', () => {
    it('should format positive percentage correctly', () => {
      const formatted = MoMCalculator.formatMoMChange(25.5);
      expect(formatted).toBe('+25.5%');
    });

    it('should format negative percentage correctly', () => {
      const formatted = MoMCalculator.formatMoMChange(-15.25);
      expect(formatted).toBe('-15.3%');
    });

    it('should format zero correctly', () => {
      const formatted = MoMCalculator.formatMoMChange(0);
      expect(formatted).toBe('0.0%');
    });

    it('should handle infinity correctly', () => {
      const formatted = MoMCalculator.formatMoMChange(Infinity);
      expect(formatted).toBe('+∞%');
    });

    it('should handle negative infinity correctly', () => {
      const formatted = MoMCalculator.formatMoMChange(-Infinity);
      expect(formatted).toBe('-∞%');
    });
  });

  describe('edge cases and error handling', () => {
    it('should handle very small numbers', () => {
      const result = MoMCalculator.calculateMoM(0.001, 0.002);
      expect(result.percentage).toBe(-50);
      expect(result.direction).toBe('decrease');
    });

    it('should handle very large numbers', () => {
      const result = MoMCalculator.calculateMoM(1e12, 5e11);
      expect(result.percentage).toBe(100);
      expect(result.direction).toBe('increase');
    });

    it('should handle decimal precision correctly', () => {
      const result = MoMCalculator.calculateMoM(100.33, 100.11);
      expect(result.percentage).toBeCloseTo(0.22, 2);
    });
  });

  describe('data sorting and consistency', () => {
    it('should handle unsorted data correctly', () => {
      const unsortedData: CostPoint[] = [
        { date: '2024-03-01', amount: 900, unit: 'USD', estimated: false },
        { date: '2024-01-01', amount: 1000, unit: 'USD', estimated: false },
        { date: '2024-02-01', amount: 1200, unit: 'USD', estimated: false },
      ];

      const result = MoMCalculator.processTimeSeries(unsortedData);

      // Should be sorted by date
      expect(result[0].date).toBe('2024-01-01');
      expect(result[1].date).toBe('2024-02-01');
      expect(result[2].date).toBe('2024-03-01');

      // MoM calculations should be correct for sorted data
      expect(result[1].mom?.percentage).toBe(20); // Feb vs Jan
      expect(result[2].mom?.percentage).toBe(-25); // Mar vs Feb
    });
  });
});

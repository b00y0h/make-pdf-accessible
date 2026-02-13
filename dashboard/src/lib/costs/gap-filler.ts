import { CostDataPoint, ServiceCostDataPoint, TagCostDataPoint } from './types';
import {
  format,
  addMonths,
  addDays,
  startOfMonth,
  startOfDay,
  parseISO,
  isAfter,
  isBefore,
} from 'date-fns';

export interface GapFillOptions {
  granularity: 'DAILY' | 'MONTHLY';
  fillValue?: number;
  currency?: string;
}

export class GapFiller {
  /**
   * Fill gaps in timeseries data to ensure continuous data points
   */
  static fillTimeSeriesGaps(
    data: CostDataPoint[],
    startDate: string,
    endDate: string,
    options: GapFillOptions
  ): CostDataPoint[] {
    if (!data || data.length === 0) {
      return this.generateEmptyTimeSeries(startDate, endDate, options);
    }

    const { granularity, fillValue = 0, currency = 'USD' } = options;
    const start = parseISO(startDate);
    const end = parseISO(endDate);

    // Create a map of existing data points
    const dataMap = new Map<string, CostDataPoint>();
    data.forEach((point) => {
      const dateStr = point.month || point.time || '';
      if (!dateStr) return;
      const key =
        granularity === 'MONTHLY'
          ? format(parseISO(dateStr), 'yyyy-MM')
          : format(parseISO(dateStr), 'yyyy-MM-dd');
      dataMap.set(key, point);
    });

    // Generate complete time series
    const filledData: CostDataPoint[] = [];
    let current = start;

    while (isBefore(current, end) || current.getTime() === end.getTime()) {
      const key =
        granularity === 'MONTHLY'
          ? format(current, 'yyyy-MM')
          : format(current, 'yyyy-MM-dd');

      const existingPoint = dataMap.get(key);
      if (existingPoint) {
        filledData.push(existingPoint);
      } else {
        // Create zero-value point for missing period
        filledData.push({
          month: key,
          time: key,
          amount: fillValue,
          currency,
        });
      }

      // Move to next period
      current =
        granularity === 'MONTHLY'
          ? addMonths(startOfMonth(current), 1)
          : addDays(startOfDay(current), 1);
    }

    return filledData;
  }

  /**
   * Fill gaps in service cost data
   */
  static fillServiceCostGaps(
    data: ServiceCostDataPoint[],
    startDate: string,
    endDate: string,
    options: GapFillOptions
  ): ServiceCostDataPoint[] {
    if (!data || data.length === 0) {
      return [];
    }

    const { granularity, fillValue = 0, currency = 'USD' } = options;

    // Get unique services
    const services = [...new Set(data.map((point) => point.service))];

    // Group data by service
    const serviceDataMap = new Map<string, Map<string, ServiceCostDataPoint>>();

    services.forEach((service) => {
      serviceDataMap.set(service, new Map());
    });

    data.forEach((point) => {
      const service = point.service;
      const timeKey =
        granularity === 'MONTHLY'
          ? format(parseISO(point.month), 'yyyy-MM')
          : format(parseISO(point.month), 'yyyy-MM-dd');

      serviceDataMap.get(service)?.set(timeKey, point);
    });

    // Fill gaps for each service
    const filledData: ServiceCostDataPoint[] = [];
    const start = parseISO(startDate);
    const end = parseISO(endDate);

    services.forEach((service) => {
      const serviceData = serviceDataMap.get(service)!;
      let current = start;

      while (isBefore(current, end) || current.getTime() === end.getTime()) {
        const timeKey =
          granularity === 'MONTHLY'
            ? format(current, 'yyyy-MM')
            : format(current, 'yyyy-MM-dd');

        const existingPoint = serviceData.get(timeKey);
        if (existingPoint) {
          filledData.push(existingPoint);
        } else {
          // Create zero-value point for missing period
          filledData.push({
            month: timeKey,
            service,
            amount: fillValue,
            currency,
          });
        }

        // Move to next period
        current =
          granularity === 'MONTHLY'
            ? addMonths(startOfMonth(current), 1)
            : addDays(startOfDay(current), 1);
      }
    });

    return filledData.sort((a, b) => {
      const timeCompare = a.month.localeCompare(b.month);
      if (timeCompare !== 0) return timeCompare;
      return a.service.localeCompare(b.service);
    });
  }

  /**
   * Fill gaps in tag cost data
   */
  static fillTagCostGaps(
    data: TagCostDataPoint[],
    startDate: string,
    endDate: string,
    options: GapFillOptions
  ): TagCostDataPoint[] {
    if (!data || data.length === 0) {
      return [];
    }

    const { granularity, fillValue = 0, currency = 'USD' } = options;

    // Get unique tag combinations
    const tagCombinations = [
      ...new Set(data.map((point) => JSON.stringify(point.tags))),
    ];

    // Group data by tag combination
    const tagDataMap = new Map<string, Map<string, TagCostDataPoint>>();

    tagCombinations.forEach((tagCombo) => {
      tagDataMap.set(tagCombo, new Map());
    });

    data.forEach((point) => {
      const tagCombo = JSON.stringify(point.tags);
      const timeKey =
        granularity === 'MONTHLY'
          ? format(parseISO(point.month), 'yyyy-MM')
          : format(parseISO(point.month), 'yyyy-MM-dd');

      tagDataMap.get(tagCombo)?.set(timeKey, point);
    });

    // Fill gaps for each tag combination
    const filledData: TagCostDataPoint[] = [];
    const start = parseISO(startDate);
    const end = parseISO(endDate);

    tagCombinations.forEach((tagCombo) => {
      const tagData = tagDataMap.get(tagCombo)!;
      const tags = JSON.parse(tagCombo);
      let current = start;

      while (isBefore(current, end) || current.getTime() === end.getTime()) {
        const timeKey =
          granularity === 'MONTHLY'
            ? format(current, 'yyyy-MM')
            : format(current, 'yyyy-MM-dd');

        const existingPoint = tagData.get(timeKey);
        if (existingPoint) {
          filledData.push(existingPoint);
        } else {
          // Create zero-value point for missing period
          filledData.push({
            month: timeKey,
            tags,
            amount: fillValue,
            currency,
          });
        }

        // Move to next period
        current =
          granularity === 'MONTHLY'
            ? addMonths(startOfMonth(current), 1)
            : addDays(startOfDay(current), 1);
      }
    });

    return filledData.sort((a, b) => {
      const timeCompare = a.month.localeCompare(b.month);
      if (timeCompare !== 0) return timeCompare;
      return JSON.stringify(a.tags).localeCompare(JSON.stringify(b.tags));
    });
  }

  /**
   * Generate empty time series for when no data exists
   */
  private static generateEmptyTimeSeries(
    startDate: string,
    endDate: string,
    options: GapFillOptions
  ): CostDataPoint[] {
    const { granularity, fillValue = 0, currency = 'USD' } = options;
    const start = parseISO(startDate);
    const end = parseISO(endDate);
    const result: CostDataPoint[] = [];

    let current = start;
    while (isBefore(current, end) || current.getTime() === end.getTime()) {
      const timeKey =
        granularity === 'MONTHLY'
          ? format(current, 'yyyy-MM')
          : format(current, 'yyyy-MM-dd');

      result.push({
        month: timeKey,
        time: timeKey,
        amount: fillValue,
        currency,
      });

      // Move to next period
      current =
        granularity === 'MONTHLY'
          ? addMonths(startOfMonth(current), 1)
          : addDays(startOfDay(current), 1);
    }

    return result;
  }

  /**
   * Validate data continuity and report gaps
   */
  static validateContinuity(
    data: CostDataPoint[],
    startDate: string,
    endDate: string,
    granularity: 'DAILY' | 'MONTHLY'
  ): {
    isComplete: boolean;
    missingPeriods: string[];
    totalPeriods: number;
    existingPeriods: number;
  } {
    const start = parseISO(startDate);
    const end = parseISO(endDate);
    const missingPeriods: string[] = [];

    // Create set of existing periods
    const existingPeriods = new Set(
      data
        .map((point) => {
          const dateStr = point.month || point.time || '';
          if (!dateStr) return '';
          const date = parseISO(dateStr);
          return granularity === 'MONTHLY'
            ? format(date, 'yyyy-MM')
            : format(date, 'yyyy-MM-dd');
        })
        .filter(Boolean)
    );

    let current = start;
    let totalPeriods = 0;

    while (isBefore(current, end) || current.getTime() === end.getTime()) {
      const timeKey =
        granularity === 'MONTHLY'
          ? format(current, 'yyyy-MM')
          : format(current, 'yyyy-MM-dd');

      totalPeriods++;

      if (!existingPeriods.has(timeKey)) {
        missingPeriods.push(timeKey);
      }

      // Move to next period
      current =
        granularity === 'MONTHLY'
          ? addMonths(startOfMonth(current), 1)
          : addDays(startOfDay(current), 1);
    }

    return {
      isComplete: missingPeriods.length === 0,
      missingPeriods,
      totalPeriods,
      existingPeriods: existingPeriods.size,
    };
  }
}

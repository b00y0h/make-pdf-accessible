import { MoMResult, CostPoint } from './costs/types';

/**
 * Calculate Month-over-Month (MoM) metrics from cost data
 */
export class MoMCalculator {
  /**
   * Calculate MoM change between two values
   */
  static calculate(current: number, previous: number): MoMResult {
    // Handle edge cases
    if (previous === 0) {
      return {
        current,
        previous,
        change: current,
        changePercent: current > 0 ? 100 : 0,
        direction: current > 0 ? 'increase' : 'stable',
      };
    }

    if (current < 0 || previous < 0) {
      throw new Error('MoM calculation does not support negative values');
    }

    const change = current - previous;
    const changePercent = (change / previous) * 100;

    let direction: 'increase' | 'decrease' | 'stable';
    if (Math.abs(changePercent) < 0.01) {
      direction = 'stable'; // Less than 0.01% change considered stable
    } else if (change > 0) {
      direction = 'increase';
    } else {
      direction = 'decrease';
    }

    return {
      current,
      previous,
      change,
      changePercent: Math.round(changePercent * 100) / 100, // Round to 2 decimals
      direction,
    };
  }

  /**
   * Calculate MoM from a series of cost points
   * Returns the MoM comparison between the last two periods
   */
  static fromSeries(series: CostPoint[]): MoMResult | null {
    if (series.length < 2) {
      return null;
    }

    // Sort by date to ensure correct order
    const sortedSeries = [...series].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const current = sortedSeries[sortedSeries.length - 1].amount;
    const previous = sortedSeries[sortedSeries.length - 2].amount;

    return this.calculate(current, previous);
  }

  /**
   * Calculate MoM for multiple series (e.g., by service)
   * Returns a map of service name to MoM result
   */
  static fromMultipleSeries(
    seriesMap: Record<string, CostPoint[]>
  ): Record<string, MoMResult | null> {
    const results: Record<string, MoMResult | null> = {};

    for (const [key, series] of Object.entries(seriesMap)) {
      results[key] = this.fromSeries(series);
    }

    return results;
  }

  /**
   * Format MoM result for display
   */
  static format(
    momResult: MoMResult,
    options: {
      showCurrency?: boolean;
      currencySymbol?: string;
      showDirection?: boolean;
      precision?: number;
    } = {}
  ): {
    current: string;
    previous: string;
    change: string;
    changePercent: string;
    direction: string;
  } {
    const {
      showCurrency = true,
      currencySymbol = '$',
      showDirection = true,
      precision = 2,
    } = options;

    const formatNumber = (value: number): string => {
      const formatted = value.toFixed(precision);
      return showCurrency ? `${currencySymbol}${formatted}` : formatted;
    };

    const changeSign = momResult.change > 0 ? '+' : '';
    const percentSign = momResult.changePercent > 0 ? '+' : '';

    let directionText = '';
    if (showDirection) {
      switch (momResult.direction) {
        case 'increase':
          directionText = '↗️';
          break;
        case 'decrease':
          directionText = '↘️';
          break;
        case 'stable':
          directionText = '→';
          break;
      }
    }

    return {
      current: formatNumber(momResult.current),
      previous: formatNumber(momResult.previous),
      change: `${changeSign}${formatNumber(Math.abs(momResult.change))}`,
      changePercent: `${percentSign}${Math.abs(momResult.changePercent).toFixed(1)}%`,
      direction: directionText,
    };
  }

  /**
   * Utility to get the last N months of data for MoM calculations
   */
  static getLastNMonths(series: CostPoint[], n: number = 12): CostPoint[] {
    const sortedSeries = [...series].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    return sortedSeries.slice(0, n).reverse();
  }

  /**
   * Fill gaps in time series with zero values
   * This ensures consistent MoM calculations even when some months have no spend
   */
  static fillGaps(
    series: CostPoint[],
    startDate: string,
    endDate: string,
    granularity: 'MONTHLY' | 'DAILY' = 'MONTHLY'
  ): CostPoint[] {
    const result: CostPoint[] = [];
    const seriesMap = new Map(series.map((point) => [point.date, point]));

    const start = new Date(startDate);
    const end = new Date(endDate);
    const current = new Date(start);

    while (current <= end) {
      const dateStr = current.toISOString().split('T')[0];

      if (seriesMap.has(dateStr)) {
        result.push(seriesMap.get(dateStr)!);
      } else {
        // Fill gap with zero cost
        result.push({
          date: dateStr,
          amount: 0,
          unit: series[0]?.unit || 'USD',
          estimated: false,
        });
      }

      // Increment by month or day based on granularity
      if (granularity === 'MONTHLY') {
        current.setMonth(current.getMonth() + 1);
      } else {
        current.setDate(current.getDate() + 1);
      }
    }

    return result;
  }
}

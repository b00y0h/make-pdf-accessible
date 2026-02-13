import {
  TopNResult,
  ServiceCostData,
  GroupResult,
  MetricValue,
} from './costs/types';

/**
 * Top N utility for grouping and aggregating cost data
 * Implements deterministic logic where "Other" is the sum of excluded keys
 */
export class TopNProcessor {
  /**
   * Process top N items from a list, with remainder grouped as "Other"
   */
  static process<T extends Record<string, any>>(
    items: T[],
    n: number,
    options: {
      sortKey?: keyof T;
      otherLabel?: string;
      includeOther?: boolean;
    } = {}
  ): TopNResult<T> {
    const {
      sortKey = 'amount' as keyof T,
      otherLabel = 'Other',
      includeOther = true,
    } = options;

    if (items.length === 0) {
      return {
        items: [],
        totalCount: 0,
      };
    }

    // Sort items by the specified key in descending order
    const sortedItems = [...items].sort((a, b) => {
      const aValue = Number(a[sortKey]) || 0;
      const bValue = Number(b[sortKey]) || 0;
      return bValue - aValue;
    });

    // Take top N items
    const topItems = sortedItems.slice(0, n);
    const remainingItems = sortedItems.slice(n);

    const result: TopNResult<T> = {
      items: topItems,
      totalCount: items.length,
    };

    // Create "Other" item if there are remaining items and includeOther is true
    if (includeOther && remainingItems.length > 0) {
      const otherTotal = remainingItems.reduce((sum, item) => {
        const value = Number(item[sortKey]) || 0;
        return sum + value;
      }, 0);

      // Create other item with the same structure as original items
      const otherItem = {
        ...remainingItems[0], // Use first remaining item as template
        [sortKey]: otherTotal,
        // Override identifying fields
        ...('service' in remainingItems[0] && { service: otherLabel }),
        ...('name' in remainingItems[0] && { name: otherLabel }),
        ...('key' in remainingItems[0] && { key: otherLabel }),
      } as T;

      result.other = otherItem;
    }

    return result;
  }

  /**
   * Process AWS Cost Explorer GroupResults into ServiceCostData with top N
   */
  static processServiceCosts(
    groups: GroupResult[],
    metric: string = 'UnblendedCost',
    n: number = 8
  ): TopNResult<ServiceCostData> {
    // Convert groups to ServiceCostData
    const serviceData: ServiceCostData[] = groups.map((group) => {
      const service = group.keys[0] || 'Unknown';
      const metricData = group.metrics[metric];
      const cost = parseFloat(metricData?.amount || '0');
      const unit = metricData?.unit || 'USD';

      return {
        service,
        cost,
        percentage: 0, // Will be calculated after we have total
        change: 0, // Will be calculated with MoM data
        changePercent: 0,
        unit,
      };
    });

    // Calculate total cost for percentage calculations
    const totalCost = serviceData.reduce((sum, item) => sum + item.cost, 0);

    // Update percentages
    serviceData.forEach((item) => {
      item.percentage = totalCost > 0 ? (item.cost / totalCost) * 100 : 0;
    });

    // Apply top N processing
    const result = this.process(serviceData, n, {
      sortKey: 'cost',
      otherLabel: 'Other Services',
      includeOther: true,
    });

    // Update "Other" percentage if it exists
    if (result.other) {
      result.other.percentage =
        totalCost > 0 ? (result.other.cost / totalCost) * 100 : 0;
    }

    return result;
  }

  /**
   * Process tag-based cost groupings
   */
  static processTagCosts(
    groups: GroupResult[],
    tagKey: string,
    metric: string = 'UnblendedCost',
    n: number = 5
  ): TopNResult<{
    tag: string;
    value: string;
    cost: number;
    unit: string;
    percentage: number;
  }> {
    // Convert groups to tag cost data
    const tagData = groups.map((group) => {
      const tagValue = group.keys[0] || 'Untagged';
      const metricData = group.metrics[metric];
      const cost = parseFloat(metricData?.amount || '0');
      const unit = metricData?.unit || 'USD';

      return {
        tag: tagKey,
        value: tagValue,
        cost,
        unit,
        percentage: 0,
      };
    });

    // Calculate total and percentages
    const totalCost = tagData.reduce((sum, item) => sum + item.cost, 0);
    tagData.forEach((item) => {
      item.percentage = totalCost > 0 ? (item.cost / totalCost) * 100 : 0;
    });

    return this.process<{
      tag: string;
      value: string;
      cost: number;
      unit: string;
      percentage: number;
    }>(tagData, n, {
      sortKey: 'cost',
      otherLabel: `Other ${tagKey} values`,
      includeOther: true,
    });
  }

  /**
   * Merge top N results from multiple time periods
   * Useful for consistent service/tag groupings across time
   */
  static mergeAcrossTime<T extends Record<string, any>>(
    periodResults: TopNResult<T>[],
    n: number
  ): { topKeys: string[]; otherKeys: string[] } {
    // Collect all unique keys and their total costs
    const keyTotals = new Map<string, number>();

    periodResults.forEach((result) => {
      result.items.forEach((item) => {
        const key = (item.service || item.value || 'Unknown') as string;
        const cost = item.cost || 0;
        keyTotals.set(key, (keyTotals.get(key) || 0) + cost);
      });

      if (result.other) {
        const key = (result.other.service ||
          result.other.value ||
          'Other') as string;
        const cost = result.other.cost || 0;
        keyTotals.set(key, (keyTotals.get(key) || 0) + cost);
      }
    });

    // Sort by total cost and take top N
    const sortedKeys = Array.from(keyTotals.entries())
      .sort(([, a], [, b]) => b - a)
      .map(([key]) => key);

    const topKeys = sortedKeys.slice(0, n).filter((key) => key !== 'Other');
    const otherKeys = sortedKeys.slice(n).filter((key) => key !== 'Other');

    return { topKeys, otherKeys };
  }

  /**
   * Format top N result for chart display
   */
  static formatForChart<T extends Record<string, any>>(
    result: TopNResult<T>,
    options: {
      labelKey: keyof T;
      valueKey?: keyof T;
      includeOther?: boolean;
      colorPalette?: string[];
    }
  ): Array<{ label: string; value: number; color?: string }> {
    const {
      labelKey,
      valueKey = 'cost' as keyof T,
      includeOther = true,
      colorPalette = [
        '#3B82F6',
        '#EF4444',
        '#10B981',
        '#F59E0B',
        '#8B5CF6',
        '#06B6D4',
        '#84CC16',
        '#F97316',
        '#EC4899',
        '#6B7280',
      ],
    } = options;

    const chartData: Array<{ label: string; value: number; color?: string }> =
      [];

    // Add top items
    result.items.forEach((item, index) => {
      chartData.push({
        label: String(item[labelKey]),
        value: Number(item[valueKey]) || 0,
        color: colorPalette[index % colorPalette.length],
      });
    });

    // Add "Other" if it exists and includeOther is true
    if (includeOther && result.other) {
      chartData.push({
        label: String(result.other[labelKey]),
        value: Number(result.other[valueKey]) || 0,
        color: '#9CA3AF', // Gray color for "Other"
      });
    }

    return chartData;
  }

  /**
   * Calculate the threshold value for the Nth item
   * Useful for consistent grouping across different time periods
   */
  static getThreshold<T extends Record<string, any>>(
    items: T[],
    n: number,
    sortKey: keyof T = 'amount' as keyof T
  ): number {
    if (items.length <= n) {
      return 0;
    }

    const sortedItems = [...items].sort((a, b) => {
      const aValue = Number(a[sortKey]) || 0;
      const bValue = Number(b[sortKey]) || 0;
      return bValue - aValue;
    });

    return Number(sortedItems[n - 1][sortKey]) || 0;
  }

  /**
   * Process top N items with "Other" aggregation - compatible with existing tests
   */
  static processTopN<T extends Record<string, any>>(
    items: T[],
    n: number
  ): T[] {
    if (items.length === 0) {
      return [];
    }

    if (n >= items.length) {
      return [...items];
    }

    if (n === 0) {
      const otherItem = this.aggregateOthers(items);
      return [otherItem];
    }

    const topItems = items.slice(0, n);
    const remainingItems = items.slice(n);

    if (remainingItems.length === 0) {
      return topItems;
    }

    const otherItem = this.aggregateOthers(remainingItems);
    return [...topItems, otherItem];
  }

  /**
   * Aggregate remaining items into an "Other" item
   */
  static aggregateOthers<T extends Record<string, any>>(items: T[]): T {
    if (items.length === 0) {
      return {
        service: 'Other Services',
        cost: 0,
        percentage: 0,
        unit: 'USD',
      } as unknown as T;
    }

    const template = items[0];
    const totalCost = items.reduce((sum, item) => sum + (item.cost || 0), 0);
    const totalPercentage = items.reduce(
      (sum, item) => sum + (item.percentage || 0),
      0
    );

    return {
      ...template,
      service: 'Other Services',
      cost: totalCost,
      percentage: totalPercentage,
      unit: items[0]?.unit || 'USD',
    } as unknown as T;
  }

  /**
   * Sort items by specified field in descending order
   */
  static sortByValue<T extends Record<string, any>>(
    items: T[],
    sortKey: keyof T
  ): T[] {
    return [...items].sort((a, b) => {
      const aValue = Number(a[sortKey]) || 0;
      const bValue = Number(b[sortKey]) || 0;
      return bValue - aValue;
    });
  }
}

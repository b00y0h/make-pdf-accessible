// AWS Cost Explorer API Types

export interface TimePeriod {
  start: string; // YYYY-MM-DD format
  end: string; // YYYY-MM-DD format
}

export interface CostPoint {
  date: string;
  amount: number;
  unit: string;
  estimated?: boolean;
}

export interface GroupDefinition {
  type: 'DIMENSION' | 'TAG' | 'COST_CATEGORY';
  key: string;
}

export interface MetricValue {
  amount: string;
  unit: string;
}

// Cost Explorer Result Types
export interface ResultByTime {
  timePeriod: TimePeriod;
  total: Record<string, MetricValue>;
  groups: GroupResult[];
  estimated: boolean;
}

export interface GroupResult {
  keys: string[];
  attributes: Record<string, AttributeValue>;
  metrics: Record<string, MetricValue>;
}

export interface AttributeValue {
  value: string;
  attributes: Record<string, string>;
}

// Normalized Response Types (single shape across CE & Athena)
export interface CostSeries {
  metric: string;
  groupBy?: string;
  series: CostPoint[];
  metadata?: {
    source: 'ce' | 'athena';
    requestId: string;
    cached?: boolean;
    cacheExpiry?: string;
    gapsFilled?: boolean;
  };
}

// Filter Types
export interface CostFilters {
  dateRange: {
    preset: '3months' | '6months' | '12months' | '18months' | 'custom';
    startDate?: string;
    endDate?: string;
    custom?: {
      start: string;
      end: string;
    };
  };
  metric: 'UnblendedCost' | 'AmortizedCost';
  granularity: 'DAILY' | 'MONTHLY' | 'HOURLY';
  services?: string[];
  tags?: Record<string, string[]>;
  accounts?: string[];
  regions?: string[];
}

// Service dimension types
export interface ServiceDimension {
  value: string;
  attributes?: Record<string, string>;
  displayName?: string;
}

// Forecast Types
export interface ForecastResult {
  timePeriod: TimePeriod;
  meanValue: string;
  predictionIntervalLowerBound: string;
  predictionIntervalUpperBound: string;
}

// Top N utility types
export interface TopNResult<T> {
  items: T[];
  other?: T;
  totalCount: number;
}

// Month-over-Month utility types
export interface MoMResult {
  current: number;
  previous: number;
  change: number;
  changePercent: number;
  direction: 'increase' | 'decrease' | 'stable';
}

// Client configuration types
export interface CostExplorerConfig {
  source: 'ce' | 'athena';
  region: string;
  payerAccountId?: string;
  linkedAccountIds?: string[];
  costAllocationTags: string[];
  cacheConfig?: {
    ttl: number; // seconds
    keyPrefix: string;
  };
}

// API Response wrapper types
export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
  details?: string;
  requestId?: string;
}

// Specific API response types
export type CostSummaryResponse = ApiResponse<{
  metric: string;
  groupBy: string;
  granularity: string;
  timePeriod: TimePeriod;
  resultsByTime: ResultByTime[];
  nextPageToken?: string;
  requestId: string;
}>;

export type CostTimeseriesResponse = ApiResponse<{
  metric: string;
  granularity: string;
  timePeriod: TimePeriod;
  series: CostPoint[];
  requestId: string;
}>;

export type CostByTagResponse = ApiResponse<{
  metric: string;
  granularity: string;
  groupBy: string;
  timePeriod: TimePeriod;
  resultsByTime: ResultByTime[];
  requestId: string;
}>;

export type CostServicesResponse = ApiResponse<{
  dimension: string;
  timePeriod: TimePeriod;
  dimensionValues: ServiceDimension[];
  requestId: string;
}>;

export type CostForecastResponse = ApiResponse<{
  metric: string;
  granularity: string;
  predictionIntervalLevel: number;
  timePeriod: TimePeriod;
  forecastResultsByTime: ForecastResult[];
  total: MetricValue;
  requestId: string;
}>;

// Component prop types
export interface CostOverviewProps {
  filters?: CostFilters;
  onFiltersChange?: (filters: CostFilters) => void;
}

export interface CostFiltersProps {
  filters: CostFilters;
  onChange: (filters: CostFilters) => void;
  availableServices?: string[];
  availableTags?: string[];
}

// Chart data types
export interface ChartDataPoint {
  date: string;
  [key: string]: string | number;
}

export interface ServiceCostData {
  service: string;
  cost: number;
  percentage: number;
  change: number;
  changePercent: number;
  unit: string;
}

// Error types
export class CostExplorerError extends Error {
  constructor(
    message: string,
    public code?: string,
    public statusCode?: number,
    public requestId?: string
  ) {
    super(message);
    this.name = 'CostExplorerError';
  }
}

export class AthenaError extends Error {
  constructor(
    message: string,
    public code?: string,
    public queryExecutionId?: string
  ) {
    super(message);
    this.name = 'AthenaError';
  }
}

// Athena/Gap-filler specific types
export interface CostDataPoint {
  month: string;
  time?: string;
  amount: number;
  currency: string;
}

export interface ServiceCostDataPoint {
  month: string;
  service: string;
  amount: number;
  currency: string;
}

export interface TagCostDataPoint {
  month: string;
  tags: Record<string, string>;
  amount: number;
  currency: string;
}

export interface TimeSeriesResponse {
  timePeriod: TimePeriod;
  dataPoints: CostDataPoint[];
  total: number;
}

export interface ServiceCostResponse {
  timePeriod: TimePeriod;
  dataPoints: ServiceCostDataPoint[];
  services: ServiceDimension[];
}

export interface TagCostResponse {
  timePeriod: TimePeriod;
  dataPoints: TagCostDataPoint[];
  tags: string[];
}

'use client';

import { useState, useEffect, useCallback } from 'react';
import { CostPoint, CostFilters } from '@/lib/costs/types';

export type DataSource = 'ce' | 'athena';

interface CostDataState {
  timeseries: CostPoint[];
  summary: CostPoint[];
  services: string[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

interface UseCostDataOptions {
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
  dataSource?: DataSource;
}

export function useCostData(
  filters: CostFilters,
  options: UseCostDataOptions = {}
) {
  const { autoRefresh = false, refreshInterval = 5 * 60 * 1000, dataSource = 'ce' } = options; // 5 minutes default

  const [state, setState] = useState<CostDataState>({
    timeseries: [],
    summary: [],
    services: [],
    loading: true,
    error: null,
    lastUpdated: null,
  });

  // Build query params from filters
  const buildQueryParams = useCallback((endpoint: string) => {
    const params = new URLSearchParams();
    
    params.set('metric', filters.metric);
    params.set('granularity', filters.granularity);
    
    if (filters.dateRange.preset !== 'custom') {
      params.set('preset', filters.dateRange.preset);
    } else if (filters.dateRange.startDate && filters.dateRange.endDate) {
      params.set('startDate', filters.dateRange.startDate);
      params.set('endDate', filters.dateRange.endDate);
    }
    
    if (filters.services && filters.services.length > 0) {
      params.set('services', filters.services.join(','));
    }
    
    if (filters.accounts && filters.accounts.length > 0) {
      params.set('accounts', filters.accounts.join(','));
    }
    
    if (filters.regions && filters.regions.length > 0) {
      params.set('regions', filters.regions.join(','));
    }
    
    if (filters.tags && Object.keys(filters.tags).length > 0) {
      params.set('tags', JSON.stringify(filters.tags));
    }
    
    return params;
  }, [filters]);

  // Get API base path based on data source
  const getApiBasePath = useCallback(() => {
    return dataSource === 'athena' ? '/api/costs/athena' : '/api/costs';
  }, [dataSource]);

  // Fetch data from API
  const fetchData = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const basePath = getApiBasePath();

      // Fetch timeseries data (total costs over time)
      const timeseriesParams = buildQueryParams('timeseries');
      const timeseriesResponse = await fetch(`${basePath}/timeseries?${timeseriesParams}`);
      
      if (!timeseriesResponse.ok) {
        throw new Error(`Timeseries API error: ${timeseriesResponse.status}`);
      }
      
      const timeseriesData = await timeseriesResponse.json();
      
      if (dataSource === 'ce' && !timeseriesData.ok) {
        throw new Error(timeseriesData.error || 'Failed to fetch timeseries data');
      }

      // Fetch summary data (costs by service) - different endpoints for different sources
      let summaryData;
      if (dataSource === 'athena') {
        const summaryParams = buildQueryParams('services');
        const summaryResponse = await fetch(`${basePath}/services?${summaryParams}`);
        
        if (!summaryResponse.ok) {
          throw new Error(`Services API error: ${summaryResponse.status}`);
        }
        
        summaryData = await summaryResponse.json();
      } else {
        const summaryParams = buildQueryParams('summary');
        summaryParams.set('groupBy', 'SERVICE');
        const summaryResponse = await fetch(`${basePath}/summary?${summaryParams}`);
        
        if (!summaryResponse.ok) {
          throw new Error(`Summary API error: ${summaryResponse.status}`);
        }
        
        summaryData = await summaryResponse.json();
        
        if (!summaryData.ok) {
          throw new Error(summaryData.error || 'Failed to fetch summary data');
        }
      }

      // Fetch available services
      let availableServices: string[] = [];
      if (dataSource === 'ce') {
        const servicesParams = buildQueryParams('services');
        const servicesResponse = await fetch(`${basePath}/services?${servicesParams}`);
        
        if (servicesResponse.ok) {
          const servicesData = await servicesResponse.json();
          if (servicesData.ok && servicesData.data.dimensionValues) {
            availableServices = servicesData.data.dimensionValues.map(
              (dim: any) => dim.value
            );
          }
        }
      } else {
        // For Athena, extract services from summary data
        if (summaryData?.services) {
          availableServices = summaryData.services.map((service: any) => service.value);
        }
      }

      // Normalize data format based on source
      let timeseriesPoints: CostPoint[] = [];
      let summaryPoints: CostPoint[] = [];

      if (dataSource === 'ce') {
        timeseriesPoints = timeseriesData.data?.series || [];
        summaryPoints = summaryData.data?.series || [];
      } else {
        // Transform Athena response to CostPoint format
        timeseriesPoints = (timeseriesData.dataPoints || []).map((point: any) => ({
          time: point.month,
          amount: point.amount,
          currency: point.currency || 'USD'
        }));
        
        summaryPoints = (summaryData.dataPoints || []).map((point: any) => ({
          time: point.month,
          amount: point.amount,
          service: point.service,
          currency: point.currency || 'USD'
        }));
      }

      setState({
        timeseries: timeseriesPoints,
        summary: summaryPoints,
        services: availableServices,
        loading: false,
        error: null,
        lastUpdated: new Date(),
      });

    } catch (error) {
      console.error('Error fetching cost data:', error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      }));
    }
  }, [buildQueryParams, getApiBasePath, dataSource]);

  // Manual refresh function
  const refresh = useCallback(() => {
    fetchData();
  }, [fetchData]);

  // Initial data fetch and when filters change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh setup
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchData]);

  return {
    ...state,
    refresh,
    isStale: state.lastUpdated && 
      Date.now() - state.lastUpdated.getTime() > refreshInterval,
  };
}

// Hook specifically for forecast data
export function useForecastData(filters: Pick<CostFilters, 'metric'>) {
  const [state, setState] = useState<{
    data: any[];
    loading: boolean;
    error: string | null;
  }>({
    data: [],
    loading: true,
    error: null,
  });

  const fetchForecast = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));

      const params = new URLSearchParams();
      params.set('metric', filters.metric === 'UnblendedCost' ? 'UNBLENDED_COST' : 'BLENDED_COST');
      params.set('granularity', 'MONTHLY');
      params.set('predictionInterval', '80');

      const response = await fetch(`/api/costs/forecast?${params}`);
      
      if (!response.ok) {
        throw new Error(`Forecast API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.ok) {
        throw new Error(data.error || 'Failed to fetch forecast data');
      }

      setState({
        data: data.data.forecastResultsByTime || [],
        loading: false,
        error: null,
      });

    } catch (error) {
      console.error('Error fetching forecast data:', error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      }));
    }
  }, [filters.metric]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  return state;
}
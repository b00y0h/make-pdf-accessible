'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect } from 'react';
import { CostFilters } from '@/lib/costs/types';

export function useFilterPersistence(
  filters: CostFilters,
  setFilters: (filters: CostFilters) => void
) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Serialize filters to URL params
  const serializeFilters = useCallback(
    (filters: CostFilters): URLSearchParams => {
      const params = new URLSearchParams();

      // Date range
      if (filters.dateRange.preset !== '12months') {
        params.set('preset', filters.dateRange.preset);
      }

      if (filters.dateRange.custom) {
        params.set('start', filters.dateRange.custom.start);
        params.set('end', filters.dateRange.custom.end);
      }

      // Metric and granularity
      if (filters.metric !== 'UnblendedCost') {
        params.set('metric', filters.metric);
      }

      if (filters.granularity !== 'MONTHLY') {
        params.set('granularity', filters.granularity);
      }

      // Multi-select filters
      if (filters.services && filters.services.length > 0) {
        params.set('services', filters.services.join(','));
      }

      if (filters.accounts && filters.accounts.length > 0) {
        params.set('accounts', filters.accounts.join(','));
      }

      if (filters.regions && filters.regions.length > 0) {
        params.set('regions', filters.regions.join(','));
      }

      // Tags (as JSON)
      if (filters.tags && Object.keys(filters.tags).length > 0) {
        params.set('tags', JSON.stringify(filters.tags));
      }

      return params;
    },
    []
  );

  // Deserialize URL params to filters
  const deserializeFilters = useCallback(
    (searchParams: URLSearchParams): CostFilters => {
      const filters: CostFilters = {
        dateRange: {
          preset: (searchParams.get('preset') as any) || '12months',
        },
        metric: (searchParams.get('metric') as any) || 'UnblendedCost',
        granularity: (searchParams.get('granularity') as any) || 'MONTHLY',
        services: [],
        accounts: [],
        regions: [],
        tags: {},
      };

      // Custom date range
      const start = searchParams.get('start');
      const end = searchParams.get('end');
      if (start && end) {
        filters.dateRange = {
          preset: 'custom',
          custom: { start, end },
        };
      }

      // Multi-select filters
      const services = searchParams.get('services');
      if (services) {
        filters.services = services.split(',').filter(Boolean);
      }

      const accounts = searchParams.get('accounts');
      if (accounts) {
        filters.accounts = accounts.split(',').filter(Boolean);
      }

      const regions = searchParams.get('regions');
      if (regions) {
        filters.regions = regions.split(',').filter(Boolean);
      }

      // Tags
      const tags = searchParams.get('tags');
      if (tags) {
        try {
          filters.tags = JSON.parse(tags);
        } catch (error) {
          console.warn('Failed to parse tags from URL:', error);
          filters.tags = {};
        }
      }

      return filters;
    },
    []
  );

  // Load filters from URL on mount
  useEffect(() => {
    const urlFilters = deserializeFilters(searchParams);

    // Only update if different from current filters
    const currentSerialized = serializeFilters(filters);
    const urlSerialized = serializeFilters(urlFilters);

    if (currentSerialized.toString() !== urlSerialized.toString()) {
      setFilters(urlFilters);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update URL when filters change
  const updateURL = useCallback(
    (newFilters: CostFilters) => {
      const params = serializeFilters(newFilters);
      const queryString = params.toString();

      // Update URL without navigation
      const newUrl = queryString
        ? `${window.location.pathname}?${queryString}`
        : window.location.pathname;

      router.replace(newUrl, { scroll: false });
    },
    [router, serializeFilters]
  );

  // Debounced URL update
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      updateURL(filters);
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [filters, updateURL]);

  // Reset filters and URL
  const resetFilters = useCallback(() => {
    const defaultFilters: CostFilters = {
      dateRange: { preset: '12months' },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: [],
      accounts: [],
      regions: [],
      tags: {},
    };

    setFilters(defaultFilters);
    router.replace(window.location.pathname, { scroll: false });
  }, [setFilters, router]);

  // Get shareable URL
  const getShareableURL = useCallback(() => {
    const params = serializeFilters(filters);
    const baseUrl = window.location.origin + window.location.pathname;
    return params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;
  }, [filters, serializeFilters]);

  return {
    resetFilters,
    getShareableURL,
  };
}

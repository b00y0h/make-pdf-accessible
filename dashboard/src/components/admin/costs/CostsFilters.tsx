'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { X, RefreshCw } from 'lucide-react';
import { CostFilters } from '@/lib/costs/types';

interface CostsFiltersProps {
  filters: CostFilters;
  onChange: (filters: CostFilters) => void;
  availableServices?: string[];
  loading?: boolean;
  onRefresh?: () => void;
}

export function CostsFilters({
  filters,
  onChange,
  availableServices = [],
  loading = false,
  onRefresh,
}: CostsFiltersProps) {
  // Handle date range change
  const handleDateRangeChange = (preset: string) => {
    onChange({
      ...filters,
      dateRange: {
        ...filters.dateRange,
        preset: preset as any,
      },
    });
  };

  // Handle metric change
  const handleMetricChange = (metric: string) => {
    onChange({
      ...filters,
      metric: metric as 'UnblendedCost' | 'AmortizedCost',
    });
  };

  // Handle granularity change
  const handleGranularityChange = (granularity: string) => {
    onChange({
      ...filters,
      granularity: granularity as 'DAILY' | 'MONTHLY',
    });
  };

  // Reset filters to defaults
  const resetFilters = () => {
    onChange({
      dateRange: {
        preset: '12months',
      },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: [],
      tags: {},
      accounts: [],
      regions: [],
    });
  };

  // Remove specific filter
  const removeFilter = (filterType: string, value?: string) => {
    switch (filterType) {
      case 'service':
        if (value) {
          onChange({
            ...filters,
            services: filters.services?.filter((s) => s !== value) || [],
          });
        }
        break;
      case 'services':
        onChange({
          ...filters,
          services: [],
        });
        break;
    }
  };

  // Get active filter count
  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.dateRange.preset !== '12months') count++;
    if (filters.metric !== 'UnblendedCost') count++;
    if (filters.granularity !== 'MONTHLY') count++;
    if (filters.services && filters.services.length > 0) count++;
    return count;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Date Range */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">
            Date Range:
          </label>
          <Select
            value={filters.dateRange.preset}
            onValueChange={handleDateRangeChange}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3months">Last 3 months</SelectItem>
              <SelectItem value="6months">Last 6 months</SelectItem>
              <SelectItem value="12months">Last 12 months</SelectItem>
              <SelectItem value="18months">Last 18 months</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Cost Type */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">
            Cost Type:
          </label>
          <Select
            value={
              filters.metric === 'UnblendedCost' ? 'unblended' : 'amortized'
            }
            onValueChange={(value) =>
              handleMetricChange(
                value === 'unblended' ? 'UnblendedCost' : 'AmortizedCost'
              )
            }
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Select type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="unblended">Unblended</SelectItem>
              <SelectItem value="amortized">Amortized</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Granularity */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">
            Granularity:
          </label>
          <Select
            value={filters.granularity.toLowerCase()}
            onValueChange={(value) =>
              handleGranularityChange(value.toUpperCase())
            }
          >
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Select granularity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="monthly">Monthly</SelectItem>
              <SelectItem value="daily">Daily</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Services Filter - Simplified for now */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Services:</label>
          <Button variant="outline" size="sm" disabled>
            {filters.services && filters.services.length > 0
              ? `${filters.services.length} selected`
              : 'All Services'}
          </Button>
        </div>

        {/* Refresh Button */}
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}

        {/* Reset Button */}
        {getActiveFiltersCount() > 0 && (
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            Reset Filters
          </Button>
        )}
      </div>

      {/* Active Filters */}
      <div className="flex items-center flex-wrap gap-2">
        <span className="text-sm text-gray-600">Active filters:</span>

        <Badge variant="secondary" className="flex items-center gap-1">
          {filters.dateRange.preset === '3months'
            ? 'Last 3 months'
            : filters.dateRange.preset === '6months'
              ? 'Last 6 months'
              : filters.dateRange.preset === '12months'
                ? 'Last 12 months'
                : filters.dateRange.preset === '18months'
                  ? 'Last 18 months'
                  : 'Custom range'}
        </Badge>

        <Badge variant="secondary" className="flex items-center gap-1">
          {filters.metric === 'UnblendedCost'
            ? 'Unblended Cost'
            : 'Amortized Cost'}
        </Badge>

        <Badge variant="secondary" className="flex items-center gap-1">
          {filters.granularity} view
        </Badge>

        {filters.services && filters.services.length > 0 ? (
          <Badge variant="secondary" className="flex items-center gap-1">
            {filters.services.length === 1
              ? filters.services[0]
              : `${filters.services.length} services`}
            <X
              className="h-3 w-3 cursor-pointer hover:text-red-500"
              onClick={() => removeFilter('services')}
            />
          </Badge>
        ) : (
          <Badge variant="secondary">All Services</Badge>
        )}

        {loading && (
          <Badge variant="outline" className="animate-pulse">
            Loading...
          </Badge>
        )}
      </div>
    </div>
  );
}

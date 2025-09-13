'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  CalendarIcon, 
  ChevronDown, 
  X, 
  Plus,
  Settings2,
  RefreshCw,
  RotateCcw
} from 'lucide-react';
import { format } from 'date-fns';
import { CostFilters, ServiceDimension } from '@/lib/costs/types';
import { cn } from '@/lib/utils';

interface AdvancedFiltersProps {
  filters: CostFilters;
  onChange: (filters: CostFilters) => void;
  availableServices?: ServiceDimension[];
  availableAccounts?: string[];
  availableRegions?: string[];
  availableTagKeys?: string[];
  loading?: boolean;
  onRefresh?: () => void;
}

export function AdvancedFilters({
  filters,
  onChange,
  availableServices = [],
  availableAccounts = [],
  availableRegions = [],
  availableTagKeys = [],
  loading = false,
  onRefresh,
}: AdvancedFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newTagKey, setNewTagKey] = useState('');
  const [newTagValue, setNewTagValue] = useState('');

  // Handle date range changes
  const handleDateRangeChange = (preset: string) => {
    onChange({
      ...filters,
      dateRange: { preset: preset as any },
    });
  };

  const handleCustomDateChange = (field: 'start' | 'end', date: Date | undefined) => {
    if (!date) return;
    
    const customRange = filters.dateRange.custom || { start: '', end: '' };
    onChange({
      ...filters,
      dateRange: {
        preset: 'custom',
        custom: {
          ...customRange,
          [field]: date.toISOString().split('T')[0],
        },
      },
    });
  };

  // Handle multi-select changes
  const handleMultiSelectChange = (
    field: 'services' | 'accounts' | 'regions',
    value: string,
    checked: boolean
  ) => {
    const currentValues = filters[field] || [];
    const newValues = checked
      ? [...currentValues, value]
      : currentValues.filter(v => v !== value);

    onChange({
      ...filters,
      [field]: newValues,
    });
  };

  // Handle tag filters
  const addTagFilter = () => {
    if (!newTagKey.trim() || !newTagValue.trim()) return;

    const currentTags = filters.tags || {};
    const currentValues = currentTags[newTagKey] || [];

    onChange({
      ...filters,
      tags: {
        ...currentTags,
        [newTagKey]: [...currentValues, newTagValue],
      },
    });

    setNewTagKey('');
    setNewTagValue('');
  };

  const removeTagFilter = (key: string, value?: string) => {
    const currentTags = filters.tags || {};
    
    if (value) {
      // Remove specific value
      const updatedValues = (currentTags[key] || []).filter(v => v !== value);
      const newTags = { ...currentTags };
      
      if (updatedValues.length === 0) {
        delete newTags[key];
      } else {
        newTags[key] = updatedValues;
      }

      onChange({
        ...filters,
        tags: newTags,
      });
    } else {
      // Remove entire key
      const newTags = { ...currentTags };
      delete newTags[key];
      
      onChange({
        ...filters,
        tags: newTags,
      });
    }
  };

  // Reset filters
  const resetFilters = () => {
    onChange({
      dateRange: { preset: '12months' },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: [],
      accounts: [],
      regions: [],
      tags: {},
    });
    setShowAdvanced(false);
  };

  // Calculate active filters count
  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.dateRange.preset !== '12months') count++;
    if (filters.metric !== 'UnblendedCost') count++;
    if (filters.granularity !== 'MONTHLY') count++;
    if (filters.services && filters.services.length > 0) count++;
    if (filters.accounts && filters.accounts.length > 0) count++;
    if (filters.regions && filters.regions.length > 0) count++;
    if (filters.tags && Object.keys(filters.tags).length > 0) count++;
    return count;
  };

  return (
    <div className="space-y-4">
      {/* Basic Filters Row */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Date Range */}
        <div className="flex items-center space-x-2">
          <Label className="text-sm font-medium">Date Range:</Label>
          <Select value={filters.dateRange.preset} onValueChange={handleDateRangeChange}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3months">Last 3 months</SelectItem>
              <SelectItem value="6months">Last 6 months</SelectItem>
              <SelectItem value="12months">Last 12 months</SelectItem>
              <SelectItem value="18months">Last 18 months</SelectItem>
              <SelectItem value="custom">Custom range</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Custom Date Range */}
        {filters.dateRange.preset === 'custom' && (
          <>
            <div className="flex items-center space-x-2">
              <Label className="text-sm">From:</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-[140px] justify-start text-left font-normal">
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {filters.dateRange.custom?.start 
                      ? format(new Date(filters.dateRange.custom.start), 'MMM dd, yyyy')
                      : 'Pick date'
                    }
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={filters.dateRange.custom?.start ? new Date(filters.dateRange.custom.start) : undefined}
                    onSelect={(date) => handleCustomDateChange('start', date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
            
            <div className="flex items-center space-x-2">
              <Label className="text-sm">To:</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-[140px] justify-start text-left font-normal">
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {filters.dateRange.custom?.end 
                      ? format(new Date(filters.dateRange.custom.end), 'MMM dd, yyyy')
                      : 'Pick date'
                    }
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={filters.dateRange.custom?.end ? new Date(filters.dateRange.custom.end) : undefined}
                    onSelect={(date) => handleCustomDateChange('end', date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
          </>
        )}

        {/* Metric Type */}
        <div className="flex items-center space-x-2">
          <Label className="text-sm font-medium">Cost Type:</Label>
          <Select 
            value={filters.metric} 
            onValueChange={(value) => onChange({ ...filters, metric: value as any })}
          >
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="UnblendedCost">Unblended</SelectItem>
              <SelectItem value="AmortizedCost">Amortized</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Granularity */}
        <div className="flex items-center space-x-2">
          <Label className="text-sm font-medium">View:</Label>
          <Select 
            value={filters.granularity} 
            onValueChange={(value) => onChange({ ...filters, granularity: value as any })}
          >
            <SelectTrigger className="w-[100px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="MONTHLY">Monthly</SelectItem>
              <SelectItem value="DAILY">Daily</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Advanced Toggle */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2"
        >
          <Settings2 className="h-4 w-4" />
          Advanced
          <ChevronDown className={cn("h-4 w-4 transition-transform", showAdvanced && "rotate-180")} />
        </Button>

        {/* Refresh */}
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Refresh
          </Button>
        )}

        {/* Reset */}
        {getActiveFiltersCount() > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={resetFilters}
            className="flex items-center gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        )}
      </div>

      {/* Advanced Filters Panel */}
      {showAdvanced && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
          {/* Services Filter */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">AWS Services</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-between">
                  {filters.services && filters.services.length > 0
                    ? `${filters.services.length} service(s)`
                    : 'All services'
                  }
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0">
                <Command>
                  <CommandInput placeholder="Search services..." />
                  <CommandList>
                    <CommandEmpty>No services found.</CommandEmpty>
                    <CommandGroup>
                      {availableServices.map((service) => (
                        <CommandItem key={service.value} className="flex items-center space-x-2">
                          <Checkbox
                            checked={filters.services?.includes(service.value) || false}
                            onCheckedChange={(checked) =>
                              handleMultiSelectChange('services', service.value, checked as boolean)
                            }
                          />
                          <span className="text-sm">{service.displayName}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Accounts Filter */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">AWS Accounts</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-between">
                  {filters.accounts && filters.accounts.length > 0
                    ? `${filters.accounts.length} account(s)`
                    : 'All accounts'
                  }
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0">
                <Command>
                  <CommandInput placeholder="Search accounts..." />
                  <CommandList>
                    <CommandEmpty>No accounts found.</CommandEmpty>
                    <CommandGroup>
                      {availableAccounts.map((account) => (
                        <CommandItem key={account} className="flex items-center space-x-2">
                          <Checkbox
                            checked={filters.accounts?.includes(account) || false}
                            onCheckedChange={(checked) =>
                              handleMultiSelectChange('accounts', account, checked as boolean)
                            }
                          />
                          <span className="text-sm">{account}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Regions Filter */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">AWS Regions</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-between">
                  {filters.regions && filters.regions.length > 0
                    ? `${filters.regions.length} region(s)`
                    : 'All regions'
                  }
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0">
                <Command>
                  <CommandInput placeholder="Search regions..." />
                  <CommandList>
                    <CommandEmpty>No regions found.</CommandEmpty>
                    <CommandGroup>
                      {availableRegions.map((region) => (
                        <CommandItem key={region} className="flex items-center space-x-2">
                          <Checkbox
                            checked={filters.regions?.includes(region) || false}
                            onCheckedChange={(checked) =>
                              handleMultiSelectChange('regions', region, checked as boolean)
                            }
                          />
                          <span className="text-sm">{region}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Tag Filters */}
          <div className="space-y-2 md:col-span-2 lg:col-span-3">
            <Label className="text-sm font-medium">Resource Tags</Label>
            <div className="flex gap-2">
              <Select value={newTagKey} onValueChange={setNewTagKey}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Tag key" />
                </SelectTrigger>
                <SelectContent>
                  {availableTagKeys.map((key) => (
                    <SelectItem key={key} value={key}>
                      {key}
                    </SelectItem>
                  ))}
                  <SelectItem value="custom">Custom...</SelectItem>
                </SelectContent>
              </Select>
              
              {newTagKey && (
                <>
                  <Input
                    placeholder="Tag value"
                    value={newTagValue}
                    onChange={(e) => setNewTagValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addTagFilter()}
                    className="w-[150px]"
                  />
                  <Button size="sm" onClick={addTagFilter} disabled={!newTagKey || !newTagValue}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Active Filters Summary */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-gray-600">Active filters:</span>
        
        {/* Date Range Badge */}
        <Badge variant="secondary">
          {filters.dateRange.preset === 'custom' && filters.dateRange.custom
            ? `${filters.dateRange.custom.start} to ${filters.dateRange.custom.end}`
            : filters.dateRange.preset === '3months' ? 'Last 3 months'
            : filters.dateRange.preset === '6months' ? 'Last 6 months'
            : filters.dateRange.preset === '12months' ? 'Last 12 months'
            : 'Last 18 months'
          }
        </Badge>

        <Badge variant="secondary">
          {filters.metric === 'UnblendedCost' ? 'Unblended' : 'Amortized'} • {filters.granularity}
        </Badge>

        {/* Services */}
        {filters.services && filters.services.length > 0 && (
          <Badge variant="secondary" className="flex items-center gap-1">
            {filters.services.length} service(s)
            <X
              className="h-3 w-3 cursor-pointer hover:text-red-500"
              onClick={() => onChange({ ...filters, services: [] })}
            />
          </Badge>
        )}

        {/* Accounts */}
        {filters.accounts && filters.accounts.length > 0 && (
          <Badge variant="secondary" className="flex items-center gap-1">
            {filters.accounts.length} account(s)
            <X
              className="h-3 w-3 cursor-pointer hover:text-red-500"
              onClick={() => onChange({ ...filters, accounts: [] })}
            />
          </Badge>
        )}

        {/* Regions */}
        {filters.regions && filters.regions.length > 0 && (
          <Badge variant="secondary" className="flex items-center gap-1">
            {filters.regions.length} region(s)
            <X
              className="h-3 w-3 cursor-pointer hover:text-red-500"
              onClick={() => onChange({ ...filters, regions: [] })}
            />
          </Badge>
        )}

        {/* Tags */}
        {Object.entries(filters.tags || {}).map(([key, values]) => (
          values.map((value) => (
            <Badge key={`${key}:${value}`} variant="secondary" className="flex items-center gap-1">
              {key}: {value}
              <X
                className="h-3 w-3 cursor-pointer hover:text-red-500"
                onClick={() => removeTagFilter(key, value)}
              />
            </Badge>
          ))
        ))}

        {loading && (
          <Badge variant="outline" className="animate-pulse">
            Loading...
          </Badge>
        )}
      </div>
    </div>
  );
}
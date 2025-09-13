'use client';

import React, { useState } from 'react';
import { CostsOverview } from '@/components/admin/costs/CostsOverview';
import { AdvancedFilters } from '@/components/admin/costs/AdvancedFilters';
import { FilterPresets } from '@/components/admin/costs/FilterPresets';
import { ServiceDetailDrawer } from '@/components/admin/costs/ServiceDetailDrawer';
import { ForecastCard } from '@/components/admin/costs/ForecastCard';
import { BudgetBanner } from '@/components/admin/costs/BudgetBanner';
import { DataSourceToggle, type DataSource } from '@/components/admin/costs/DataSourceToggle';
import { useCostData } from '@/hooks/useCostData';
import { useFilterPersistence } from '@/hooks/useFilterPersistence';
import { CostFilters } from '@/lib/costs/types';
import { toast } from 'sonner';

export default function CostsPage() {
  // Initialize data source (default to Cost Explorer)
  const [dataSource, setDataSource] = useState<DataSource>('ce');
  
  // Initialize filters
  const [filters, setFilters] = useState<CostFilters>({
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

  // Service detail drawer state
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // URL persistence for filters
  const { resetFilters, getShareableURL } = useFilterPersistence(filters, setFilters);

  // Fetch cost data based on current filters
  const { 
    timeseries, 
    summary, 
    services: availableServices,
    loading, 
    error, 
    refresh,
    lastUpdated 
  } = useCostData(filters, { 
    autoRefresh: false, // Disable auto-refresh for now
    dataSource
  });

  // Example budget configuration (in real app, this would come from environment or API)
  const budgets = [
    {
      name: 'Monthly AWS Budget',
      amount: 5000,
      unit: 'USD',
      threshold: 80,
      link: 'https://console.aws.amazon.com/billing/home#/budgets',
    },
    {
      name: 'Quarterly Budget',
      amount: 15000,
      unit: 'USD',
      threshold: 75,
      link: 'https://console.aws.amazon.com/billing/home#/budgets',
    }
  ];

  // Handle service click for drill-down
  const handleServiceClick = (serviceCode: string) => {
    setSelectedService(serviceCode);
    setDrawerOpen(true);
  };

  // Handle sharing
  const handleShare = async (url: string) => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'AWS Cost Analysis',
          text: 'Check out this cost analysis',
          url: url,
        });
      } else {
        await navigator.clipboard.writeText(url);
        toast.success('URL copied to clipboard');
      }
    } catch (error) {
      console.error('Error sharing:', error);
      toast.error('Failed to share URL');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cost Management</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor and analyze AWS costs with month-over-month insights
          </p>
          {lastUpdated && (
            <p className="mt-1 text-xs text-gray-500">
              Last updated: {lastUpdated.toLocaleString()}
            </p>
          )}
        </div>
        <div className="mt-4 sm:mt-0">
          <DataSourceToggle
            dataSource={dataSource}
            onChange={setDataSource}
            disabled={loading}
          />
        </div>
      </div>

      {/* Budget Banner */}
      <BudgetBanner 
        currentCosts={timeseries}
        budgets={budgets}
        loading={loading}
      />

      {/* Filter Presets */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Cost Analysis</h2>
        <FilterPresets
          currentFilters={filters}
          onApplyPreset={setFilters}
          onShare={() => handleShare(getShareableURL())}
        />
      </div>

      {/* Advanced Filters */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <AdvancedFilters 
            filters={filters}
            onChange={setFilters}
            availableServices={availableServices}
            availableAccounts={[]} // TODO: Fetch from API
            availableRegions={['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']} // TODO: Fetch from API
            availableTagKeys={['application', 'environment', 'component', 'cost_center', 'service', 'managed_by']}
            loading={loading}
            onRefresh={refresh}
          />
        </div>
      </div>

      {/* Forecast Card */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <ForecastCard filters={filters} />
        </div>
        <div className="lg:col-span-3">
          {/* Main overview content */}
          <CostsOverview 
            timeseries={timeseries}
            summary={summary}
            loading={loading}
            error={error}
            filters={filters}
            onServiceClick={handleServiceClick}
          />
        </div>
      </div>

      {/* Service Detail Drawer */}
      <ServiceDetailDrawer
        service={selectedService}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        filters={filters}
        dataSource={dataSource}
      />
    </div>
  );
}
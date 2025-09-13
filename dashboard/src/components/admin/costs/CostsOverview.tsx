'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CostKPIs } from './CostKPIs';
import { CostTrendChart } from './CostTrendChart';
import { ServiceCostChart } from './ServiceCostChart';
import { TopServicesTable } from './TopServicesTable';
import { CostFilters } from '@/lib/costs/types';

interface CostsOverviewProps {
  timeseries: any[];
  summary: any[];
  loading: boolean;
  error: string | null;
  filters: CostFilters;
  onServiceClick?: (serviceCode: string) => void;
}

export function CostsOverview({
  timeseries,
  summary,
  loading,
  error,
  filters,
  onServiceClick,
}: CostsOverviewProps) {
  if (error) {
    return (
      <div className="space-y-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="text-center">
              <h3 className="text-lg font-medium text-red-800 mb-2">
                Error Loading Cost Data
              </h3>
              <p className="text-red-600 mb-4">{error}</p>
              <div className="text-sm text-red-700 bg-red-100 p-3 rounded">
                <p className="font-medium mb-1">Common issues:</p>
                <ul className="text-left space-y-1">
                  <li>
                    • AWS Cost Explorer API is not available in LocalStack
                  </li>
                  <li>• Check AWS credentials and permissions</li>
                  <li>• Ensure cost allocation tags are activated</li>
                  <li>• Verify IAM permissions include ce:GetCostAndUsage</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Strip */}
      <CostKPIs data={timeseries} loading={loading} />

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Line Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Monthly Cost Trend</span>
              <span className="text-sm font-normal text-gray-500">
                {filters.metric === 'UnblendedCost' ? 'Unblended' : 'Amortized'}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CostTrendChart
              data={timeseries}
              metric={filters.metric}
              loading={loading}
            />
          </CardContent>
        </Card>

        {/* Stacked Area Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Cost by Service</CardTitle>
          </CardHeader>
          <CardContent>
            <ServiceCostChart data={summary} loading={loading} topN={8} />
          </CardContent>
        </Card>
      </div>

      {/* Top Services Table */}
      <TopServicesTable
        data={summary}
        loading={loading}
        topN={10}
        onServiceClick={onServiceClick}
      />
    </div>
  );
}

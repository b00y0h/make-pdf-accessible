'use client';

import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Download, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { CostPoint, ServiceCostData } from '@/lib/costs/types';
import { TopNProcessor } from '@/lib/topn';
import { MoMCalculator } from '@/lib/mom';

interface TopServicesTableProps {
  data: CostPoint[];
  loading?: boolean;
  topN?: number;
  onServiceClick?: (serviceCode: string) => void;
}

export function TopServicesTable({
  data,
  loading = false,
  topN = 10,
  onServiceClick,
}: TopServicesTableProps) {
  // Process data for table
  const tableData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // For demo purposes, simulate service breakdown
    // In real implementation, this would come from grouped API data
    const services = [
      'EC2-Instance',
      'S3',
      'Lambda',
      'RDS',
      'CloudWatch',
      'API Gateway',
      'ELB',
      'Route53',
      'CloudFront',
      'EBS',
      'ElastiCache',
      'SNS',
      'SQS',
      'DynamoDB',
      'Redshift',
    ];

    // Get latest and previous month data
    const sortedData = [...data].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const latestMonth = sortedData[sortedData.length - 1];
    const previousMonth = sortedData[sortedData.length - 2];

    if (!latestMonth) return [];

    const totalCurrent = latestMonth.amount;
    const totalPrevious = previousMonth?.amount || 0;

    // Simulate service breakdown with different percentages and MoM changes
    const serviceData: ServiceCostData[] = services.map((service, index) => {
      // Simulate different cost distributions
      const basePercentage =
        index === 0
          ? 0.35
          : index === 1
            ? 0.18
            : index === 2
              ? 0.12
              : index === 3
                ? 0.08
                : index === 4
                  ? 0.05
                  : 0.02;

      const currentCost = totalCurrent * basePercentage;
      const previousCost =
        totalPrevious * basePercentage * (0.8 + Math.random() * 0.4); // Simulate variance

      const mom = MoMCalculator.calculate(currentCost, previousCost);

      return {
        service,
        cost: currentCost,
        percentage: (currentCost / totalCurrent) * 100,
        change: mom.change,
        changePercent: mom.changePercent,
        unit: latestMonth.unit || 'USD',
      };
    });

    // Apply Top N processing
    const topServices = TopNProcessor.processServiceCosts(
      serviceData.map((s) => ({
        keys: [s.service],
        metrics: { UnblendedCost: { amount: s.cost.toString(), unit: s.unit } },
        attributes: {},
      })),
      'UnblendedCost',
      topN
    );

    return topServices.items.concat(
      topServices.other ? [topServices.other] : []
    );
  }, [data, topN]);

  // Export to CSV
  const exportToCSV = () => {
    if (tableData.length === 0) return;

    const headers = ['Service', 'Cost', '% of Total', 'MoM Change', 'MoM %'];
    const csvContent = [
      headers.join(','),
      ...tableData.map((row) =>
        [
          row.service,
          row.cost.toFixed(2),
          row.percentage.toFixed(1),
          row.change.toFixed(2),
          row.changePercent.toFixed(1),
        ].join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute(
      'download',
      `top-services-${new Date().toISOString().split('T')[0]}.csv`
    );
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Format currency
  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Get trend icon and color
  const getTrendIcon = (changePercent: number) => {
    if (Math.abs(changePercent) < 0.01) {
      return <Minus className="h-4 w-4 text-gray-500" />;
    }
    return changePercent > 0 ? (
      <TrendingUp className="h-4 w-4 text-red-600" />
    ) : (
      <TrendingDown className="h-4 w-4 text-green-600" />
    );
  };

  if (loading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Top Services This Month</CardTitle>
          <Skeleton className="h-9 w-24" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <div className="flex items-center space-x-4">
                  <Skeleton className="h-4 w-12" />
                  <Skeleton className="h-4 w-16" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Top Services This Month</CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={exportToCSV}
          disabled={tableData.length === 0}
          className="flex items-center gap-2"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </CardHeader>
      <CardContent>
        {tableData.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">No service data available</p>
            <p className="text-sm text-gray-400 mt-1">
              Service breakdown will appear when data is available
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 font-medium text-gray-700">
                    Service
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-gray-700">
                    Cost
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-gray-700">
                    % of Total
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-gray-700">
                    MoM Δ
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-gray-700">
                    MoM %
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-gray-700">
                    Trend
                  </th>
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, index) => (
                  <tr
                    key={row.service}
                    className={`border-b border-gray-100 hover:bg-gray-50 ${
                      onServiceClick && row.service !== 'Other Services'
                        ? 'cursor-pointer'
                        : ''
                    } ${
                      row.service === 'Other Services'
                        ? 'bg-gray-50 font-medium'
                        : ''
                    }`}
                    onClick={() => {
                      if (onServiceClick && row.service !== 'Other Services') {
                        onServiceClick(row.service);
                      }
                    }}
                  >
                    <td className="py-3 px-3">
                      <div className="flex items-center">
                        <span
                          className={
                            row.service === 'Other Services'
                              ? 'text-gray-600'
                              : ''
                          }
                        >
                          {row.service}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      {formatCurrency(row.cost, row.unit)}
                    </td>
                    <td className="py-3 px-3 text-right">
                      {row.percentage.toFixed(1)}%
                    </td>
                    <td
                      className={`py-3 px-3 text-right font-mono ${
                        row.change > 0
                          ? 'text-red-600'
                          : row.change < 0
                            ? 'text-green-600'
                            : 'text-gray-500'
                      }`}
                    >
                      {row.change >= 0 ? '+' : ''}
                      {formatCurrency(row.change, row.unit)}
                    </td>
                    <td
                      className={`py-3 px-3 text-right ${
                        row.changePercent > 0
                          ? 'text-red-600'
                          : row.changePercent < 0
                            ? 'text-green-600'
                            : 'text-gray-500'
                      }`}
                    >
                      {row.changePercent >= 0 ? '+' : ''}
                      {row.changePercent.toFixed(1)}%
                    </td>
                    <td className="py-3 px-3 text-center">
                      {getTrendIcon(row.changePercent)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tableData.length > 0 && (
          <div className="mt-4 pt-4 border-t text-sm text-gray-500">
            <p>
              Showing top {Math.min(topN, tableData.length)} services by current
              month cost.
              {tableData.find((row) => row.service.includes('Other')) &&
                ' "Other Services" represents the sum of remaining services.'}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

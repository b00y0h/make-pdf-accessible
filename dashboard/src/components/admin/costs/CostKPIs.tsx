'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { CostPoint } from '@/lib/costs/types';
import { MoMCalculator } from '@/lib/mom';

interface CostKPIsProps {
  data: CostPoint[];
  loading?: boolean;
}

export function CostKPIs({ data, loading = false }: CostKPIsProps) {
  // Calculate KPIs from data
  const kpis = React.useMemo(() => {
    if (!data || data.length < 2) {
      return {
        current: 0,
        mom: null,
        unit: 'USD',
      };
    }

    // Sort data by date
    const sortedData = [...data].sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const current = sortedData[sortedData.length - 1]?.amount || 0;
    const unit = sortedData[sortedData.length - 1]?.unit || 'USD';
    const mom = MoMCalculator.fromSeries(sortedData);

    return { current, mom, unit };
  }, [data]);

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
  const getTrendDisplay = (mom: any) => {
    if (!mom) return { icon: Minus, color: 'text-gray-500', bgColor: 'bg-gray-100' };
    
    switch (mom.direction) {
      case 'increase':
        return { icon: TrendingUp, color: 'text-red-600', bgColor: 'bg-red-100' };
      case 'decrease':
        return { icon: TrendingDown, color: 'text-green-600', bgColor: 'bg-green-100' };
      default:
        return { icon: Minus, color: 'text-gray-500', bgColor: 'bg-gray-100' };
    }
  };

  const trendDisplay = getTrendDisplay(kpis.mom);
  const TrendIcon = trendDisplay.icon;

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                <Skeleton className="h-4 w-32" />
              </CardTitle>
              <Skeleton className="h-4 w-4 rounded" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                <Skeleton className="h-8 w-24" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                <Skeleton className="h-4 w-20" />
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {/* Current Month Total */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total This Month</CardTitle>
          <div className={`rounded-full p-1 ${trendDisplay.bgColor}`}>
            <TrendIcon className={`h-4 w-4 ${trendDisplay.color}`} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatCurrency(kpis.current, kpis.unit)}
          </div>
          <p className="text-xs text-muted-foreground">
            Current month spend
          </p>
        </CardContent>
      </Card>

      {/* Month-over-Month Change */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Month-over-Month</CardTitle>
          <div className={`rounded-full p-1 ${trendDisplay.bgColor}`}>
            <TrendIcon className={`h-4 w-4 ${trendDisplay.color}`} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {kpis.mom ? (
              <span className={trendDisplay.color}>
                {kpis.mom.change >= 0 ? '+' : ''}
                {formatCurrency(Math.abs(kpis.mom.change), kpis.unit)}
              </span>
            ) : (
              <span className="text-gray-500">--</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {kpis.mom ? 'vs previous month' : 'Insufficient data'}
          </p>
        </CardContent>
      </Card>

      {/* Month-over-Month Percentage */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">MoM Percentage</CardTitle>
          <div className={`rounded-full p-1 ${trendDisplay.bgColor}`}>
            <TrendIcon className={`h-4 w-4 ${trendDisplay.color}`} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {kpis.mom ? (
              <span className={trendDisplay.color}>
                {kpis.mom.changePercent >= 0 ? '+' : ''}
                {Math.abs(kpis.mom.changePercent).toFixed(1)}%
              </span>
            ) : (
              <span className="text-gray-500">--</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {kpis.mom ? 
              `${kpis.mom.direction} from last month` : 
              'Insufficient data'
            }
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
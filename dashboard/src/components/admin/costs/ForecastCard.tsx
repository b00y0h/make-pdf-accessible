'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, AlertTriangle, Info } from 'lucide-react';
import { useForecastData } from '@/hooks/useCostData';
import { CostFilters } from '@/lib/costs/types';

interface ForecastCardProps {
  filters: Pick<CostFilters, 'metric'>;
}

export function ForecastCard({ filters }: ForecastCardProps) {
  const { data: forecastData, loading, error } = useForecastData(filters);

  // Get next month's forecast (first item in forecast results)
  const nextMonthForecast = forecastData && forecastData.length > 0 ? forecastData[0] : null;

  // Format currency
  const formatCurrency = (amount: string, currency: string = 'USD') => {
    const value = parseFloat(amount);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Calculate prediction band width
  const getPredictionBandWidth = () => {
    if (!nextMonthForecast) return null;
    
    const mean = parseFloat(nextMonthForecast.meanValue);
    const lower = parseFloat(nextMonthForecast.predictionIntervalLowerBound);
    const upper = parseFloat(nextMonthForecast.predictionIntervalUpperBound);
    
    const lowerDiff = mean - lower;
    const upperDiff = upper - mean;
    const avgBand = (lowerDiff + upperDiff) / 2;
    const bandPercentage = mean > 0 ? (avgBand / mean) * 100 : 0;
    
    return {
      lower: formatCurrency(lower.toString()),
      upper: formatCurrency(upper.toString()),
      percentage: bandPercentage.toFixed(1),
    };
  };

  const predictionBand = getPredictionBandWidth();

  if (loading) {
    return (
      <Card>
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
          <div className="mt-3 p-2 bg-gray-50 rounded">
            <Skeleton className="h-3 w-full mb-1" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-yellow-800">
            Cost Forecast
          </CardTitle>
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
        </CardHeader>
        <CardContent>
          <div className="text-sm text-yellow-700">
            <p className="font-medium">Forecast unavailable</p>
            <p className="text-xs mt-1">
              {error.includes('LocalStack') || error.includes('not yet implemented') 
                ? 'Cost forecasting requires AWS Cost Explorer Pro'
                : error
              }
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!nextMonthForecast) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Cost Forecast</CardTitle>
          <Info className="h-4 w-4 text-gray-500" />
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-sm text-gray-500">No forecast data available</p>
            <p className="text-xs text-gray-400 mt-1">
              Forecast data will appear when available
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Format the time period for display
  const formatTimePeriod = (timePeriod: any) => {
    if (!timePeriod || !timePeriod.start) return 'Next month';
    
    try {
      const startDate = new Date(timePeriod.start);
      return startDate.toLocaleDateString('en-US', { 
        month: 'long', 
        year: 'numeric' 
      });
    } catch {
      return 'Next month';
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Cost Forecast</CardTitle>
        <TrendingUp className="h-4 w-4 text-blue-600" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-blue-600">
          {formatCurrency(nextMonthForecast.meanValue)}
        </div>
        <p className="text-xs text-muted-foreground">
          {formatTimePeriod(nextMonthForecast.timePeriod)} estimate
        </p>
        
        {predictionBand && (
          <div className="mt-3 p-2 bg-blue-50 rounded border border-blue-100">
            <div className="text-xs font-medium text-blue-800 mb-1">
              Prediction Range (80% confidence)
            </div>
            <div className="text-xs text-blue-700">
              <div className="flex justify-between">
                <span>Lower bound:</span>
                <span className="font-medium">{predictionBand.lower}</span>
              </div>
              <div className="flex justify-between">
                <span>Upper bound:</span>
                <span className="font-medium">{predictionBand.upper}</span>
              </div>
              <div className="text-xs text-blue-600 mt-1">
                ±{predictionBand.percentage}% variance
              </div>
            </div>
          </div>
        )}
        
        <div className="mt-2 text-xs text-gray-500">
          Based on historical usage patterns
        </div>
      </CardContent>
    </Card>
  );
}
'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { CostPoint } from '@/lib/costs/types';

interface CostTrendChartProps {
  data: CostPoint[];
  metric: 'UnblendedCost' | 'AmortizedCost';
  loading?: boolean;
}

interface ChartDataPoint {
  date: string;
  displayDate: string;
  cost: number;
  estimated: boolean;
}

export function CostTrendChart({
  data,
  metric,
  loading = false,
}: CostTrendChartProps) {
  // Transform data for chart
  const chartData: ChartDataPoint[] = data.map((point) => ({
    date: point.date,
    displayDate: format(parseISO(point.date), 'MMM yyyy'),
    cost: point.amount,
    estimated: point.estimated || false,
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border rounded shadow-lg">
          <p className="font-medium">{label}</p>
          <p className="text-blue-600">
            Cost: ${data.cost.toFixed(2)} {payload[0].payload.unit || 'USD'}
          </p>
          {data.estimated && (
            <p className="text-orange-500 text-sm">Estimated</p>
          )}
        </div>
      );
    }
    return null;
  };

  // Format Y-axis values
  const formatYAxis = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}K`;
    }
    return `$${value.toFixed(0)}`;
  };

  if (loading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">No cost data available</p>
          <p className="text-sm text-gray-400 mt-1">
            Check your AWS Cost Explorer configuration
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis
            dataKey="displayDate"
            tick={{ fontSize: 12 }}
            tickLine={{ stroke: '#e5e7eb' }}
          />
          <YAxis
            tickFormatter={formatYAxis}
            tick={{ fontSize: 12 }}
            tickLine={{ stroke: '#e5e7eb' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line
            type="monotone"
            dataKey="cost"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
            name={`${metric} Cost`}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

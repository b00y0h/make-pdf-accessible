'use client';

import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { CostPoint } from '@/lib/costs/types';
import { TopNProcessor } from '@/lib/topn';

interface ServiceCostChartProps {
  data: CostPoint[];
  loading?: boolean;
  topN?: number;
}

// Color palette for services
const SERVICE_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6b7280'
];

export function ServiceCostChart({ data, loading = false, topN = 8 }: ServiceCostChartProps) {
  // Transform and process data
  const chartData = useMemo((): { chartPoints: any[]; displayServices: string[] } => {
    if (!data || data.length === 0) return { chartPoints: [], displayServices: [] };

    // Group data by date and service
    const dateServiceMap = new Map<string, Map<string, number>>();
    
    data.forEach(point => {
      if (!dateServiceMap.has(point.date)) {
        dateServiceMap.set(point.date, new Map());
      }
      // For this example, we'll simulate service breakdown
      // In real implementation, this would come from grouped API data
      const serviceMap = dateServiceMap.get(point.date)!;
      
      // Simulate service breakdown (this should come from actual grouped data)
      const services = ['EC2-Instance', 'S3', 'Lambda', 'RDS', 'CloudWatch', 'API Gateway', 'ELB', 'Route53', 'Other'];
      const totalCost = point.amount;
      
      // Distribute cost across services (simulate real data)
      services.forEach((service, index) => {
        const percentage = index === 0 ? 0.4 : index === 1 ? 0.2 : index === 2 ? 0.15 : 
                          index === 3 ? 0.1 : index === 4 ? 0.05 : 
                          index === services.length - 1 ? 0.05 : 0.01;
        serviceMap.set(service, totalCost * percentage);
      });
    });

    // Convert to chart format
    const chartPoints: any[] = [];
    const allServices = new Set<string>();
    
    dateServiceMap.forEach((serviceMap, date) => {
      const point: any = {
        date,
        displayDate: format(parseISO(date), 'MMM yyyy'),
      };
      
      serviceMap.forEach((cost, service) => {
        point[service] = cost;
        allServices.add(service);
      });
      
      chartPoints.push(point);
    });

    // Sort by date
    chartPoints.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    // Apply Top N processing to determine which services to show
    const serviceList = Array.from(allServices);
    const latestPoint = chartPoints[chartPoints.length - 1];
    
    if (latestPoint) {
      const serviceData = serviceList.map(service => ({
        service,
        cost: latestPoint[service] || 0,
      }));

      const topServices = TopNProcessor.processServiceCosts(
        serviceData.map(s => ({
          keys: [s.service],
          metrics: { UnblendedCost: { amount: s.cost.toString(), unit: 'USD' } },
          attributes: {},
        })),
        'UnblendedCost',
        topN
      );

      // Get the services to display
      const displayServices = topServices.items.map(item => item.service);
      if (topServices.other) {
        displayServices.push('Other');
        
        // Aggregate "Other" services
        chartPoints.forEach(point => {
          let otherTotal = 0;
          serviceList.forEach(service => {
            if (!topServices.items.find(item => item.service === service)) {
              otherTotal += point[service] || 0;
              delete point[service];
            }
          });
          point['Other'] = otherTotal;
        });
      }

      return { chartPoints, displayServices };
    }

    return { chartPoints, displayServices: serviceList.slice(0, topN) };
  }, [data, topN]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const total = payload.reduce((sum: number, entry: any) => sum + entry.value, 0);
      
      return (
        <div className="bg-white p-3 border rounded shadow-lg max-w-xs">
          <p className="font-medium mb-2">{label}</p>
          <div className="space-y-1">
            {payload
              .sort((a: any, b: any) => b.value - a.value)
              .map((entry: any, index: number) => (
                <div key={index} className="flex justify-between items-center">
                  <div className="flex items-center">
                    <div 
                      className="w-3 h-3 rounded mr-2" 
                      style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-sm">{entry.dataKey}:</span>
                  </div>
                  <span className="text-sm font-medium ml-2">
                    ${entry.value.toFixed(2)}
                  </span>
                </div>
              ))}
          </div>
          <div className="border-t pt-2 mt-2">
            <div className="flex justify-between font-medium">
              <span>Total:</span>
              <span>${total.toFixed(2)}</span>
            </div>
          </div>
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

  if (!chartData.chartPoints || chartData.chartPoints.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">No service cost data available</p>
          <p className="text-sm text-gray-400 mt-1">
            Service breakdown will appear when data is available
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart 
          data={chartData.chartPoints} 
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
          {chartData.displayServices.map((service, index) => (
            <Area
              key={service}
              type="monotone"
              dataKey={service}
              stackId="1"
              stroke={SERVICE_COLORS[index % SERVICE_COLORS.length]}
              fill={SERVICE_COLORS[index % SERVICE_COLORS.length]}
              fillOpacity={0.6}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
'use client';

import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Loader2, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';
import { CostFilters } from '@/lib/costs/types';
import { formatCurrency } from '@/lib/utils';

interface ServiceDetailDrawerProps {
  service: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filters: CostFilters;
  dataSource: 'ce' | 'athena';
}

interface ServiceDetailData {
  timeseries: Array<{
    month: string;
    amount: number;
    currency: string;
  }>;
  tagBreakdown: Array<{
    tagKey: string;
    tagValue: string;
    amount: number;
    percentage: number;
  }>;
  regionBreakdown: Array<{
    region: string;
    amount: number;
    percentage: number;
  }>;
  accountBreakdown: Array<{
    accountId: string;
    amount: number;
    percentage: number;
  }>;
  total: number;
  trend: {
    direction: 'up' | 'down' | 'stable';
    percentage: number;
  };
}

export function ServiceDetailDrawer({
  service,
  open,
  onOpenChange,
  filters,
  dataSource,
}: ServiceDetailDrawerProps) {
  const [data, setData] = useState<ServiceDetailData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch service detail data
  useEffect(() => {
    if (!service || !open) {
      setData(null);
      return;
    }

    const fetchServiceDetails = async () => {
      setLoading(true);
      setError(null);

      try {
        // Build query params
        const params = new URLSearchParams();
        params.set('service', service);
        params.set('metric', filters.metric);
        params.set('granularity', filters.granularity);
        
        if (filters.dateRange.preset !== 'custom') {
          params.set('preset', filters.dateRange.preset);
        } else if (filters.dateRange.custom) {
          params.set('start', filters.dateRange.custom.start);
          params.set('end', filters.dateRange.custom.end);
        }

        if (filters.accounts && filters.accounts.length > 0) {
          params.set('accounts', filters.accounts.join(','));
        }

        if (filters.regions && filters.regions.length > 0) {
          params.set('regions', filters.regions.join(','));
        }

        if (filters.tags && Object.keys(filters.tags).length > 0) {
          params.set('tags', JSON.stringify(filters.tags));
        }

        // Fetch data from the appropriate endpoint
        const basePath = dataSource === 'athena' ? '/api/costs/athena' : '/api/costs';
        
        // Fetch timeseries for the specific service
        const timeseriesResponse = await fetch(`${basePath}/timeseries?${params}`);
        
        if (!timeseriesResponse.ok) {
          throw new Error('Failed to fetch service timeseries');
        }

        const timeseriesData = await timeseriesResponse.json();

        // Fetch tag breakdown
        const tagResponse = await fetch(`${basePath}/by-tag?${params}`);
        let tagData = { dataPoints: [] };
        
        if (tagResponse.ok) {
          tagData = await tagResponse.json();
        }

        // Mock region and account breakdowns (would need separate API endpoints)
        const mockRegionData = [
          { region: 'us-east-1', amount: 1234.56, percentage: 45.2 },
          { region: 'us-west-2', amount: 876.32, percentage: 32.1 },
          { region: 'eu-west-1', amount: 543.21, percentage: 19.9 },
          { region: 'ap-southeast-1', amount: 76.89, percentage: 2.8 },
        ];

        const mockAccountData = [
          { accountId: '123456789012', amount: 1534.32, percentage: 56.2 },
          { accountId: '234567890123', amount: 987.65, percentage: 36.2 },
          { accountId: '345678901234', amount: 209.01, percentage: 7.6 },
        ];

        // Process timeseries data
        let processedTimeseries: any[] = [];
        let total = 0;

        if (dataSource === 'ce' && timeseriesData.ok) {
          processedTimeseries = timeseriesData.data?.series || [];
          total = processedTimeseries.reduce((sum, point) => sum + (point.amount || 0), 0);
        } else if (dataSource === 'athena') {
          processedTimeseries = (timeseriesData.dataPoints || []).map((point: any) => ({
            month: point.month,
            amount: point.amount,
            currency: point.currency || 'USD',
          }));
          total = processedTimeseries.reduce((sum, point) => sum + point.amount, 0);
        }

        // Calculate trend (comparing last two periods)
        let trend = { direction: 'stable' as const, percentage: 0 };
        if (processedTimeseries.length >= 2) {
          const current = processedTimeseries[processedTimeseries.length - 1]?.amount || 0;
          const previous = processedTimeseries[processedTimeseries.length - 2]?.amount || 0;
          
          if (previous > 0) {
            const change = ((current - previous) / previous) * 100;
            trend = {
              direction: change > 5 ? 'up' : change < -5 ? 'down' : 'stable',
              percentage: Math.abs(change),
            };
          }
        }

        // Process tag data
        let processedTags: any[] = [];
        if (dataSource === 'athena' && tagData.dataPoints) {
          const tagMap = new Map<string, number>();
          
          tagData.dataPoints.forEach((point: any) => {
            Object.entries(point.tags || {}).forEach(([key, value]) => {
              const tagKey = `${key}:${value}`;
              tagMap.set(tagKey, (tagMap.get(tagKey) || 0) + point.amount);
            });
          });

          const totalTagAmount = Array.from(tagMap.values()).reduce((sum, amount) => sum + amount, 0);
          
          processedTags = Array.from(tagMap.entries())
            .map(([tagKey, amount]) => {
              const [key, value] = tagKey.split(':');
              return {
                tagKey: key,
                tagValue: value,
                amount,
                percentage: totalTagAmount > 0 ? (amount / totalTagAmount) * 100 : 0,
              };
            })
            .sort((a, b) => b.amount - a.amount)
            .slice(0, 10); // Top 10
        }

        setData({
          timeseries: processedTimeseries,
          tagBreakdown: processedTags,
          regionBreakdown: mockRegionData,
          accountBreakdown: mockAccountData,
          total,
          trend,
        });

      } catch (err) {
        console.error('Error fetching service details:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch service details');
      } finally {
        setLoading(false);
      }
    };

    fetchServiceDetails();
  }, [service, open, filters, dataSource]);

  if (!service) return null;

  const formatServiceName = (serviceCode: string) => {
    const serviceNames: Record<string, string> = {
      'AmazonEC2': 'Amazon EC2',
      'AmazonS3': 'Amazon S3',
      'AmazonRDS': 'Amazon RDS',
      'AWSLambda': 'AWS Lambda',
      'AmazonCloudFront': 'Amazon CloudFront',
      'AmazonRoute53': 'Amazon Route 53',
    };
    return serviceNames[serviceCode] || serviceCode;
  };

  const TrendIcon = ({ direction }: { direction: 'up' | 'down' | 'stable' }) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-red-500" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-green-500" />;
      default:
        return <Minus className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[600px] sm:w-[800px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between">
            <span>{formatServiceName(service)} Cost Analysis</span>
            <Button variant="outline" size="sm" asChild>
              <a
                href={`https://console.aws.amazon.com/cost-management/home#/cost-explorer`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2"
              >
                <ExternalLink className="h-4 w-4" />
                AWS Console
              </a>
            </Button>
          </SheetTitle>
        </SheetHeader>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2">Loading service details...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {data && !loading && (
          <div className="space-y-6 mt-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Cost</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {formatCurrency(data.total)}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {filters.dateRange.preset === 'custom' ? 'Custom Period' : 
                     filters.dateRange.preset === '3months' ? 'Last 3M' :
                     filters.dateRange.preset === '6months' ? 'Last 6M' :
                     'Last 12M'}
                  </Badge>
                </div>
              </div>

              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Trend</p>
                    <div className="flex items-center gap-2">
                      <TrendIcon direction={data.trend.direction} />
                      <span className="text-2xl font-bold text-gray-900">
                        {data.trend.percentage.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <Badge 
                    variant={data.trend.direction === 'up' ? 'destructive' : 
                            data.trend.direction === 'down' ? 'default' : 'secondary'}
                    className="text-xs"
                  >
                    {data.trend.direction === 'up' ? 'Increasing' :
                     data.trend.direction === 'down' ? 'Decreasing' : 'Stable'}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Detailed Analysis Tabs */}
            <Tabs defaultValue="trend" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="trend">Cost Trend</TabsTrigger>
                <TabsTrigger value="tags">Top Tags</TabsTrigger>
                <TabsTrigger value="regions">Regions</TabsTrigger>
                <TabsTrigger value="accounts">Accounts</TabsTrigger>
              </TabsList>

              <TabsContent value="trend" className="space-y-4">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.timeseries}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="month" 
                        tick={{ fontSize: 12 }}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => `$${value.toLocaleString()}`}
                      />
                      <Tooltip 
                        formatter={(value: any) => [formatCurrency(value), 'Cost']}
                        labelFormatter={(label) => `Month: ${label}`}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="amount" 
                        stroke="#3b82f6" 
                        strokeWidth={3}
                        dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </TabsContent>

              <TabsContent value="tags" className="space-y-4">
                {data.tagBreakdown.length > 0 ? (
                  <div className="space-y-3">
                    {data.tagBreakdown.map((tag, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-xs">
                            {tag.tagKey}
                          </Badge>
                          <span className="font-medium">{tag.tagValue}</span>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{formatCurrency(tag.amount)}</p>
                          <p className="text-xs text-gray-600">{tag.percentage.toFixed(1)}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No tag data available for this service
                  </div>
                )}
              </TabsContent>

              <TabsContent value="regions" className="space-y-4">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.regionBreakdown}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="region" tick={{ fontSize: 12 }} />
                      <YAxis 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => `$${value.toLocaleString()}`}
                      />
                      <Tooltip 
                        formatter={(value: any) => [formatCurrency(value), 'Cost']}
                      />
                      <Bar dataKey="amount" fill="#10b981" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </TabsContent>

              <TabsContent value="accounts" className="space-y-4">
                <div className="space-y-3">
                  {data.accountBreakdown.map((account, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="text-xs font-mono">
                          {account.accountId}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">{formatCurrency(account.amount)}</p>
                        <p className="text-xs text-gray-600">{account.percentage.toFixed(1)}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
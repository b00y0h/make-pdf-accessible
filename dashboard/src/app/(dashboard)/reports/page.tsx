'use client';

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
  BarChart3,
  TrendingUp,
  Download,
  Calendar,
  Users,
  FileText,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  Activity,
  Filter,
  CalendarDays,
} from 'lucide-react';
import { useReportsSummary, useDocuments, useExportCSV } from '@/hooks/useApi';
import toast from 'react-hot-toast';

function StatSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16 mb-2" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}

function RecentDocumentsSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-64" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-4" />
                <div>
                  <Skeleton className="h-4 w-48 mb-1" />
                  <Skeleton className="h-3 w-32" />
                </div>
              </div>
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'processing':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-blue-500" />;
    default:
      return <FileText className="h-4 w-4 text-gray-500" />;
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'processing':
      return (
        <Badge variant="warning" className="text-xs">
          Processing
        </Badge>
      );
    case 'completed':
      return (
        <Badge variant="success" className="text-xs">
          Completed
        </Badge>
      );
    case 'failed':
      return (
        <Badge variant="error" className="text-xs">
          Failed
        </Badge>
      );
    case 'pending':
      return (
        <Badge variant="secondary" className="text-xs">
          Pending
        </Badge>
      );
    default:
      return <Badge className="text-xs">Unknown</Badge>;
  }
}

export default function ReportsPage() {
  const [exportFilters, setExportFilters] = useState({
    start_date: '',
    end_date: '',
    status_filter: '',
    owner_filter: '',
  });
  const [filtersOpen, setFiltersOpen] = useState(false);

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useReportsSummary();

  const {
    data: recentDocs,
    isLoading: docsLoading,
    error: docsError,
  } = useDocuments({ per_page: 10 });

  const exportMutation = useExportCSV();

  React.useEffect(() => {
    if (summaryError) {
      toast.error('Failed to load reports summary');
    }
    if (docsError) {
      toast.error('Failed to load recent documents');
    }
  }, [summaryError, docsError]);

  const handleExportCSV = async () => {
    try {
      // Filter out empty values
      const filters = Object.fromEntries(
        Object.entries(exportFilters).filter(([_, value]) => value !== '')
      );

      await exportMutation.mutateAsync(filters);
      toast.success('CSV export downloaded successfully');
      setFiltersOpen(false);
    } catch (error) {
      toast.error('Failed to export CSV');
    }
  };

  const handleQuickExport = async () => {
    try {
      await exportMutation.mutateAsync({});
      toast.success('Full CSV export downloaded successfully');
    } catch (error) {
      toast.error('Failed to export CSV');
    }
  };

  const successRate = summary ? Math.round(summary.completion_rate * 100) : 0;
  const avgProcessingTime = summary?.avg_processing_time_hours
    ? `${Math.round(summary.avg_processing_time_hours * 60)} min`
    : 'N/A';

  const statusCounts = React.useMemo(() => {
    if (!recentDocs?.documents) return {};

    return recentDocs.documents.reduce(
      (acc, doc) => {
        acc[doc.status] = (acc[doc.status] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
  }, [recentDocs?.documents]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Reports & Analytics
          </h1>
          <p className="text-muted-foreground">
            Comprehensive insights into your PDF accessibility processing
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchSummary()}
            disabled={summaryLoading}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${summaryLoading ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleQuickExport}
            disabled={exportMutation.isPending}
          >
            <Download className="h-4 w-4 mr-2" />
            {exportMutation.isPending ? 'Exporting...' : 'Quick Export'}
          </Button>
          <Popover open={filtersOpen} onOpenChange={setFiltersOpen}>
            <PopoverTrigger asChild>
              <Button size="sm" variant="default">
                <Filter className="h-4 w-4 mr-2" />
                Filtered Export
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80" align="end">
              <div className="grid gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium leading-none">Export Filters</h4>
                  <p className="text-sm text-muted-foreground">
                    Apply filters to customize your CSV export
                  </p>
                </div>
                <div className="grid gap-3">
                  <div className="grid gap-2">
                    <Label htmlFor="start-date">Start Date</Label>
                    <Input
                      id="start-date"
                      type="date"
                      value={exportFilters.start_date}
                      onChange={(e) =>
                        setExportFilters((prev) => ({
                          ...prev,
                          start_date: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="end-date">End Date</Label>
                    <Input
                      id="end-date"
                      type="date"
                      value={exportFilters.end_date}
                      onChange={(e) =>
                        setExportFilters((prev) => ({
                          ...prev,
                          end_date: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="status-filter">Status</Label>
                    <Select
                      value={exportFilters.status_filter}
                      onValueChange={(value) =>
                        setExportFilters((prev) => ({
                          ...prev,
                          status_filter: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All statuses" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">All statuses</SelectItem>
                        <SelectItem value="completed">Completed</SelectItem>
                        <SelectItem value="processing">Processing</SelectItem>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="failed">Failed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="owner-filter">Owner ID (Optional)</Label>
                    <Input
                      id="owner-filter"
                      placeholder="Filter by specific owner..."
                      value={exportFilters.owner_filter}
                      onChange={(e) =>
                        setExportFilters((prev) => ({
                          ...prev,
                          owner_filter: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    onClick={handleExportCSV}
                    disabled={exportMutation.isPending}
                    className="flex-1"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setExportFilters({
                        start_date: '',
                        end_date: '',
                        status_filter: '',
                        owner_filter: '',
                      })
                    }
                  >
                    Clear
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {summaryLoading ? (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        ) : summary ? (
          <>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Documents
                </CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summary.total_documents.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">
                  All-time processed
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Success Rate
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {successRate}%
                </div>
                <p className="text-xs text-muted-foreground">Completion rate</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Avg. Processing Time
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{avgProcessingTime}</div>
                <p className="text-xs text-muted-foreground">Per document</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Active Processing
                </CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {summary.processing_documents}
                </div>
                <p className="text-xs text-muted-foreground">
                  Currently in queue
                </p>
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="col-span-full flex items-center justify-center h-32 text-muted-foreground">
            <div className="text-center">
              <AlertCircle className="h-8 w-8 mx-auto mb-2" />
              <p>Failed to load statistics</p>
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Status Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Status Breakdown
            </CardTitle>
            <CardDescription>
              Current status distribution of documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-12" />
                  </div>
                ))}
              </div>
            ) : summary ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Completed</span>
                  </div>
                  <span className="font-medium">
                    {summary.completed_documents}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-yellow-500" />
                    <span className="text-sm">Processing</span>
                  </div>
                  <span className="font-medium">
                    {summary.processing_documents}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-blue-500" />
                    <span className="text-sm">Pending</span>
                  </div>
                  <span className="font-medium">
                    {summary.pending_documents}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    <span className="text-sm">Failed</span>
                  </div>
                  <span className="font-medium">
                    {summary.failed_documents}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                <p>No status data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Documents */}
        {docsLoading ? (
          <RecentDocumentsSkeleton />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Recent Activity
              </CardTitle>
              <CardDescription>
                Latest document processing activity
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!recentDocs?.documents || recentDocs.documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent activity</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentDocs.documents.slice(0, 5).map((doc) => (
                    <div
                      key={doc.doc_id}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        {getStatusIcon(doc.status)}
                        <div className="flex-1">
                          <p className="text-sm font-medium truncate max-w-48">
                            {doc.filename}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(doc.updated_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      {getStatusBadge(doc.status)}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Enhanced Export Options */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Options
          </CardTitle>
          <CardDescription>
            Download reports and data with advanced filtering options
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            {/* Quick Export Actions */}
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <Button
                variant="outline"
                onClick={handleQuickExport}
                disabled={exportMutation.isPending}
                className="justify-start"
              >
                <Download className="h-4 w-4 mr-2" />
                {exportMutation.isPending ? 'Exporting...' : 'All Documents'}
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  exportMutation.mutate({ status_filter: 'completed' })
                }
                disabled={exportMutation.isPending}
                className="justify-start"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Completed Only
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  exportMutation.mutate({ status_filter: 'failed' })
                }
                disabled={exportMutation.isPending}
                className="justify-start"
              >
                <AlertCircle className="h-4 w-4 mr-2" />
                Failed Only
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  const thirtyDaysAgo = new Date();
                  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                  exportMutation.mutate({
                    start_date: thirtyDaysAgo.toISOString().split('T')[0],
                  });
                }}
                disabled={exportMutation.isPending}
                className="justify-start"
              >
                <CalendarDays className="h-4 w-4 mr-2" />
                Last 30 Days
              </Button>
            </div>

            {/* Advanced Filtering */}
            <div className="border-t pt-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="font-medium">Custom Filters</h4>
                  <p className="text-sm text-muted-foreground">
                    Use the &quot;Filtered Export&quot; button above for
                    advanced filtering options
                  </p>
                </div>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Filter className="h-4 w-4 mr-2" />
                      Advanced
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80" align="end">
                    <div className="space-y-3">
                      <div>
                        <h4 className="font-medium mb-2">Quick Date Ranges</h4>
                        <div className="grid gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const lastWeek = new Date();
                              lastWeek.setDate(lastWeek.getDate() - 7);
                              exportMutation.mutate({
                                start_date: lastWeek
                                  .toISOString()
                                  .split('T')[0],
                              });
                            }}
                            disabled={exportMutation.isPending}
                            className="justify-start"
                          >
                            Last 7 Days
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const lastMonth = new Date();
                              lastMonth.setMonth(lastMonth.getMonth() - 1);
                              exportMutation.mutate({
                                start_date: lastMonth
                                  .toISOString()
                                  .split('T')[0],
                              });
                            }}
                            disabled={exportMutation.isPending}
                            className="justify-start"
                          >
                            Last Month
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const lastQuarter = new Date();
                              lastQuarter.setMonth(lastQuarter.getMonth() - 3);
                              exportMutation.mutate({
                                start_date: lastQuarter
                                  .toISOString()
                                  .split('T')[0],
                              });
                            }}
                            disabled={exportMutation.isPending}
                            className="justify-start"
                          >
                            Last Quarter
                          </Button>
                        </div>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

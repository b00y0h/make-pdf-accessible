'use client';

import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Users,
  BarChart3,
  ArrowUpRight,
  RefreshCw,
} from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';
import { useReportsSummary, useDocuments } from '@/hooks/useApi';
import { Button } from '@/components/ui/button';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';

function StatsCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
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
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Recent Documents
        </CardTitle>
        <CardDescription>Latest document processing activity</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-4 w-4" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-full max-w-48" />
                <Skeleton className="h-3 w-32" />
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
      return <Badge variant="warning">Processing</Badge>;
    case 'completed':
      return <Badge variant="success">Completed</Badge>;
    case 'failed':
      return <Badge variant="error">Failed</Badge>;
    case 'pending':
      return <Badge variant="secondary">Pending</Badge>;
    default:
      return <Badge>Unknown</Badge>;
  }
}

export default function DashboardPage() {
  const router = useRouter();

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
  } = useDocuments({ per_page: 5 });

  // Show error toasts
  React.useEffect(() => {
    if (summaryError) {
      toast.error('Failed to load dashboard summary');
    }
    if (docsError) {
      toast.error('Failed to load recent documents');
    }
  }, [summaryError, docsError]);

  const successRate = summary ? Math.round(summary.completion_rate * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your PDF accessibility processing
          </p>
        </div>
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
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {summaryLoading ? (
          <>
            <StatsCardSkeleton />
            <StatsCardSkeleton />
            <StatsCardSkeleton />
            <StatsCardSkeleton />
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
                  All-time uploads
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Processing
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summary.processing_documents}
                </div>
                <p className="text-xs text-muted-foreground">
                  Currently in queue
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Success Rate
                </CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{successRate}%</div>
                <p className="text-xs text-muted-foreground">
                  {summary.completed_documents.toLocaleString()} completed,{' '}
                  {summary.failed_documents} failed
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pending</CardTitle>
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summary.pending_documents}
                </div>
                <p className="text-xs text-muted-foreground">
                  Awaiting processing
                </p>
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="col-span-full flex items-center justify-center h-32 text-muted-foreground">
            <div className="text-center">
              <AlertCircle className="h-8 w-8 mx-auto mb-2" />
              <p>Failed to load dashboard data</p>
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Processing Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Processing Documents
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/queue?status=processing')}
              >
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            </CardTitle>
            <CardDescription>
              Documents currently being processed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {docsLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Skeleton className="h-4 w-48" />
                        <Skeleton className="h-3 w-16" />
                      </div>
                      <Skeleton className="h-2 w-full" />
                    </div>
                  ))}
                </div>
              ) : recentDocs?.documents?.filter(
                  (doc) => doc.status === 'processing'
                ).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No documents currently processing</p>
                </div>
              ) : (
                recentDocs?.documents
                  ?.filter((doc) => doc.status === 'processing')
                  ?.slice(0, 3)
                  ?.map((doc) => (
                    <div
                      key={doc.doc_id}
                      className="space-y-2 p-3 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => router.push(`/documents/${doc.doc_id}`)}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium truncate">
                          {doc.filename}
                        </p>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(new Date(doc.updated_at))}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(doc.status)}
                        <span className="text-xs text-muted-foreground capitalize">
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        {docsLoading ? (
          <RecentDocumentsSkeleton />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Documents
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push('/queue')}
                >
                  <ArrowUpRight className="h-4 w-4" />
                </Button>
              </CardTitle>
              <CardDescription>
                Latest document processing activity
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentDocs?.documents?.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No documents uploaded yet</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => router.push('/queue')}
                    >
                      Upload your first document
                    </Button>
                  </div>
                ) : (
                  recentDocs?.documents?.slice(0, 5)?.map((doc) => (
                    <div
                      key={doc.doc_id}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => router.push(`/documents/${doc.doc_id}`)}
                    >
                      {getStatusIcon(doc.status)}
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium truncate">
                          {doc.filename}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Created {formatRelativeTime(new Date(doc.created_at))}
                        </p>
                      </div>
                      {getStatusBadge(doc.status)}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

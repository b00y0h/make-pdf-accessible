'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search,
  Filter,
  Download,
  Eye,
  FileText,
  Calendar,
  User,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { formatDate, formatBytes } from '@/lib/utils';
import { useDocuments } from '@/hooks/useApi';
import toast from 'react-hot-toast';

interface Document {
  doc_id: string;
  filename: string;
  status: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  user_id: string;
  metadata?: {
    originalSize?: number;
    pageCount?: number;
    title?: string;
    author?: string;
  };
  scores?: {
    overall?: number;
    structure?: number;
    alt_text?: number;
    color_contrast?: number;
    navigation?: number;
  };
  artifacts?: Record<string, string>;
  error_message?: string;
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'completed':
      return <Badge variant="success">Completed</Badge>;
    case 'failed':
      return <Badge variant="error">Failed</Badge>;
    case 'processing':
      return <Badge variant="warning">Processing</Badge>;
    default:
      return <Badge>Unknown</Badge>;
  }
}

function getWcagBadge(level: string | null) {
  if (!level) return null;

  const variant =
    level === 'AAA' ? 'success' : level === 'AA' ? 'warning' : 'secondary';
  return <Badge variant={variant}>WCAG {level}</Badge>;
}

function getAccessibilityScoreColor(score: number | null) {
  if (score === null) return 'text-gray-500';
  if (score >= 90) return 'text-green-600 dark:text-green-400';
  if (score >= 70) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function DocumentSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-4 p-4 border rounded-lg">
          <Skeleton className="h-8 w-8" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-64" />
              <div className="flex gap-2">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-6 w-16" />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-3 w-28" />
            </div>
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-8" />
            <Skeleton className="h-8 w-8" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DocumentsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  
  const { data: documentsResponse, isLoading, error, refetch } = useDocuments({
    page: 1,
    limit: 50
  });
  
  React.useEffect(() => {
    if (error) {
      toast.error('Failed to load documents');
    }
  }, [error]);
  
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
            <p className="text-muted-foreground">
              Manage your processed accessible documents
            </p>
          </div>
        </div>
        
        {/* Stats Skeleton */}
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-12 mb-2" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>Document Library</CardTitle>
          </CardHeader>
          <CardContent>
            <DocumentSkeleton />
          </CardContent>
        </Card>
      </div>
    );
  }

  const documents: Document[] = documentsResponse?.documents || [];
  
  // Filter documents
  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = !searchTerm || 
      doc.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.user_id.toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchesStatus = statusFilter === 'all' || doc.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });
  
  const completedDocs = documents.filter((doc) => doc.status === 'completed');
  const failedDocs = documents.filter((doc) => doc.status === 'failed');
  const avgScore = completedDocs.length > 0 
    ? completedDocs.reduce((sum, doc) => sum + (doc.scores?.overall || 0), 0) / completedDocs.length
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground">
            Manage your processed accessible documents
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Download className="mr-2 h-4 w-4" />
            Export All
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Documents
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{documents.length}</div>
            <p className="text-xs text-muted-foreground">
              {completedDocs.length} completed, {failedDocs.length} failed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Score</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(avgScore)}%</div>
            <p className="text-xs text-muted-foreground">Accessibility score</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">WCAG AA+</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {
                completedDocs.filter(
                  (doc) => doc.wcagLevel === 'AA' || doc.wcagLevel === 'AAA'
                ).length
              }
            </div>
            <p className="text-xs text-muted-foreground">Compliant documents</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Issues</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {completedDocs.reduce((sum, doc) => sum + (doc.issues || 0), 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all documents
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filter */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search documents..." 
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-input rounded-md text-sm"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Documents Table */}
      <Card>
        <CardHeader>
          <CardTitle>Document Library</CardTitle>
          <CardDescription>
            All your processed accessible documents
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredDocuments.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold mb-2">No documents found</h3>
              <p className="text-sm">
                {searchTerm ? 'Try adjusting your search terms' : 'Upload a document to get started'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredDocuments.map((doc) => (
                <div
                  key={doc.doc_id}
                  className="flex items-center gap-4 p-4 border rounded-lg hover:bg-accent/50 transition-colors"
                >
                  <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />

                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Link 
                          href={`/documents/${doc.doc_id}`}
                          className="font-medium truncate hover:underline"
                        >
                          {doc.filename || 'Untitled Document'}
                        </Link>
                        {getStatusBadge(doc.status)}
                        {doc.scores?.overall && doc.scores.overall >= 85 && (
                          <Badge variant="success">WCAG AA</Badge>
                        )}
                        {doc.scores?.overall && doc.scores.overall >= 95 && (
                          <Badge variant="success">WCAG AAA</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{formatBytes(doc.metadata?.originalSize || 0)}</span>
                        {doc.scores?.overall && (
                          <span className={getAccessibilityScoreColor(doc.scores.overall)}>
                            {doc.scores.overall}% accessible
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        <span>{doc.user_id}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        <span>Uploaded {formatDate(doc.created_at)}</span>
                      </div>
                      {doc.completed_at && (
                        <div className="flex items-center gap-1">
                          <CheckCircle className="h-3 w-3" />
                          <span>Processed {formatDate(doc.completed_at)}</span>
                        </div>
                      )}
                      {doc.metadata?.pageCount && (
                        <span>{doc.metadata.pageCount} pages</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link href={`/documents/${doc.doc_id}`}>
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </Link>
                    {doc.status === 'completed' && doc.artifacts && (
                      <>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => {
                            // Download accessible PDF
                            window.open(`/api/v1/documents/${doc.doc_id}/downloads?document_type=accessible_pdf`, '_blank');
                          }}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Link href={`/documents/${doc.doc_id}`}>
                          <Button variant="ghost" size="sm">
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        </Link>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

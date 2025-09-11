import React from 'react';
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
} from 'lucide-react';
import { formatDate, formatBytes } from '@/lib/utils';

// Mock data for documents
const documents = [
  {
    id: '1',
    name: 'Annual Report 2024.pdf',
    originalSize: 15728640,
    accessibleSize: 16842752,
    uploadedAt: new Date('2024-01-15T10:30:00Z'),
    processedAt: new Date('2024-01-15T10:45:00Z'),
    uploadedBy: 'John Doe',
    status: 'completed' as const,
    accessibilityScore: 95,
    issues: 2,
    wcagLevel: 'AA' as const,
  },
  {
    id: '2',
    name: 'Product Catalog Spring 2024.pdf',
    originalSize: 8472960,
    accessibleSize: 9216000,
    uploadedAt: new Date('2024-01-14T14:20:00Z'),
    processedAt: new Date('2024-01-14T14:38:00Z'),
    uploadedBy: 'Jane Smith',
    status: 'completed' as const,
    accessibilityScore: 88,
    issues: 5,
    wcagLevel: 'AA' as const,
  },
  {
    id: '3',
    name: 'Employee Handbook v3.pdf',
    originalSize: 5242880,
    accessibleSize: 5832704,
    uploadedAt: new Date('2024-01-13T09:15:00Z'),
    processedAt: new Date('2024-01-13T09:28:00Z'),
    uploadedBy: 'Bob Johnson',
    status: 'completed' as const,
    accessibilityScore: 92,
    issues: 3,
    wcagLevel: 'AA' as const,
  },
  {
    id: '4',
    name: 'Training Materials Q2.pdf',
    originalSize: 12582912,
    accessibleSize: null,
    uploadedAt: new Date('2024-01-12T16:45:00Z'),
    processedAt: null,
    uploadedBy: 'Alice Brown',
    status: 'failed' as const,
    accessibilityScore: null,
    issues: null,
    wcagLevel: null,
  },
  {
    id: '5',
    name: 'Marketing Brochure Q1.pdf',
    originalSize: 7340032,
    accessibleSize: 8126464,
    uploadedAt: new Date('2024-01-11T11:00:00Z'),
    processedAt: new Date('2024-01-11T11:15:00Z'),
    uploadedBy: 'Charlie Wilson',
    status: 'completed' as const,
    accessibilityScore: 78,
    issues: 8,
    wcagLevel: 'A' as const,
  },
  {
    id: '6',
    name: 'Legal Document Template.pdf',
    originalSize: 2097152,
    accessibleSize: 2359296,
    uploadedAt: new Date('2024-01-10T13:30:00Z'),
    processedAt: new Date('2024-01-10T13:35:00Z'),
    uploadedBy: 'Diana Prince',
    status: 'completed' as const,
    accessibilityScore: 100,
    issues: 0,
    wcagLevel: 'AAA' as const,
  },
];

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

export default function DocumentsPage() {
  const completedDocs = documents.filter((doc) => doc.status === 'completed');
  const failedDocs = documents.filter((doc) => doc.status === 'failed');
  const avgScore =
    completedDocs.reduce((sum, doc) => sum + (doc.accessibilityScore || 0), 0) /
    completedDocs.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground">
            Manage your processed accessible documents
          </p>
        </div>
        <Button>
          <Download className="mr-2 h-4 w-4" />
          Export All
        </Button>
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
              <Input placeholder="Search documents..." className="pl-8" />
            </div>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              Filter
            </Button>
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
          <div className="space-y-4">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-4 p-4 border rounded-lg hover:bg-accent/50 transition-colors"
              >
                <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />

                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium truncate">{doc.name}</h3>
                      {getStatusBadge(doc.status)}
                      {getWcagBadge(doc.wcagLevel)}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{formatBytes(doc.originalSize)}</span>
                      {doc.accessibilityScore !== null && (
                        <span
                          className={getAccessibilityScoreColor(
                            doc.accessibilityScore
                          )}
                        >
                          {doc.accessibilityScore}% accessible
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      <span>{doc.uploadedBy}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>Uploaded {formatDate(doc.uploadedAt)}</span>
                    </div>
                    {doc.processedAt && (
                      <div className="flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" />
                        <span>Processed {formatDate(doc.processedAt)}</span>
                      </div>
                    )}
                    {doc.issues !== null && doc.issues > 0 && (
                      <div className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
                        <AlertCircle className="h-3 w-3" />
                        <span>{doc.issues} issues</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm">
                    <Eye className="h-4 w-4" />
                  </Button>
                  {doc.status === 'completed' && (
                    <>
                      <Button variant="ghost" size="sm">
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

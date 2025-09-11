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
  Image,
  CheckCircle,
  XCircle,
  Clock,
  Edit3,
  RotateCcw,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

// Mock data for alt text review items
const altTextItems = [
  {
    id: '1',
    documentName: 'Annual Report 2024.pdf',
    pageNumber: 5,
    imageDescription: 'Bar chart showing quarterly revenue growth',
    generatedAltText:
      'A bar chart displaying quarterly revenue growth from Q1 to Q4 2024, showing an upward trend with Q1 at $2.1M, Q2 at $2.8M, Q3 at $3.2M, and Q4 at $3.9M.',
    status: 'pending' as const,
    confidence: 95,
    reviewedAt: null,
    reviewedBy: null,
    originalImageUrl: '/mock-chart-1.png',
  },
  {
    id: '2',
    documentName: 'Product Catalog Spring 2024.pdf',
    pageNumber: 12,
    imageDescription: 'Product photo of wireless headphones',
    generatedAltText:
      'Black over-ear wireless headphones with padded ear cups and adjustable headband, positioned at a three-quarter angle against a white background.',
    status: 'approved' as const,
    confidence: 88,
    reviewedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    reviewedBy: 'Sarah Johnson',
    originalImageUrl: '/mock-product-1.png',
  },
  {
    id: '3',
    documentName: 'Employee Handbook v3.pdf',
    pageNumber: 23,
    imageDescription: 'Organizational chart',
    generatedAltText:
      'Organizational chart showing company hierarchy with CEO at top, three VPs below, and department managers underneath each VP.',
    status: 'rejected' as const,
    confidence: 72,
    reviewedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
    reviewedBy: 'Mike Chen',
    originalImageUrl: '/mock-org-chart-1.png',
    feedback:
      'Alt text needs to include specific names and departments for better accessibility.',
  },
  {
    id: '4',
    documentName: 'Training Materials Q2.pdf',
    pageNumber: 8,
    imageDescription: 'Process workflow diagram',
    generatedAltText:
      'Workflow diagram illustrating the five-step customer onboarding process: Registration, Verification, Setup, Training, and Activation, connected by arrows showing the sequential flow.',
    status: 'pending' as const,
    confidence: 91,
    reviewedAt: null,
    reviewedBy: null,
    originalImageUrl: '/mock-workflow-1.png',
  },
  {
    id: '5',
    documentName: 'Marketing Brochure Q1.pdf',
    pageNumber: 3,
    imageDescription: 'Team photo in office setting',
    generatedAltText:
      'Group photo of diverse team of six professionals in a modern office environment, smiling at camera.',
    status: 'needs_revision' as const,
    confidence: 65,
    reviewedAt: new Date(Date.now() - 1 * 60 * 60 * 1000),
    reviewedBy: 'Alex Rodriguez',
    originalImageUrl: '/mock-team-1.png',
    feedback:
      'Should describe the office setting and team composition in more detail.',
  },
];

function getStatusBadge(status: string) {
  switch (status) {
    case 'pending':
      return <Badge variant="warning">Pending Review</Badge>;
    case 'approved':
      return <Badge variant="success">Approved</Badge>;
    case 'rejected':
      return <Badge variant="error">Rejected</Badge>;
    case 'needs_revision':
      return <Badge variant="secondary">Needs Revision</Badge>;
    default:
      return <Badge>Unknown</Badge>;
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'approved':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'rejected':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'needs_revision':
      return <AlertTriangle className="h-4 w-4 text-orange-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 90) return 'text-green-600 dark:text-green-400';
  if (confidence >= 70) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

export default function AltTextPage() {
  const pendingItems = altTextItems.filter((item) => item.status === 'pending');
  const approvedItems = altTextItems.filter(
    (item) => item.status === 'approved'
  );
  const needsRevisionItems = altTextItems.filter(
    (item) => item.status === 'needs_revision' || item.status === 'rejected'
  );

  const avgConfidence =
    altTextItems.reduce((sum, item) => sum + item.confidence, 0) /
    altTextItems.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Alt Text Review</h1>
          <p className="text-muted-foreground">
            Review and approve AI-generated alternative text for images
          </p>
        </div>
        <Button>
          <Sparkles className="mr-2 h-4 w-4" />
          Regenerate All
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Pending Review
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingItems.length}</div>
            <p className="text-xs text-muted-foreground">Awaiting review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approved</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{approvedItems.length}</div>
            <p className="text-xs text-muted-foreground">
              Ready for publication
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Needs Work</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {needsRevisionItems.length}
            </div>
            <p className="text-xs text-muted-foreground">Requires revision</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Avg Confidence
            </CardTitle>
            <Sparkles className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round(avgConfidence)}%
            </div>
            <p className="text-xs text-muted-foreground">AI confidence level</p>
          </CardContent>
        </Card>
      </div>

      {/* Alt Text Items */}
      <Card>
        <CardHeader>
          <CardTitle>Alt Text Items</CardTitle>
          <CardDescription>
            Review AI-generated alternative text descriptions for images
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {altTextItems.map((item) => (
              <div key={item.id} className="border rounded-lg p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(item.status)}
                    <div>
                      <h3 className="font-medium">{item.documentName}</h3>
                      <p className="text-sm text-muted-foreground">
                        Page {item.pageNumber}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-sm font-medium ${getConfidenceColor(item.confidence)}`}
                    >
                      {item.confidence}% confidence
                    </span>
                    {getStatusBadge(item.status)}
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  {/* Image Preview */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      {/* eslint-disable-next-line jsx-a11y/alt-text */}
                      <Image className="h-4 w-4" aria-hidden="true" />
                      <span className="font-medium">Image</span>
                    </div>
                    <div className="aspect-video bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300 dark:border-gray-700">
                      <div className="text-center text-muted-foreground">
                        {/* eslint-disable-next-line jsx-a11y/alt-text */}
                        <Image
                          className="h-12 w-12 mx-auto mb-2 opacity-50"
                          aria-hidden="true"
                        />
                        <p className="text-sm">{item.imageDescription}</p>
                      </div>
                    </div>
                  </div>

                  {/* Generated Alt Text */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      <span className="font-medium">Generated Alt Text</span>
                    </div>
                    <div className="min-h-[200px] p-4 border rounded-lg bg-muted/30">
                      <p className="text-sm leading-relaxed">
                        {item.generatedAltText}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Edit alt text..."
                        className="text-sm"
                      />
                      <Button size="sm" variant="outline">
                        <Edit3 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Review Status */}
                {item.reviewedBy && (
                  <div className="flex items-center justify-between bg-muted/30 rounded-lg p-3">
                    <div className="text-sm">
                      <span className="text-muted-foreground">
                        Reviewed by{' '}
                      </span>
                      <span className="font-medium">{item.reviewedBy}</span>
                      <span className="text-muted-foreground">
                        {' '}
                        {formatRelativeTime(item.reviewedAt!)}
                      </span>
                    </div>
                    {item.feedback && (
                      <div className="text-sm text-muted-foreground max-w-md">
                        <strong>Feedback:</strong> {item.feedback}
                      </div>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-2">
                  <Button variant="outline" size="sm">
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Regenerate
                  </Button>

                  {item.status === 'pending' && (
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        <XCircle className="mr-2 h-4 w-4" />
                        Reject
                      </Button>
                      <Button size="sm">
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Approve
                      </Button>
                    </div>
                  )}

                  {(item.status === 'rejected' ||
                    item.status === 'needs_revision') && (
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        Request Revision
                      </Button>
                      <Button size="sm">
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Approve
                      </Button>
                    </div>
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

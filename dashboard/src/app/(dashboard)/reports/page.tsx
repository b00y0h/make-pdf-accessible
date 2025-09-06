import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
} from 'lucide-react'

// Mock data for reports
const monthlyStats = {
  documentsProcessed: 247,
  averageProcessingTime: '12 min',
  successRate: 94.3,
  totalIssuesFound: 156,
  avgAccessibilityScore: 89,
  activeUsers: 23,
}

const topIssues = [
  { type: 'Missing Alt Text', count: 45, severity: 'high' },
  { type: 'Low Color Contrast', count: 32, severity: 'medium' },
  { type: 'Improper Heading Structure', count: 28, severity: 'high' },
  { type: 'Missing Table Headers', count: 21, severity: 'medium' },
  { type: 'Unclear Link Text', count: 18, severity: 'low' },
  { type: 'Missing Document Title', count: 12, severity: 'high' },
]

const wcagCompliance = {
  levelA: { count: 89, percentage: 36 },
  levelAA: { count: 124, percentage: 50 },
  levelAAA: { count: 34, percentage: 14 },
}

const userActivity = [
  { name: 'Sarah Johnson', documentsProcessed: 45, successRate: 96 },
  { name: 'Mike Chen', documentsProcessed: 38, successRate: 92 },
  { name: 'Alex Rodriguez', documentsProcessed: 33, successRate: 89 },
  { name: 'Emily Davis', documentsProcessed: 29, successRate: 97 },
  { name: 'John Smith', documentsProcessed: 24, successRate: 85 },
]

const recentReports = [
  {
    id: '1',
    name: 'Monthly Accessibility Report - January 2024',
    generatedAt: new Date('2024-01-31T23:59:59Z'),
    type: 'Monthly Summary',
    status: 'completed',
  },
  {
    id: '2',
    name: 'WCAG Compliance Report - Q4 2023',
    generatedAt: new Date('2024-01-15T10:30:00Z'),
    type: 'Compliance Report',
    status: 'completed',
  },
  {
    id: '3',
    name: 'User Activity Report - January 2024',
    generatedAt: new Date('2024-01-10T14:20:00Z'),
    type: 'User Analytics',
    status: 'completed',
  },
]

function getSeverityBadge(severity: string) {
  switch (severity) {
    case 'high':
      return <Badge variant="error">High</Badge>
    case 'medium':
      return <Badge variant="warning">Medium</Badge>
    case 'low':
      return <Badge variant="secondary">Low</Badge>
    default:
      return <Badge>Unknown</Badge>
  }
}

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports & Analytics</h1>
          <p className="text-muted-foreground">
            Track accessibility compliance and processing metrics
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Calendar className="mr-2 h-4 w-4" />
            Date Range
          </Button>
          <Button>
            <Download className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyStats.documentsProcessed}</div>
            <p className="text-xs text-muted-foreground">
              This month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyStats.averageProcessingTime}</div>
            <p className="text-xs text-muted-foreground">
              Per document
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyStats.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              +2.1% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Issues Found</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyStats.totalIssuesFound}</div>
            <p className="text-xs text-muted-foreground">
              Across all documents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Score</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyStats.avgAccessibilityScore}%</div>
            <p className="text-xs text-muted-foreground">
              Accessibility score
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyStats.activeUsers}</div>
            <p className="text-xs text-muted-foreground">
              This month
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* WCAG Compliance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              WCAG Compliance Levels
            </CardTitle>
            <CardDescription>
              Distribution of documents by WCAG compliance level
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="font-medium">WCAG AAA</span>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{wcagCompliance.levelAAA.count}</div>
                  <div className="text-sm text-muted-foreground">{wcagCompliance.levelAAA.percentage}%</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-blue-500" />
                  <span className="font-medium">WCAG AA</span>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{wcagCompliance.levelAA.count}</div>
                  <div className="text-sm text-muted-foreground">{wcagCompliance.levelAA.percentage}%</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-yellow-500" />
                  <span className="font-medium">WCAG A</span>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{wcagCompliance.levelA.count}</div>
                  <div className="text-sm text-muted-foreground">{wcagCompliance.levelA.percentage}%</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Top Issues */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Top Accessibility Issues
            </CardTitle>
            <CardDescription>
              Most common issues found across documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {topIssues.map((issue, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">{issue.type}</span>
                    {getSeverityBadge(issue.severity)}
                  </div>
                  <span className="text-lg font-bold">{issue.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* User Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Top Users This Month
            </CardTitle>
            <CardDescription>
              Most active users by documents processed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {userActivity.map((user, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="font-medium">{user.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {user.documentsProcessed} documents • {user.successRate}% success rate
                    </p>
                  </div>
                  <Badge variant={user.successRate >= 95 ? 'success' : user.successRate >= 90 ? 'warning' : 'secondary'}>
                    {user.successRate}%
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Reports */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Recent Reports
            </CardTitle>
            <CardDescription>
              Previously generated reports and analytics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentReports.map(report => (
                <div key={report.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="space-y-1">
                    <p className="font-medium">{report.name}</p>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Badge variant="secondary">{report.type}</Badge>
                      <span>•</span>
                      <span>{report.generatedAt.toLocaleDateString()}</span>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Generate New Report */}
      <Card>
        <CardHeader>
          <CardTitle>Generate New Report</CardTitle>
          <CardDescription>
            Create custom reports for specific time periods or criteria
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button>
              <BarChart3 className="mr-2 h-4 w-4" />
              Monthly Summary
            </Button>
            <Button variant="outline">
              <CheckCircle className="mr-2 h-4 w-4" />
              WCAG Compliance
            </Button>
            <Button variant="outline">
              <Users className="mr-2 h-4 w-4" />
              User Activity
            </Button>
            <Button variant="outline">
              <AlertCircle className="mr-2 h-4 w-4" />
              Issues Analysis
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

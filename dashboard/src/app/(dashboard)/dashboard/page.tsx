import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Users,
  BarChart3,
  ArrowUpRight,
} from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'

// Mock data - in a real app this would come from an API
const stats = {
  totalDocuments: 2847,
  processing: 23,
  completed: 2456,
  failed: 12,
  totalUsers: 156,
  todayUploads: 47,
}

const recentActivity = [
  {
    id: '1',
    type: 'upload',
    document: 'Annual Report 2024.pdf',
    user: 'John Doe',
    timestamp: new Date(Date.now() - 2 * 60 * 1000),
    status: 'processing',
  },
  {
    id: '2',
    type: 'completed',
    document: 'Marketing Brochure.pdf',
    user: 'Jane Smith',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    status: 'completed',
  },
  {
    id: '3',
    type: 'failed',
    document: 'Technical Manual.pdf',
    user: 'Bob Johnson',
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
    status: 'failed',
  },
  {
    id: '4',
    type: 'upload',
    document: 'User Guide v2.pdf',
    user: 'Alice Brown',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    status: 'processing',
  },
]

const processingQueue = [
  {
    id: '1',
    name: 'Annual Report 2024.pdf',
    progress: 75,
    stage: 'Alt Text Generation',
    eta: '2 min',
  },
  {
    id: '2',
    name: 'Product Catalog.pdf',
    progress: 45,
    stage: 'OCR Processing',
    eta: '8 min',
  },
  {
    id: '3',
    name: 'Employee Handbook.pdf',
    progress: 20,
    stage: 'Structure Analysis',
    eta: '12 min',
  },
]

function getStatusIcon(status: string) {
  switch (status) {
    case 'processing':
      return <Clock className="h-4 w-4 text-yellow-500" />
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />
    default:
      return <FileText className="h-4 w-4 text-gray-500" />
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'processing':
      return <Badge variant="warning">Processing</Badge>
    case 'completed':
      return <Badge variant="success">Completed</Badge>
    case 'failed':
      return <Badge variant="error">Failed</Badge>
    default:
      return <Badge>Unknown</Badge>
  }
}

export default function DashboardPage() {
  const successRate = Math.round((stats.completed / (stats.completed + stats.failed)) * 100)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your PDF accessibility processing
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDocuments.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                +{stats.todayUploads} today
              </span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processing</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.processing}</div>
            <p className="text-xs text-muted-foreground">
              Currently in queue
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{successRate}%</div>
            <p className="text-xs text-muted-foreground">
              {stats.completed.toLocaleString()} completed, {stats.failed} failed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalUsers}</div>
            <p className="text-xs text-muted-foreground">
              Registered users
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Processing Queue */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Processing Queue
            </CardTitle>
            <CardDescription>
              Documents currently being processed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {processingQueue.map((item) => (
                <div key={item.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium truncate">{item.name}</p>
                    <span className="text-xs text-muted-foreground">
                      ETA: {item.eta}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{item.stage}</span>
                      <span>{item.progress}%</span>
                    </div>
                    <Progress value={item.progress} className="h-2" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Recent Activity
              </span>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </CardTitle>
            <CardDescription>
              Latest document processing activity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-3">
                  {getStatusIcon(activity.status)}
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium truncate">
                      {activity.document}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      By {activity.user} • {formatRelativeTime(activity.timestamp)}
                    </p>
                  </div>
                  {getStatusBadge(activity.status)}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Clock,
  FileText,
  AlertCircle,
  Play,
  Pause,
  RotateCcw,
  MoreVertical,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { formatRelativeTime, formatBytes } from '@/lib/utils'

// Mock data for processing queue
const queueItems = [
  {
    id: '1',
    name: 'Annual Report 2024.pdf',
    size: 15728640, // 15MB
    stage: 'Alt Text Generation',
    progress: 75,
    eta: '2 min',
    startedAt: new Date(Date.now() - 5 * 60 * 1000),
    priority: 'high' as const,
    status: 'processing' as const,
  },
  {
    id: '2',
    name: 'Product Catalog Spring 2024.pdf',
    size: 8472960, // 8MB
    stage: 'OCR Processing',
    progress: 45,
    eta: '8 min',
    startedAt: new Date(Date.now() - 3 * 60 * 1000),
    priority: 'medium' as const,
    status: 'processing' as const,
  },
  {
    id: '3',
    name: 'Employee Handbook v3.pdf',
    size: 5242880, // 5MB
    stage: 'Structure Analysis',
    progress: 20,
    eta: '12 min',
    startedAt: new Date(Date.now() - 1 * 60 * 1000),
    priority: 'low' as const,
    status: 'processing' as const,
  },
  {
    id: '4',
    name: 'Training Materials Q2.pdf',
    size: 12582912, // 12MB
    stage: 'Queued',
    progress: 0,
    eta: '15 min',
    startedAt: new Date(Date.now() - 30 * 1000),
    priority: 'medium' as const,
    status: 'queued' as const,
  },
  {
    id: '5',
    name: 'Legal Document Template.pdf',
    size: 2097152, // 2MB
    stage: 'Queued',
    progress: 0,
    eta: '18 min',
    startedAt: new Date(),
    priority: 'low' as const,
    status: 'queued' as const,
  },
  {
    id: '6',
    name: 'Marketing Brochure.pdf',
    size: 7340032, // 7MB
    stage: 'Error: Invalid PDF structure',
    progress: 0,
    eta: 'N/A',
    startedAt: new Date(Date.now() - 10 * 60 * 1000),
    priority: 'high' as const,
    status: 'failed' as const,
  },
]

function getPriorityBadge(priority: string) {
  switch (priority) {
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

function getStatusBadge(status: string) {
  switch (status) {
    case 'processing':
      return <Badge variant="warning">Processing</Badge>
    case 'queued':
      return <Badge variant="secondary">Queued</Badge>
    case 'failed':
      return <Badge variant="error">Failed</Badge>
    default:
      return <Badge>Unknown</Badge>
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'processing':
      return <Play className="h-4 w-4 text-yellow-500" />
    case 'queued':
      return <Clock className="h-4 w-4 text-gray-500" />
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />
    default:
      return <FileText className="h-4 w-4 text-gray-500" />
  }
}

export default function QueuePage() {
  const processingItems = queueItems.filter(item => item.status === 'processing')
  const queuedItems = queueItems.filter(item => item.status === 'queued')
  const failedItems = queueItems.filter(item => item.status === 'failed')

  const totalItems = queueItems.length
  const activeItems = processingItems.length
  const avgProcessingTime = '8 min' // This would be calculated from historical data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Processing Queue</h1>
          <p className="text-muted-foreground">
            Monitor and manage document processing jobs
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Pause className="mr-2 h-4 w-4" />
            Pause Queue
          </Button>
          <Button>
            <Play className="mr-2 h-4 w-4" />
            Resume All
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalItems}</div>
            <p className="text-xs text-muted-foreground">
              In queue and processing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeItems}</div>
            <p className="text-xs text-muted-foreground">
              Currently processing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Jobs</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{failedItems.length}</div>
            <p className="text-xs text-muted-foreground">
              Require attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgProcessingTime}</div>
            <p className="text-xs text-muted-foreground">
              Per document
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Queue List */}
      <Card>
        <CardHeader>
          <CardTitle>Processing Jobs</CardTitle>
          <CardDescription>
            Documents currently in the processing pipeline
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {queueItems.map(item => (
              <div key={item.id} className="flex items-center gap-4 p-4 border rounded-lg">
                <div className="flex-shrink-0">
                  {getStatusIcon(item.status)}
                </div>
                
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <p className="font-medium truncate">{item.name}</p>
                      {getPriorityBadge(item.priority)}
                      {getStatusBadge(item.status)}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span>{formatBytes(item.size)}</span>
                      <span>•</span>
                      <span>{formatRelativeTime(item.startedAt)}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span className={item.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}>
                      {item.stage}
                    </span>
                    <span className="text-muted-foreground">
                      ETA: {item.eta}
                    </span>
                  </div>
                  
                  {item.status === 'processing' && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span>Progress</span>
                        <span>{item.progress}%</span>
                      </div>
                      <Progress value={item.progress} className="h-2" />
                    </div>
                  )}
                </div>
                
                <div className="flex-shrink-0">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {item.status === 'processing' && (
                        <DropdownMenuItem>
                          <Pause className="mr-2 h-4 w-4" />
                          Pause Job
                        </DropdownMenuItem>
                      )}
                      {item.status === 'failed' && (
                        <DropdownMenuItem>
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Retry Job
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem>
                        <FileText className="mr-2 h-4 w-4" />
                        View Details
                      </DropdownMenuItem>
                      <DropdownMenuItem className="text-red-600">
                        Cancel Job
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

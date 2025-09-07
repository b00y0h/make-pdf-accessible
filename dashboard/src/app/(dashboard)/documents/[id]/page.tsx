'use client'

import React, { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  ArrowLeft,
  Download,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Eye,
  Edit3,
  Save,
  X,
  RefreshCw,
  ExternalLink,
} from 'lucide-react'
import { formatRelativeTime, formatBytes } from '@/lib/utils'
import { useDocument, useDownloadUrl, useUpdateAltText } from '@/hooks/useApi'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

function DocumentSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10" />
        <div>
          <Skeleton className="h-7 w-80 mb-2" />
          <Skeleton className="h-4 w-60" />
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    </div>
  )
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'processing':
      return <Clock className="h-5 w-5 text-yellow-500" />
    case 'completed':
      return <CheckCircle className="h-5 w-5 text-green-500" />
    case 'failed':
      return <AlertCircle className="h-5 w-5 text-red-500" />
    case 'pending':
      return <Clock className="h-5 w-5 text-blue-500" />
    default:
      return <FileText className="h-5 w-5 text-gray-500" />
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'processing':
      return <Badge variant="warning" className="text-sm">Processing</Badge>
    case 'completed':
      return <Badge variant="success" className="text-sm">Completed</Badge>
    case 'failed':
      return <Badge variant="error" className="text-sm">Failed</Badge>
    case 'pending':
      return <Badge variant="secondary" className="text-sm">Pending</Badge>
    default:
      return <Badge className="text-sm">Unknown</Badge>
  }
}

interface DownloadButtonProps {
  docId: string
  type: string
  label: string
  description: string
  disabled?: boolean
}

function DownloadButton({ docId, type, label, description, disabled }: DownloadButtonProps) {
  const downloadMutation = useDownloadUrl()

  const handleDownload = async () => {
    try {
      const result = await downloadMutation.mutateAsync({ docId, type })
      // Open the pre-signed URL
      window.open(result.download_url, '_blank')
      toast.success(`Download started for ${label}`)
    } catch (error) {
      toast.error(`Failed to download ${label}`)
    }
  }

  return (
    <Button
      variant="outline"
      onClick={handleDownload}
      disabled={disabled || downloadMutation.isPending}
      className="w-full justify-start h-auto py-3"
    >
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-3">
          <Download className="h-4 w-4" />
          <div className="text-left">
            <div className="font-medium">{label}</div>
            <div className="text-xs text-muted-foreground">{description}</div>
          </div>
        </div>
        {downloadMutation.isPending && <RefreshCw className="h-4 w-4 animate-spin" />}
      </div>
    </Button>
  )
}

export default function DocumentDetailPage() {
  const params = useParams()
  const router = useRouter()
  const docId = params.id as string
  
  const [editingAltText, setEditingAltText] = useState(false)
  const [altTextValue, setAltTextValue] = useState('')

  const { 
    data: document, 
    isLoading, 
    error, 
    refetch 
  } = useDocument(docId)

  const updateAltTextMutation = useUpdateAltText()

  React.useEffect(() => {
    if (error) {
      toast.error('Failed to load document details')
    }
  }, [error])

  React.useEffect(() => {
    if (document?.artifacts?.alt_text) {
      try {
        const altTextData = JSON.parse(document.artifacts.alt_text)
        setAltTextValue(JSON.stringify(altTextData, null, 2))
      } catch {
        setAltTextValue(document.artifacts.alt_text)
      }
    }
  }, [document])

  React.useEffect(() => {
    if (updateAltTextMutation.isSuccess) {
      toast.success('Alt text updated successfully')
      setEditingAltText(false)
      refetch()
    }
    if (updateAltTextMutation.error) {
      toast.error('Failed to update alt text')
    }
  }, [updateAltTextMutation.isSuccess, updateAltTextMutation.error, refetch])

  const handleSaveAltText = async () => {
    try {
      const altTextData = JSON.parse(altTextValue)
      await updateAltTextMutation.mutateAsync({
        docId,
        altText: altTextData
      })
    } catch (error) {
      toast.error('Invalid JSON format')
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>
        <DocumentSkeleton />
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Document not found</h3>
            <p className="text-muted-foreground text-center mb-4">
              The requested document could not be found or you don't have permission to view it.
            </p>
            <Button onClick={() => router.push('/queue')}>
              Go to Queue
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const hasArtifacts = document.artifacts && Object.keys(document.artifacts).some(key => document.artifacts![key])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          {getStatusIcon(document.status)}
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{document.filename}</h1>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>ID: {document.doc_id}</span>
              <span>Created {formatRelativeTime(new Date(document.created_at))}</span>
              <span>Updated {formatRelativeTime(new Date(document.updated_at))}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge(document.status)}
          {document.priority && (
            <Badge variant="error" className="text-xs">High Priority</Badge>
          )}
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {getStatusIcon(document.status)}
              <span className="font-medium capitalize">{document.status}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {document.status === 'completed' && 'Processing completed successfully'}
              {document.status === 'processing' && 'Document is being processed'}
              {document.status === 'failed' && 'Processing failed'}
              {document.status === 'pending' && 'Waiting to be processed'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">User</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{document.user_id}</div>
            <p className="text-xs text-muted-foreground mt-1">Document owner</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">
              {document.priority ? 'High Priority' : 'Normal Priority'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Processing priority</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="downloads" className="space-y-4">
        <TabsList>
          <TabsTrigger value="downloads">Downloads</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          <TabsTrigger value="alt-text">Alt Text</TabsTrigger>
          <TabsTrigger value="metadata">Metadata</TabsTrigger>
        </TabsList>

        <TabsContent value="downloads" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Available Downloads</CardTitle>
              <CardDescription>
                Download the original document and processed versions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <DownloadButton
                docId={document.doc_id}
                type="original"
                label="Original PDF"
                description="The original uploaded document"
              />
              
              <DownloadButton
                docId={document.doc_id}
                type="accessible"
                label="Accessible PDF"
                description="PDF with accessibility improvements"
                disabled={document.status !== 'completed'}
              />
              
              <DownloadButton
                docId={document.doc_id}
                type="report"
                label="Processing Report"
                description="Detailed report of accessibility improvements"
                disabled={document.status !== 'completed'}
              />
              
              <DownloadButton
                docId={document.doc_id}
                type="csvzip"
                label="Data Export (CSV)"
                description="Export processing data as CSV files"
                disabled={document.status !== 'completed'}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="artifacts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Processing Artifacts</CardTitle>
              <CardDescription>
                Intermediate files and data generated during processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!hasArtifacts ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No artifacts available yet</p>
                  <p className="text-xs">Artifacts will appear as the document is processed</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {document.artifacts?.textract && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">Textract Data</div>
                        <div className="text-xs text-muted-foreground">OCR and text extraction results</div>
                      </div>
                      <Button variant="outline" size="sm">
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View
                      </Button>
                    </div>
                  )}
                  
                  {document.artifacts?.structure && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">Document Structure</div>
                        <div className="text-xs text-muted-foreground">Hierarchical structure analysis</div>
                      </div>
                      <Button variant="outline" size="sm">
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View
                      </Button>
                    </div>
                  )}
                  
                  {document.artifacts?.tagged_pdf && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">Tagged PDF</div>
                        <div className="text-xs text-muted-foreground">PDF with accessibility tags</div>
                      </div>
                      <Button variant="outline" size="sm">
                        <Download className="h-4 w-4 mr-2" />
                        Download
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alt-text" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Alt Text Configuration
                <div className="flex items-center gap-2">
                  {!editingAltText ? (
                    <Button 
                      size="sm" 
                      onClick={() => setEditingAltText(true)}
                      disabled={!document.artifacts?.alt_text}
                    >
                      <Edit3 className="h-4 w-4 mr-2" />
                      Edit
                    </Button>
                  ) : (
                    <>
                      <Button 
                        size="sm" 
                        onClick={handleSaveAltText}
                        disabled={updateAltTextMutation.isPending}
                      >
                        <Save className="h-4 w-4 mr-2" />
                        Save
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => {
                          setEditingAltText(false)
                          // Reset to original value
                          if (document.artifacts?.alt_text) {
                            try {
                              const altTextData = JSON.parse(document.artifacts.alt_text)
                              setAltTextValue(JSON.stringify(altTextData, null, 2))
                            } catch {
                              setAltTextValue(document.artifacts.alt_text)
                            }
                          }
                        }}
                      >
                        <X className="h-4 w-4 mr-2" />
                        Cancel
                      </Button>
                    </>
                  )}
                </div>
              </CardTitle>
              <CardDescription>
                Review and edit automatically generated alt text descriptions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!document.artifacts?.alt_text ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Eye className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No alt text available yet</p>
                  <p className="text-xs">Alt text will be generated during processing</p>
                </div>
              ) : editingAltText ? (
                <div className="space-y-4">
                  <Textarea
                    value={altTextValue}
                    onChange={(e) => setAltTextValue(e.target.value)}
                    placeholder="Edit alt text JSON..."
                    className="min-h-64 font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    Edit the JSON structure containing alt text descriptions for images and elements
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto max-h-96">
                    {altTextValue}
                  </pre>
                  <p className="text-xs text-muted-foreground">
                    Alt text descriptions for images and visual elements in the document
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metadata" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Document Metadata</CardTitle>
              <CardDescription>
                Additional information and processing details
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <div className="text-sm font-medium">Document ID</div>
                  <div className="text-sm text-muted-foreground font-mono">{document.doc_id}</div>
                </div>
                <div>
                  <div className="text-sm font-medium">User ID</div>
                  <div className="text-sm text-muted-foreground font-mono">{document.user_id}</div>
                </div>
                <div>
                  <div className="text-sm font-medium">Created</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(document.created_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Last Updated</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(document.updated_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Priority</div>
                  <div className="text-sm text-muted-foreground">
                    {document.priority ? 'High' : 'Normal'}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Webhook URL</div>
                  <div className="text-sm text-muted-foreground font-mono">
                    {document.webhook_url || 'None'}
                  </div>
                </div>
              </div>
              
              {document.metadata && (
                <div className="mt-6">
                  <div className="text-sm font-medium mb-2">Custom Metadata</div>
                  <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto">
                    {JSON.stringify(document.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
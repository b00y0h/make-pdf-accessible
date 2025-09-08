'use client'

import React, { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  CheckCircle,
  AlertCircle,
  Clock,
  Settings,
  ArrowRight,
  Upload as UploadIcon
} from 'lucide-react'
import { FileUpload, FileUploadFile, useFileUpload } from '@/components/FileUpload'
import { useS3Upload } from '@/hooks/useS3Upload'
import toast from 'react-hot-toast'

interface UploadSettings {
  priority: boolean
  webhookUrl: string
  metadata: Record<string, any>
}

export default function UploadPage() {
  const router = useRouter()
  const { files, updateFile, removeFile, addFiles, clearAll } = useFileUpload()
  const { uploadToS3, uploadMultiple, isUploading } = useS3Upload()
  
  const [settings, setSettings] = useState<UploadSettings>({
    priority: false,
    webhookUrl: '',
    metadata: {}
  })
  const [showSettings, setShowSettings] = useState(false)
  const [metadataText, setMetadataText] = useState('')
  
  // Handle files selected from dropzone
  const handleFilesSelected = useCallback((newFiles: FileUploadFile[]) => {
    addFiles(newFiles)
  }, [addFiles])

  // Start upload process
  const handleUpload = useCallback(async () => {
    const filesToUpload = files.filter(f => f.status === 'idle')
    
    if (filesToUpload.length === 0) {
      toast.error('No files ready for upload')
      return
    }

    // Parse metadata
    let parsedMetadata = settings.metadata
    if (metadataText.trim()) {
      try {
        parsedMetadata = { ...parsedMetadata, ...JSON.parse(metadataText) }
      } catch (e) {
        toast.error('Invalid metadata JSON format')
        return
      }
    }

    try {
      // Upload files sequentially to avoid overwhelming the server
      for (const file of filesToUpload) {
        updateFile(file.id, { status: 'uploading', progress: 0 })

        try {
          const result = await uploadToS3(file, {
            onProgress: (progress) => {
              updateFile(file.id, { 
                status: 'uploading', 
                progress: progress.percentage 
              })
            },
            onSuccess: (result) => {
              updateFile(file.id, { 
                status: 'success', 
                progress: 100,
                docId: result.docId
              })
              toast.success(`${file.name} uploaded successfully!`)
            },
            onError: (error) => {
              updateFile(file.id, { 
                status: 'error', 
                error: error.message 
              })
              toast.error(`Failed to upload ${file.name}: ${error.message}`)
            }
          })
        } catch (error) {
          console.error(`Upload failed for ${file.name}:`, error)
        }
      }

      // Show success message for completed uploads
      const successCount = files.filter(f => f.status === 'success').length
      if (successCount > 0) {
        toast.success(`Successfully uploaded ${successCount} file${successCount > 1 ? 's' : ''}!`)
      }

    } catch (error) {
      console.error('Upload process failed:', error)
      toast.error('Upload process failed')
    }
  }, [files, uploadToS3, updateFile, settings, metadataText])

  // Navigate to document detail
  const handleViewDocument = useCallback((docId: string) => {
    router.push(`/documents/${docId}`)
  }, [router])

  // Stats
  const completedCount = files.filter(f => f.status === 'success').length
  const errorCount = files.filter(f => f.status === 'error').length  
  const uploadingCount = files.filter(f => f.status === 'uploading').length
  const readyCount = files.filter(f => f.status === 'idle').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload Documents</h1>
          <p className="text-muted-foreground">
            Upload PDF documents to make them accessible
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-2"
          >
            <Settings className="h-4 w-4" />
            Settings
          </Button>
          
          {readyCount > 0 && (
            <Button
              onClick={handleUpload}
              disabled={isUploading || readyCount === 0}
              className="flex items-center gap-2"
            >
              <UploadIcon className="h-4 w-4" />
              Upload {readyCount} File{readyCount !== 1 ? 's' : ''}
              {isUploading && <Clock className="h-4 w-4 animate-spin" />}
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      {files.length > 0 && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Ready</CardTitle>
              <UploadIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{readyCount}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Uploading</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{uploadingCount}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{completedCount}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Errors</CardTitle>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{errorCount}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Upload Settings */}
      {showSettings && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Settings</CardTitle>
            <CardDescription>
              Configure advanced upload options
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="priority"
                checked={settings.priority}
                onCheckedChange={(checked) => 
                  setSettings(prev => ({ ...prev, priority: checked }))
                }
              />
              <Label htmlFor="priority">Priority processing</Label>
            </div>

            <div className="space-y-2">
              <Label htmlFor="webhook">Webhook URL (optional)</Label>
              <Input
                id="webhook"
                type="url"
                placeholder="https://your-site.com/webhook"
                value={settings.webhookUrl}
                onChange={(e) => 
                  setSettings(prev => ({ ...prev, webhookUrl: e.target.value }))
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="metadata">Additional Metadata (JSON)</Label>
              <Textarea
                id="metadata"
                placeholder='{"project": "test", "department": "legal"}'
                value={metadataText}
                onChange={(e) => setMetadataText(e.target.value)}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* File Upload Area */}
      <FileUpload
        onFilesSelected={handleFilesSelected}
        maxFiles={10}
        maxSize={50 * 1024 * 1024} // 50MB
        accept={{
          'application/pdf': ['.pdf']
        }}
        showFileList={true}
      />

      {/* Success Actions */}
      {completedCount > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Complete!</CardTitle>
            <CardDescription>
              Your documents are now being processed for accessibility
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              {files
                .filter(f => f.status === 'success' && f.docId)
                .map(file => (
                  <div key={file.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      <div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          Document ID: {file.docId?.slice(0, 8)}...
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewDocument(file.docId!)}
                      className="flex items-center gap-2"
                    >
                      View Details
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                ))
              }
            </div>

            <div className="flex justify-between">
              <Button 
                variant="outline" 
                onClick={clearAll}
              >
                Clear All
              </Button>
              <Button onClick={() => router.push('/queue')}>
                View All Documents
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

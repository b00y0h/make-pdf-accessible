'use client'

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  Upload as UploadIcon,
  File,
  X,
  CheckCircle,
  AlertCircle,
  FileText,
  Clock,
} from 'lucide-react'
import { formatBytes } from '@/lib/utils'

interface UploadFile {
  id: string
  file: File
  progress: number
  status: 'uploading' | 'processing' | 'completed' | 'error'
  error?: string
}

export default function UploadPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadFile[]>([])
  const [isUploading, setIsUploading] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substring(7),
      file,
      progress: 0,
      status: 'uploading' as const,
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])
    setIsUploading(true)

    // Simulate file upload and processing
    newFiles.forEach(uploadFile => {
      simulateUpload(uploadFile)
    })
  }, [])

  const simulateUpload = (uploadFile: UploadFile) => {
    const interval = setInterval(() => {
      setUploadedFiles(prev =>
        prev.map(file => {
          if (file.id === uploadFile.id) {
            if (file.progress < 100) {
              return { ...file, progress: Math.min(file.progress + 10, 100) }
            } else if (file.status === 'uploading') {
              return { ...file, status: 'processing' }
            } else if (file.status === 'processing') {
              // Randomly complete or error for demo
              const success = Math.random() > 0.2
              return {
                ...file,
                status: success ? 'completed' : 'error',
                error: success ? undefined : 'Processing failed: Invalid PDF format',
              }
            }
          }
          return file
        })
      )
    }, 500)

    // Clean up interval after completion
    setTimeout(() => {
      clearInterval(interval)
      setIsUploading(false)
    }, 6000)
  }

  const removeFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== id))
  }

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } =
    useDropzone({
      onDrop,
      accept: {
        'application/pdf': ['.pdf'],
      },
      maxSize: 50 * 1024 * 1024, // 50MB
    })

  const getDropzoneClass = () => {
    let baseClass = 'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer'
    
    if (isDragAccept) {
      return `${baseClass} border-green-500 bg-green-50 dark:bg-green-900/20`
    }
    if (isDragReject) {
      return `${baseClass} border-red-500 bg-red-50 dark:bg-red-900/20`
    }
    if (isDragActive) {
      return `${baseClass} border-blue-500 bg-blue-50 dark:bg-blue-900/20`
    }
    return `${baseClass} border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600`
  }

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
    }
  }

  const getStatusBadge = (status: UploadFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Badge variant="warning">Uploading</Badge>
      case 'processing':
        return <Badge variant="warning">Processing</Badge>
      case 'completed':
        return <Badge variant="success">Completed</Badge>
      case 'error':
        return <Badge variant="error">Error</Badge>
    }
  }

  const completedCount = uploadedFiles.filter(f => f.status === 'completed').length
  const errorCount = uploadedFiles.filter(f => f.status === 'error').length
  const processingCount = uploadedFiles.filter(f => 
    f.status === 'uploading' || f.status === 'processing'
  ).length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Documents</h1>
        <p className="text-muted-foreground">
          Upload PDF documents to make them accessible
        </p>
      </div>

      {/* Stats */}
      {uploadedFiles.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Processing</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{processingCount}</div>
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

      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle>Upload PDFs</CardTitle>
          <CardDescription>
            Drag and drop PDF files here, or click to select files. Max file size: 50MB
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div {...getRootProps()} className={getDropzoneClass()}>
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 rounded-full bg-gray-100 dark:bg-gray-800">
                <UploadIcon className="h-8 w-8 text-gray-600 dark:text-gray-400" />
              </div>
              <div className="text-center">
                {isDragActive ? (
                  <p className="text-lg font-medium">
                    {isDragAccept
                      ? 'Drop the PDF files here...'
                      : 'Only PDF files are accepted'}
                  </p>
                ) : (
                  <div>
                    <p className="text-lg font-medium">Drop PDF files here or click to browse</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Supported formats: PDF (max 50MB each)
                    </p>
                  </div>
                )}
              </div>
              <Button variant="outline">
                Select Files
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Progress</CardTitle>
            <CardDescription>
              Track the progress of your uploaded files
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {uploadedFiles.map(uploadFile => (
                <div key={uploadFile.id} className="flex items-center gap-4 p-4 border rounded-lg">
                  <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium truncate">{uploadFile.file.name}</p>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(uploadFile.status)}
                        {getStatusBadge(uploadFile.status)}
                      </div>
                    </div>
                    
                    <div className="text-sm text-muted-foreground mb-2">
                      {formatBytes(uploadFile.file.size)}
                    </div>
                    
                    {uploadFile.status !== 'error' && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span>
                            {uploadFile.status === 'uploading'
                              ? 'Uploading...'
                              : uploadFile.status === 'processing'
                              ? 'Processing...'
                              : 'Complete'}
                          </span>
                          <span>{uploadFile.progress}%</span>
                        </div>
                        <Progress value={uploadFile.progress} className="h-2" />
                      </div>
                    )}
                    
                    {uploadFile.error && (
                      <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                        {uploadFile.error}
                      </p>
                    )}
                  </div>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(uploadFile.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

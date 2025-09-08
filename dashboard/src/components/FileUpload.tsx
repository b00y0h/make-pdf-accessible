'use client'

import React, { useCallback, useState } from 'react'
import { useDropzone, DropzoneOptions } from 'react-dropzone'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  Upload as UploadIcon,
  FileText,
  X,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react'
import { cn } from '@/lib/utils'

export interface FileUploadFile extends File {
  id: string
  progress: number
  status: 'idle' | 'uploading' | 'success' | 'error'
  error?: string
  docId?: string
}

export interface FileUploadProps {
  /** Callback when files are selected */
  onFilesSelected?: (files: FileUploadFile[]) => void
  /** Callback when upload starts */
  onUploadStart?: (file: FileUploadFile) => void
  /** Callback when upload progresses */
  onUploadProgress?: (file: FileUploadFile, progress: number) => void
  /** Callback when upload completes */
  onUploadComplete?: (file: FileUploadFile) => void
  /** Callback when upload fails */
  onUploadError?: (file: FileUploadFile, error: string) => void
  /** Maximum number of files */
  maxFiles?: number
  /** Maximum file size in bytes */
  maxSize?: number
  /** Accepted file types */
  accept?: Record<string, string[]>
  /** Whether upload is disabled */
  disabled?: boolean
  /** Custom className */
  className?: string
  /** Show file list */
  showFileList?: boolean
}

const DEFAULT_MAX_SIZE = 50 * 1024 * 1024 // 50MB
const DEFAULT_ACCEPT = {
  'application/pdf': ['.pdf']
}

function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

export function FileUpload({
  onFilesSelected,
  onUploadStart,
  onUploadProgress,
  onUploadComplete,
  onUploadError,
  maxFiles = 10,
  maxSize = DEFAULT_MAX_SIZE,
  accept = DEFAULT_ACCEPT,
  disabled = false,
  className,
  showFileList = true
}: FileUploadProps) {
  const [files, setFiles] = useState<FileUploadFile[]>([])

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Process accepted files
    const newFiles: FileUploadFile[] = acceptedFiles.map((file, index) => ({
      ...file,
      id: `${Date.now()}-${index}`,
      progress: 0,
      status: 'idle' as const
    }))

    setFiles(prev => [...prev, ...newFiles])
    onFilesSelected?.(newFiles)

    // Handle rejected files
    if (rejectedFiles.length > 0) {
      console.warn('Some files were rejected:', rejectedFiles)
    }
  }, [onFilesSelected])

  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }, [])

  const updateFileStatus = useCallback((
    fileId: string, 
    updates: Partial<Pick<FileUploadFile, 'status' | 'progress' | 'error' | 'docId'>>
  ) => {
    setFiles(prev => prev.map(file => 
      file.id === fileId ? { ...file, ...updates } : file
    ))
  }, [])

  // Dropzone configuration
  const dropzoneOptions: DropzoneOptions = {
    onDrop,
    accept,
    maxSize,
    maxFiles: maxFiles - files.length,
    disabled,
    multiple: maxFiles > 1,
    noClick: disabled,
    noKeyboard: disabled
  }

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
    isFocused
  } = useDropzone(dropzoneOptions)

  // File status helpers
  const getStatusIcon = (status: FileUploadFile['status']) => {
    switch (status) {
      case 'idle':
        return <FileText className="h-4 w-4 text-muted-foreground" />
      case 'uploading':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
    }
  }

  const getStatusBadge = (status: FileUploadFile['status']) => {
    switch (status) {
      case 'idle':
        return <Badge variant="outline">Ready</Badge>
      case 'uploading':
        return <Badge variant="secondary">Uploading</Badge>
      case 'success':
        return <Badge variant="default" className="bg-green-500 hover:bg-green-600">Success</Badge>
      case 'error':
        return <Badge variant="destructive">Error</Badge>
    }
  }

  // Dropzone styling
  const getDropzoneClassName = () => {
    return cn(
      'border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 cursor-pointer',
      'hover:border-primary/50 hover:bg-muted/25',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
      {
        'border-green-500 bg-green-50 dark:bg-green-950/20': isDragAccept,
        'border-red-500 bg-red-50 dark:bg-red-950/20': isDragReject,
        'border-primary bg-primary/5': isDragActive && !isDragReject,
        'border-primary/50 bg-muted/25': isFocused,
        'opacity-50 cursor-not-allowed': disabled,
        'border-muted-foreground/25': !isDragActive && !isFocused
      },
      className
    )
  }

  const acceptedFileTypes = Object.values(accept).flat().join(', ')
  const hasFiles = files.length > 0
  const canAddMore = files.length < maxFiles

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      {canAddMore && (
        <div
          {...getRootProps()}
          className={getDropzoneClassName()}
          role="button"
          tabIndex={0}
          aria-label={`Upload files. Accepted types: ${acceptedFileTypes}. Maximum size: ${formatBytes(maxSize)}`}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center gap-4">
            <div className="p-4 rounded-full bg-muted">
              <UploadIcon className="h-8 w-8 text-muted-foreground" />
            </div>
            
            <div className="text-center space-y-2">
              {isDragActive ? (
                <div>
                  {isDragAccept ? (
                    <p className="text-lg font-medium text-green-600 dark:text-green-400">
                      Drop files here to upload
                    </p>
                  ) : (
                    <p className="text-lg font-medium text-red-600 dark:text-red-400">
                      Some files are not supported
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <p className="text-lg font-medium">
                    Drag files here or click to browse
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Supported formats: {acceptedFileTypes}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Max file size: {formatBytes(maxSize)} • Max files: {maxFiles}
                  </p>
                </div>
              )}
            </div>
            
            {!isDragActive && (
              <Button 
                variant="outline" 
                disabled={disabled}
                aria-hidden="true"
                tabIndex={-1}
              >
                <UploadIcon className="h-4 w-4 mr-2" />
                Select Files
              </Button>
            )}
          </div>
        </div>
      )}

      {/* File List */}
      {showFileList && hasFiles && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">
                  Uploaded Files ({files.length}/{maxFiles})
                </h3>
                {files.some(f => f.status === 'error') && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setFiles(prev => prev.filter(f => f.status !== 'error'))}
                  >
                    Clear Errors
                  </Button>
                )}
              </div>

              <div className="space-y-3">
                {files.map(file => (
                  <div
                    key={file.id}
                    className="flex items-center gap-3 p-3 border rounded-lg"
                  >
                    {getStatusIcon(file.status)}
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="font-medium text-sm truncate pr-2">
                          {file.name}
                        </p>
                        {getStatusBadge(file.status)}
                      </div>
                      
                      <p className="text-xs text-muted-foreground mb-2">
                        {formatBytes(file.size)}
                        {file.docId && (
                          <span className="ml-2">ID: {file.docId.slice(0, 8)}...</span>
                        )}
                      </p>
                      
                      {file.status === 'uploading' && (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span>Uploading...</span>
                            <span>{file.progress}%</span>
                          </div>
                          <Progress value={file.progress} className="h-2" />
                        </div>
                      )}
                      
                      {file.error && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {file.error}
                        </p>
                      )}
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(file.id)}
                      disabled={file.status === 'uploading'}
                      aria-label={`Remove ${file.name}`}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Export file update function for external use
export function useFileUpload() {
  const [files, setFiles] = useState<FileUploadFile[]>([])

  const updateFile = useCallback((
    fileId: string, 
    updates: Partial<Pick<FileUploadFile, 'status' | 'progress' | 'error' | 'docId'>>
  ) => {
    setFiles(prev => prev.map(file => 
      file.id === fileId ? { ...file, ...updates } : file
    ))
  }, [])

  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }, [])

  const addFiles = useCallback((newFiles: FileUploadFile[]) => {
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const clearAll = useCallback(() => {
    setFiles([])
  }, [])

  return {
    files,
    updateFile,
    removeFile,
    addFiles,
    clearAll
  }
}
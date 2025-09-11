'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  File,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import clsx from 'clsx';

export interface FileWithPreview extends File {
  preview?: string;
  id: string;
}

interface FileUploadProps {
  onFilesSelected: (files: FileWithPreview[]) => void;
  maxFiles?: number;
  maxSize?: number;
  accept?: { [key: string]: string[] };
  disabled?: boolean;
  className?: string;
}

const DEFAULT_ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
    '.docx',
  ],
  'text/plain': ['.txt'],
};

const DEFAULT_MAX_SIZE = 100 * 1024 * 1024; // 100MB

export function FileUpload({
  onFilesSelected,
  maxFiles = 1,
  maxSize = DEFAULT_MAX_SIZE,
  accept = DEFAULT_ACCEPT,
  disabled = false,
  className,
}: FileUploadProps) {
  const [rejectedFiles, setRejectedFiles] = useState<
    Array<{
      file: File;
      errors: Array<{ code: string; message: string }>;
    }>
  >([]);

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: any[]) => {
      // Clear previous rejections
      setRejectedFiles(fileRejections);

      if (acceptedFiles.length > 0) {
        // Add unique IDs to files
        const filesWithPreview: FileWithPreview[] = acceptedFiles.map((file) =>
          Object.assign(file, {
            id: `${file.name}-${file.size}-${Date.now()}`,
            preview: file.type.startsWith('image/')
              ? URL.createObjectURL(file)
              : undefined,
          })
        );

        onFilesSelected(filesWithPreview);
      }
    },
    [onFilesSelected]
  );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
    isFocused,
  } = useDropzone({
    onDrop,
    accept,
    maxFiles,
    maxSize,
    disabled,
    multiple: maxFiles > 1,
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getAcceptedFileTypes = () => {
    return Object.values(accept).flat().join(', ');
  };

  const dropzoneClasses = clsx(
    'border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 ease-in-out',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
    {
      'border-blue-400 bg-blue-50 text-blue-700':
        isDragActive && isDragAccept && !disabled,
      'border-red-400 bg-red-50 text-red-700':
        isDragActive && isDragReject && !disabled,
      'border-gray-300 bg-gray-50 text-gray-500 cursor-not-allowed': disabled,
      'border-gray-300 hover:border-gray-400 text-gray-700 cursor-pointer':
        !disabled && !isDragActive,
      'ring-2 ring-blue-500 ring-offset-2': isFocused && !disabled,
    },
    className
  );

  return (
    <div className="space-y-4">
      {/* Main dropzone */}
      <div
        {...getRootProps()}
        className={dropzoneClasses}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-label={`Upload files. Accepted formats: ${getAcceptedFileTypes()}. Maximum size: ${formatFileSize(maxSize)}.`}
      >
        <input
          {...getInputProps()}
          aria-describedby="file-upload-description"
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <Upload
            className={clsx('w-12 h-12', {
              'text-blue-500': isDragActive && isDragAccept && !disabled,
              'text-red-500': isDragActive && isDragReject && !disabled,
              'text-gray-400': disabled,
              'text-gray-500': !disabled && !isDragActive,
            })}
            aria-hidden="true"
          />

          <div className="space-y-2">
            {isDragActive ? (
              <p className="text-lg font-medium">
                {isDragAccept ? 'Drop files here...' : 'File type not accepted'}
              </p>
            ) : (
              <>
                <p className="text-lg font-medium">
                  Drop files here, or click to select
                </p>
                <p
                  id="file-upload-description"
                  className="text-sm text-gray-500"
                >
                  Accepted formats: {getAcceptedFileTypes()}
                  <br />
                  Maximum file size: {formatFileSize(maxSize)}
                  {maxFiles > 1 && (
                    <>
                      <br />
                      Maximum {maxFiles} files
                    </>
                  )}
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Rejected files */}
      {rejectedFiles.length > 0 && (
        <div
          className="rounded-md bg-red-50 p-4"
          role="alert"
          aria-live="polite"
        >
          <div className="flex">
            <AlertCircle
              className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                {rejectedFiles.length} file{rejectedFiles.length > 1 ? 's' : ''}{' '}
                rejected
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <ul className="list-disc list-inside space-y-1">
                  {rejectedFiles.map((rejection, index) => (
                    <li key={index}>
                      <span className="font-medium">{rejection.file.name}</span>
                      {rejection.errors.map((error, errorIndex) => (
                        <span
                          key={errorIndex}
                          className="block ml-4 text-red-600"
                        >
                          {error.code === 'file-too-large' &&
                            `File is too large (${formatFileSize(rejection.file.size)})`}
                          {error.code === 'file-invalid-type' &&
                            'File type not supported'}
                          {error.code === 'too-many-files' &&
                            'Too many files selected'}
                        </span>
                      ))}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface FileListProps {
  files: FileWithPreview[];
  onRemoveFile: (fileId: string) => void;
  uploadProgress?: { [fileId: string]: number };
  uploadStatus?: {
    [fileId: string]: 'pending' | 'uploading' | 'success' | 'error';
  };
  disabled?: boolean;
}

export function FileList({
  files,
  onRemoveFile,
  uploadProgress = {},
  uploadStatus = {},
  disabled = false,
}: FileListProps) {
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (fileId: string) => {
    const status = uploadStatus[fileId];
    switch (status) {
      case 'uploading':
        return (
          <Loader2
            className="w-4 h-4 text-blue-500 animate-spin"
            aria-label="Uploading"
          />
        );
      case 'success':
        return (
          <CheckCircle
            className="w-4 h-4 text-green-500"
            aria-label="Upload successful"
          />
        );
      case 'error':
        return (
          <AlertCircle
            className="w-4 h-4 text-red-500"
            aria-label="Upload failed"
          />
        );
      default:
        return <File className="w-4 h-4 text-gray-500" aria-hidden="true" />;
    }
  };

  const getProgressBarColor = (status?: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  if (files.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-gray-900">
        Selected Files ({files.length})
      </h3>

      <ul
        className="divide-y divide-gray-200 border border-gray-200 rounded-md"
        role="list"
      >
        {files.map((file) => {
          const progress = uploadProgress[file.id] || 0;
          const status = uploadStatus[file.id];

          return (
            <li key={file.id} className="p-3 flex items-center justify-between">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                {getStatusIcon(file.id)}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-sm text-gray-500 ml-2 flex-shrink-0">
                      {formatFileSize(file.size)}
                    </p>
                  </div>

                  {/* Progress bar */}
                  {(status === 'uploading' || status === 'success') && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                        <span>
                          {status === 'success'
                            ? 'Complete'
                            : `${Math.round(progress)}%`}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className={clsx(
                            'h-1.5 rounded-full transition-all duration-300',
                            getProgressBarColor(status)
                          )}
                          style={{
                            width: `${status === 'success' ? 100 : progress}%`,
                          }}
                          role="progressbar"
                          aria-valuenow={status === 'success' ? 100 : progress}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-label={`Upload progress: ${status === 'success' ? 100 : Math.round(progress)}%`}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error message */}
                  {status === 'error' && (
                    <p className="mt-1 text-xs text-red-600">
                      Upload failed. Please try again.
                    </p>
                  )}
                </div>
              </div>

              {!disabled && status !== 'uploading' && (
                <button
                  type="button"
                  onClick={() => onRemoveFile(file.id)}
                  className="ml-3 p-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FileUpload,
  FileList,
  FileWithPreview,
} from '../../components/FileUpload';
import { useS3Upload } from '../../hooks/useS3Upload';
import { ChevronLeft, Settings, HelpCircle } from 'lucide-react';
import clsx from 'clsx';

interface UploadSettings {
  priority: boolean;
  webhookUrl: string;
  metadata: { [key: string]: string };
}

export default function UploadPage() {
  const router = useRouter();
  const { uploadFiles, uploadProgress, isUploading, resetProgress } =
    useS3Upload();

  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<UploadSettings>({
    priority: false,
    webhookUrl: '',
    metadata: {},
  });

  const handleFilesSelected = useCallback(
    (files: FileWithPreview[]) => {
      setSelectedFiles(files);
      resetProgress();
    },
    [resetProgress]
  );

  const handleRemoveFile = useCallback((fileId: string) => {
    setSelectedFiles((prev) => prev.filter((file) => file.id !== fileId));
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    try {
      const documents = await uploadFiles(selectedFiles, {
        priority: settings.priority,
        webhookUrl: settings.webhookUrl || undefined,
        metadata: settings.metadata,
      });

      // Navigate to document detail for the first uploaded document
      if (documents.length > 0) {
        router.push(`/documents/${documents[0].doc_id}`);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      // Error handling is managed by the useS3Upload hook
    }
  }, [selectedFiles, uploadFiles, settings, router]);

  const getUploadStatus = () => {
    const progressValues = Object.values(uploadProgress) as Array<{
      progress: number;
      status: 'pending' | 'uploading' | 'success' | 'error';
    }>;
    if (progressValues.length === 0) return null;

    const hasError = progressValues.some((p) => p.status === 'error');
    const allSuccess = progressValues.every((p) => p.status === 'success');
    const isUploading = progressValues.some((p) => p.status === 'uploading');

    if (hasError && allSuccess) return 'partial';
    if (hasError) return 'error';
    if (allSuccess && progressValues.length > 0) return 'success';
    if (isUploading) return 'uploading';
    return 'pending';
  };

  const uploadStatus = getUploadStatus();
  const canUpload = selectedFiles.length > 0 && !isUploading;
  const showProgress = Object.keys(uploadProgress).length > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.back()}
                className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md"
                aria-label="Go back"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              <h1 className="text-2xl font-bold text-gray-900">
                Upload Documents
              </h1>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className={clsx(
                  'p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  showSettings
                    ? 'text-blue-600 bg-blue-50'
                    : 'text-gray-400 hover:text-gray-600'
                )}
                aria-label="Toggle upload settings"
                aria-pressed={showSettings}
              >
                <Settings className="w-5 h-5" />
              </button>

              <button
                className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md"
                aria-label="Help"
              >
                <HelpCircle className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Upload area - spans 2 columns */}
          <div className="lg:col-span-2 space-y-6">
            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h2 className="text-sm font-medium text-blue-900 mb-2">
                How it works
              </h2>
              <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                <li>Select or drop your PDF, Word, or text files</li>
                <li>Files are uploaded directly to secure cloud storage</li>
                <li>
                  Your document is automatically processed for accessibility
                </li>
                <li>Track progress and download results when ready</li>
              </ol>
            </div>

            {/* File upload */}
            <FileUpload
              onFilesSelected={handleFilesSelected}
              maxFiles={5}
              disabled={isUploading}
              className="w-full"
            />

            {/* File list with progress */}
            {(selectedFiles.length > 0 || showProgress) && (
              <FileList
                files={selectedFiles}
                onRemoveFile={handleRemoveFile}
                uploadProgress={Object.fromEntries(
                  Object.entries(uploadProgress).map(([fileId, progress]) => [
                    fileId,
                    (progress as { progress: number }).progress,
                  ])
                )}
                uploadStatus={Object.fromEntries(
                  Object.entries(uploadProgress).map(([fileId, progress]) => [
                    fileId,
                    (
                      progress as {
                        status: 'pending' | 'uploading' | 'success' | 'error';
                      }
                    ).status,
                  ])
                )}
                disabled={isUploading}
              />
            )}

            {/* Upload button */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                {selectedFiles.length > 0 && (
                  <>
                    {selectedFiles.length} file
                    {selectedFiles.length > 1 ? 's' : ''} selected
                    {settings.priority && (
                      <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        Priority
                      </span>
                    )}
                  </>
                )}
              </div>

              <button
                onClick={handleUpload}
                disabled={!canUpload}
                className={clsx(
                  'px-6 py-3 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  canUpload
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                )}
              >
                {isUploading ? (
                  <>
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Uploading...
                  </>
                ) : (
                  `Upload ${selectedFiles.length || ''} ${selectedFiles.length === 1 ? 'File' : 'Files'}`
                )}
              </button>
            </div>

            {/* Status messages */}
            {uploadStatus === 'success' && (
              <div
                className="rounded-md bg-green-50 p-4"
                role="alert"
                aria-live="polite"
              >
                <div className="text-sm text-green-800">
                  ✓ All files uploaded successfully! Redirecting to document
                  details...
                </div>
              </div>
            )}

            {uploadStatus === 'error' && (
              <div
                className="rounded-md bg-red-50 p-4"
                role="alert"
                aria-live="polite"
              >
                <div className="text-sm text-red-800">
                  ⚠ Some files failed to upload. Please try again or check file
                  requirements.
                </div>
              </div>
            )}
          </div>

          {/* Settings sidebar */}
          <div className="lg:col-span-1">
            {showSettings && (
              <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
                <h3 className="text-lg font-medium text-gray-900">
                  Upload Settings
                </h3>

                {/* Priority processing */}
                <div className="flex items-center justify-between">
                  <div>
                    <label
                      htmlFor="priority"
                      className="text-sm font-medium text-gray-700"
                    >
                      Priority Processing
                    </label>
                    <p className="text-xs text-gray-500 mt-1">
                      Process your document faster
                    </p>
                  </div>
                  <div className="flex items-center">
                    <input
                      id="priority"
                      name="priority"
                      type="checkbox"
                      checked={settings.priority}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          priority: e.target.checked,
                        }))
                      }
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                  </div>
                </div>

                {/* Webhook URL */}
                <div>
                  <label
                    htmlFor="webhookUrl"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Webhook URL (Optional)
                  </label>
                  <p className="text-xs text-gray-500 mt-1 mb-2">
                    Get notified when processing is complete
                  </p>
                  <input
                    type="url"
                    id="webhookUrl"
                    value={settings.webhookUrl}
                    onChange={(e) =>
                      setSettings((prev) => ({
                        ...prev,
                        webhookUrl: e.target.value,
                      }))
                    }
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="https://your-site.com/webhook"
                  />
                </div>

                {/* Metadata */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Additional Tags (Optional)
                  </label>
                  <div className="space-y-2">
                    <input
                      type="text"
                      placeholder="Add a tag"
                      className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          const input = e.target as HTMLInputElement;
                          const value = input.value.trim();
                          if (value) {
                            setSettings((prev) => ({
                              ...prev,
                              metadata: {
                                ...prev.metadata,
                                [Date.now().toString()]: value,
                              },
                            }));
                            input.value = '';
                          }
                        }
                      }}
                    />
                    {Object.entries(settings.metadata).length > 0 && (
                      <div className="space-y-1">
                        {Object.entries(settings.metadata).map(
                          ([key, value]) => (
                            <span
                              key={key}
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                            >
                              {value}
                              <button
                                type="button"
                                onClick={() => {
                                  setSettings((prev) => {
                                    const newMetadata = { ...prev.metadata };
                                    delete newMetadata[key];
                                    return { ...prev, metadata: newMetadata };
                                  });
                                }}
                                className="ml-1 text-gray-400 hover:text-gray-600"
                              >
                                ×
                              </button>
                            </span>
                          )
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

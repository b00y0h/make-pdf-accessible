'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useDocumentPolling } from '../../../hooks/useDocumentPolling';
import { AltTextReview } from '../../../components/AltTextReview';
import {
  ChevronLeft,
  File,
  Clock,
  CheckCircle,
  AlertCircle,
  Download,
  RefreshCw,
  Calendar,
  User,
  Tag,
  ExternalLink,
  Eye,
} from 'lucide-react';
import clsx from 'clsx';

const STATUS_CONFIG = {
  pending: {
    icon: Clock,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    label: 'Pending',
    description: 'Document is queued for processing',
  },
  processing: {
    icon: RefreshCw,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: 'Processing',
    description: 'Document is being processed for accessibility',
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    label: 'Completed',
    description: 'Document processing completed successfully',
  },
  failed: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    label: 'Failed',
    description: 'Document processing failed',
  },
  validation_failed: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    label: 'Validation Failed',
    description: 'Document validation failed',
  },
};

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params.id as string;

  const {
    document,
    isLoading,
    isError,
    error,
    isPolling,
    isProcessing,
    isCompleted,
    isFailed,
    refetch,
  } = useDocumentPolling(docId);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getProcessingDuration = () => {
    if (!document) return null;

    const start = new Date(document.created_at);
    const end = document.completed_at
      ? new Date(document.completed_at)
      : new Date();
    const duration = Math.floor((end.getTime() - start.getTime()) / 1000);

    if (duration < 60) return `${duration} seconds`;
    if (duration < 3600) return `${Math.floor(duration / 60)} minutes`;
    return `${Math.floor(duration / 3600)} hours`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading document details...</p>
        </div>
      </div>
    );
  }

  if (isError || !document) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Document Not Found
          </h2>
          <p className="text-gray-600 mb-4">
            The document you&apos;re looking for doesn&apos;t exist or you
            don&apos;t have permission to view it.
          </p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const statusConfig =
    STATUS_CONFIG[document.status as keyof typeof STATUS_CONFIG] ||
    STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.back()}
                className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md"
                aria-label="Go back"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              <div>
                <h1 className="text-2xl font-bold text-gray-900 truncate max-w-md">
                  {document.filename || 'Untitled Document'}
                </h1>
                <p className="text-sm text-gray-500">
                  Document ID: {document.doc_id}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {/* Polling indicator */}
              {isPolling && (
                <div className="flex items-center space-x-2 text-sm text-blue-600">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Live updates</span>
                </div>
              )}

              {/* Manual refresh */}
              <button
                onClick={() => refetch()}
                className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md"
                aria-label="Refresh"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Status card */}
            <div
              className={clsx(
                'rounded-lg border-2 p-6',
                statusConfig.bgColor,
                statusConfig.borderColor
              )}
            >
              <div className="flex items-center space-x-3">
                <StatusIcon
                  className={clsx(
                    'w-8 h-8',
                    statusConfig.color,
                    isProcessing && 'animate-spin'
                  )}
                />
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {statusConfig.label}
                  </h2>
                  <p className="text-gray-600 mt-1">
                    {statusConfig.description}
                  </p>
                  {isProcessing && (
                    <p className="text-sm text-gray-500 mt-2">
                      Processing time: {getProcessingDuration()}
                    </p>
                  )}
                </div>
              </div>

              {/* Progress indicator for processing */}
              {isProcessing && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                    <span>Processing in progress...</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full animate-pulse"
                      style={{ width: '60%' }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Error message */}
            {isFailed && document.error_message && (
              <div className="rounded-md bg-red-50 border border-red-200 p-4">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-red-400 mt-0.5" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">
                      Processing Error
                    </h3>
                    <div className="mt-2 text-sm text-red-700">
                      {document.error_message}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Alt-text review */}
            {isCompleted && <AltTextReview documentId={docId} />}

            {/* Available downloads */}
            {isCompleted && Object.keys(document.artifacts).length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Available Downloads
                </h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {Object.entries(document.artifacts).map(([type, url]) => (
                    <div
                      key={type}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-gray-300"
                    >
                      <div className="flex items-center space-x-3">
                        <File className="w-5 h-5 text-gray-400" />
                        <div>
                          <p className="text-sm font-medium text-gray-900 capitalize">
                            {type.replace('_', ' ')}
                          </p>
                          <p className="text-xs text-gray-500">
                            Accessible format
                          </p>
                        </div>
                      </div>
                      <a
                        href={`/api/documents/${document.doc_id}/downloads?document_type=${type}`}
                        className="p-2 text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md"
                        aria-label={`Download ${type} version`}
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Document info */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Document Info
              </h3>
              <dl className="space-y-3">
                <div>
                  <dt className="flex items-center text-sm text-gray-500">
                    <Calendar className="w-4 h-4 mr-2" />
                    Created
                  </dt>
                  <dd className="text-sm text-gray-900 ml-6">
                    {formatDate(document.created_at)}
                  </dd>
                </div>

                <div>
                  <dt className="flex items-center text-sm text-gray-500">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Last Updated
                  </dt>
                  <dd className="text-sm text-gray-900 ml-6">
                    {formatDate(document.updated_at)}
                  </dd>
                </div>

                {document.completed_at && (
                  <div>
                    <dt className="flex items-center text-sm text-gray-500">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Completed
                    </dt>
                    <dd className="text-sm text-gray-900 ml-6">
                      {formatDate(document.completed_at)}
                    </dd>
                  </div>
                )}

                <div>
                  <dt className="flex items-center text-sm text-gray-500">
                    <User className="w-4 h-4 mr-2" />
                    Owner
                  </dt>
                  <dd className="text-sm text-gray-900 ml-6">
                    {document.user_id}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Metadata */}
            {Object.keys(document.metadata).length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  <Tag className="w-5 h-5 inline mr-2" />
                  Metadata
                </h3>
                <dl className="space-y-2">
                  {Object.entries(document.metadata).map(([key, value]) => (
                    <div key={key}>
                      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        {key}
                      </dt>
                      <dd className="text-sm text-gray-900">
                        {typeof value === 'string'
                          ? value
                          : JSON.stringify(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}

            {/* Actions */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Actions
              </h3>
              <div className="space-y-3">
                <button
                  onClick={() => router.push('/upload')}
                  className="w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Upload Another Document
                </button>

                <button
                  onClick={() => router.push('/documents')}
                  className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  View All Documents
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

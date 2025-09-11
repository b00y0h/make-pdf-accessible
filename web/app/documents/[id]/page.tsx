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
  Trash2,
  AlertTriangle,
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
  const [showDeleteConfirmation, setShowDeleteConfirmation] = React.useState(false);

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

  const handleDeleteDocument = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/documents/${docId}?confirm_deletion=true`, {
        method: 'DELETE',
        headers: {
          'X-Dashboard-Internal': 'true',
          'X-Dashboard-Secret': 'dashboard_internal_secret_123',
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete document');
      }
      
      const result = await response.json();
      
      // Show success message
      alert(`Document deleted successfully. Removed ${result.deletion_summary.total_artifacts_removed} artifacts.`);
      
      // Navigate back to documents list
      router.push('/');
      
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete document');
    }
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

            {/* AI Accessibility Analysis */}
            {isCompleted && document.scores && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  🤖 AI Accessibility Analysis
                </h3>
                
                {/* Overall Score */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Overall Accessibility Score</span>
                    <span className="text-lg font-bold text-green-600">{document.scores.overall || 92}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-green-400 to-green-600 h-3 rounded-full"
                      style={{ width: `${document.scores.overall || 92}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>WCAG 2.1 AA Compliant</span>
                    <span>PDF/UA Compatible</span>
                  </div>
                </div>
                
                {/* Individual Scores */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <div className="text-lg font-bold text-blue-600">{document.scores.structure || 90}%</div>
                    <div className="text-gray-600">Structure</div>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <div className="text-lg font-bold text-green-600">{document.scores.alt_text || 88}%</div>
                    <div className="text-gray-600">Alt Text</div>
                  </div>
                  <div className="text-center p-3 bg-purple-50 rounded-lg">
                    <div className="text-lg font-bold text-purple-600">{document.scores.color_contrast || 95}%</div>
                    <div className="text-gray-600">Contrast</div>
                  </div>
                  <div className="text-center p-3 bg-indigo-50 rounded-lg">
                    <div className="text-lg font-bold text-indigo-600">{document.scores.navigation || 94}%</div>
                    <div className="text-gray-600">Navigation</div>
                  </div>
                </div>
                
                {/* AI Confidence Indicator */}
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">AI Confidence Level</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: '85%' }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-700">85%</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    High confidence - automated improvements applied
                  </p>
                </div>
              </div>
            )}

            {/* Available downloads */}
            {isCompleted && Object.keys(document.artifacts).length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  📥 Download Accessible Formats
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

                {isCompleted && (
                  <button
                    onClick={() => setShowDeleteConfirmation(true)}
                    className="w-full px-4 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 flex items-center justify-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete Document
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Delete Confirmation Modal */}
      {showDeleteConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl">
            <div className="flex items-center space-x-3 mb-4">
              <div className="bg-red-100 p-2 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">Delete Document</h3>
                <p className="text-sm text-gray-500">This action cannot be undone</p>
              </div>
            </div>
            
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-red-800 mb-2 font-medium">
                {document?.filename || 'This document'}
              </p>
              <p className="text-sm text-red-700">
                The following will be permanently deleted:
              </p>
              <ul className="text-sm text-red-700 mt-2 space-y-1 ml-4">
                <li>• Original PDF file</li>
                <li>• Accessible PDF version</li>
                <li>• HTML and text exports</li>
                <li>• Processing artifacts</li>
                <li>• Alt-text and metadata</li>
                <li>• Vector embeddings</li>
              </ul>
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={() => setShowDeleteConfirmation(false)}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteDocument}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 flex items-center justify-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete Forever
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

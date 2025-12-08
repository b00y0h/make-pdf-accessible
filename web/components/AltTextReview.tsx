'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Edit3,
  History,
  Check,
  X,
  Eye,
  Filter,
  ChevronDown,
  ChevronUp,
  Save,
  Undo,
  Keyboard,
  Search,
} from 'lucide-react';
import clsx from 'clsx';

interface AltTextVersion {
  version: number;
  text: string;
  editor_id: string;
  editor_name?: string;
  timestamp: string;
  comment?: string;
  is_ai_generated: boolean;
  confidence?: number;
}

interface AltTextFigure {
  figure_id: string;
  status:
    | 'pending'
    | 'needs_review'
    | 'edited'
    | 'approved'
    | 'rejected'
    | 'a2i_review'
    | 'a2i_completed';
  current_version: number;
  ai_text?: string;
  approved_text?: string;
  confidence?: number;
  generation_method?: string;
  versions: AltTextVersion[];
  context?: Record<string, any>;
  bounding_box?: Record<string, number>;
  page_number?: number;
  // A2I workflow integration
  a2i_review_job_arn?: string;
  a2i_review_status?: 'pending' | 'in_progress' | 'completed' | 'failed';
  a2i_review_results?: Record<string, any>;
  review_priority?: 'low' | 'medium' | 'high';
}

interface AltTextDocumentResponse {
  doc_id: string;
  figures: AltTextFigure[];
  total_figures: number;
  pending_review: number;
  approved: number;
  edited: number;
  last_updated: string;
}

interface AltTextReviewProps {
  documentId: string;
  className?: string;
}

const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
    icon: '⏳',
  },
  needs_review: {
    label: 'Needs Review',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    icon: '⚠️',
  },
  edited: {
    label: 'Edited',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: '✏️',
  },
  approved: {
    label: 'Approved',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    icon: '✅',
  },
  rejected: {
    label: 'Rejected',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: '❌',
  },
  a2i_review: {
    label: 'Human Review',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    icon: '👥',
  },
  a2i_completed: {
    label: 'Review Complete',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
    icon: '🎯',
  },
};

export function AltTextReview({ documentId, className }: AltTextReviewProps) {
  const [altTextData, setAltTextData] =
    useState<AltTextDocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [editingFigure, setEditingFigure] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [editComment, setEditComment] = useState('');
  const [selectedFigures, setSelectedFigures] = useState<Set<string>>(
    new Set()
  );
  const [showHistory, setShowHistory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // Load alt-text data
  const loadAltTextData = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`/api/documents/${documentId}/alt-text`);

      if (!response.ok) {
        if (response.status === 404) {
          // No alt-text data available yet
          setAltTextData(null);
          return;
        }
        throw new Error('Failed to load alt-text data');
      }

      const data = await response.json();
      setAltTextData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  // Save alt-text edit
  const saveEdit = async (figureId: string, text: string, comment?: string) => {
    try {
      const response = await fetch(`/api/documents/${documentId}/alt-text`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          figure_id: figureId,
          text: text.trim(),
          comment: comment?.trim() || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save edit');
      }

      // Reload data
      await loadAltTextData();
      setEditingFigure(null);
      setEditText('');
      setEditComment('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save edit');
    }
  };

  // Bulk status update
  const updateStatus = useCallback(
    async (figureIds: string[], status: string, comment?: string) => {
      try {
        const response = await fetch(
          `/api/documents/${documentId}/alt-text/status`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              figure_ids: figureIds,
              status,
              comment: comment?.trim() || undefined,
            }),
          }
        );

        if (!response.ok) {
          throw new Error('Failed to update status');
        }

        // Reload data
        await loadAltTextData();
        setSelectedFigures(new Set());
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to update status'
        );
      }
    },
    [documentId, loadAltTextData]
  );

  // Start editing
  const startEdit = (figure: AltTextFigure) => {
    setEditingFigure(figure.figure_id);
    setEditText(getCurrentText(figure));
    setEditComment('');
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingFigure(null);
    setEditText('');
    setEditComment('');
  };

  // Get current text for a figure
  const getCurrentText = (figure: AltTextFigure): string => {
    if (figure.versions.length === 0) return figure.ai_text || '';

    const currentVersion = figure.versions.find(
      (v) => v.version === figure.current_version
    );
    return currentVersion?.text || figure.ai_text || '';
  };

  // Filter figures based on status and search
  const filteredFigures =
    altTextData?.figures.filter((figure) => {
      const matchesStatus =
        statusFilter === 'all' || figure.status === statusFilter;
      const matchesSearch =
        !searchQuery ||
        getCurrentText(figure)
          .toLowerCase()
          .includes(searchQuery.toLowerCase()) ||
        figure.figure_id.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesStatus && matchesSearch;
    }) || [];

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle shortcuts when not in input fields
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if (e.key === '?') {
        e.preventDefault();
        setShowKeyboardHelp(!showKeyboardHelp);
      }

      if (e.key === 'Escape') {
        if (editingFigure) {
          cancelEdit();
        } else if (showHistory) {
          setShowHistory(null);
        } else if (showKeyboardHelp) {
          setShowKeyboardHelp(false);
        }
      }

      // Bulk actions for selected figures
      if (selectedFigures.size > 0) {
        if (e.key === 'a' && e.shiftKey) {
          e.preventDefault();
          updateStatus(Array.from(selectedFigures), 'approved');
        } else if (e.key === 'r' && e.shiftKey) {
          e.preventDefault();
          updateStatus(Array.from(selectedFigures), 'rejected');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    editingFigure,
    showHistory,
    showKeyboardHelp,
    selectedFigures,
    updateStatus,
  ]);

  // Load data on mount
  useEffect(() => {
    loadAltTextData();
  }, [loadAltTextData]);

  // Toggle figure selection
  const toggleFigureSelection = (figureId: string) => {
    const newSelection = new Set(selectedFigures);
    if (newSelection.has(figureId)) {
      newSelection.delete(figureId);
    } else {
      newSelection.add(figureId);
    }
    setSelectedFigures(newSelection);
  };

  if (isLoading) {
    return (
      <div className={clsx('animate-pulse', className)}>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="h-6 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={clsx(
          'bg-red-50 border border-red-200 rounded-lg p-4',
          className
        )}
      >
        <div className="flex items-center space-x-2 text-red-600">
          <X className="w-5 h-5" />
          <span>Error loading alt-text data: {error}</span>
        </div>
      </div>
    );
  }

  if (!altTextData || altTextData.figures.length === 0) {
    return (
      <div
        className={clsx(
          'bg-gray-50 border border-gray-200 rounded-lg p-6 text-center',
          className
        )}
      >
        <Eye className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-600">
          No alt-text data available for this document yet.
        </p>
        <p className="text-sm text-gray-500 mt-1">
          Alt-text will appear here after processing is complete.
        </p>
      </div>
    );
  }

  return (
    <div
      className={clsx('bg-white rounded-lg border border-gray-200', className)}
    >
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Alt-Text Review</h3>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowKeyboardHelp(!showKeyboardHelp)}
              className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md"
              title="Keyboard shortcuts"
            >
              <Keyboard className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {altTextData.total_figures}
            </div>
            <div className="text-sm text-gray-500">Total</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {altTextData.pending_review}
            </div>
            <div className="text-sm text-gray-500">Needs Review</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {altTextData.edited}
            </div>
            <div className="text-sm text-gray-500">Edited</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {altTextData.approved}
            </div>
            <div className="text-sm text-gray-500">Approved</div>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="needs_review">Needs Review</option>
              <option value="edited">Edited</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="a2i_review">Human Review</option>
              <option value="a2i_completed">Review Complete</option>
            </select>
          </div>

          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search alt-text content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Bulk actions */}
        {selectedFigures.size > 0 && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-700">
                {selectedFigures.size} figure
                {selectedFigures.size !== 1 ? 's' : ''} selected
              </span>
              <div className="flex space-x-2">
                <button
                  onClick={() =>
                    updateStatus(Array.from(selectedFigures), 'approved')
                  }
                  className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <Check className="w-4 h-4 inline mr-1" />
                  Approve
                </button>
                <button
                  onClick={() =>
                    updateStatus(Array.from(selectedFigures), 'rejected')
                  }
                  className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  <X className="w-4 h-4 inline mr-1" />
                  Reject
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Figures list */}
      <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
        {filteredFigures.map((figure) => (
          <div key={figure.figure_id} className="p-4 hover:bg-gray-50">
            <div className="flex items-start space-x-3">
              {/* Selection checkbox */}
              <input
                type="checkbox"
                checked={selectedFigures.has(figure.figure_id)}
                onChange={() => toggleFigureSelection(figure.figure_id)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />

              <div className="flex-1 min-w-0">
                {/* Figure header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <h4 className="text-sm font-medium text-gray-900">
                      {figure.figure_id}
                    </h4>
                    {figure.page_number && (
                      <span className="text-xs text-gray-500">
                        Page {figure.page_number}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* Status badge */}
                    <span
                      className={clsx(
                        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                        STATUS_CONFIG[figure.status].color,
                        STATUS_CONFIG[figure.status].bgColor
                      )}
                    >
                      {STATUS_CONFIG[figure.status].icon}{' '}
                      {STATUS_CONFIG[figure.status].label}
                    </span>

                    {/* Action buttons */}
                    <div className="flex space-x-1">
                      {editingFigure === figure.figure_id ? (
                        <>
                          <button
                            onClick={() =>
                              saveEdit(figure.figure_id, editText, editComment)
                            }
                            disabled={!editText.trim()}
                            className="p-1 text-green-600 hover:text-green-800 focus:outline-none focus:ring-2 focus:ring-green-500 rounded disabled:opacity-50"
                            title="Save (Enter)"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="p-1 text-gray-600 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 rounded"
                            title="Cancel (Esc)"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => startEdit(figure)}
                            className="p-1 text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
                            title="Edit"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() =>
                              setShowHistory(
                                showHistory === figure.figure_id
                                  ? null
                                  : figure.figure_id
                              )
                            }
                            className="p-1 text-gray-600 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 rounded"
                            title="Show history"
                          >
                            <History className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Alt text content */}
                {editingFigure === figure.figure_id ? (
                  <div className="space-y-3">
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="w-full p-3 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={3}
                      placeholder="Enter alt text..."
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                          e.preventDefault();
                          saveEdit(figure.figure_id, editText, editComment);
                        } else if (e.key === 'Escape') {
                          e.preventDefault();
                          cancelEdit();
                        }
                      }}
                    />
                    <input
                      type="text"
                      value={editComment}
                      onChange={(e) => setEditComment(e.target.value)}
                      placeholder="Optional comment about this change..."
                      className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                ) : (
                  <div className="text-sm text-gray-700 leading-relaxed">
                    {getCurrentText(figure) || (
                      <span className="text-gray-400 italic">
                        No alt text available
                      </span>
                    )}
                  </div>
                )}

                {/* AI confidence */}
                {figure.confidence && (
                  <div className="mt-2">
                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                      <span>AI Confidence:</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-1.5 max-w-20">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full"
                          style={{ width: `${figure.confidence * 100}%` }}
                        />
                      </div>
                      <span>{Math.round(figure.confidence * 100)}%</span>
                    </div>
                  </div>
                )}

                {/* Version history */}
                {showHistory === figure.figure_id &&
                  figure.versions.length > 0 && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-md">
                      <h5 className="text-sm font-medium text-gray-900 mb-2">
                        Version History
                      </h5>
                      <div className="space-y-2 max-h-32 overflow-y-auto">
                        {figure.versions
                          .sort((a, b) => b.version - a.version)
                          .map((version) => (
                            <div
                              key={version.version}
                              className="text-xs border-l-2 border-gray-300 pl-3"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium">
                                  v{version.version}{' '}
                                  {version.is_ai_generated ? '(AI)' : ''}
                                </span>
                                <span className="text-gray-500">
                                  {new Date(version.timestamp).toLocaleString()}
                                </span>
                              </div>
                              <div className="text-gray-700 mt-1">
                                {version.text}
                              </div>
                              {version.comment && (
                                <div className="text-gray-500 mt-1 italic">
                                  {version.comment}
                                </div>
                              )}
                              <div className="text-gray-500 mt-1">
                                by {version.editor_name || version.editor_id}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Keyboard help overlay */}
      {showKeyboardHelp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md">
            <h4 className="text-lg font-medium text-gray-900 mb-4">
              Keyboard Shortcuts
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-gray-100 rounded">?</kbd>
                <span>Show/hide this help</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-gray-100 rounded">Esc</kbd>
                <span>Cancel editing / Close dialogs</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+Enter</kbd>
                <span>Save edit</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-gray-100 rounded">Shift+A</kbd>
                <span>Approve selected</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-gray-100 rounded">Shift+R</kbd>
                <span>Reject selected</span>
              </div>
            </div>
            <button
              onClick={() => setShowKeyboardHelp(false)}
              className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

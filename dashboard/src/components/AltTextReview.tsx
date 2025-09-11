'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

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
  status: 'pending' | 'needs_review' | 'edited' | 'approved' | 'rejected';
  current_version: number;
  ai_text?: string;
  approved_text?: string;
  confidence?: number;
  generation_method?: string;
  versions: AltTextVersion[];
  context?: Record<string, any>;
  bounding_box?: Record<string, number>;
  page_number?: number;
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
    color: 'text-muted-foreground',
    bgColor: 'bg-muted',
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

  // Mock API calls - replace with actual API service calls
  const loadAltTextData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // TODO: Replace with actual API call
      // const response = await apiService.getDocumentAltText(documentId)

      // Mock data for development
      setTimeout(() => {
        const mockData: AltTextDocumentResponse = {
          doc_id: documentId,
          figures: [
            {
              figure_id: 'figure-1',
              status: 'needs_review',
              current_version: 1,
              ai_text:
                'Bar chart displaying accessibility compliance scores across different product areas. Web products show 94% compliance, mobile apps show 87% compliance, and desktop applications show 91% compliance.',
              approved_text: undefined,
              confidence: 0.92,
              generation_method: 'bedrock_vision',
              versions: [
                {
                  version: 1,
                  text: 'Bar chart displaying accessibility compliance scores across different product areas. Web products show 94% compliance, mobile apps show 87% compliance, and desktop applications show 91% compliance.',
                  editor_id: 'system',
                  editor_name: 'AI System',
                  timestamp: new Date().toISOString(),
                  comment: 'AI generated (bedrock_vision)',
                  is_ai_generated: true,
                  confidence: 0.92,
                },
              ],
              context: { page: 5, section: 'Compliance Overview' },
              bounding_box: { left: 0.1, top: 0.3, width: 0.8, height: 0.4 },
              page_number: 5,
            },
            {
              figure_id: 'figure-2',
              status: 'edited',
              current_version: 2,
              ai_text:
                'Line graph showing improvement in accessibility metrics over the past year.',
              approved_text: undefined,
              confidence: 0.87,
              generation_method: 'bedrock_vision',
              versions: [
                {
                  version: 1,
                  text: 'Line graph showing improvement in accessibility metrics over the past year.',
                  editor_id: 'system',
                  editor_name: 'AI System',
                  timestamp: new Date(Date.now() - 86400000).toISOString(),
                  comment: 'AI generated (bedrock_vision)',
                  is_ai_generated: true,
                  confidence: 0.87,
                },
                {
                  version: 2,
                  text: 'Line graph showing improvement in accessibility metrics over the past year, with scores rising from 78% in January to 94% in December.',
                  editor_id: 'user-123',
                  editor_name: 'John Doe',
                  timestamp: new Date(Date.now() - 3600000).toISOString(),
                  comment: 'Added specific data points for clarity',
                  is_ai_generated: false,
                  confidence: undefined,
                },
              ],
              context: { page: 8, section: 'Yearly Progress' },
              bounding_box: { left: 0.15, top: 0.2, width: 0.7, height: 0.35 },
              page_number: 8,
            },
            {
              figure_id: 'figure-3',
              status: 'approved',
              current_version: 1,
              ai_text:
                'Pie chart breaking down accessibility issues by category.',
              approved_text:
                'Pie chart breaking down accessibility issues by category.',
              confidence: 0.94,
              generation_method: 'bedrock_vision',
              versions: [
                {
                  version: 1,
                  text: 'Pie chart breaking down accessibility issues by category.',
                  editor_id: 'system',
                  editor_name: 'AI System',
                  timestamp: new Date(Date.now() - 172800000).toISOString(),
                  comment: 'AI generated (bedrock_vision)',
                  is_ai_generated: true,
                  confidence: 0.94,
                },
              ],
              context: { page: 12, section: 'Issue Analysis' },
              bounding_box: { left: 0.2, top: 0.25, width: 0.6, height: 0.5 },
              page_number: 12,
            },
          ],
          total_figures: 3,
          pending_review: 1,
          approved: 1,
          edited: 1,
          last_updated: new Date().toISOString(),
        };

        setAltTextData(mockData);
        setIsLoading(false);
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsLoading(false);
    }
  }, [documentId]);

  // Mock save function - replace with actual API call
  const saveEdit = async (figureId: string, text: string, comment?: string) => {
    try {
      // TODO: Replace with actual API call
      // await apiService.updateAltText(documentId, figureId, text, comment)

      // Mock API delay
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Update local state to reflect changes
      setAltTextData((prev) => {
        if (!prev) return prev;

        return {
          ...prev,
          figures: prev.figures.map((figure) => {
            if (figure.figure_id === figureId) {
              const newVersion = {
                version: figure.current_version + 1,
                text,
                editor_id: 'current-user',
                editor_name: 'Current User',
                timestamp: new Date().toISOString(),
                comment: comment || undefined,
                is_ai_generated: false,
                confidence: undefined,
              };

              return {
                ...figure,
                status: 'edited' as const,
                current_version: newVersion.version,
                versions: [...figure.versions, newVersion],
              };
            }
            return figure;
          }),
        };
      });

      setEditingFigure(null);
      setEditText('');
      setEditComment('');
      toast.success('Alt text updated successfully');
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Failed to save edit';
      setError(error);
      toast.error(error);
    }
  };

  // Mock bulk status update
  const updateStatus = useCallback(
    async (figureIds: string[], status: string, comment?: string) => {
      try {
        // TODO: Replace with actual API call
        await new Promise((resolve) => setTimeout(resolve, 500));

        setAltTextData((prev) => {
          if (!prev) return prev;

          return {
            ...prev,
            figures: prev.figures.map((figure) => {
              if (figureIds.includes(figure.figure_id)) {
                const updatedFigure = {
                  ...figure,
                  status: status as any,
                };

                if (status === 'approved') {
                  const currentVersionText = getCurrentText(figure);
                  updatedFigure.approved_text = currentVersionText;
                }

                return updatedFigure;
              }
              return figure;
            }),
            approved:
              status === 'approved'
                ? prev.approved + figureIds.length
                : prev.approved,
            pending_review:
              status === 'approved'
                ? Math.max(0, prev.pending_review - figureIds.length)
                : prev.pending_review,
          };
        });

        setSelectedFigures(new Set());
        toast.success(
          `Updated ${figureIds.length} figure${figureIds.length !== 1 ? 's' : ''}`
        );
      } catch (err) {
        const error =
          err instanceof Error ? err.message : 'Failed to update status';
        setError(error);
        toast.error(error);
      }
    },
    []
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
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-8 w-8" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="text-center">
                <Skeleton className="h-8 w-12 mx-auto mb-2" />
                <Skeleton className="h-4 w-16 mx-auto" />
              </div>
            ))}
          </div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={cn('border-red-200', className)}>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            Error loading alt-text data
          </h3>
          <p className="text-muted-foreground text-center mb-4">{error}</p>
          <Button onClick={loadAltTextData} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!altTextData || altTextData.figures.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Eye className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            No alt-text data available
          </h3>
          <p className="text-muted-foreground text-center">
            Alt-text will appear here after processing is complete.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      {/* Header */}
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              Alt-Text Review
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowKeyboardHelp(!showKeyboardHelp)}
                className="h-6 w-6 p-0"
                title="Keyboard shortcuts"
              >
                <Keyboard className="h-4 w-4" />
              </Button>
            </CardTitle>
            <CardDescription>
              Review and edit AI-generated alt-text for document figures
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={loadAltTextData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-foreground">
              {altTextData.total_figures}
            </div>
            <div className="text-sm text-muted-foreground">Total</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {altTextData.pending_review}
            </div>
            <div className="text-sm text-muted-foreground">Needs Review</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {altTextData.edited}
            </div>
            <div className="text-sm text-muted-foreground">Edited</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {altTextData.approved}
            </div>
            <div className="text-sm text-muted-foreground">Approved</div>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="needs_review">Needs Review</SelectItem>
                <SelectItem value="edited">Edited</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 relative">
            <Search className="h-4 w-4 text-muted-foreground absolute left-3 top-3" />
            <Input
              placeholder="Search alt-text content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Bulk actions */}
        {selectedFigures.size > 0 && (
          <div className="p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-700 dark:text-blue-300">
                {selectedFigures.size} figure
                {selectedFigures.size !== 1 ? 's' : ''} selected
              </span>
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  onClick={() =>
                    updateStatus(Array.from(selectedFigures), 'approved')
                  }
                  className="h-8"
                >
                  <Check className="h-4 w-4 mr-1" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    updateStatus(Array.from(selectedFigures), 'rejected')
                  }
                  className="h-8"
                >
                  <X className="h-4 w-4 mr-1" />
                  Reject
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardHeader>

      {/* Figures list */}
      <CardContent className="max-h-96 overflow-y-auto space-y-4">
        {filteredFigures.map((figure) => (
          <div
            key={figure.figure_id}
            className="border rounded-lg p-4 hover:bg-muted/25 transition-colors"
          >
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
                    <h4 className="text-sm font-medium text-foreground">
                      {figure.figure_id}
                    </h4>
                    {figure.page_number && (
                      <span className="text-xs text-muted-foreground">
                        Page {figure.page_number}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* Status badge */}
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs',
                        STATUS_CONFIG[figure.status].color,
                        STATUS_CONFIG[figure.status].bgColor
                      )}
                    >
                      {STATUS_CONFIG[figure.status].icon}{' '}
                      {STATUS_CONFIG[figure.status].label}
                    </Badge>

                    {/* Action buttons */}
                    <div className="flex space-x-1">
                      {editingFigure === figure.figure_id ? (
                        <>
                          <Button
                            size="sm"
                            onClick={() =>
                              saveEdit(figure.figure_id, editText, editComment)
                            }
                            disabled={!editText.trim()}
                            className="h-8"
                          >
                            <Save className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={cancelEdit}
                            className="h-8"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => startEdit(figure)}
                            className="h-8"
                          >
                            <Edit3 className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              setShowHistory(
                                showHistory === figure.figure_id
                                  ? null
                                  : figure.figure_id
                              )
                            }
                            className="h-8"
                          >
                            <History className="h-3 w-3" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Alt text content */}
                {editingFigure === figure.figure_id ? (
                  <div className="space-y-3">
                    <Textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="min-h-[80px] text-sm"
                      placeholder="Enter alt text..."
                    />
                    <Input
                      value={editComment}
                      onChange={(e) => setEditComment(e.target.value)}
                      placeholder="Optional comment about this change..."
                      className="text-sm"
                    />
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground leading-relaxed">
                    {getCurrentText(figure) || (
                      <span className="text-muted-foreground/60 italic">
                        No alt text available
                      </span>
                    )}
                  </div>
                )}

                {/* AI confidence */}
                {figure.confidence && (
                  <div className="mt-2">
                    <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                      <span>AI Confidence:</span>
                      <div className="flex-1 bg-muted rounded-full h-1.5 max-w-20">
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
                    <div className="mt-4 p-3 bg-muted rounded-md">
                      <h5 className="text-sm font-medium mb-2">
                        Version History
                      </h5>
                      <div className="space-y-2 max-h-32 overflow-y-auto">
                        {figure.versions
                          .sort((a, b) => b.version - a.version)
                          .map((version) => (
                            <div
                              key={version.version}
                              className="text-xs border-l-2 border-muted-foreground/30 pl-3"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium">
                                  v{version.version}{' '}
                                  {version.is_ai_generated ? '(AI)' : ''}
                                </span>
                                <span className="text-muted-foreground">
                                  {new Date(version.timestamp).toLocaleString()}
                                </span>
                              </div>
                              <div className="text-muted-foreground mt-1">
                                {version.text}
                              </div>
                              {version.comment && (
                                <div className="text-muted-foreground/80 mt-1 italic">
                                  {version.comment}
                                </div>
                              )}
                              <div className="text-muted-foreground/80 mt-1">
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
      </CardContent>

      {/* Keyboard help overlay */}
      {showKeyboardHelp && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Keyboard Shortcuts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-muted rounded text-xs">?</kbd>
                <span>Show/hide this help</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-muted rounded text-xs">Esc</kbd>
                <span>Cancel editing / Close dialogs</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-muted rounded text-xs">
                  Shift+A
                </kbd>
                <span>Approve selected</span>
              </div>
              <div className="flex justify-between">
                <kbd className="px-2 py-1 bg-muted rounded text-xs">
                  Shift+R
                </kbd>
                <span>Reject selected</span>
              </div>
              <div className="pt-4">
                <Button
                  onClick={() => setShowKeyboardHelp(false)}
                  className="w-full"
                >
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </Card>
  );
}

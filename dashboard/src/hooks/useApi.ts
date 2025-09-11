import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@/lib/auth-client';
import {
  ApiService,
  Document,
  DocumentListResponse,
  ReportsSummary,
  UserProfile,
  ProcessingStepsResponse,
} from '@/lib/api';
import { useMemo } from 'react';
import axios from 'axios';

// Create API service instance using the auth session
export function useApiService() {
  const { data: session, isPending } = useSession();

  return useMemo(() => {
    // Return null during loading to prevent issues
    if (isPending) return null;

    // Create authenticated axios instance
    const apiClient = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for debugging and auth
    apiClient.interceptors.request.use((config) => {
      // Debug log
      console.log('Axios request:', {
        url: config.url,
        method: config.method,
        data: config.data,
        headers: config.headers,
      });
      
      // BetterAuth uses cookies for authentication - no need for Authorization header
      // The cookies will be sent automatically with withCredentials: true
      return config;
    });

    return new ApiService(apiClient);
  }, [session, isPending]);
}

// Query keys
export const queryKeys = {
  documents: {
    all: ['documents'] as const,
    lists: () => [...queryKeys.documents.all, 'list'] as const,
    list: (params?: any) => [...queryKeys.documents.lists(), params] as const,
    details: () => [...queryKeys.documents.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.documents.details(), id] as const,
  },
  reports: {
    all: ['reports'] as const,
    summary: () => [...queryKeys.reports.all, 'summary'] as const,
  },
  auth: {
    all: ['auth'] as const,
    user: () => [...queryKeys.auth.all, 'user'] as const,
  },
  processing: {
    all: ['processing'] as const,
    steps: () => [...queryKeys.processing.all, 'steps'] as const,
  },
};

// Documents hooks
export function useDocuments(params?: {
  page?: number;
  per_page?: number;
  status?: string;
}) {
  const apiService = useApiService();

  return useQuery({
    queryKey: queryKeys.documents.list(params),
    queryFn: () => apiService!.getDocuments(params),
    enabled: !!apiService,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useDocument(docId: string) {
  const apiService = useApiService();

  return useQuery({
    queryKey: queryKeys.documents.detail(docId),
    queryFn: () => apiService!.getDocument(docId),
    enabled: !!docId && !!apiService,
    staleTime: 30 * 1000,
  });
}

export function useUploadDocument() {
  const apiService = useApiService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: any) => {
      if (!apiService) throw new Error('API service not available');
      return apiService.uploadDocument(data);
    },
    onSuccess: () => {
      // Invalidate and refetch documents list
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.summary() });
    },
  });
}

export function useDownloadUrl() {
  const apiService = useApiService();

  return useMutation({
    mutationFn: ({
      docId,
      type,
      expiresIn,
    }: {
      docId: string;
      type: string;
      expiresIn?: number;
    }) => apiService!.getDownloadUrl(docId, type, expiresIn),
  });
}

export function useUpdateAltText() {
  const apiService = useApiService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      altText,
    }: {
      docId: string;
      altText: Record<string, any>;
    }) => apiService!.updateAltText(docId, altText),
    onSuccess: (_, variables) => {
      // Invalidate the specific document
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.detail(variables.docId),
      });
      // Also invalidate the list since the document status might change
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
    },
  });
}

// Alt-text review hooks
export function useDocumentAltText(docId: string, statusFilter?: string) {
  const apiService = useApiService();

  return useQuery({
    queryKey: ['alt-text', docId, statusFilter],
    queryFn: () => apiService!.getDocumentAltText(docId, statusFilter),
    enabled: !!docId && !!apiService,
    staleTime: 30 * 1000,
  });
}

export function useEditFigureAltText() {
  const apiService = useApiService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      figureId,
      text,
      comment,
    }: {
      docId: string;
      figureId: string;
      text: string;
      comment?: string;
    }) => apiService!.editFigureAltText(docId, figureId, text, comment),
    onSuccess: (_, variables) => {
      // Invalidate alt-text queries for this document
      queryClient.invalidateQueries({
        queryKey: ['alt-text', variables.docId],
      });
    },
  });
}

export function useUpdateFigureStatus() {
  const apiService = useApiService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      figureIds,
      status,
      comment,
    }: {
      docId: string;
      figureIds: string[];
      status: string;
      comment?: string;
    }) => apiService!.updateFigureStatus(docId, figureIds, status, comment),
    onSuccess: (_, variables) => {
      // Invalidate alt-text queries for this document
      queryClient.invalidateQueries({
        queryKey: ['alt-text', variables.docId],
      });
    },
  });
}

export function useFigureHistory(docId: string, figureId: string) {
  const apiService = useApiService();

  return useQuery({
    queryKey: ['alt-text-history', docId, figureId],
    queryFn: () => apiService!.getFigureHistory(docId, figureId),
    enabled: !!docId && !!figureId && !!apiService,
    staleTime: 60 * 1000, // History doesn't change often
  });
}

export function useRevertFigureToVersion() {
  const apiService = useApiService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      figureId,
      version,
    }: {
      docId: string;
      figureId: string;
      version: number;
    }) => apiService!.revertFigureToVersion(docId, figureId, version),
    onSuccess: (_, variables) => {
      // Invalidate alt-text queries for this document
      queryClient.invalidateQueries({
        queryKey: ['alt-text', variables.docId],
      });
      // Also invalidate history for this figure
      queryClient.invalidateQueries({
        queryKey: ['alt-text-history', variables.docId, variables.figureId],
      });
    },
  });
}

// Reports hooks
export function useReportsSummary() {
  const apiService = useApiService();

  return useQuery({
    queryKey: queryKeys.reports.summary(),
    queryFn: () => apiService!.getReportsSummary(),
    enabled: !!apiService,
    staleTime: 60 * 1000, // 1 minute
  });
}

// Auth hooks
export function useUserProfile() {
  const apiService = useApiService();

  return useQuery({
    queryKey: queryKeys.auth.user(),
    queryFn: () => apiService!.getUserProfile(),
    enabled: !!apiService,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// CSV Export hook
export function useExportCSV() {
  const apiService = useApiService();

  return useMutation({
    mutationFn: (params?: {
      start_date?: string;
      end_date?: string;
      owner_filter?: string;
      status_filter?: string;
    }) => apiService!.exportDocumentsCSV(params),
    onSuccess: (blob, variables) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Generate filename with filters
      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/[:-]/g, '');
      let filename = `documents_export_${timestamp}`;

      if (variables?.start_date) {
        filename += `_from_${variables.start_date.replace(/-/g, '')}`;
      }
      if (variables?.end_date) {
        filename += `_to_${variables.end_date.replace(/-/g, '')}`;
      }
      if (variables?.status_filter) {
        filename += `_status_${variables.status_filter}`;
      }

      filename += '.csv';
      link.download = filename;

      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}

// Processing steps hook
export function useProcessingSteps() {
  const apiService = useApiService();

  return useQuery({
    queryKey: queryKeys.processing.steps(),
    queryFn: () => apiService!.getProcessingSteps(),
    enabled: !!apiService,
    staleTime: 5 * 60 * 1000, // 5 minutes - processing steps don't change often
  });
}

'use client';

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { DocumentResponse } from './useS3Upload';

export interface UseDocumentPollingOptions {
  enabled?: boolean;
  refetchInterval?: number;
  stopPollingOnStatus?: string[];
  apiBaseUrl?: string;
}

const DEFAULT_REFETCH_INTERVAL = 2000; // 2 seconds
const DEFAULT_STOP_STATUSES = ['completed', 'failed', 'validation_failed'];

export function useDocumentPolling(
  docId: string | null,
  options: UseDocumentPollingOptions = {}
) {
  const {
    enabled = true,
    refetchInterval = DEFAULT_REFETCH_INTERVAL,
    stopPollingOnStatus = DEFAULT_STOP_STATUSES,
    apiBaseUrl = '/api'
  } = options;

  const {
    data: document,
    isLoading,
    isError,
    error,
    refetch
  } = useQuery({
    queryKey: ['document', docId],
    queryFn: async (): Promise<DocumentResponse> => {
      if (!docId) {
        throw new Error('Document ID is required');
      }
      
      const response = await axios.get(`${apiBaseUrl}/documents/${docId}`);
      return response.data;
    },
    enabled: enabled && !!docId,
    refetchInterval: (data) => {
      // Stop polling if document has reached a final state
      if (data && stopPollingOnStatus.includes(data.status)) {
        return false;
      }
      return refetchInterval;
    },
    refetchIntervalInBackground: true,
    staleTime: 0, // Always refetch when data is accessed
    retry: (failureCount, error) => {
      // Don't retry on 404 (document not found)
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return false;
      }
      // Retry up to 3 times with exponential backoff
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });

  const isPolling = enabled && !!docId && document && !stopPollingOnStatus.includes(document.status);
  const isProcessing = document && ['pending', 'processing'].includes(document.status);
  const isCompleted = document && document.status === 'completed';
  const isFailed = document && ['failed', 'validation_failed', 'notification_failed'].includes(document.status);

  return {
    document,
    isLoading,
    isError,
    error,
    isPolling,
    isProcessing,
    isCompleted,
    isFailed,
    refetch
  };
}

export function useDocumentsList(options: { 
  page?: number; 
  per_page?: number; 
  status?: string;
  apiBaseUrl?: string;
} = {}) {
  const { 
    page = 1, 
    per_page = 10, 
    status,
    apiBaseUrl = '/api' 
  } = options;

  return useQuery({
    queryKey: ['documents', { page, per_page, status }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: per_page.toString(),
        ...(status && { status })
      });
      
      const response = await axios.get(`${apiBaseUrl}/documents?${params}`);
      return response.data;
    },
    staleTime: 30000, // Consider data fresh for 30 seconds
    retry: 2
  });
}
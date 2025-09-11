import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useDocument, queryKeys } from './useApi';
import { Document } from '@/lib/api';
import { useCallback, useEffect } from 'react';

export interface UseDocumentPollingOptions {
  /** Polling interval in milliseconds when document is processing */
  processingInterval?: number;
  /** Polling interval in milliseconds when document is pending */
  pendingInterval?: number;
  /** Whether to enable background refetching */
  refetchInBackground?: boolean;
  /** Whether to start polling immediately */
  enabled?: boolean;
}

export interface UseDocumentPollingReturn {
  document: Document | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isPolling: boolean;
  isProcessing: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isPending: boolean;
  refetch: () => Promise<any>;
  stopPolling: () => void;
  startPolling: () => void;
}

const DEFAULT_OPTIONS: Required<UseDocumentPollingOptions> = {
  processingInterval: 2000, // 2 seconds
  pendingInterval: 5000, // 5 seconds
  refetchInBackground: true,
  enabled: true,
};

export function useDocumentPolling(
  docId: string,
  options: UseDocumentPollingOptions = {}
): UseDocumentPollingReturn {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const queryClient = useQueryClient();

  // Use the base document query
  const {
    data: document,
    isLoading,
    isError,
    error,
    refetch: baseRefetch,
  } = useDocument(docId);

  // Determine current status
  const isProcessing = document?.status === 'processing';
  const isPending = document?.status === 'pending';
  const isCompleted = document?.status === 'completed';
  const isFailed = document?.status === 'failed';

  // Determine if we should be polling
  const shouldPoll = opts.enabled && !isCompleted && !isFailed && !!document;

  // Calculate polling interval based on status
  const pollingInterval = isProcessing
    ? opts.processingInterval
    : isPending
      ? opts.pendingInterval
      : false;

  // Setup polling query
  const { refetch: pollRefetch } = useQuery({
    queryKey: [...queryKeys.documents.detail(docId), 'polling'],
    queryFn: async () => {
      // Invalidate the main query to trigger a fresh fetch
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.detail(docId),
        exact: true,
      });
      return null;
    },
    enabled: shouldPoll,
    refetchInterval: shouldPoll ? pollingInterval : false,
    refetchIntervalInBackground: opts.refetchInBackground,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  });

  // Manual refetch function
  const refetch = useCallback(async () => {
    return await baseRefetch();
  }, [baseRefetch]);

  // Stop polling manually
  const stopPolling = useCallback(() => {
    queryClient.removeQueries({
      queryKey: [...queryKeys.documents.detail(docId), 'polling'],
    });
  }, [queryClient, docId]);

  // Start polling manually
  const startPolling = useCallback(() => {
    if (shouldPoll) {
      pollRefetch();
    }
  }, [shouldPoll, pollRefetch]);

  // Auto-stop polling when status changes to final state
  useEffect(() => {
    if (isCompleted || isFailed) {
      stopPolling();
    }
  }, [isCompleted, isFailed, stopPolling]);

  // Log status changes for debugging
  useEffect(() => {
    if (document) {
      console.debug(`Document ${docId} status: ${document.status}`, {
        isPolling: shouldPoll,
        interval: pollingInterval,
        document,
      });
    }
  }, [document?.status, docId, shouldPoll, pollingInterval, document]);

  return {
    document,
    isLoading,
    isError,
    error,
    isPolling: shouldPoll,
    isProcessing,
    isCompleted,
    isFailed,
    isPending,
    refetch,
    stopPolling,
    startPolling,
  };
}

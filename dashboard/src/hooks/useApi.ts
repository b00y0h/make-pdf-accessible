import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { ApiService, Document, DocumentListResponse, ReportsSummary, UserProfile } from '@/lib/api'
import { useMemo } from 'react'

// Create API service instance using the auth context
export function useApiService() {
  const { apiClient, isLoading } = useAuth()
  return useMemo(() => {
    // Return null during loading to prevent issues
    if (isLoading) return null
    return new ApiService(apiClient)
  }, [apiClient, isLoading])
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
}

// Documents hooks
export function useDocuments(params?: {
  page?: number
  per_page?: number
  status?: string
}) {
  const apiService = useApiService()
  
  return useQuery({
    queryKey: queryKeys.documents.list(params),
    queryFn: () => apiService!.getDocuments(params),
    enabled: !!apiService,
    staleTime: 30 * 1000, // 30 seconds
  })
}

export function useDocument(docId: string) {
  const apiService = useApiService()
  
  return useQuery({
    queryKey: queryKeys.documents.detail(docId),
    queryFn: () => apiService!.getDocument(docId),
    enabled: !!docId && !!apiService,
    staleTime: 30 * 1000,
  })
}

export function useUploadDocument() {
  const apiService = useApiService()
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: Parameters<typeof apiService.uploadDocument>[0]) => 
      apiService!.uploadDocument(data),
    onSuccess: () => {
      // Invalidate and refetch documents list
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() })
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.summary() })
    },
  })
}

export function useDownloadUrl() {
  const apiService = useApiService()
  
  return useMutation({
    mutationFn: ({ docId, type, expiresIn }: { 
      docId: string; 
      type: string; 
      expiresIn?: number 
    }) => apiService!.getDownloadUrl(docId, type, expiresIn),
  })
}

export function useUpdateAltText() {
  const apiService = useApiService()
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ docId, altText }: { docId: string; altText: Record<string, any> }) => 
      apiService!.updateAltText(docId, altText),
    onSuccess: (_, variables) => {
      // Invalidate the specific document
      queryClient.invalidateQueries({ 
        queryKey: queryKeys.documents.detail(variables.docId) 
      })
      // Also invalidate the list since the document status might change
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() })
    },
  })
}

// Reports hooks
export function useReportsSummary() {
  const apiService = useApiService()
  
  return useQuery({
    queryKey: queryKeys.reports.summary(),
    queryFn: () => apiService!.getReportsSummary(),
    enabled: !!apiService,
    staleTime: 60 * 1000, // 1 minute
  })
}

// Auth hooks
export function useUserProfile() {
  const apiService = useApiService()
  
  return useQuery({
    queryKey: queryKeys.auth.user(),
    queryFn: () => apiService!.getUserProfile(),
    enabled: !!apiService,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
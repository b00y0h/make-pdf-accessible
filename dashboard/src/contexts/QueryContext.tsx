'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode, useState } from 'react'

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        retry: (failureCount, error) => {
          // Don't retry on 401/403 errors
          if (error instanceof Error && 'status' in error) {
            const status = (error as any).status
            if (status === 401 || status === 403) {
              return false
            }
          }
          return failureCount < 3
        },
      },
      mutations: {
        retry: (failureCount, error) => {
          // Don't retry on client errors (4xx)
          if (error instanceof Error && 'status' in error) {
            const status = (error as any).status
            if (status >= 400 && status < 500) {
              return false
            }
          }
          return failureCount < 1
        },
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
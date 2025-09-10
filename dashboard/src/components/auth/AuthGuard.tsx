'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from '@/lib/auth-client'

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter()
  const { data: session, isLoading } = useSession()

  useEffect(() => {
    if (!isLoading && !session?.user) {
      router.push('/sign-in')
    }
  }, [session, isLoading, router])

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-blue-600"></div>
          <span>Loading...</span>
        </div>
      </div>
    )
  }

  // If user is not authenticated, show nothing (redirect will happen)
  if (!session?.user) {
    return null
  }

  // User is authenticated, show protected content
  return <>{children}</>
}
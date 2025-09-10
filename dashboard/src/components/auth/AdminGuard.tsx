'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from '@/lib/auth-client'

interface AdminGuardProps {
  children: React.ReactNode
}

export function AdminGuard({ children }: AdminGuardProps) {
  const router = useRouter()
  const { data: session, isLoading } = useSession()

  useEffect(() => {
    if (!isLoading && !session?.user) {
      router.push('/sign-in')
    } else if (!isLoading && session?.user && session.user.role !== 'admin') {
      // Redirect non-admin users to regular dashboard
      router.push('/dashboard')
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

  // If user is not authenticated or not admin, show nothing (redirect will happen)
  if (!session?.user || session.user.role !== 'admin') {
    return null
  }

  // User is admin, show protected content
  return <>{children}</>
}
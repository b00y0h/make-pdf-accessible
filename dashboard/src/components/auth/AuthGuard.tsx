'use client'

import { useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2, Shield } from 'lucide-react'

interface AuthGuardProps {
  children: ReactNode
  fallback?: ReactNode
  requireRoles?: string[]
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ 
  children, 
  fallback,
  requireRoles = []
}) => {
  const { isAuthenticated, isLoading, user, login } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Store intended destination
      const currentPath = window.location.pathname + window.location.search
      login(currentPath)
    }
  }, [isLoading, isAuthenticated, login])

  // Show loading state
  if (isLoading) {
    return fallback || (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardContent className="p-8 text-center space-y-4">
            <div className="flex items-center justify-center">
              <Shield className="h-12 w-12 text-blue-600 mb-4" />
            </div>
            <div className="flex items-center justify-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              <span className="text-gray-600">Checking authentication...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Redirect if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardContent className="p-8 text-center space-y-4">
            <Shield className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600">Redirecting to login...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Check role requirements
  if (requireRoles.length > 0 && user) {
    const userRoles = user['cognito:groups'] || []
    const hasRequiredRole = requireRoles.some(role => userRoles.includes(role))
    
    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <Card className="w-full max-w-md">
            <CardContent className="p-8 text-center space-y-4">
              <Shield className="h-12 w-12 text-red-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900">Access Denied</h2>
              <p className="text-gray-600">
                You don't have permission to access this page.
              </p>
              <p className="text-sm text-gray-500">
                Required roles: {requireRoles.join(', ')}
                <br />
                Your roles: {userRoles.length > 0 ? userRoles.join(', ') : 'None'}
              </p>
            </CardContent>
          </Card>
        </div>
      )
    }
  }

  return <>{children}</>
}

// Higher-order component version
export const withAuthGuard = <P extends object>(
  Component: React.ComponentType<P>,
  requireRoles?: string[]
) => {
  const WrappedComponent = (props: P) => (
    <AuthGuard requireRoles={requireRoles}>
      <Component {...props} />
    </AuthGuard>
  )
  
  WrappedComponent.displayName = `withAuthGuard(${Component.displayName || Component.name})`
  return WrappedComponent
}
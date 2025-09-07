'use client'

import { useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuthCallback } from '@/contexts/AuthContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, AlertCircle } from 'lucide-react'

export default function AuthCallback() {
  const searchParams = useSearchParams()
  const { handleCallback, isProcessing, error } = useAuthCallback()

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const errorParam = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')

    if (errorParam) {
      console.error('OAuth error:', errorParam, errorDescription)
      return
    }

    if (code) {
      handleCallback(code, state || undefined)
    }
  }, [searchParams, handleCallback])

  const handleRetry = () => {
    window.location.href = '/login'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>
            {isProcessing ? 'Signing you in...' : error ? 'Sign in failed' : 'Processing authentication...'}
          </CardTitle>
          <CardDescription>
            {isProcessing 
              ? 'Please wait while we complete your sign in'
              : error 
                ? 'There was a problem with your authentication'
                : 'Redirecting you to the dashboard'
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          {isProcessing && (
            <div className="flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          )}
          
          {error && (
            <div className="space-y-4">
              <div className="flex items-center justify-center text-red-600">
                <AlertCircle className="h-8 w-8" />
              </div>
              <div className="text-sm text-gray-600">
                <p className="font-medium text-red-600 mb-2">Error Details:</p>
                <p className="bg-red-50 p-3 rounded border text-left">{error}</p>
              </div>
              <Button 
                onClick={handleRetry}
                className="w-full"
                variant="default"
              >
                Try Again
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
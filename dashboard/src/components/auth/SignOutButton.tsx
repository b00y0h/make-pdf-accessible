'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { signOut } from '@/lib/auth-client'
import toast from 'react-hot-toast'

interface SignOutButtonProps {
  variant?: 'button' | 'menu-item'
  className?: string
}

export function SignOutButton({ variant = 'button', className = '' }: SignOutButtonProps) {
  const [isSigningOut, setIsSigningOut] = useState(false)
  const router = useRouter()

  const handleSignOut = async () => {
    setIsSigningOut(true)
    
    try {
      await signOut()
      toast.success('Signed out successfully')
      router.push('/sign-in')
      // Refresh the page to clear any cached session state
      window.location.reload()
    } catch (error) {
      console.error('Sign out error:', error)
      toast.error('Failed to sign out')
    } finally {
      setIsSigningOut(false)
    }
  }

  if (variant === 'menu-item') {
    return (
      <button
        onClick={handleSignOut}
        disabled={isSigningOut}
        className={`flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left disabled:opacity-50 ${className}`}
      >
        <LogOut className="h-4 w-4" />
        <span>{isSigningOut ? 'Signing out...' : 'Sign Out'}</span>
      </button>
    )
  }

  return (
    <button
      onClick={handleSignOut}
      disabled={isSigningOut}
      className={`inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      <LogOut className="h-4 w-4" />
      <span>{isSigningOut ? 'Signing out...' : 'Sign Out'}</span>
    </button>
  )
}
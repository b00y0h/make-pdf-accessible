'use client'

import React from 'react'
import Link from 'next/link'
import { useSession } from '@/lib/auth-client'
import { 
  Bell as BellIcon, 
  Menu as Bars3Icon,
  Home as HomeIcon
} from 'lucide-react'
import { SignOutButton } from '@/components/auth/SignOutButton'

export function AdminHeader() {
  const { data: session } = useSession()
  const user = session?.user

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Left side */}
          <div className="flex items-center">
            {/* Mobile menu button */}
            <button
              type="button"
              className="md:hidden -ml-2 mr-2 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            >
              <span className="sr-only">Open sidebar</span>
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            </button>

            {/* Breadcrumb / Current page */}
            <div className="flex items-center space-x-2 text-gray-500">
              <Link
                href="/dashboard"
                className="flex items-center text-sm hover:text-gray-700"
              >
                <HomeIcon className="h-4 w-4 mr-1" />
                Dashboard
              </Link>
              <span>/</span>
              <span className="text-sm text-gray-900 font-medium">Admin</span>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <button
              type="button"
              className="bg-white p-1 rounded-full text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <span className="sr-only">View notifications</span>
              <BellIcon className="h-6 w-6" aria-hidden="true" />
            </button>

            {/* Sign out button */}
            <SignOutButton />

            {/* User info */}
            <div className="flex items-center space-x-3">
              <div className="text-right text-sm">
                <div className="font-medium text-gray-900">
                  {user?.name || user?.email}
                </div>
                <div className="text-gray-500 capitalize">
                  {user?.role} Access
                </div>
              </div>
              <div className="flex-shrink-0">
                <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center">
                  <span className="text-indigo-600 text-sm font-medium">
                    {user?.name?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
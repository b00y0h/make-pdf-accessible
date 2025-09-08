'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { 
  HomeIcon, 
  UsersIcon, 
  DocumentTextIcon,
  CogIcon,
  ShieldCheckIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: HomeIcon },
  { name: 'Users', href: '/admin/users', icon: UsersIcon },
  { name: 'Documents', href: '/admin/documents', icon: DocumentTextIcon },
  { name: 'Analytics', href: '/admin/analytics', icon: ChartBarIcon },
  { name: 'Audit Logs', href: '/admin/audit', icon: ShieldCheckIcon },
  { name: 'Settings', href: '/admin/settings', icon: CogIcon },
]

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

export function AdminSidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  return (
    <div className="flex flex-col w-64 bg-gray-800">
      {/* Logo */}
      <div className="flex items-center justify-center h-16 px-4 bg-gray-900">
        <h1 className="text-white text-lg font-semibold">AccessPDF Admin</h1>
      </div>

      {/* Navigation */}
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
        <nav className="mt-5 flex-1 px-2 space-y-1">
          {navigation.map((item) => {
            const isCurrent = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={classNames(
                  isCurrent
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white',
                  'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                )}
              >
                <item.icon
                  className={classNames(
                    isCurrent ? 'text-gray-300' : 'text-gray-400 group-hover:text-gray-300',
                    'mr-3 flex-shrink-0 h-6 w-6'
                  )}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* User section */}
      <div className="flex-shrink-0 flex border-t border-gray-700 p-4">
        <div className="flex-shrink-0 w-full group block">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="inline-block h-10 w-10 rounded-full bg-gray-600 flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {user?.name?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'A'}
                </span>
              </div>
            </div>
            <div className="ml-3 flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.name || user?.email}
              </p>
              <p className="text-xs text-gray-400 capitalize">
                {user?.role} User
              </p>
            </div>
          </div>
          <div className="mt-2">
            <button
              onClick={logout}
              className="w-full text-left text-xs text-gray-400 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
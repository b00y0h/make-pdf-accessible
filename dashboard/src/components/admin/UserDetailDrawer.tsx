'use client'

import React, { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { 
  XMarkIcon,
  UserIcon,
  DocumentTextIcon,
  CalendarIcon,
  ClipboardIcon,
  TrashIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { UserSummary } from '@/types/admin'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'

interface UserDetailDrawerProps {
  user: UserSummary | null
  isOpen: boolean
  onClose: () => void
  onUserUpdated: () => void
}

export function UserDetailDrawer({ user, isOpen, onClose, onUserUpdated }: UserDetailDrawerProps) {
  const { apiClient } = useAuth()
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState('')

  const handleCopyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(`${label} copied to clipboard`)
    } catch (error) {
      toast.error('Failed to copy to clipboard')
    }
  }

  const handleDeleteUser = async () => {
    if (!user || deleteConfirmText !== 'DELETE') return

    try {
      setIsDeleting(true)
      const response = await apiClient.delete(`/api/admin/users/${user._id || user.sub}`)
      
      if (response.data.success) {
        toast.success('User deleted successfully')
        onUserUpdated()
        onClose()
      } else {
        toast.error(response.data.error || 'Failed to delete user')
      }
    } catch (error: any) {
      console.error('Delete user error:', error)
      toast.error(error.response?.data?.error || 'Failed to delete user')
    } finally {
      setIsDeleting(false)
      setShowDeleteConfirm(false)
      setDeleteConfirmText('')
    }
  }

  const formatDate = (date: Date | string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!user) return null

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-500"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-500"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-500"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-500"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto relative w-screen max-w-2xl">
                  <Transition.Child
                    as={Fragment}
                    enter="ease-in-out duration-500"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in-out duration-500"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                  >
                    <div className="absolute left-0 top-0 -ml-8 flex pr-2 pt-4 sm:-ml-10 sm:pr-4">
                      <button
                        type="button"
                        className="relative rounded-md text-gray-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-white"
                        onClick={onClose}
                      >
                        <span className="absolute -inset-2.5" />
                        <span className="sr-only">Close panel</span>
                        <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                      </button>
                    </div>
                  </Transition.Child>
                  
                  <div className="flex h-full flex-col overflow-y-scroll bg-white py-6 shadow-xl">
                    <div className="px-4 sm:px-6">
                      <Dialog.Title className="text-base font-semibold leading-6 text-gray-900">
                        User Details
                      </Dialog.Title>
                    </div>
                    
                    <div className="relative mt-6 flex-1 px-4 sm:px-6">
                      {/* User Profile Section */}
                      <div className="pb-6 border-b border-gray-200">
                        <div className="flex items-center space-x-4">
                          <div className="flex-shrink-0">
                            <div className="h-16 w-16 rounded-full bg-gray-300 flex items-center justify-center">
                              <span className="text-xl font-medium text-gray-700">
                                {(user.name || user.email)?.charAt(0)?.toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <div className="flex-1">
                            <h2 className="text-xl font-bold text-gray-900">
                              {user.name || 'No name set'}
                            </h2>
                            <div className="flex items-center space-x-2">
                              <p className="text-gray-600">{user.email}</p>
                              <button
                                onClick={() => handleCopyToClipboard(user.email, 'Email')}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                <ClipboardIcon className="h-4 w-4" />
                              </button>
                            </div>
                            <div className="mt-1">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                user.role === 'admin' 
                                  ? 'bg-purple-100 text-purple-800' 
                                  : 'bg-green-100 text-green-800'
                              }`}>
                                {user.role || 'user'}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* User Info Section */}
                      <div className="py-6 border-b border-gray-200">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Account Information</h3>
                        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          <div>
                            <dt className="text-sm font-medium text-gray-500">User ID</dt>
                            <dd className="mt-1 text-sm text-gray-900 flex items-center space-x-2">
                              <span className="font-mono">{user._id?.toString() || user.sub}</span>
                              <button
                                onClick={() => handleCopyToClipboard(user._id?.toString() || user.sub, 'User ID')}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                <ClipboardIcon className="h-4 w-4" />
                              </button>
                            </dd>
                          </div>
                          
                          {user.username && (
                            <div>
                              <dt className="text-sm font-medium text-gray-500">Username</dt>
                              <dd className="mt-1 text-sm text-gray-900">{user.username}</dd>
                            </div>
                          )}

                          <div>
                            <dt className="text-sm font-medium text-gray-500">Created</dt>
                            <dd className="mt-1 text-sm text-gray-900">{formatDate(user.createdAt)}</dd>
                          </div>

                          <div>
                            <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                            <dd className="mt-1 text-sm text-gray-900">{formatDate(user.updatedAt)}</dd>
                          </div>

                          {user.lastActivity && (
                            <div>
                              <dt className="text-sm font-medium text-gray-500">Last Activity</dt>
                              <dd className="mt-1 text-sm text-gray-900">{formatDate(user.lastActivity)}</dd>
                            </div>
                          )}
                        </dl>
                      </div>

                      {/* Document Statistics */}
                      <div className="py-6 border-b border-gray-200">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Document Statistics</h3>
                        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                          <div className="text-center">
                            <div className="text-2xl font-bold text-gray-900">{user.documentCount}</div>
                            <div className="text-sm text-gray-500">Total Documents</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-green-600">{user.documentsCompleted}</div>
                            <div className="text-sm text-gray-500">Completed</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-blue-600">{user.documentsProcessing}</div>
                            <div className="text-sm text-gray-500">Processing</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-red-600">{user.documentsFailed}</div>
                            <div className="text-sm text-gray-500">Failed</div>
                          </div>
                        </div>
                        
                        {user.documentCount > 0 && (
                          <div className="mt-4">
                            <div className="text-sm text-gray-500 mb-1">Success Rate</div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-green-600 h-2 rounded-full" 
                                style={{ 
                                  width: `${Math.round((user.documentsCompleted / user.documentCount) * 100)}%` 
                                }}
                              ></div>
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {Math.round((user.documentsCompleted / user.documentCount) * 100)}% success rate
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Danger Zone */}
                      {user.role !== 'admin' && (
                        <div className="py-6">
                          <h3 className="text-lg font-medium text-red-900 mb-4">Danger Zone</h3>
                          <div className="bg-red-50 border border-red-200 rounded-md p-4">
                            <div className="flex">
                              <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
                              <div className="ml-3">
                                <h4 className="text-sm font-medium text-red-800">Delete User Account</h4>
                                <p className="mt-1 text-sm text-red-700">
                                  This will permanently delete the user account and all associated documents. 
                                  This action cannot be undone.
                                </p>
                                <div className="mt-4">
                                  {!showDeleteConfirm ? (
                                    <button
                                      onClick={() => setShowDeleteConfirm(true)}
                                      className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                                    >
                                      <TrashIcon className="h-4 w-4 mr-2" />
                                      Delete User
                                    </button>
                                  ) : (
                                    <div className="space-y-3">
                                      <p className="text-sm font-medium text-red-800">
                                        Type "DELETE" to confirm:
                                      </p>
                                      <input
                                        type="text"
                                        value={deleteConfirmText}
                                        onChange={(e) => setDeleteConfirmText(e.target.value)}
                                        placeholder="Type DELETE to confirm"
                                        className="block w-full px-3 py-2 border border-red-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                                      />
                                      <div className="flex space-x-3">
                                        <button
                                          onClick={handleDeleteUser}
                                          disabled={deleteConfirmText !== 'DELETE' || isDeleting}
                                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                                        >
                                          {isDeleting ? 'Deleting...' : 'Confirm Delete'}
                                        </button>
                                        <button
                                          onClick={() => {
                                            setShowDeleteConfirm(false)
                                            setDeleteConfirmText('')
                                          }}
                                          className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                        >
                                          Cancel
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}
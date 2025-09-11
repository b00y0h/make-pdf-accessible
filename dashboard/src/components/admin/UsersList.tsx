'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSession } from '@/lib/auth-client';
import { useApiService } from '@/hooks/useApi';
import { UserSummary, UserListParams, UserListResponse } from '@/types/admin';
import {
  Search as MagnifyingGlassIcon,
  User as UserIcon,
  FileText as DocumentTextIcon,
  Shield as ShieldIcon,
  Trash2 as TrashIcon,
} from 'lucide-react';
import { UserDetailDrawer } from './UserDetailDrawer';
import toast from 'react-hot-toast';

const SORT_OPTIONS = [
  { value: 'createdAt', label: 'Date Created' },
  { value: 'lastActivity', label: 'Last Activity' },
  { value: 'email', label: 'Email' },
  { value: 'name', label: 'Name' },
  { value: 'documentCount', label: 'Document Count' },
];

export function UsersList() {
  const { data: session } = useSession();
  const apiService = useApiService();
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<UserSummary | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [updatingRole, setUpdatingRole] = useState<string | null>(null);
  const [deletingUser, setDeletingUser] = useState<string | null>(null);

  // Filters and pagination
  const [params, setParams] = useState<UserListParams>({
    page: 1,
    pageSize: 20,
    sortBy: 'createdAt',
    sortOrder: 'desc',
  });

  const [pagination, setPagination] = useState({
    total: 0,
    totalPages: 0,
  });

  const [searchInput, setSearchInput] = useState('');
  const lastParamsRef = useRef<UserListParams>();

  useEffect(() => {
    if (!apiService) return;

    // Check if params actually changed (deep comparison)
    const currentParams = {
      page: params.page,
      pageSize: params.pageSize,
      sortBy: params.sortBy,
      sortOrder: params.sortOrder,
      search: params.search,
      role: params.role,
    };

    const lastParams = lastParamsRef.current;

    // Skip if params haven't changed
    if (
      lastParams &&
      lastParams.page === currentParams.page &&
      lastParams.pageSize === currentParams.pageSize &&
      lastParams.sortBy === currentParams.sortBy &&
      lastParams.sortOrder === currentParams.sortOrder &&
      lastParams.search === currentParams.search &&
      lastParams.role === currentParams.role
    ) {
      console.log('Skipping fetch - params unchanged');
      return;
    }

    console.log('UsersList fetching with new params:', currentParams);
    lastParamsRef.current = currentParams;

    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError(null);

        // Use apiService method
        const response = await apiService.getUsers(params);

        if (response.success) {
          const data: UserListResponse = response.data;
          setUsers(data.users);
          setPagination({
            total: data.total,
            totalPages: data.totalPages,
          });
        } else {
          setError(response.error || 'Failed to fetch users');
        }
      } catch (err: any) {
        console.error('Error fetching users:', err);
        setError(err.response?.data?.error || 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [apiService, params]);

  // Separate function for manual refresh (used by drawer)
  const refreshUsers = useCallback(async () => {
    if (!apiService) return;

    try {
      setLoading(true);
      setError(null);

      const response = await apiService.getUsers(params);

      if (response.success) {
        const data: UserListResponse = response.data;
        setUsers(data.users);
        setPagination({
          total: data.total,
          totalPages: data.totalPages,
        });
      } else {
        setError(response.error || 'Failed to fetch users');
      }
    } catch (err: any) {
      console.error('Error refreshing users:', err);
      setError(err.response?.data?.error || 'Failed to refresh users');
    } finally {
      setLoading(false);
    }
  }, [apiService, params]);

  const handleSearch = useCallback((value: string) => {
    setParams((prev) => ({
      ...prev,
      search: value || undefined,
      page: 1, // Reset to first page when searching
    }));
  }, []);

  const handleSort = useCallback((sortBy: string) => {
    setParams((prev) => ({
      ...prev,
      sortBy: sortBy as UserListParams['sortBy'],
      sortOrder:
        prev.sortBy === sortBy && prev.sortOrder === 'desc' ? 'asc' : 'desc',
      page: 1,
    }));
  }, []);

  const handlePageChange = useCallback((newPage: number) => {
    setParams((prev) => ({ ...prev, page: newPage }));
  }, []);

  const handleUserClick = useCallback((user: UserSummary) => {
    setSelectedUser(user);
    setIsDrawerOpen(true);
  }, []);

  const handleToggleAdmin = useCallback(
    async (user: UserSummary) => {
      if (!apiService || updatingRole) return;

      const userId = user._id?.toString() || user.sub || user.id;
      if (!userId) return;

      try {
        setUpdatingRole(userId);
        const newRole = user.role === 'admin' ? 'user' : 'admin';

        const response = await fetch(`/api/admin/users/${userId}/role`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ role: newRole }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        if (result.success) {
          // Update the user in the local state
          setUsers((prev) =>
            prev.map((u) =>
              (u._id?.toString() || u.sub || u.id) === userId
                ? { ...u, role: newRole }
                : u
            )
          );
          toast.success(`User role updated to ${newRole}`);
        } else {
          throw new Error(result.error || 'Failed to update user role');
        }
      } catch (error: any) {
        console.error('Error updating user role:', error);
        toast.error(error.message || 'Failed to update user role');
      } finally {
        setUpdatingRole(null);
      }
    },
    [apiService, updatingRole]
  );

  const handleDeleteUser = useCallback(
    async (user: UserSummary) => {
      if (!apiService || deletingUser) return;

      const userId = user._id?.toString() || user.sub || user.id;
      if (!userId) return;

      // Prevent self-deletion
      if (session?.user?.id === userId) {
        toast.error('You cannot delete your own account');
        return;
      }

      if (
        !confirm(
          `Are you sure you want to delete ${user.name || user.email}? This action cannot be undone.`
        )
      ) {
        return;
      }

      try {
        setDeletingUser(userId);

        const response = await fetch(`/api/admin/users/${userId}`, {
          method: 'DELETE',
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        if (result.success) {
          // Remove the user from the local state
          setUsers((prev) =>
            prev.filter((u) => (u._id?.toString() || u.sub || u.id) !== userId)
          );
          // Update pagination if needed
          setPagination((prev) => ({
            ...prev,
            total: prev.total - 1,
          }));
          toast.success('User deleted successfully');
        } else {
          throw new Error(result.error || 'Failed to delete user');
        }
      } catch (error: any) {
        console.error('Error deleting user:', error);
        toast.error(error.message || 'Failed to delete user');
      } finally {
        setDeletingUser(null);
      }
    },
    [apiService, deletingUser, session]
  );

  const formatDate = (date: Date | string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const renderUserActions = (user: UserSummary) => {
    const userId = user._id?.toString() || user.sub || user.id;
    const isCurrentUser = session?.user?.id === userId;
    const isUpdating = updatingRole === userId;
    const isDeleting = deletingUser === userId;

    return (
      <div className="flex items-center space-x-2">
        <button
          onClick={() => handleUserClick(user)}
          className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
        >
          View Details
        </button>

        {!isCurrentUser && (
          <>
            <button
              onClick={() => handleToggleAdmin(user)}
              disabled={isUpdating || isDeleting}
              className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded ${
                user.role === 'admin'
                  ? 'text-purple-700 bg-purple-100 hover:bg-purple-200'
                  : 'text-green-700 bg-green-100 hover:bg-green-200'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={user.role === 'admin' ? 'Remove admin role' : 'Make admin'}
            >
              {isUpdating ? (
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current mr-1"></div>
              ) : (
                <ShieldIcon className="h-3 w-3 mr-1" />
              )}
              {user.role === 'admin' ? 'Remove Admin' : 'Make Admin'}
            </button>

            <button
              onClick={() => handleDeleteUser(user)}
              disabled={isUpdating || isDeleting}
              className="inline-flex items-center px-2 py-1 text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Delete user"
            >
              {isDeleting ? (
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current mr-1"></div>
              ) : (
                <TrashIcon className="h-3 w-3 mr-1" />
              )}
              Delete
            </button>
          </>
        )}
      </div>
    );
  };

  if (loading && users.length === 0) {
    return (
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="text-gray-500 mt-2">Loading users...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white shadow rounded-lg">
        {/* Header with search and filters */}
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
            {/* Search */}
            <div className="flex-1 max-w-lg">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search users by name or email..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSearch(searchInput);
                    }
                  }}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Sort and filter controls */}
            <div className="flex items-center space-x-3">
              <select
                value={params.sortBy}
                onChange={(e) => handleSort(e.target.value)}
                className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    Sort by {option.label}
                  </option>
                ))}
              </select>

              <select
                value={params.role || 'all'}
                onChange={(e) =>
                  setParams((prev) => ({
                    ...prev,
                    role:
                      e.target.value === 'all'
                        ? undefined
                        : (e.target.value as UserListParams['role']),
                    page: 1,
                  }))
                }
                className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
              >
                <option value="all">All Roles</option>
                <option value="admin">Admin</option>
                <option value="user">User</option>
              </select>
            </div>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="px-4 py-3 bg-red-50 border-l-4 border-red-400">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Users table */}
        {users.length === 0 ? (
          <div className="text-center py-12">
            <UserIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              No users found
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              {params.search
                ? 'Try adjusting your search criteria.'
                : 'Users will appear here once created.'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Documents
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Activity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="relative px-6 py-3">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr
                      key={user._id?.toString() || user.sub || user.id}
                      className="hover:bg-gray-50"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                              <span className="text-sm font-medium text-gray-700">
                                {(user.name || user.email)
                                  ?.charAt(0)
                                  ?.toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">
                              {user.name || 'No name'}
                            </div>
                            <div className="text-sm text-gray-500">
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            user.role === 'admin'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-green-100 text-green-800'
                          }`}
                        >
                          {user.role || 'user'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center">
                            <DocumentTextIcon className="h-4 w-4 text-gray-400 mr-1" />
                            {user.documentCount}
                          </div>
                          <div className="text-xs text-gray-500">
                            {user.documentsCompleted} completed
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.lastActivity
                          ? formatDate(user.lastActivity)
                          : 'Never'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(user.createdAt)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {renderUserActions(user)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination.totalPages > 1 && (
              <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                <div className="flex-1 flex justify-between sm:hidden">
                  <button
                    onClick={() => handlePageChange(params.page - 1)}
                    disabled={params.page <= 1}
                    className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => handlePageChange(params.page + 1)}
                    disabled={params.page >= pagination.totalPages}
                    className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      Showing{' '}
                      <span className="font-medium">
                        {(params.page - 1) * params.pageSize + 1}
                      </span>{' '}
                      to{' '}
                      <span className="font-medium">
                        {Math.min(
                          params.page * params.pageSize,
                          pagination.total
                        )}
                      </span>{' '}
                      of <span className="font-medium">{pagination.total}</span>{' '}
                      results
                    </p>
                  </div>
                  <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                      <button
                        onClick={() => handlePageChange(params.page - 1)}
                        disabled={params.page <= 1}
                        className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>

                      {Array.from(
                        { length: Math.min(pagination.totalPages, 5) },
                        (_, i) => {
                          let pageNum: number;
                          if (pagination.totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (params.page <= 3) {
                            pageNum = i + 1;
                          } else if (params.page >= pagination.totalPages - 2) {
                            pageNum = pagination.totalPages - 4 + i;
                          } else {
                            pageNum = params.page - 2 + i;
                          }

                          return (
                            <button
                              key={pageNum}
                              onClick={() => handlePageChange(pageNum)}
                              className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                                pageNum === params.page
                                  ? 'z-10 bg-indigo-50 border-indigo-500 text-indigo-600'
                                  : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                              }`}
                            >
                              {pageNum}
                            </button>
                          );
                        }
                      )}

                      <button
                        onClick={() => handlePageChange(params.page + 1)}
                        disabled={params.page >= pagination.totalPages}
                        className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* User detail drawer */}
      <UserDetailDrawer
        user={selectedUser}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedUser(null);
        }}
        onUserUpdated={refreshUsers}
      />
    </>
  );
}

import React from 'react';
import { UsersList } from '@/components/admin/UsersList';

export const metadata = {
  title: 'User Management - Admin - AccessPDF',
  description: 'Manage users, view details, and perform admin actions',
};

export default function UsersPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage all users, view their documents, and perform administrative
            actions
          </p>
        </div>
      </div>

      {/* Users list */}
      <UsersList />
    </div>
  );
}

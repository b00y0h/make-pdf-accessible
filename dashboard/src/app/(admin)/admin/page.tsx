import React from 'react';
import { AdminDashboardStats } from '@/components/admin/AdminDashboardStats';
import { RecentActivity } from '@/components/admin/RecentActivity';

export const metadata = {
  title: 'Admin Dashboard - AccessPDF',
  description: 'Admin dashboard for managing users and system overview',
};

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">
          Overview of system activity and user management
        </p>
      </div>

      {/* Stats grid */}
      <AdminDashboardStats />

      {/* Recent activity */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Recent Activity
          </h3>
          <div className="mt-5">
            <RecentActivity />
          </div>
        </div>
      </div>
    </div>
  );
}

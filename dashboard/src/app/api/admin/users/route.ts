import { NextRequest } from 'next/server'
import { withRBAC } from '@/lib/rbac-middleware'
import { getAdminRepository } from '@/lib/mongodb'
import { UserListParams } from '@/types/admin'

async function getUsersHandler(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    
    // Parse query parameters
    const params: UserListParams = {
      page: parseInt(searchParams.get('page') || '1'),
      pageSize: Math.min(parseInt(searchParams.get('pageSize') || '20'), 100), // Max 100 per page
      search: searchParams.get('search') || undefined,
      sortBy: (searchParams.get('sortBy') as any) || 'createdAt',
      sortOrder: (searchParams.get('sortOrder') as 'asc' | 'desc') || 'desc',
      role: (searchParams.get('role') as 'admin' | 'user') || undefined,
    }

    // Get admin repository and fetch users
    const adminRepo = await getAdminRepository()
    const result = await adminRepo.getUsers(params)

    return Response.json({
      success: true,
      data: result,
    })

  } catch (error) {
    console.error('Error fetching users:', error)
    return Response.json(
      { 
        success: false,
        error: 'Failed to fetch users' 
      },
      { status: 500 }
    )
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getUsersHandler, { requiredRole: 'admin' })
import { NextRequest } from 'next/server'
import { withRBAC } from '@/lib/rbac-middleware'
import { getAdminRepository } from '@/lib/mongodb'

async function deleteUserHandler(request: NextRequest, { params }: { params: { userId: string } }) {
  try {
    const { userId } = params
    const actorUserId = (request as any).user?._id?.toString() || (request as any).user?.sub

    if (!actorUserId) {
      return Response.json(
        { success: false, error: 'Actor user ID not found' },
        { status: 401 }
      )
    }

    // Prevent self-deletion
    if (userId === actorUserId) {
      return Response.json(
        { success: false, error: 'Cannot delete your own account' },
        { status: 400 }
      )
    }

    // Get admin repository and delete user
    const adminRepo = await getAdminRepository()
    const deletionJob = await adminRepo.deleteUser(userId, actorUserId)

    return Response.json({
      success: true,
      data: {
        jobId: deletionJob._id?.toString(),
        status: deletionJob.status,
        deletedDocuments: deletionJob.meta?.deletedDocuments || 0,
        message: 'User and all associated data deleted successfully'
      }
    })

  } catch (error: any) {
    console.error('Error deleting user:', error)
    
    // Handle specific error cases
    if (error.message === 'User not found') {
      return Response.json(
        { success: false, error: 'User not found' },
        { status: 404 }
      )
    }

    return Response.json(
      { 
        success: false,
        error: 'Failed to delete user' 
      },
      { status: 500 }
    )
  }
}

async function getUserHandler(request: NextRequest, { params }: { params: { userId: string } }) {
  try {
    const { userId } = params

    // Get admin repository and fetch user
    const adminRepo = await getAdminRepository()
    const user = await adminRepo.getUserById(userId)

    if (!user) {
      return Response.json(
        { success: false, error: 'User not found' },
        { status: 404 }
      )
    }

    return Response.json({
      success: true,
      data: user,
    })

  } catch (error) {
    console.error('Error fetching user:', error)
    return Response.json(
      { 
        success: false,
        error: 'Failed to fetch user' 
      },
      { status: 500 }
    )
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getUserHandler, { requiredRole: 'admin' })
export const DELETE = withRBAC(deleteUserHandler, { requiredRole: 'admin' })
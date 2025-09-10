import { NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { Pool } from 'pg';

async function updateUserRoleHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    // Extract userId from URL pathname
    const url = new URL(request.url);
    const pathSegments = url.pathname.split('/');
    const userId = pathSegments[pathSegments.indexOf('users') + 1];

    if (!userId) {
      return NextResponse.json(
        { success: false, error: 'User ID not found in URL' },
        { status: 400 }
      );
    }
    const body = await request.json();
    const { role } = body;

    if (!role || !['admin', 'user'].includes(role)) {
      return NextResponse.json(
        { success: false, error: 'Invalid role. Must be "admin" or "user"' },
        { status: 400 }
      );
    }

    const actorUserId = request.user?.id || request.user?.sub;

    if (!actorUserId) {
      return NextResponse.json(
        { success: false, error: 'Actor user ID not found' },
        { status: 401 }
      );
    }

    // Prevent self-role modification
    if (userId === actorUserId) {
      return NextResponse.json(
        { success: false, error: 'Cannot modify your own role' },
        { status: 400 }
      );
    }

    // Connect to BetterAuth PostgreSQL database
    const pool = new Pool({
      connectionString:
        process.env.AUTH_DATABASE_URL ||
        'postgresql://postgres:password@localhost:5433/better_auth',
    });

    try {
      // Check if user exists
      const userCheck = await pool.query(
        'SELECT id, role FROM "user" WHERE id = $1',
        [userId]
      );

      if (userCheck.rows.length === 0) {
        await pool.end();
        return NextResponse.json(
          { success: false, error: 'User not found' },
          { status: 404 }
        );
      }

      const currentRole = userCheck.rows[0].role;

      if (currentRole === role) {
        await pool.end();
        return NextResponse.json(
          { success: false, error: `User already has ${role} role` },
          { status: 400 }
        );
      }

      // Update user role
      await pool.query(
        'UPDATE "user" SET role = $1, "updatedAt" = NOW() WHERE id = $2',
        [role, userId]
      );

      await pool.end();

      return NextResponse.json({
        success: true,
        data: {
          userId,
          role,
          message: `User role updated to ${role} successfully`,
        },
      });
    } catch (dbError) {
      await pool.end();
      throw dbError;
    }
  } catch (error: any) {
    console.error('Error updating user role:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to update user role',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const PATCH = withRBAC(updateUserRoleHandler, { requiredRole: 'admin' });

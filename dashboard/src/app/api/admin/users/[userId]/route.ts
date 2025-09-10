import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { Pool } from 'pg';

async function deleteUserHandler(
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

    const actorUserId = request.user?.id || request.user?.sub;

    if (!actorUserId) {
      return NextResponse.json(
        { success: false, error: 'Actor user ID not found' },
        { status: 401 }
      );
    }

    // Prevent self-deletion
    if (userId === actorUserId) {
      return NextResponse.json(
        { success: false, error: 'Cannot delete your own account' },
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
        'SELECT id, email FROM "user" WHERE id = $1',
        [userId]
      );

      if (userCheck.rows.length === 0) {
        await pool.end();
        return NextResponse.json(
          { success: false, error: 'User not found' },
          { status: 404 }
        );
      }

      // Delete the user from BetterAuth database
      await pool.query('DELETE FROM "user" WHERE id = $1', [userId]);

      await pool.end();

      return NextResponse.json({
        success: true,
        data: {
          userId,
          message: 'User deleted successfully',
        },
      });
    } catch (dbError) {
      await pool.end();
      throw dbError;
    }
  } catch (error: any) {
    console.error('Error deleting user:', error);

    // Handle specific error cases
    if (error.message === 'User not found') {
      return NextResponse.json(
        { success: false, error: 'User not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to delete user',
      },
      { status: 500 }
    );
  }
}

async function getUserHandler(
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

    // Connect to BetterAuth PostgreSQL database
    const pool = new Pool({
      connectionString:
        process.env.AUTH_DATABASE_URL ||
        'postgresql://postgres:password@localhost:5433/better_auth',
    });

    try {
      // Get user from BetterAuth database
      const userResult = await pool.query(
        'SELECT id, email, name, username, role, "emailVerified", "createdAt", "updatedAt" FROM "user" WHERE id = $1',
        [userId]
      );

      if (userResult.rows.length === 0) {
        await pool.end();
        return NextResponse.json(
          { success: false, error: 'User not found' },
          { status: 404 }
        );
      }

      const user = userResult.rows[0];
      await pool.end();

      return NextResponse.json({
        success: true,
        data: {
          _id: user.id,
          id: user.id,
          sub: user.id,
          email: user.email,
          name: user.name,
          username: user.username,
          role: user.role || 'user',
          emailVerified: user.emailVerified,
          createdAt: user.createdAt,
          updatedAt: user.updatedAt,
          // Mock document stats for now
          documentCount: 0,
          documentsCompleted: 0,
          documentsPending: 0,
          documentsProcessing: 0,
          documentsFailed: 0,
          lastActivity: null,
        },
      });
    } catch (dbError) {
      await pool.end();
      throw dbError;
    }
  } catch (error) {
    console.error('Error fetching user:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to fetch user',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getUserHandler, { requiredRole: 'admin' });
export const DELETE = withRBAC(deleteUserHandler, { requiredRole: 'admin' });

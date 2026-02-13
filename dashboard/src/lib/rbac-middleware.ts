import { NextRequest, NextResponse } from 'next/server';
import { connectToDatabase } from '@/lib/mongodb';
import { User, UserRole } from '@/types/admin';

export interface RBACOptions {
  requiredRole?: UserRole;
  allowSelf?: boolean; // Allow users to access their own resources
  userIdParam?: string; // Parameter name for user ID (e.g., 'userId', 'id')
}

export interface AuthenticatedRequest extends NextRequest {
  user?: User;
}

/**
 * RBAC Middleware for API routes
 * Validates authentication and authorization for protected endpoints
 */
export function withRBAC(
  handler: (request: AuthenticatedRequest) => Promise<NextResponse>,
  options: RBACOptions = {}
) {
  return async (request: NextRequest) => {
    try {
      // Use BetterAuth session for authentication
      const { auth } = await import('@/lib/auth-server');

      const session = await auth.api.getSession({
        headers: request.headers,
      });

      if (!session?.user) {
        return NextResponse.json(
          { error: 'Authentication required' },
          { status: 401 }
        );
      }

      // Check role authorization
      const userRole = (session.user.role || 'user') as UserRole;
      if (options.requiredRole && userRole !== options.requiredRole) {
        return NextResponse.json(
          { error: 'Insufficient permissions' },
          { status: 403 }
        );
      }

      // Check if user can access their own resource
      if (options.allowSelf && options.userIdParam) {
        const url = new URL(request.url);
        const segments = url.pathname.split('/');
        const userIdIndex = segments.findIndex(
          (segment) => segment === options.userIdParam
        );

        if (userIdIndex !== -1 && segments[userIdIndex + 1]) {
          const resourceUserId = segments[userIdIndex + 1];
          if (resourceUserId !== session.user.id && userRole !== 'admin') {
            return NextResponse.json(
              { error: 'Access denied' },
              { status: 403 }
            );
          }
        }
      }

      // Add user to request
      const authenticatedRequest = request as AuthenticatedRequest;
      authenticatedRequest.user = {
        id: session.user.id,
        sub: session.user.id,
        email: session.user.email,
        name: session.user.name,
        username: session.user.username,
        role: userRole,
        createdAt: new Date(session.user.createdAt),
        updatedAt: new Date(session.user.updatedAt),
      } as User;

      return await handler(authenticatedRequest);
    } catch (error) {
      console.error('RBAC middleware error:', error);
      return NextResponse.json(
        { error: 'Internal server error' },
        { status: 500 }
      );
    }
  };
}

/**
 * Client-side RBAC hook for components
 */
export function useRBAC() {
  const { useSession } = require('@/lib/auth');
  const session = useSession();

  return {
    hasRole: (role: UserRole) => session.data?.user?.role === role,
    canAccess: (resource: string, action: string) => {
      // Implement resource-based access control as needed
      return session.data?.user?.role === 'admin';
    },
    isAdmin: session.data?.user?.role === 'admin',
    user: session.data?.user,
  };
}

/**
 * Utility function to check if user has required permissions
 */
export function hasPermission(
  user: User,
  requiredRole: UserRole,
  resourceUserId?: string
): boolean {
  // Admin can access everything
  if (user.role === 'admin') {
    return true;
  }

  // Check role requirement
  if (
    requiredRole === ('admin' as UserRole) &&
    user.role !== ('admin' as UserRole)
  ) {
    return false;
  }

  // Check if user can access their own resource
  if (resourceUserId && user.sub !== resourceUserId) {
    return false;
  }

  return true;
}

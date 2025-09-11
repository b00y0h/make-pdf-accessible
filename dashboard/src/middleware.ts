import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import {
  getSessionFromRequest,
  validateSession,
  isAdmin,
} from '@/lib/auth-middleware';

// Routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/queue',
  '/documents',
  '/reports',
  '/settings',
  '/admin',
  '/upload',
  '/alt-text',
];

// Routes that require admin role
const adminRoutes = ['/admin'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for API routes and auth routes to prevent loops
  if (pathname.startsWith('/api/') || pathname.startsWith('/_next/')) {
    return NextResponse.next();
  }

  // Check if the route needs protection
  const isProtectedRoute = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  );
  const isAdminRoute = adminRoutes.some((route) => pathname.startsWith(route));

  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  try {
    // Get session from the request using Edge Runtime compatible method
    const session = await getSessionFromRequest(request);

    // If no session and trying to access protected route, redirect to sign-in
    if (!session || !validateSession(session)) {
      const signInUrl = new URL('/sign-in', request.url);
      signInUrl.searchParams.set('callbackUrl', pathname);
      return NextResponse.redirect(signInUrl);
    }

    // Check admin access
    if (isAdminRoute && !isAdmin(session)) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
  } catch (error) {
    console.error('Middleware error:', error);
    // On error, redirect to sign-in
    const signInUrl = new URL('/sign-in', request.url);
    signInUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(signInUrl);
  }
}

export const config = {
  matcher: [
    // Match all routes except API, static assets, and public files
    '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
  ],
};

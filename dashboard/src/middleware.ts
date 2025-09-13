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

  // Handle CORS for API routes
  if (pathname.startsWith('/api/')) {
    const response = NextResponse.next();

    // Allow requests from the marketing site
    const origin = request.headers.get('origin');
    if (
      origin === 'http://localhost:3000' ||
      origin === 'https://localhost:3000'
    ) {
      response.headers.set('Access-Control-Allow-Origin', origin);
      response.headers.set('Access-Control-Allow-Credentials', 'true');
      response.headers.set(
        'Access-Control-Allow-Methods',
        'GET, POST, PUT, DELETE, OPTIONS'
      );
      response.headers.set(
        'Access-Control-Allow-Headers',
        'Content-Type, Authorization'
      );
    }

    // Handle preflight requests
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 200, headers: response.headers });
    }

    return response;
  }

  // Skip middleware for Next.js internals
  if (pathname.startsWith('/_next/')) {
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
    // Match all routes including API, but exclude static assets
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
};

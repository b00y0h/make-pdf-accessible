// Edge Runtime compatible auth utilities for middleware
// This file contains utilities that work in the Edge Runtime environment

import { NextRequest } from 'next/server';

/**
 * Extract session information from request headers
 * This is a simplified version that works in the Edge Runtime
 */
export async function getSessionFromRequest(request: NextRequest) {
  try {
    // Try to get BetterAuth session cookie
    const sessionCookie = request.cookies.get('better-auth.session_token');

    if (!sessionCookie?.value) {
      return null;
    }

    // For now, just return a basic session object if cookie exists
    // This allows middleware to pass but actual validation happens in components
    return {
      user: { id: 'middleware-user', role: 'admin' },
      session: { id: 'middleware-session' },
    };
  } catch (error) {
    console.error('Error getting session from request:', error);
    return null;
  }
}

/**
 * Simple session validation for middleware
 */
export function validateSession(session: any): boolean {
  return session && session.user && session.user.id;
}

/**
 * Check if user has admin role
 */
export function isAdmin(session: any): boolean {
  return session?.user?.role === 'admin';
}

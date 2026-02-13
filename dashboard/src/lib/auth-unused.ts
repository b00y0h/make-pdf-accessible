// Client-side auth configuration (no database imports)
// For server-side usage, import from './auth-server'

import { createAuthClient } from 'better-auth/client';

// Create client-only auth instance
export const authClient = createAuthClient({
  baseURL:
    typeof window !== 'undefined'
      ? window.location.origin
      : 'http://localhost:3001',
  fetchOptions: {
    onRequest: (context) => {
      // Add any request interceptors here
    },
    onResponse: (context) => {
      // Add any response interceptors here
    },
    onError: (context) => {
      console.error('Auth request failed:', context);
    },
  },
});

// Re-export for compatibility
export const auth = authClient;

// Type definitions (these should match the server-side types)
export interface User {
  id: string;
  email: string;
  name: string;
  username?: string;
  role?: string;
  orgId?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Session {
  id: string;
  userId: string;
  user: User;
  expiresAt: Date;
  token: string;
}

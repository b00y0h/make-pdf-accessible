import { betterAuth } from 'better-auth';
import { username } from 'better-auth/plugins';
import { nextCookies } from 'better-auth/next-js';
import { Pool } from 'pg';

// Server-only auth configuration
export const auth = betterAuth({
  database: new Pool({
    connectionString:
      process.env.AUTH_DATABASE_URL ||
      'postgresql://postgres:password@localhost:5433/better_auth',
  }),
  baseURL: process.env.BETTER_AUTH_URL || 'http://localhost:3001',
  secret:
    process.env.BETTER_AUTH_SECRET ||
    'your-better-auth-secret-change-in-production',
  trustedOrigins: [
    'http://localhost:3000',
    'http://localhost:3001',
    'http://dashboard:3001',
  ],
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Set to true in production
    async sendResetPassword(data, request) {
      // Password reset email implementation needed
      // For now, log the request in development
      if (process.env.NODE_ENV === 'development') {
        console.log('Password reset requested for:', data.user.email);
        console.log('Reset URL:', data.url);
      }
      // TODO: Implement actual email sending in production
    },
  },
  plugins: [
    username(),
    nextCookies(), // Must be last plugin for proper cookie handling
  ],
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID || '',
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
      redirectUri: process.env.BETTER_AUTH_URL
        ? `${process.env.BETTER_AUTH_URL}/api/auth/callback/google`
        : 'http://localhost:3001/api/auth/callback/google',
    },
    github: {
      clientId: process.env.GITHUB_CLIENT_ID || '',
      clientSecret: process.env.GITHUB_CLIENT_SECRET || '',
      redirectUri: process.env.BETTER_AUTH_URL
        ? `${process.env.BETTER_AUTH_URL}/api/auth/callback/github`
        : 'http://localhost:3001/api/auth/callback/github',
    },
    apple: {
      clientId: process.env.APPLE_CLIENT_ID || '',
      clientSecret: process.env.APPLE_CLIENT_SECRET || '',
    },
    discord: {
      clientId: process.env.DISCORD_CLIENT_ID || '',
      clientSecret: process.env.DISCORD_CLIENT_SECRET || '',
    },
    facebook: {
      clientId: process.env.FACEBOOK_CLIENT_ID || '',
      clientSecret: process.env.FACEBOOK_CLIENT_SECRET || '',
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
  },
  user: {
    additionalFields: {
      role: {
        type: 'string',
        required: false,
        defaultValue: 'user',
      },
      orgId: {
        type: 'string',
        required: false,
      },
    },
  },
  advanced: {
    crossSubDomainCookies: {
      enabled: true,
      domain: '.localhost',
    },
    database: {
      generateId: () => crypto.randomUUID(),
    },
  },
});

export type Session = typeof auth.$Infer.Session;

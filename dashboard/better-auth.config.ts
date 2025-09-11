import { betterAuth } from 'better-auth';
import { username } from 'better-auth/plugins';
import { Pool } from 'pg';

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
  trustedOrigins: ['http://localhost:3001', 'http://dashboard:3001'],
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
    async sendResetPassword(data, request) {
      // Password reset email implementation needed
      // For now, log the request
      if (process.env.NODE_ENV === 'development') {
        // Only log in development
      }
    },
  },
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
  plugins: [username()],
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
});

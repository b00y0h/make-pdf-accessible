# Social Authentication Setup Guide

## Current Status

Your better-auth configuration is now properly set up with social providers. Here's what's been configured:

### ✅ Completed Setup

1. **Better-Auth Configuration**: Updated `src/lib/auth-server.ts` with social providers
2. **Client Configuration**: Updated `src/lib/auth-client.ts` to use the official better-auth React client
3. **Environment Variables**: Added required environment variables to `.env.local` and `.env.example`
4. **API Routes**: The catch-all route `[...all]/route.ts` is properly configured

### 🔧 Social Providers Configured

- Google OAuth
- GitHub OAuth
- Apple OAuth
- Discord OAuth
- Facebook OAuth

## Testing Social Authentication

### 1. Start the Development Server

```bash
cd dashboard
pnpm dev
```

### 2. Test Social Login Endpoints

Once the server is running, you can test the social auth endpoints:

```bash
# Test Google OAuth (should redirect to Google)
curl -I http://localhost:3001/api/auth/sign-in/social/google

# Test GitHub OAuth (should redirect to GitHub)
curl -I http://localhost:3001/api/auth/sign-in/social/github
```

You should see `302` redirects to the respective OAuth providers.

### 3. Set Up OAuth Applications

To actually use social login, you need to create OAuth applications with each provider:

#### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:3001/api/auth/callback/google`
6. Update `.env.local` with your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

#### GitHub OAuth Setup

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App
3. Set Authorization callback URL: `http://localhost:3001/api/auth/callback/github`
4. Update `.env.local` with your `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`

#### Discord OAuth Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to OAuth2 section
4. Add redirect URI: `http://localhost:3001/api/auth/callback/discord`
5. Update `.env.local` with your `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET`

### 4. Test in Browser

1. Navigate to `http://localhost:3001/sign-in`
2. Click on any social provider button
3. You should be redirected to the provider's OAuth page
4. After authorization, you'll be redirected back to your app

## Your Sign-In Page

Your existing sign-in page at `/sign-in/page.tsx` is already properly configured and should work with the social providers once you add the real OAuth credentials.

The social login buttons use the better-auth client methods:

```typescript
await signIn.social({
  provider: 'google', // or "github", "apple", "discord", "facebook"
  callbackURL: '/dashboard',
});
```

## Troubleshooting

### Common Issues

1. **"Provider not configured" error**: Make sure environment variables are set correctly
2. **Redirect URI mismatch**: Ensure OAuth app redirect URIs match exactly
3. **CORS errors**: Check `trustedOrigins` in auth configuration
4. **Database errors**: Ensure PostgreSQL is running and better-auth tables are created

### Debug Mode

Add this to your `.env.local` for more detailed logging:

```bash
DEBUG=better-auth:*
```

## Next Steps

1. Set up OAuth applications with your preferred providers
2. Add real credentials to `.env.local`
3. Test the social login flow
4. Consider adding email verification for production
5. Set up proper error handling and user feedback

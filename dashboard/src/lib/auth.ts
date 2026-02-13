import { createAuthClient } from 'better-auth/react';

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

export interface AuthResponse {
  user: User | null;
  error?: string;
}

// Create the better-auth client
export const authClient = createAuthClient({
  baseURL:
    typeof window !== 'undefined'
      ? window.location.origin
      : 'http://localhost:3001',
});

// Social provider types
export type SocialProvider =
  | 'google'
  | 'github'
  | 'apple'
  | 'discord'
  | 'facebook';

class AuthService {
  async getSession(): Promise<AuthResponse> {
    try {
      const session = await authClient.getSession();
      return { user: session.data?.user || null };
    } catch (error) {
      console.error('Failed to get session:', error);
      return { user: null, error: 'Failed to get session' };
    }
  }

  async signIn(email: string, password: string): Promise<AuthResponse> {
    try {
      const result = await authClient.signIn.email({
        email,
        password,
      });

      if (result.error) {
        return { user: null, error: result.error.message };
      }

      return { user: result.data?.user || null };
    } catch (error) {
      console.error('Failed to sign in:', error);
      return { user: null, error: 'Failed to sign in' };
    }
  }

  async signUp(
    email: string,
    password: string,
    name?: string,
    username?: string
  ): Promise<AuthResponse> {
    try {
      const result = await authClient.signUp.email({
        email,
        password,
        name: name || '',
      });

      if (result.error) {
        return { user: null, error: result.error.message };
      }

      return { user: result.data?.user || null };
    } catch (error) {
      console.error('Failed to sign up:', error);
      return { user: null, error: 'Failed to sign up' };
    }
  }

  async signInWithSocial(
    provider: SocialProvider,
    redirectTo?: string
  ): Promise<void> {
    try {
      await authClient.signIn.social({
        provider,
        callbackURL: redirectTo || window.location.origin + '/dashboard',
      });
    } catch (error) {
      console.error(`Failed to sign in with ${provider}:`, error);
      throw error;
    }
  }

  async signOut(): Promise<void> {
    try {
      await authClient.signOut();
    } catch (error) {
      console.error('Failed to sign out:', error);
    }
  }

  async resetPassword(
    email: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const result = await authClient.requestPasswordReset({
        email,
        redirectTo: window.location.origin + '/reset-password',
      });

      if (result.error) {
        return { success: false, error: result.error.message };
      }

      return { success: true };
    } catch (error) {
      console.error('Failed to reset password:', error);
      return { success: false, error: 'Failed to reset password' };
    }
  }

  async updatePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const result = await authClient.changePassword({
        newPassword,
        currentPassword,
      });

      if (result.error) {
        return { success: false, error: result.error.message };
      }

      return { success: true };
    } catch (error) {
      console.error('Failed to update password:', error);
      return { success: false, error: 'Failed to update password' };
    }
  }
}

export const auth = new AuthService();

// Export hooks for React components
export const useSession = authClient.useSession;
export const useUser = () => {
  const session = authClient.useSession();
  return session.data?.user || null;
};

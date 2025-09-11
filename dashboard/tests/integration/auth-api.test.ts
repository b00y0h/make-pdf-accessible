/**
 * Authentication API Tests
 * Tests the BetterAuth integration endpoints
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Authentication API Endpoints', () => {
  test.describe('GET /api/auth/session', () => {
    test('should return session data', async ({ request }) => {
      const response = await request.get(`${BASE_URL}/api/auth/session`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      // When not authenticated, should return null or empty user
      expect(data).toBeDefined();
    });
  });

  test.describe('POST /api/auth/sign-in/email', () => {
    test('should reject invalid credentials', async ({ request }) => {
      const response = await request.post(
        `${BASE_URL}/api/auth/sign-in/email`,
        {
          data: {
            email: 'nonexistent@example.com',
            password: 'wrongpassword',
          },
        }
      );

      expect(response.status()).toBe(400);
    });

    test('should reject invalid email format', async ({ request }) => {
      const response = await request.post(
        `${BASE_URL}/api/auth/sign-in/email`,
        {
          data: {
            email: 'not-an-email',
            password: 'password123',
          },
        }
      );

      expect(response.status()).toBe(400);
    });

    test('should reject empty credentials', async ({ request }) => {
      const response = await request.post(
        `${BASE_URL}/api/auth/sign-in/email`,
        {
          data: {
            email: '',
            password: '',
          },
        }
      );

      expect(response.status()).toBe(400);
    });
  });

  test.describe('POST /api/auth/sign-up/email', () => {
    test('should reject invalid email format for signup', async ({
      request,
    }) => {
      const response = await request.post(
        `${BASE_URL}/api/auth/sign-up/email`,
        {
          data: {
            email: 'invalid-email',
            password: 'Password123!',
            name: 'Test User',
          },
        }
      );

      expect(response.status()).toBe(400);
    });

    test('should reject short passwords', async ({ request }) => {
      const response = await request.post(
        `${BASE_URL}/api/auth/sign-up/email`,
        {
          data: {
            email: 'test@example.com',
            password: '123',
            name: 'Test User',
          },
        }
      );

      expect(response.status()).toBe(400);
    });
  });

  test.describe('POST /api/auth/sign-out', () => {
    test('should successfully sign out', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/auth/sign-out`);
      expect(response.ok()).toBeTruthy();
    });
  });

  test.describe('Social Auth Endpoints', () => {
    test('should have Google OAuth endpoint', async ({ request }) => {
      const response = await request.get(
        `${BASE_URL}/api/auth/sign-in/social/google`,
        {
          maxRedirects: 0,
        }
      );

      // Should redirect to Google OAuth
      expect([302, 307]).toContain(response.status());
    });

    test('should have GitHub OAuth endpoint', async ({ request }) => {
      const response = await request.get(
        `${BASE_URL}/api/auth/sign-in/social/github`,
        {
          maxRedirects: 0,
        }
      );

      // Should redirect to GitHub OAuth
      expect([302, 307]).toContain(response.status());
    });
  });
});

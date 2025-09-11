import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@playwright/test';
import { chromium, Browser, Page } from '@playwright/test';

describe('Authentication Flow', () => {
  let browser: Browser;
  let page: Page;
  const baseURL = 'http://localhost:3001';
  
  beforeAll(async () => {
    browser = await chromium.launch();
  });
  
  afterAll(async () => {
    await browser.close();
  });
  
  beforeEach(async () => {
    page = await browser.newPage();
  });
  
  describe('Sign In Page', () => {
    it('should display the sign-in form', async () => {
      await page.goto(`${baseURL}/sign-in`);
      
      // Check for email input
      const emailInput = await page.locator('input[name="email"]');
      await expect(emailInput).toBeVisible();
      
      // Check for password input
      const passwordInput = await page.locator('input[name="password"]');
      await expect(passwordInput).toBeVisible();
      
      // Check for submit button
      const submitButton = await page.locator('button[type="submit"]');
      await expect(submitButton).toBeVisible();
      await expect(submitButton).toContainText('Sign in');
    });
    
    it('should display social login buttons', async () => {
      await page.goto(`${baseURL}/sign-in`);
      
      // Check for social provider buttons
      const googleButton = await page.locator('button:has-text("Google")');
      await expect(googleButton).toBeVisible();
      
      const githubButton = await page.locator('button:has-text("GitHub")');
      await expect(githubButton).toBeVisible();
    });
    
    it('should show validation errors for empty form submission', async () => {
      await page.goto(`${baseURL}/sign-in`);
      
      // Click submit without filling form
      const submitButton = await page.locator('button[type="submit"]');
      await submitButton.click();
      
      // Wait for validation messages
      await page.waitForTimeout(500);
      
      // Check for required field indicators or error messages
      const emailInput = await page.locator('input[name="email"]');
      const emailRequired = await emailInput.evaluate((el: HTMLInputElement) => el.required);
      expect(emailRequired).toBe(true);
      
      const passwordInput = await page.locator('input[name="password"]');
      const passwordRequired = await passwordInput.evaluate((el: HTMLInputElement) => el.required);
      expect(passwordRequired).toBe(true);
    });
  });
  
  describe('Authentication API', () => {
    it('should handle invalid credentials', async () => {
      const response = await page.request.post(`${baseURL}/api/auth/sign-in/email`, {
        data: {
          email: 'nonexistent@example.com',
          password: 'wrongpassword'
        }
      });
      
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body).toHaveProperty('error');
    });
    
    it('should validate email format', async () => {
      const response = await page.request.post(`${baseURL}/api/auth/sign-in/email`, {
        data: {
          email: 'invalid-email',
          password: 'password123'
        }
      });
      
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body).toHaveProperty('error');
    });
  });
  
  describe('Session Management', () => {
    it('should check session endpoint', async () => {
      const response = await page.request.get(`${baseURL}/api/auth/session`);
      
      // Should return session data (null if not logged in)
      expect(response.ok()).toBe(true);
      const body = await response.json();
      
      // When not logged in, should return null or empty session
      if (!body.user) {
        expect(body.user).toBeNull();
      }
    });
  });
  
  describe('Protected Routes', () => {
    it('should redirect to sign-in when accessing protected routes', async () => {
      // Try to access a protected route
      await page.goto(`${baseURL}/dashboard`);
      
      // Should be redirected to sign-in
      await page.waitForURL(/\/sign-in/);
      expect(page.url()).toContain('/sign-in');
    });
  });
  
  describe('Sign Out', () => {
    it('should have sign-out endpoint', async () => {
      const response = await page.request.post(`${baseURL}/api/auth/sign-out`);
      
      // Sign out should always succeed
      expect(response.ok()).toBe(true);
    });
  });
});
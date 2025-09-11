import { describe, it, expect } from '@jest/globals';

describe('Authentication Utilities', () => {
  describe('Email validation', () => {
    const isValidEmail = (email: string): boolean => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(email);
    };

    it('should validate correct email formats', () => {
      expect(isValidEmail('user@example.com')).toBe(true);
      expect(isValidEmail('test.user@company.co.uk')).toBe(true);
      expect(isValidEmail('name+tag@domain.org')).toBe(true);
    });

    it('should reject invalid email formats', () => {
      expect(isValidEmail('notanemail')).toBe(false);
      expect(isValidEmail('missing@domain')).toBe(false);
      expect(isValidEmail('@nodomain.com')).toBe(false);
      expect(isValidEmail('spaces in@email.com')).toBe(false);
    });
  });

  describe('Password strength', () => {
    const isStrongPassword = (password: string): boolean => {
      // At least 8 characters, one uppercase, one lowercase, one number
      const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
      return passwordRegex.test(password);
    };

    it('should accept strong passwords', () => {
      expect(isStrongPassword('Password123')).toBe(true);
      expect(isStrongPassword('MySecure2024Pass')).toBe(true);
    });

    it('should reject weak passwords', () => {
      expect(isStrongPassword('password')).toBe(false); // No uppercase or number
      expect(isStrongPassword('PASSWORD123')).toBe(false); // No lowercase
      expect(isStrongPassword('Pass123')).toBe(false); // Too short
      expect(isStrongPassword('PasswordABC')).toBe(false); // No number
    });
  });

  describe('Role validation', () => {
    const VALID_ROLES = ['user', 'admin', 'super_admin'] as const;
    type Role = typeof VALID_ROLES[number];

    const isValidRole = (role: string): role is Role => {
      return VALID_ROLES.includes(role as Role);
    };

    it('should validate correct roles', () => {
      expect(isValidRole('user')).toBe(true);
      expect(isValidRole('admin')).toBe(true);
      expect(isValidRole('super_admin')).toBe(true);
    });

    it('should reject invalid roles', () => {
      expect(isValidRole('moderator')).toBe(false);
      expect(isValidRole('superuser')).toBe(false);
      expect(isValidRole('')).toBe(false);
    });
  });
});
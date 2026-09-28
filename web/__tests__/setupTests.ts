import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from './msw/handlers';

// Set test environment
if (!process.env.NODE_ENV) {
  process.env.NODE_ENV = 'test';
}

// Setup MSW server
const server = setupServer(...handlers);

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  // Testing Library only unmounts automatically when Vitest globals are enabled
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});

// Global test utilities
export { server };

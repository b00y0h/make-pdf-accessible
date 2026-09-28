import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Coverage is configured once for the whole run; projects can't set their own.
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
      exclude: [
        'node_modules/**',
        '.next/**',
        'dist/**',
        'coverage/**',
        '.husky/**',
        '.github/**',
        'scripts/*-init/**',
        'tests/fixtures/**',
        '**/*.d.ts',
        '**/*.config.*',
        '**/build/**',
      ],
    },

    projects: [
      // Web app (Next.js with React)
      {
        test: {
          name: 'web-jsdom',
          root: './web',
          environment: 'jsdom',
          // web's *.test.* files run under Jest (web/jest.config.js)
          include: ['__tests__/**/*.spec.{ts,tsx}'],
          setupFiles: ['./__tests__/setupTests.ts'],
        },
      },

      // Dashboard app (Next.js with React)
      {
        test: {
          name: 'dashboard-jsdom',
          root: './dashboard',
          environment: 'jsdom',
          setupFiles: ['./test/setupTests.ts'],
        },
      },

      // API service
      {
        test: {
          name: 'api-node',
          root: './services/api',
          environment: 'node',
          setupFiles: ['./test/setupTests.ts'],
        },
      },

      // Functions
      {
        test: {
          name: 'functions-node',
          root: './services/functions',
          environment: 'node',
        },
      },

      // Worker service
      {
        test: {
          name: 'worker-node',
          root: './services/worker',
          environment: 'node',
        },
      },

      // Packages
      {
        test: {
          name: 'packages-node',
          root: './packages',
          environment: 'node',
        },
      },

      // Integrations
      {
        test: {
          name: 'integrations-node',
          root: './integrations',
          environment: 'node',
        },
      },
    ],
  },
});

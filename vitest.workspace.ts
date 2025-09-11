import { defineWorkspace } from 'vitest/config';

export default defineWorkspace(
  [
    // Web app (Next.js with React)
    {
      test: {
        name: 'web-jsdom',
        root: './web',
        environment: 'jsdom',
        setupFiles: ['./web/__tests__/setupTests.ts'],
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },

    // Dashboard app (Next.js with React)
    {
      test: {
        name: 'dashboard-jsdom',
        root: './dashboard',
        environment: 'jsdom',
        setupFiles: ['./test/setupTests.ts'],
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },

    // API service
    {
      test: {
        name: 'api-node',
        root: './services/api',
        environment: 'node',
        setupFiles: ['./test/setupTests.ts'],
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },

    // Functions
    {
      test: {
        name: 'functions-node',
        root: './services/functions',
        environment: 'node',
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },

    // Worker service
    {
      test: {
        name: 'worker-node',
        root: './services/worker',
        environment: 'node',
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },

    // Packages
    {
      test: {
        name: 'packages-node',
        root: './packages',
        environment: 'node',
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },

    // Integrations
    {
      test: {
        name: 'integrations-node',
        root: './integrations',
        environment: 'node',
        coverage: {
          provider: 'v8',
          reporter: ['text', 'html', 'lcov'],
          thresholds: {
            statements: 80,
            branches: 80,
            functions: 80,
            lines: 80,
          },
        },
      },
    },
  ],
  {
    test: {
      // Global test configuration
      globals: true,
      coverage: {
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
    },
  }
);

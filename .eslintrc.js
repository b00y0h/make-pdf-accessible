/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  ignorePatterns: [
    'node_modules/',
    'dist/',
    'build/',
    '.next/',
    'out/',
    '**/*.pyc',
    '__pycache__/',
    'venv/',
    '.venv/',
    // These apps lint themselves with their own eslint.config.mjs (ESLint 9).
    'apps/',
    'web/',
    'dashboard/',
  ],
  overrides: [
    {
      files: ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],
      extends: [
        'eslint:recommended',
        'plugin:@typescript-eslint/recommended',
        'prettier',
      ],
      parser: '@typescript-eslint/parser',
      plugins: ['@typescript-eslint'],
      env: {
        node: true,
        es2022: true,
      },
    },
    {
      // Scripts that site owners embed in their pages.
      files: ['integrations/**/*.js'],
      env: {
        browser: true,
      },
    },
    {
      // Run by the mongo shell when the database container starts.
      files: ['scripts/mongo-init/*.js'],
      globals: {
        db: 'writable',
        print: 'readonly',
        rs: 'readonly',
        sleep: 'readonly',
      },
    },
  ],
};

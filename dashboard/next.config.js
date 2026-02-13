const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost'],
    dangerouslyAllowSVG: true,
  },
  env: {
    CUSTOM_KEY: 'my-value',
  },
  webpack: (config, { isServer }) => {
    // Add explicit path alias resolution
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './src'),
    };

    // Handle node: protocol imports in browser builds
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        'node:sqlite': false,
        'node:fs': false,
        'node:path': false,
        'node:crypto': false,
        fs: false,
        path: false,
        crypto: false,
        sqlite3: false,
        'better-sqlite3': false,
      };

      // Add externals for Node.js modules that shouldn't be bundled for browser
      config.externals.push({
        'better-sqlite3': 'commonjs better-sqlite3',
        'node:sqlite': 'commonjs node:sqlite',
      });
    }

    return config;
  },
  serverExternalPackages: ['better-sqlite3'],
  outputFileTracingRoot: '../',
};

module.exports = nextConfig;

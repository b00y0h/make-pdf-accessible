const path = require('path');
const fs = require('fs');

// Debug: log the resolved paths and verify files exist
const srcPath = path.resolve(__dirname, 'src');
const libPath = path.join(srcPath, 'lib');
console.log('[next.config.js] __dirname:', __dirname);
console.log('[next.config.js] srcPath:', srcPath);
console.log('[next.config.js] srcPath exists:', fs.existsSync(srcPath));
console.log('[next.config.js] libPath:', libPath);
console.log('[next.config.js] libPath exists:', fs.existsSync(libPath));
if (fs.existsSync(libPath)) {
  console.log(
    '[next.config.js] lib contents:',
    fs.readdirSync(libPath).slice(0, 5)
  );
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost'],
    dangerouslyAllowSVG: true,
  },
  env: {
    CUSTOM_KEY: 'my-value',
  },
  webpack: (config, { isServer, dir }) => {
    // Use 'dir' from Next.js context which is the project root
    const projectSrc = path.join(dir, 'src');
    console.log('[webpack] dir:', dir);
    console.log('[webpack] projectSrc:', projectSrc);

    // Add explicit path alias resolution for all @/ paths
    config.resolve.alias = {
      ...config.resolve.alias,
      '@/lib': path.join(projectSrc, 'lib'),
      '@/components': path.join(projectSrc, 'components'),
      '@/hooks': path.join(projectSrc, 'hooks'),
      '@/app': path.join(projectSrc, 'app'),
      '@': projectSrc,
    };

    // Ensure modules resolution includes src directory
    config.resolve.modules = [
      ...(config.resolve.modules || []),
      projectSrc,
      'node_modules',
    ];

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

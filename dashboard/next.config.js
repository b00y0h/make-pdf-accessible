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
    remotePatterns: [{ hostname: 'localhost' }],
    dangerouslyAllowSVG: true,
  },
  env: {
    CUSTOM_KEY: 'my-value',
  },
  // Turbopack resolves the `@/*` aliases from tsconfig.json paths.
  serverExternalPackages: ['better-sqlite3'],
  outputFileTracingRoot: '../',
};

module.exports = nextConfig;

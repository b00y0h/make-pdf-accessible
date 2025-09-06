/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['localhost'],
    dangerouslyAllowSVG: true,
  },
  env: {
    CUSTOM_KEY: 'my-value',
  },
}

module.exports = nextConfig

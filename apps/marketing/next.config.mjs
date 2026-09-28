/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: the site is served from S3 through CloudFront with no server runtime (ADR-0009).
  output: 'export',
  // Every route becomes <route>/index.html so S3 keys map to paths; CloudFront rewrites the slash form.
  trailingSlash: true,
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  // Security headers are set by the CloudFront response headers policy (infra/terraform/modules/static-site).
};

export default nextConfig;

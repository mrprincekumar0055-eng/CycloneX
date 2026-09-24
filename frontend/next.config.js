/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: '/',
        destination: '/dashboard',
        permanent: false,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
      { source: '/tracking', destination: '/cyclones' },
      { source: '/prediction', destination: '/forecast' },
      { source: '/scenarios', destination: '/demo' },
      { source: '/training', destination: '/model-performance' },
      { source: '/models', destination: '/model-performance' },
      { source: '/data', destination: '/exposure' },
      { source: '/about', destination: '/judge-qa' },
      { source: '/authority', destination: '/admin' },
    ];
  },
};

module.exports = nextConfig;


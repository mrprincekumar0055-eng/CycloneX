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
    const backendUrl = process.env.BACKEND_URL
      ? process.env.BACKEND_URL.replace(/\/+$/, '')
      : (process.env.NODE_ENV !== 'production' ? 'http://127.0.0.1:8000' : null);

    const apiRewrites = backendUrl
      ? [
          {
            source: '/api/v1/:path*',
            destination: `${backendUrl}/api/v1/:path*`,
          },
        ]
      : [];

    return [
      ...apiRewrites,
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


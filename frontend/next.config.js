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
    const rawBackend = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
    let apiRewrites = [];

    if (rawBackend && (rawBackend.startsWith('http://') || rawBackend.startsWith('https://'))) {
      const cleanBackend = rawBackend.replace(/\/+$/, '').replace(/\/api\/v1$/, '');
      apiRewrites = [
        {
          source: '/api/v1/:path*',
          destination: `${cleanBackend}/api/v1/:path*`,
        },
      ];
    } else if (process.env.NODE_ENV !== 'production') {
      apiRewrites = [
        {
          source: '/api/v1/:path*',
          destination: 'http://127.0.0.1:8000/api/v1/:path*',
        },
      ];
    }

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


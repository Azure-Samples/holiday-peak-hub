/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // For Azure Static Web Apps deployment

  // API proxy for local development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : 'http://localhost:8000/api/:path*',
      },
    ];
  },

  // Image optimization configuration
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'https',
        hostname: 'holidaypeakhubstorage.blob.core.windows.net',
      },
      {
        protocol: 'https',
        hostname: '*.azurestaticapps.net',
      },
    ],
    unoptimized: process.env.NODE_ENV === 'production', // For static export
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_ENTRA_CLIENT_ID: process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID,
    NEXT_PUBLIC_ENTRA_TENANT_ID: process.env.NEXT_PUBLIC_ENTRA_TENANT_ID,
  },
};

module.exports = nextConfig;

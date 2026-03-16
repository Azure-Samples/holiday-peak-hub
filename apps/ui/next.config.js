/** @type {import('next').NextConfig} */
const isTestEnv = process.env.NODE_ENV === 'test';
const crudApiUrl = process.env.NEXT_PUBLIC_CRUD_API_URL || (isTestEnv ? 'http://localhost:8000' : undefined);

if (!crudApiUrl) {
  throw new Error('NEXT_PUBLIC_CRUD_API_URL must be set to the cloud CRUD gateway URL.');
}

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // For Azure Static Web Apps deployment
  typescript: {
    ignoreBuildErrors: true,
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
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
      {
        protocol: 'https',
        hostname: 'picsum.photos',
      },
    ],
    unoptimized: process.env.NODE_ENV === 'production', // For static export
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_CRUD_API_URL: crudApiUrl,
    NEXT_PUBLIC_API_URL: crudApiUrl,
    NEXT_PUBLIC_ENTRA_CLIENT_ID: process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID,
    NEXT_PUBLIC_ENTRA_TENANT_ID: process.env.NEXT_PUBLIC_ENTRA_TENANT_ID,
  },
};

module.exports = nextConfig;

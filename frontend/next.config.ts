import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/screenshots/**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        pathname: '/screenshots/**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/screenshots/:path*',
        destination: 'http://localhost:8000/screenshots/:path*',
      },
    ]
  },
}

export default nextConfig

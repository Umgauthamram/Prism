import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/env/:path*',
        destination: `${process.env.NEXT_PUBLIC_ENV_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },
};

export default nextConfig;

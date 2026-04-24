import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  async rewrites() {
    return [];
  },
};

export default nextConfig;

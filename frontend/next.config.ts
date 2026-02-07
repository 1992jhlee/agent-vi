import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // ISR 설정
  },
  async redirects() {
    return [
      // Legacy report URLs → insights
      {
        source: "/reports",
        destination: "/insights",
        permanent: true, // 308 redirect
      },
      {
        source: "/reports/:path*",
        destination: "/insights/:path*",
        permanent: true,
      },
      // Legacy company URLs → research
      {
        source: "/companies",
        destination: "/research",
        permanent: true,
      },
      {
        source: "/companies/:path*",
        destination: "/research/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;

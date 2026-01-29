import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // ISR 설정
  },
};

export default nextConfig;

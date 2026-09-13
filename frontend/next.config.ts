import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false,
  async redirects() {
    return [{ source: "/home", destination: "/", permanent: false }];
  },
};

export default nextConfig;

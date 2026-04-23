import type { NextConfig } from "next";

const apiBase = process.env.INTERNAL_OPS_API_BASE ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/admin/:path*",
        destination: `${apiBase}/admin/:path*`,
      },
    ];
  },
};

export default nextConfig;

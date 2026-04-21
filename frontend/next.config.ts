import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16: Playwright navega via 127.0.0.1; sem esta lista o webpack-hmr
  // bloqueia o client bundle e a página não hidrata.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;

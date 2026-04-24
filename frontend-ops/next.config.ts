import type { NextConfig } from "next";

// Default :8001 evita colisão com o backend principal do dev em :8000.
// Override com INTERNAL_OPS_API_BASE quando rodar o backend de ops noutra porta.
const apiBase = process.env.INTERNAL_OPS_API_BASE ?? "http://127.0.0.1:8001";

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

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// F12.1 · ADR-130 — registra src/i18n/request.ts como provider de locale.
const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  // Next 16: Playwright navega via 127.0.0.1; sem esta lista o webpack-hmr
  // bloqueia o client bundle e a página não hidrata.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Upload de lote (até 150 docs × ~50MB). Default de 10MB trunca o multipart
  // e derruba a conexão com o backend (ECONNRESET).
  experimental: {
    proxyClientMaxBodySize: "512mb",
  },
  async rewrites() {
    // BACKEND_INTERNAL_URL=http://backend:8000 em prod (compose); fallback é dev local.
    const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default withNextIntl(nextConfig);

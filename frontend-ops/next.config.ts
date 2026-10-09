import type { NextConfig } from "next";

// Default :8001 evita colisão com o backend principal do dev em :8000.
// Override com INTERNAL_OPS_API_BASE quando rodar o backend de ops noutra porta.
// Lido no `next build` (o rewrite fica no routes-manifest): na imagem Docker é
// build arg. `||` e não `??`: string vazia viraria destino `/admin/:path*`, um
// rewrite para si mesmo; `new URL` derruba o build em vez de gravar lixo.
function resolveApiBase(): string {
  const base = process.env.INTERNAL_OPS_API_BASE || "http://127.0.0.1:8001";
  new URL(base);
  return base;
}

const apiBase = resolveApiBase();

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

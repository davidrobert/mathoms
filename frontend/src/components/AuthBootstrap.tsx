"use client";

/**
 * Instala, no client, o handler global de `token_revoked` (F9.2 · débito #6).
 *
 * Quando o backend retorna 401 com `detail.code === "token_revoked"`
 * (ex: usuário foi removido de um workspace), `apiFetch` chama o handler
 * e este redireciona para `/login`, preservando o path atual via `?next=`.
 *
 * Montado uma vez no layout do app (rota `(app)`). Fora dele, pages
 * públicas (login, register, /invite/[token]) não precisam do handler —
 * já não dependem de estado autenticado.
 */

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { setTokenRevokedHandler } from "@/lib/api";
import { clearCurrentUserCache } from "@/lib/useCurrentUser";

export function AuthBootstrap() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    setTokenRevokedHandler(() => {
      clearCurrentUserCache();
      const nextParam = pathname
        ? `?next=${encodeURIComponent(pathname)}`
        : "";
      router.replace(`/login${nextParam}`);
    });
    return () => setTokenRevokedHandler(null);
  }, [router, pathname]);

  return null;
}

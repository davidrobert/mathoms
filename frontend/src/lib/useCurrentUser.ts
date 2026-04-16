"use client";

/**
 * Hook que resolve o usuário autenticado (F9 · débito #4).
 *
 * Pareia com `useCurrentWorkspace` — enquanto aquele devolve o
 * workspace corrente e o role do user nele, este devolve a identidade
 * humana do usuário (id, email, nome).
 *
 * Cacheado em memória via module-level singleton para evitar request
 * duplicado quando múltiplos componentes montam ao mesmo tempo. Em
 * mudança de token (login/logout), rechama.
 */

import { useEffect, useState } from "react";
import { getMe, getToken, type UserResponse } from "./api";

let cachedUser: UserResponse | null = null;
let inflight: Promise<UserResponse> | null = null;

function resetCache() {
  cachedUser = null;
  inflight = null;
}

export function useCurrentUser() {
  const [user, setUser] = useState<UserResponse | null>(cachedUser);
  const [loading, setLoading] = useState(cachedUser === null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    if (cachedUser) {
      setUser(cachedUser);
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const promise = inflight ?? getMe();
        inflight = promise;
        const me = await promise;
        if (!cancelled) {
          cachedUser = me;
          setUser(me);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      } finally {
        inflight = null;
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { user, loading, error, reset: resetCache };
}

export function clearCurrentUserCache() {
  resetCache();
}

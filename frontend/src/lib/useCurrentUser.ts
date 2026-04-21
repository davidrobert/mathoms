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

interface LoadCallbacks {
  onUser: (u: UserResponse) => void;
  onError: (e: Error) => void;
  onDone: () => void;
  isCancelled: () => boolean;
}

async function fetchCurrentUser(cb: LoadCallbacks): Promise<void> {
  try {
    const promise = inflight ?? getMe();
    inflight = promise;
    const me = await promise;
    if (cb.isCancelled()) return;
    cachedUser = me;
    cb.onUser(me);
  } catch (err) {
    if (cb.isCancelled()) return;
    cb.onError(err instanceof Error ? err : new Error(String(err)));
  } finally {
    inflight = null;
    if (!cb.isCancelled()) cb.onDone();
  }
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
    fetchCurrentUser({
      onUser: setUser,
      onError: setError,
      onDone: () => setLoading(false),
      isCancelled: () => cancelled,
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { user, loading, error, reset: resetCache };
}

export function clearCurrentUserCache() {
  resetCache();
}

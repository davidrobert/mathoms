"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { AdminApiError } from "./api";

interface SettledFetch<Q, T> {
  query: Q;
  data: T | null;
  error: string | null;
}

export interface AdminFetchState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Busca `fetchFor(query)` a cada `query` nova (Object.is) e descarta a resposta de pedido já substituído. */
export function useAdminFetch<Q, T>(
  query: Q,
  fetchFor: (query: Q) => Promise<T>,
  failureCopy: string,
): AdminFetchState<T> {
  const [settled, setSettled] = useState<SettledFetch<Q, T> | null>(null);
  const fetchLatest = useEffectEvent(fetchFor);

  useEffect(() => {
    let cancelled = false;
    fetchLatest(query).then(
      (data) => {
        if (!cancelled) setSettled({ query, data, error: null });
      },
      (err: unknown) => {
        if (cancelled) return;
        const error = err instanceof AdminApiError ? `${err.status} · ${err.code}` : failureCopy;
        setSettled((prev) => ({ query, data: prev?.data ?? null, error }));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [query, failureCopy]);

  // loading e o erro escondido durante a nova busca derivam do pedido em voo: o
  // react-hooks 7 (set-state-in-effect) reprova o setLoading(true) síncrono no effect.
  const loading = settled === null || !Object.is(settled.query, query);
  return { data: settled?.data ?? null, error: loading ? null : (settled?.error ?? null), loading };
}

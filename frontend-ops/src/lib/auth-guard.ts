"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, AdminApiError } from "./api";
import type { AdminPrincipal } from "./types";

// Cookie ops_session vive em Path=/admin + HttpOnly, então middleware Next
// não consegue lê-lo. Gate fica client-side: chama /admin/me e redireciona
// para /login se 401. Ver ADR-116.
export function useAuthGuard(): {
  principal: AdminPrincipal | null;
  loading: boolean;
} {
  const router = useRouter();
  const [principal, setPrincipal] = useState<AdminPrincipal | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((p) => {
        if (!cancelled) {
          setPrincipal(p);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof AdminApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  return { principal, loading };
}

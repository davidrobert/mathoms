"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import type { ReportMode } from "@/generated/report-layout";

const VALID_MODES = new Set<ReportMode>(["estrategico", "tatico", "usa"]);

interface ReportModeContextValue {
  mode: ReportMode;
  setMode: (mode: ReportMode) => void;
}

const ReportModeContext = createContext<ReportModeContextValue | null>(null);

/** F9 · F3.2 — Provider com sync bidirecional URL ↔ state.
 *
 * - Lê `?mode=tatico` da URL na montagem (deep-link de modo)
 * - Atualiza `?mode=` quando o usuário troca via seletor no header
 * - Preserva hash existente (?mode=usa#S3 funciona)
 * - Modo inválido na URL → fallback para `estrategico`
 */
export function ReportModeProvider({
  initialMode = "estrategico",
  children,
}: {
  initialMode?: ReportMode;
  children: ReactNode;
}) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [mode, setModeState] = useState<ReportMode>(() => {
    const fromUrl = searchParams.get("mode") as ReportMode | null;
    if (fromUrl && VALID_MODES.has(fromUrl)) return fromUrl;
    return initialMode;
  });

  // Sync URL → state when URL changes externally (back/forward nav)
  useEffect(() => {
    const fromUrl = searchParams.get("mode") as ReportMode | null;
    if (fromUrl && VALID_MODES.has(fromUrl) && fromUrl !== mode) {
      setModeState(fromUrl);
    }
  }, [searchParams, mode]);

  const setMode = useCallback(
    (newMode: ReportMode) => {
      if (!VALID_MODES.has(newMode) || newMode === mode) return;
      setModeState(newMode);
      // Sync state → URL (shallow, no scroll reset)
      const params = new URLSearchParams(searchParams.toString());
      if (newMode === "estrategico") {
        params.delete("mode"); // default mode doesn't need URL param
      } else {
        params.set("mode", newMode);
      }
      const qs = params.toString();
      const hash = typeof window !== "undefined" ? window.location.hash : "";
      router.replace(`${pathname}${qs ? `?${qs}` : ""}${hash}`, {
        scroll: false,
      });
    },
    [mode, searchParams, router, pathname],
  );

  return (
    <ReportModeContext.Provider value={{ mode, setMode }}>
      {children}
    </ReportModeContext.Provider>
  );
}

export function useReportMode(): ReportModeContextValue {
  const ctx = useContext(ReportModeContext);
  if (!ctx) {
    throw new Error(
      "useReportMode deve ser usado dentro de <ReportModeProvider>",
    );
  }
  return ctx;
}

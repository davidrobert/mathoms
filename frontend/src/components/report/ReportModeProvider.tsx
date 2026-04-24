"use client";

import {
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import type { ReportMode } from "@/generated/report-layout";
import {
  ReportModeContext,
  VALID_MODES,
  useReportMode,
} from "./ReportModeContext";

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
      const params = new URLSearchParams(searchParams.toString());
      if (newMode === "estrategico") {
        params.delete("mode");
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

export { useReportMode };

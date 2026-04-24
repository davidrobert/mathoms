import type { ReactNode } from "react";
import type { ReportMode } from "@/generated/report-layout";
import { ReportModeContext } from "./ReportModeContext";

/** ADR-124 · Fase 11.1 — Provider estático para render path `/api/reports/[id]/export`.
 *
 * Usado por `renderToStaticMarkup` no Route Handler: não chama hooks de router
 * (`useSearchParams`/`useRouter`/`usePathname`), que falhariam fora de uma
 * Next Page. `setMode` é no-op — troca de modo em HTML auto-contido é inerte
 * (botões ficam visíveis mas não navegam).
 */
export function StaticReportModeProvider({
  mode,
  children,
}: {
  mode: ReportMode;
  children: ReactNode;
}) {
  return (
    <ReportModeContext.Provider value={{ mode, setMode: () => {} }}>
      {children}
    </ReportModeContext.Provider>
  );
}

import { AlertTriangle } from "lucide-react";
import { ReportCard } from "../ReportCard";
import type { DiagnosticoComportamental } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Card "Diagnóstico Comportamental".
 *  Lista padrões identificados com evidência e sugestão de mudança.
 */
export function DiagnosticoComportamentalCard({
  diagnostico,
}: {
  diagnostico: DiagnosticoComportamental[] | undefined;
}) {
  const items = diagnostico ?? [];

  return (
    <ReportCard variant="primary" size="half" title="Diagnóstico Comportamental">
      {items.length === 0 ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Nenhum padrão comportamental identificado.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((item, idx) => (
            <li
              key={idx}
              className="rounded-md border border-[var(--surface-border)] bg-[var(--surface-muted)] p-3"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-alert)]" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-[var(--surface-foreground)]">
                    {item.padrao}
                  </p>
                  {item.evidencia && (
                    <p className="text-xs text-[var(--surface-muted-foreground)]">
                      {item.evidencia}
                    </p>
                  )}
                  {item.mudanca_sugerida && (
                    <p className="text-xs text-[var(--brand-primary)]">
                      {item.mudanca_sugerida}
                    </p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </ReportCard>
  );
}

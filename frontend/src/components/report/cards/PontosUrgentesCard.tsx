import { AlertOctagon } from "lucide-react";
import { ReportCard } from "../ReportCard";
import { dedupeBySemanticKey } from "../utils/curadoriaDestaques";

interface PontoUrgente {
  prioridade?: string;
  acao?: string;
  impacto?: string;
}

/** Card "Pontos Urgentes" (S10).
 *
 * Sibling de `PontosFortesCard` com `variant="critical"`; recebe a
 * lista de `PontoUrgente` do DTO e a renderiza dentro de um `ReportCard`.
 * Curadoria defensiva (A28.l10): alerta circular de score não é exibido —
 * "Nenhum ponto urgente" honesto > alerta que não alerta.
 */
export function PontosUrgentesCard({
  pontos,
}: {
  pontos: PontoUrgente[] | unknown[] | undefined;
}) {
  const items = dedupeBySemanticKey((pontos ?? []) as PontoUrgente[]);

  return (
    <ReportCard variant="critical" size="half" title="Pontos Urgentes">
      {items.length === 0 ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Nenhum ponto urgente neste período.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((p, i) => (
            <li key={i} className="flex items-start gap-2">
              <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-loss)]" />
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold">{p.acao ?? `Ação ${i + 1}`}</p>
                  {p.prioridade && (
                    <span className="rounded-full bg-[color-mix(in_srgb,var(--semantic-loss)_15%,transparent)] px-2 py-0.5 text-[0.65rem] font-semibold uppercase text-[var(--semantic-loss-on-tint)]">
                      {p.prioridade}
                    </span>
                  )}
                </div>
                {p.impacto && (
                  <p className="text-xs text-[var(--surface-muted-foreground)]">
                    {p.impacto}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </ReportCard>
  );
}

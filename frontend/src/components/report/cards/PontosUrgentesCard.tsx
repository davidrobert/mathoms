import { AlertOctagon } from "lucide-react";
import { ReportCard } from "../ReportCard";
import { dedupeBySemanticKey } from "../utils/curadoriaDestaques";
import { fiduciaryDisclaimer } from "./protectionBundle.types";

interface PontoUrgente {
  prioridade?: string;
  acao?: string;
  impacto?: string;
  code?: string;
}

function citesCoverage(ponto: PontoUrgente): boolean {
  const text = `${ponto.code ?? ""} ${ponto.acao ?? ""}`;
  return /seguro_vida|seguro de vida|cobertura recomendada/i.test(text);
}

function UrgenteRow({
  ponto,
  index,
  effectiveDate,
}: {
  ponto: PontoUrgente;
  index: number;
  effectiveDate?: string | null;
}) {
  return (
    <li className="flex items-start gap-2">
      <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-loss)]" />
      <div>
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold">{ponto.acao ?? `Ação ${index + 1}`}</p>
          {ponto.prioridade && (
            <span className="rounded-full bg-[color-mix(in_srgb,var(--semantic-loss)_15%,transparent)] px-2 py-0.5 text-[0.65rem] font-semibold uppercase text-[var(--semantic-loss-on-tint)]">
              {ponto.prioridade}
            </span>
          )}
        </div>
        {ponto.impacto && (
          <p className="text-xs text-[var(--surface-muted-foreground)]">{ponto.impacto}</p>
        )}
        {citesCoverage(ponto) && (
          <p className="mt-1 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
            {fiduciaryDisclaimer("wealth management", effectiveDate)}
          </p>
        )}
      </div>
    </li>
  );
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
  effectiveDate = null,
}: {
  pontos: PontoUrgente[] | unknown[] | undefined;
  effectiveDate?: string | null;
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
            <UrgenteRow key={i} ponto={p} index={i} effectiveDate={effectiveDate} />
          ))}
        </ul>
      )}
    </ReportCard>
  );
}

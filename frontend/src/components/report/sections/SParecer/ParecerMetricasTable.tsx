"use client";

// ADR-199 Ato 5 §5b — Métricas observáveis (mini-trilha).
// `<progress>` HTML nativo com `aria-valuetext` p/ screen reader.

import type { Metrica } from "@/lib/api";

interface ParecerMetricasTableProps {
  metricas: Metrica[];
  /** Teaser tier free — sinaliza count gated. */
  gatedCount?: number;
}

/** Tenta extrair número do valor formatado (ex.: "4%" → 4). Retorna null se
 *  não der pra parsear — UI omite a mini-trilha nesse caso. */
function extractNumber(formatted: string): number | null {
  const cleaned = formatted.replace(/[^0-9,.-]/g, "").replace(",", ".");
  const n = parseFloat(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function ParecerMetricasTable({
  metricas,
  gatedCount = 0,
}: ParecerMetricasTableProps) {
  if (metricas.length === 0 && gatedCount === 0) return null;

  return (
    <section
      className="md:col-span-2"
      aria-labelledby="parecer-metricas-title"
      data-testid="parecer-metricas-table"
    >
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3
          id="parecer-metricas-title"
          className="font-heading text-lg font-semibold text-[var(--surface-foreground)]"
        >
          Métricas a observar
        </h3>
        {gatedCount > 0 && (
          <span className="text-xs text-[var(--surface-muted-foreground)]">
            +{gatedCount} no Premium
          </span>
        )}
      </header>

      {metricas.length === 0 ? (
        <p className="rounded-md border border-dashed border-[var(--surface-border)] p-4 text-center text-sm text-[var(--surface-muted-foreground)]">
          Destrave Premium para acompanhar métricas observáveis.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-[var(--surface-muted-foreground)]">
                <th className="py-2 pr-4">Métrica</th>
                <th className="py-2 pr-4">Valor atual</th>
                <th className="py-2 pr-4">Alvo</th>
                <th className="py-2 pr-4">Trilha</th>
                <th className="py-2 pr-4">Revisão</th>
                <th className="py-2 pr-4">§</th>
              </tr>
            </thead>
            <tbody>
              {metricas.map((m, idx) => (
                <MetricaRow key={`${m.nome}-${idx}`} metrica={m} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function MetricaRow({ metrica }: { metrica: Metrica }) {
  const atual = extractNumber(metrica.valor_atual);
  const alvo = extractNumber(metrica.target);
  const showProgress = atual !== null && alvo !== null && alvo > 0;
  const pct = showProgress
    ? Math.max(0, Math.min(100, ((atual ?? 0) / (alvo ?? 1)) * 100))
    : null;

  return (
    <tr className="border-t border-[var(--surface-border)]">
      <td className="py-2 pr-4 font-medium">{metrica.nome}</td>
      <td className="py-2 pr-4 font-mono text-xs">{metrica.valor_atual}</td>
      <td className="py-2 pr-4 font-mono text-xs">{metrica.target}</td>
      <td className="py-2 pr-4">
        {pct !== null ? (
          <progress
            value={pct}
            max={100}
            aria-valuetext={`${metrica.valor_atual} de ${metrica.target}`}
            className="parecer-progress h-1.5 w-24"
          />
        ) : (
          <span className="text-[10px] text-[var(--surface-muted-foreground)]">
            —
          </span>
        )}
      </td>
      <td className="py-2 pr-4 text-xs capitalize">{metrica.frequencia_revisao}</td>
      <td className="py-2 pr-4 text-xs text-[var(--surface-muted-foreground)]">
        §{metrica.section_id}
      </td>
    </tr>
  );
}

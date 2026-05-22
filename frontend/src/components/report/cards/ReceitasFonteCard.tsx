"use client";

import { useState, useMemo } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { usePeriodTransactions } from "@/hooks/usePeriodTransactions";
import { aggregateReceitas, getPeriodMonths, type Period } from "@/lib/periodUtils";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

// Cobertura: todas as categorias de receita produzidas pelo pipeline
// (`pipeline/domain/services/income_origin_resolver.py::_DEFAULT_STATIC_ORIGINS`
// + `receita_clt`/`receita_pj` resolvidos dinamicamente
// + labels PJ-side de `transaction_classifier_pj.PJ_LABELS`, [[ADR-236]]).
const FONTE_LABELS: Record<string, string> = {
  receita_clt: "CLT",
  receita_pj: "PJ",
  receita_aluguel: "Aluguéis",
  receita_investimento: "Rendimentos de Investimento",
  receita_resgate: "Resgates de Aplicações",
  receita_venda_ativo: "Venda de Ativo",
  receita_fgts: "FGTS",
  receita_restituicao: "Restituições",
  outras_receitas: "Outras receitas",
  pro_labore: "Pró-labore",
  lucros_distribuidos: "Lucros distribuídos",
};

/** F9 · F2.A · S1 — Card "Receitas por Fonte" com toggle de período.
 *
 * `anchorDate` (opcional) ancora a janela 3M/6M/12M/YTD no fim do dataset
 * — passa-se o último mês de `fluxo.receita_despesa_mensal_detalhado.labels`.
 * Sem âncora, cai no `fluxo.por_fonte` (E5 estático). Com âncora e janela
 * vazia, mostra "Sem dados" em vez de fallback. */
export function ReceitasFonteCard({
  fluxo,
  anchorDate,
}: {
  fluxo: FluxoCaixaSummary | undefined;
  anchorDate?: Date;
}) {
  const [period, setPeriod] = useState<Period>("3m");
  const { transactions, isLoading } = usePeriodTransactions(period, anchorDate);

  const numMonths = getPeriodMonths(period, anchorDate);

  const { entries, isLiveData } = useMemo(() => {
    if (transactions.length > 0) {
      const agg = aggregateReceitas(transactions);
      const sorted = Object.entries(agg)
        .filter(([, v]) => v > 0)
        .sort(([, a], [, b]) => b - a) as Array<[string, number]>;
      return { entries: sorted, isLiveData: true };
    }
    if (anchorDate && !isLoading) {
      // Anchor presente + load concluído + transactions vazia = janela
      // genuinamente vazia. Não cair em E5 estático.
      return { entries: [] as Array<[string, number]>, isLiveData: true };
    }
    const porFonte = fluxo?.por_fonte ?? {};
    const sorted = Object.entries(porFonte)
      .filter(([, v]) => typeof v === "number" && v > 0)
      .sort(([, a], [, b]) => (b as number) - (a as number)) as Array<[string, number]>;
    return { entries: sorted, isLiveData: false };
  }, [transactions, fluxo, anchorDate, isLoading]);

  const displayEntries: Array<[string, number]> = isLiveData
    ? entries.map(([k, v]) => [k, v / numMonths])
    : entries;

  const total = displayEntries.reduce((sum, [, v]) => sum + v, 0);

  return (
    <ReportCard
      variant="feature"
      title="Receitas por Fonte"
      headerRight={<PeriodToggle value={period} onChange={setPeriod} />}
    >
      {displayEntries.length === 0 && !isLoading ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de receitas neste período.
        </p>
      ) : (
        <div
          className={`overflow-x-auto transition-opacity duration-150 ${isLoading ? "opacity-40" : "opacity-100"}`}
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-border)] text-left">
                <th className="pb-2 font-display font-semibold">Fonte</th>
                <th className="pb-2 text-right font-display font-semibold">
                  {isLiveData ? "Média/mês" : "Total"}
                </th>
                <th className="pb-2 text-right font-display font-semibold">%</th>
              </tr>
            </thead>
            <tbody>
              {displayEntries.map(([key, value]) => {
                const pct = total > 0 ? (value / total) * 100 : 0;
                return (
                  <tr
                    key={key}
                    className="border-b border-[var(--surface-border)]/40 last:border-0"
                  >
                    <td className="py-2">{FONTE_LABELS[key] ?? key}</td>
                    <td className="py-2 text-right">
                      <MonetaryValue value={value} />
                    </td>
                    <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                      {pct.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
              <tr className="font-semibold">
                <td className="pt-3">Total</td>
                <td className="pt-3 text-right">
                  <MonetaryValue value={total} />
                </td>
                <td className="pt-3 text-right font-mono tabular-nums">100,0%</td>
              </tr>
            </tbody>
          </table>
          {isLiveData && (
            <p className="mt-2 text-xs text-[var(--surface-muted-foreground)]">
              Média mensal · {period.toUpperCase()} ({numMonths} meses)
            </p>
          )}
        </div>
      )}
    </ReportCard>
  );
}

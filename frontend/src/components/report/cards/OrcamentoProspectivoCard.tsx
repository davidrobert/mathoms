"use client";

import { useState, useMemo } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { usePeriodTransactions } from "@/hooks/usePeriodTransactions";
import {
  aggregateDespesasMediaMensal,
  getPeriodMonths,
  type Period,
} from "@/lib/periodUtils";
import { humanizeCategoryLabel } from "@/lib/categoryLabels";
import type { OrcamentoProspectivoData } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Card "Orçamento Prospectivo" com toggle de período.
 *
 * `anchorDate` (opcional) ancora a janela 3M/6M/12M/YTD no fim do dataset
 * — passa-se o último mês de `fluxo.receita_despesa_mensal_detalhado.labels`.
 * Sem âncora, cai no `orcamento.categorias` (E5 estático). Com âncora e
 * janela vazia, mostra "Sem transações em [período]" em vez de fallback. */
export function OrcamentoProspectivoCard({
  orcamento,
  anchorDate,
}: {
  orcamento: OrcamentoProspectivoData | undefined;
  anchorDate?: Date;
}) {
  const [period, setPeriod] = useState<Period>("3m");
  const { transactions, isLoading } = usePeriodTransactions(period, anchorDate);

  const numMonths = getPeriodMonths(period, anchorDate);

  const { entries, total, isLiveData } = useMemo(() => {
    if (transactions.length > 0) {
      const agg = aggregateDespesasMediaMensal(transactions, numMonths);
      const sorted = Object.entries(agg)
        .filter(([, v]) => v > 0)
        .sort(([, a], [, b]) => b - a) as Array<[string, number]>;
      const t = sorted.reduce((sum, [, v]) => sum + v, 0);
      return { entries: sorted, total: t, isLiveData: true };
    }
    if (anchorDate && !isLoading) {
      // Anchor presente + load concluído + transactions vazia = janela
      // genuinamente vazia. Não cair em E5 estático (mascararia o toggle).
      return {
        entries: [] as Array<[string, number]>,
        total: 0,
        isLiveData: true,
      };
    }
    const categorias = orcamento?.categorias ?? {};
    const sorted = Object.entries(categorias)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a) as Array<[string, number]>;
    return { entries: sorted, total: orcamento?.total ?? 0, isLiveData: false };
  }, [transactions, orcamento, numMonths, anchorDate, isLoading]);

  // Pareto cumulative %
  let acumulado = 0;
  const entriesComAcum = entries.map(([key, value]) => {
    acumulado += total > 0 ? (value / total) * 100 : 0;
    return { key, value, acum: acumulado };
  });

  return (
    <ReportCard
      variant="feature"
      title="Orçamento Prospectivo Mensal"
      headerRight={<PeriodToggle value={period} onChange={setPeriod} />}
    >
      {entries.length === 0 && !isLoading ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de orçamento neste período.
        </p>
      ) : (
        <div className={`transition-opacity duration-150 ${isLoading ? "opacity-40" : "opacity-100"}`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--surface-border)] text-left">
                  <th scope="col" className="pb-2 font-display font-semibold">Categoria</th>
                  <th scope="col" className="pb-2 text-right font-display font-semibold">
                    Teto/mês
                  </th>
                  <th scope="col" className="pb-2 text-right font-display font-semibold">%</th>
                  <th scope="col" className="pb-2 text-right font-display font-semibold text-[var(--surface-muted-foreground)]">
                    Acum.
                  </th>
                </tr>
              </thead>
              <tbody>
                {entriesComAcum.map(({ key, value, acum }) => {
                  const pct = total > 0 ? (value / total) * 100 : 0;
                  const isParetoThreshold = acum >= 80 && acum - pct < 80;
                  return (
                    <tr
                      key={key}
                      className="border-b border-[var(--surface-border)]/40 last:border-0"
                    >
                      <td className="py-2">{humanizeCategoryLabel(key)}</td>
                      <td className="py-2 text-right">
                        <MonetaryValue value={value} />
                      </td>
                      <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                        {pct.toFixed(1)}%
                      </td>
                      <td
                        className="py-2 text-right font-mono tabular-nums"
                        style={{
                          color: isParetoThreshold
                            ? "var(--semantic-alert)"
                            : acum >= 80
                              ? "var(--surface-muted-foreground)"
                              : "var(--semantic-gain)",
                        }}
                      >
                        {acum.toFixed(0)}%
                      </td>
                    </tr>
                  );
                })}
                <tr className="font-semibold">
                  <td className="pt-3">Total</td>
                  <td className="pt-3 text-right">
                    <MonetaryValue value={total} />
                  </td>
                  <td className="pt-3 text-right font-mono tabular-nums">
                    100,0%
                  </td>
                  <td className="pt-3" />
                </tr>
              </tbody>
            </table>
          </div>
          {isLiveData && (
            <p className="mt-2 text-xs text-[var(--surface-muted-foreground)]">
              Média mensal · {period.toUpperCase()} ({numMonths} meses)
            </p>
          )}
          {!isLiveData && orcamento?.legenda && (
            <p className="mt-3 text-xs italic text-[var(--surface-muted-foreground)]">
              {orcamento.legenda}
            </p>
          )}
        </div>
      )}
    </ReportCard>
  );
}

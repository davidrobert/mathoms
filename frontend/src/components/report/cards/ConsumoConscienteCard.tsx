"use client";

import { useState } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { useConsumoPontuais } from "@/hooks/useConsumoPontuais";
import type { Period } from "@/lib/periodUtils";
import type { ConsumoConscienteData } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Card "Consumo Consciente".
 *  KPIs do E5 no topo (janela completa de análise); lista de gastos pontuais
 *  ≥ R$2k abaixo, com toggle de período próprio (afeta só a lista).
 *
 *  A lista vem do endpoint /reports/consumo-pontuais — backend aplica
 *  threshold + filtro de transferência interna (família) via
 *  InternalTransferDetector, evitando que PIX entre contas próprias
 *  apareçam como gasto.
 *
 *  O toggle vive ao lado do título da lista (não no header do card) para
 *  evitar leitura ambígua: KPIs e a frase analítica do E5 refletem a
 *  janela completa, enquanto a lista responde ao período selecionado.
 */
export function ConsumoConscienteCard({
  consumo,
}: {
  consumo: ConsumoConscienteData | undefined;
}) {
  const [period, setPeriod] = useState<Period>("3m");
  const { items: pontuais, isLoading } = useConsumoPontuais(period);

  return (
    <ReportCard variant="success" title="Consumo Consciente">
      {consumo ? (
        <div className="space-y-4">
          <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
            <div>
              <dt className="text-[var(--surface-muted-foreground)]">
                Gastos pontuais
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                <MonetaryValue value={consumo.total_pontuais} />
              </dd>
            </div>
            <div>
              <dt className="text-[var(--surface-muted-foreground)]">
                Equiv. meses de aporte
              </dt>
              <dd className="mt-1 font-mono text-lg font-semibold tabular-nums">
                {consumo.equivalente_meses_aporte?.toFixed(1).replace(".", ",") ??
                  "—"}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--surface-muted-foreground)]">
                Folga mensal
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                <MonetaryValue value={consumo.folga_mensal} />
              </dd>
              <dd className="text-xs text-[var(--surface-muted-foreground)]">
                {consumo.folga_pct?.toFixed(0) ?? "—"}% da receita
              </dd>
            </div>
            <div>
              <dt className="text-[var(--surface-muted-foreground)]">
                Teto sugerido
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                <MonetaryValue value={consumo.teto_sugerido} />
              </dd>
            </div>
          </dl>
          {consumo.analise && (
            <p className="rounded-md bg-[var(--surface-muted)] p-3 text-sm text-[var(--surface-muted-foreground)]">
              {consumo.analise}
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de consumo consciente.
        </p>
      )}

      <div className="mt-4 border-t border-[var(--surface-border)] pt-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--surface-muted-foreground)]">
            Gastos pontuais ≥ R$2k
          </p>
          <PeriodToggle value={period} onChange={setPeriod} />
        </div>
        {pontuais.length === 0 && !isLoading ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Nenhum gasto pontual encontrado neste período.
          </p>
        ) : (
          <div
            className={`divide-y divide-[var(--surface-border)]/40 transition-opacity duration-150 ${isLoading ? "opacity-40" : "opacity-100"}`}
          >
            {pontuais.slice(0, 10).map((t, i) => (
              <div
                key={`${t.data}-${t.descricao}-${i}`}
                className="flex items-center justify-between gap-2 py-1.5 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate">{t.descricao}</p>
                  <p className="text-xs text-[var(--surface-muted-foreground)]">
                    {t.data} · {t.categoria ?? "sem categoria"}
                  </p>
                </div>
                <MonetaryValue value={t.valor} className="shrink-0 font-semibold" />
              </div>
            ))}
            {pontuais.length > 10 && (
              <p className="pt-2 text-xs text-[var(--surface-muted-foreground)]">
                +{pontuais.length - 10} mais…
              </p>
            )}
          </div>
        )}
      </div>
    </ReportCard>
  );
}

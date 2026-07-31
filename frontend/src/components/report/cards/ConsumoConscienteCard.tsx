"use client";

import { useState } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { formatJanelaTooltip } from "../utils/janelaLabel";
import { useConsumoPontuais } from "@/hooks/useConsumoPontuais";
import { humanizeCategoryLabel } from "@/lib/categoryLabels";
import type { Period } from "@/lib/periodUtils";
import type { ConsumoConscienteData } from "@/types/report-analysis";

/** `formatJanelaTooltip` fala de "média mensal" — errado para uma contagem de
 * meses. Este KPI é `total_pontuais / aporte_mensal` e `aporte_mensal` não
 * chega ao frontend, então não há como reprojetá-lo para a janela. */
const EQUIV_APORTE_TOOLTIP =
  "Equivalente calculado sobre o total de gastos pontuais de todo o período analisado.";

/** KPIs do E5, cada um com a própria janela declarada (ADR-306 D1/D6). */
function ConsumoKpis({ consumo }: { consumo: ConsumoConscienteData }) {
  const naJanela = Boolean(consumo.janela && consumo.janela !== "full");
  const pontuais = naJanela
    ? (consumo.total_pontuais_janela ?? consumo.total_pontuais)
    : consumo.total_pontuais;
  const janelaTooltip = formatJanelaTooltip(consumo.janela, consumo.janela_meses);
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">
          <span className="inline-flex items-center gap-1">
            Gastos pontuais
            {janelaTooltip && (
              <InfoTooltip
                ariaLabel="Sobre a janela dos gastos pontuais"
                content={janelaTooltip}
              />
            )}
          </span>
        </dt>
        <dd className="mt-1 text-lg font-semibold">
          <MonetaryValue value={pontuais} />
        </dd>
      </div>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">
          <span className="inline-flex items-center gap-1">
            Equiv. meses de aporte
            <InfoTooltip
              ariaLabel="Sobre a janela do equivalente em meses de aporte"
              content={EQUIV_APORTE_TOOLTIP}
            />
          </span>
        </dt>
        <dd className="mt-1 font-mono text-lg font-semibold tabular-nums">
          {consumo.equivalente_meses_aporte?.toFixed(1).replace(".", ",") ?? "—"}
        </dd>
      </div>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">Folga mensal</dt>
        <dd className="mt-1 text-lg font-semibold">
          <MonetaryValue value={consumo.folga_mensal} />
        </dd>
        <dd className="text-xs text-[var(--surface-muted-foreground)]">
          {consumo.folga_pct?.toFixed(0) ?? "—"}% da receita
        </dd>
      </div>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">Teto sugerido</dt>
        <dd className="mt-1 text-lg font-semibold">
          <MonetaryValue value={consumo.teto_sugerido} />
        </dd>
      </div>
    </dl>
  );
}

/** F9 · F2.B · S2 — Card "Consumo Consciente".
 *  KPIs do E5 no topo; lista de gastos pontuais ≥ R$2k abaixo, com toggle de
 *  período próprio (afeta só a lista).
 *
 *  A lista vem do endpoint /reports/consumo-pontuais — backend aplica
 *  threshold + filtro de transferência interna (família) via
 *  InternalTransferDetector, evitando que PIX entre contas próprias
 *  apareçam como gasto.
 *
 *  ADR-306 D1/D6 (A40.l3) — cada KPI declara a própria janela:
 *  - "Gastos pontuais" usa `total_pontuais_janela` quando `janela != full`;
 *    é o número que entra em `folga_mensal`, logo o único que deixa o leitor
 *    reproduzir a álgebra do card.
 *  - "Folga mensal"/"% da receita"/"Teto sugerido" já vêm da janela (E5).
 *  - "Equiv. meses de aporte" fica **full-period**: é
 *    `total_pontuais / aporte_mensal` e `aporte_mensal` não está no payload —
 *    irrecomputável para a janela, então recebe rótulo próprio.
 *  - `consumo.analise` é string pré-formatada no E5 citando o total full.
 *
 *  O toggle vive ao lado do título da lista (não no header do card) para
 *  evitar leitura ambígua: a lista responde ao período selecionado, os KPIs
 *  não.
 */
export function ConsumoConscienteCard({
  consumo,
  anchorDate,
}: {
  consumo: ConsumoConscienteData | undefined;
  anchorDate?: Date;
}) {
  const [period, setPeriod] = useState<Period>("3m");
  const { items: pontuais, isLoading } = useConsumoPontuais(period, anchorDate);

  return (
    <ReportCard variant="success" title="Consumo Consciente">
      {consumo ? (
        <div className="space-y-4">
          <ConsumoKpis consumo={consumo} />
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
                    {t.data} ·{" "}
                    {t.categoria ? humanizeCategoryLabel(t.categoria) : "sem categoria"}
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

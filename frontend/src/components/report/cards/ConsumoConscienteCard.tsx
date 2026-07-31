"use client";

import { useState, type ReactNode } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { resolveConsumoBases } from "../utils/fluxoJanela";
import { janelaBadgeLabel } from "../utils/janelaLabel";
import { useConsumoPontuais } from "@/hooks/useConsumoPontuais";
import { humanizeCategoryLabel } from "@/lib/categoryLabels";
import { PERIOD_LABELS, type Period } from "@/lib/periodUtils";
import type { ConsumoConscienteData } from "@/types/report-analysis";

/** Rótulo impresso ao lado do número. Tooltip **não conta** como rótulo: é
 * portal com hover/focus e não sai no PDF, que é o artefato que a família
 * guarda e leva ao contador (medido no PDF real, I5). */
function JanelaBadge({ label }: { readonly label: string }) {
  return (
    <span
      data-janela-badge
      className="block text-[11px] font-normal normal-case text-[var(--surface-muted-foreground)]"
    >
      {label}
    </span>
  );
}

function KpiTerm({ children }: { readonly children: ReactNode }) {
  return <dt className="text-[var(--surface-muted-foreground)]">{children}</dt>;
}

/** KPIs do E5 — **duas** bases coexistem no card, cada uma com rótulo impresso
 * ao lado do próprio número (ADR-306 §Emenda A40.l3: tooltip não conta):
 *
 * - Gastos pontuais + equivalente em meses de aporte → agregado histórico
 *   (D6: "`total_pontuais` **(tabela)** segue full-period"). Mesma base da
 *   prosa do E5, que também fala do período completo — o card fica
 *   internamente coerente.
 * - Folga mensal + teto sugerido → janela canônica (D1), que é de onde o E5 os
 *   deriva. Rótulo lido do campo `janela`; ausente ⇒ sem rótulo inventado.
 *
 * Trocar o KPI de pontuais para a base de janela (+ ritmo mensal) muda o que a
 * família vê e exige co-change no E5 — saiu para a lane A40.l15. */
function ConsumoKpis({ consumo }: { consumo: ConsumoConscienteData }) {
  const bases = resolveConsumoBases(consumo);
  if (!bases) return null;
  const historico = janelaBadgeLabel(bases.historico.rotulo);
  const folga = janelaBadgeLabel(bases.rotuloFolga);
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
      <div>
        <KpiTerm>
          Gastos pontuais
          {historico && <JanelaBadge label={historico} />}
        </KpiTerm>
        <dd className="mt-1 text-lg font-semibold">
          <MonetaryValue value={bases.historico.valor} />
        </dd>
      </div>
      <div>
        <KpiTerm>
          Equiv. meses de aporte
          {historico && <JanelaBadge label={historico} />}
        </KpiTerm>
        <dd className="mt-1 font-mono text-lg font-semibold tabular-nums">
          {bases.equivalente.valor?.toFixed(1).replace(".", ",") ?? "—"}
        </dd>
      </div>
      <div>
        <KpiTerm>
          Folga mensal
          {folga && <JanelaBadge label={folga} />}
        </KpiTerm>
        <dd className="mt-1 text-lg font-semibold">
          <MonetaryValue value={consumo.folga_mensal} />
        </dd>
        <dd className="text-xs text-[var(--surface-muted-foreground)]">
          {formatPct(consumo.folga_pct)} da receita
        </dd>
      </div>
      <div>
        <KpiTerm>
          Teto sugerido
          {folga && <JanelaBadge label={folga} />}
        </KpiTerm>
        <dd className="mt-1 text-lg font-semibold">
          <MonetaryValue value={consumo.teto_sugerido} />
        </dd>
      </div>
    </dl>
  );
}

function formatPct(value: number | string | undefined): string {
  const n = typeof value === "string" ? Number(value) : value;
  return n != null && Number.isFinite(n) ? `${n.toFixed(0)}%` : "—";
}

/** Escopo da LISTA, impresso. A lista tem toggle próprio (default 3m) e é a
 * terceira base temporal do card: sem esta linha o leitor somava os itens
 * exibidos e não chegava ao total do KPI, que é de todo o período. Não repete o
 * total aqui — ele já está no KPI, com o mesmo rótulo. */
function TabelaHeader({
  period,
  itens,
}: {
  readonly period: Period;
  readonly itens: number;
}) {
  return (
    <p
      data-consumo-tabela-escopo
      className="mb-2 text-xs text-[var(--surface-muted-foreground)]"
    >
      Lista: últimos {PERIOD_LABELS[period]} · {itens}{" "}
      {itens === 1 ? "lançamento" : "lançamentos"}.
    </p>
  );
}

/** F9 · F2.B · S2 — Card "Consumo Consciente".
 *
 *  KPIs do E5 no topo; lista de gastos pontuais ≥ R$2k abaixo, com toggle de
 *  período próprio (afeta só a lista).
 *
 *  A lista vem do endpoint /reports/consumo-pontuais — backend aplica
 *  threshold + filtro de transferência interna (família) via
 *  InternalTransferDetector, evitando que PIX entre contas próprias
 *  apareçam como gasto. **O KPI não aplica esse filtro** (o calculator do E5
 *  filtra só categoria + threshold): divergência conhecida, registrada como
 *  follow-up na lane A40.l3.
 *
 *  ADR-306 D1/D6 (A40.l3) — regra de apresentação: nenhum par de valores
 *  monetários de bases diferentes fica visualmente adjacente sem rótulo
 *  **impresso**. Pontuais + equivalente = agregado histórico (D6), mesma base
 *  da prosa do E5; folga + teto = janela canônica (D1); escopo da lista
 *  declarado em cima dela.
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
        <TabelaHeader period={period} itens={pontuais.length} />
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

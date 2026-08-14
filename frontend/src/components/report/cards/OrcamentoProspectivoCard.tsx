"use client";

import { useState } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { formatPercent } from "@/lib/format";
import { humanizeCategoryLabel } from "@/lib/categoryLabels";
import { formatInteractiveWindowBasis } from "../utils/interactiveWindowLabel";
import type {
  FluxoCaixaSummary,
  FluxoConsumoMensalRow,
  FluxoJanelaInterativa,
  FluxoPeriodoInterativo,
} from "@/types/report-analysis";

function HistoricalConsumptionCard() {
  return (
    <ReportCard variant="feature" title="Consumo por Categoria">
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Detalhamento por janela indisponível neste relatório histórico. Gere um
        novo relatório para consultar médias mensais comparáveis.
      </p>
    </ReportCard>
  );
}

function ConsumptionWindowSummary({
  janela,
}: {
  readonly janela: FluxoJanelaInterativa;
}) {
  return (
    <div aria-live="polite" data-window-summary>
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Referência mensal de consumo
      </p>
      <p className="mt-1 flex items-baseline gap-1">
        <MonetaryValue
          value={janela.despesa_consumo_mensal_media}
          size="kpi"
          data-testid="consumo-window-kpi"
        />
        <span className="text-xs text-[var(--surface-muted-foreground)]">
          /mês
        </span>
      </p>
      <p
        data-window-basis
        className="mt-1 text-xs text-[var(--surface-muted-foreground)]"
      >
        {formatInteractiveWindowBasis(janela)}
      </p>
    </div>
  );
}

function ConsumptionTableHead() {
  return (
    <thead>
      <tr className="border-b border-[var(--surface-border)] text-left">
        <th scope="col" className="pb-2 font-display font-semibold">
          Categoria
        </th>
        <th scope="col" className="pb-2 text-right font-display font-semibold">
          Referência mensal
        </th>
        <th scope="col" className="pb-2 text-right font-display font-semibold">
          Participação
        </th>
        <th scope="col" className="pb-2 text-right font-display font-semibold">
          Acumulado
        </th>
      </tr>
    </thead>
  );
}

function ConsumptionRow({ row }: { readonly row: FluxoConsumoMensalRow }) {
  return (
    <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
      <td className="py-2">{humanizeCategoryLabel(row.categoria)}</td>
      <td className="py-2 text-right">
        <MonetaryValue value={row.mensal_media} />
      </td>
      <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
        {formatPercent(row.participacao_pct, 2)}
      </td>
      <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
        {formatPercent(row.participacao_acumulada_pct, 2)}
      </td>
    </tr>
  );
}

function ConsumptionTable({
  janela,
}: {
  readonly janela: FluxoJanelaInterativa;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <ConsumptionTableHead />
        <tbody>
          {janela.tabela_consumo_por_categoria_mensal.map((row) => (
            <ConsumptionRow key={row.categoria} row={row} />
          ))}
          <tr className="font-semibold">
            <td className="pt-3">Referência mensal total</td>
            <td className="pt-3 text-right">
              <MonetaryValue value={janela.despesa_consumo_mensal_media} />
            </td>
            <td className="pt-3 text-right font-mono tabular-nums">
              {formatPercent(100, 2)}
            </td>
            <td className="pt-3" />
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function TransferNote({ value }: { readonly value: number }) {
  return (
    <p className="text-xs text-[var(--surface-muted-foreground)]">
      Aportes e transferências patrimoniais: <MonetaryValue value={value} />
      /mês. Este valor não entra na referência de consumo.
    </p>
  );
}

function ConsumptionWindowContent({
  janela,
}: {
  readonly janela: FluxoJanelaInterativa;
}) {
  if (janela.janela_meses === 0) {
    return (
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Não há meses documentados com movimento nesta janela.
      </p>
    );
  }
  const hasRows = janela.tabela_consumo_por_categoria_mensal.length !== 0;
  return (
    <div className="space-y-4">
      <ConsumptionWindowSummary janela={janela} />
      {hasRows ? (
        <ConsumptionTable janela={janela} />
      ) : (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem consumo registrado nesta janela.
        </p>
      )}
      <TransferNote value={janela.transferencia_patrimonial_mensal} />
    </div>
  );
}

/** A40.l44 PR5 — consumo histórico ex-aporte, sem recomputação no cliente. */
export function OrcamentoProspectivoCard({
  fluxo,
}: {
  readonly fluxo: FluxoCaixaSummary | undefined;
}) {
  const [period, setPeriod] = useState<FluxoPeriodoInterativo>("12m");
  if (!fluxo?.janelas) return <HistoricalConsumptionCard />;

  const janela = fluxo.janelas[period] as FluxoJanelaInterativa | undefined;
  return (
    <ReportCard
      variant="feature"
      title="Consumo por Categoria"
      headerRight={
        <PeriodToggle
          value={period}
          onChange={setPeriod}
          ariaLabel="Janela do consumo por categoria"
        />
      }
    >
      {janela ? (
        <ConsumptionWindowContent janela={janela} />
      ) : (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Dados desta janela indisponíveis. Escolha outro período.
        </p>
      )}
    </ReportCard>
  );
}

"use client";

import { useMemo, useState } from "react";

import { ReportCard } from "../ReportCard";
import { ChartDonut } from "./primitives/ChartDonut";
import { useChartTheme } from "./primitives/useChartTheme";
import { fmtBRL } from "./_shared";
import { PeriodToggle, type Period } from "../ui/PeriodToggle";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { useIsPrint } from "../hooks/useIsPrint";
import type { FluxoCaixaSummary, ChartSeries } from "@/types/report-analysis";

const CATEGORY_LABELS: Record<string, string> = {
  assinaturas: "Assinaturas",
  seguros: "Seguros",
  financeiro: "Financeiro",
  impostos: "Impostos",
  nao_identificado: "Não identificado",
  reserva_desejos: "Reserva de desejos",
  transporte: "Transporte",
  financiamentos: "Financiamentos",
  moradia: "Moradia",
  alimentacao: "Alimentação",
  suporte_familiar: "Suporte familiar",
  saude: "Saúde",
  lazer_viagens: "Lazer e viagens",
  vestuario: "Vestuário",
  educacao: "Educação",
  servicos_domesticos: "Serviços domésticos",
  melhoria_reforma: "Melhoria e reforma",
};

interface CategoryRow {
  readonly key: string;
  readonly label: string;
  readonly value: number;
}

function humanize(key: string): string {
  return CATEGORY_LABELS[key] ?? key.replace(/_/g, " ");
}

function sumWindow(data: readonly number[], start: number, end: number): number {
  let total = 0;
  for (let i = start; i < end && i < data.length; i++) total += data[i] ?? 0;
  return total;
}

/** Soma cada `despesa_dataset[i].data[start..end)` em uma fatia. Categorias
 *  com soma > 0 são ordenadas desc; chave estável vem do `label` original. */
function buildSlices(
  datasets: readonly ChartSeries[] | undefined,
  start: number,
  end: number,
): readonly CategoryRow[] {
  if (!datasets || datasets.length === 0) return [];
  return datasets
    .map((ds) => ({
      key: ds.label,
      label: humanize(ds.label),
      value: sumWindow(ds.data, start, end),
    }))
    .filter((row) => row.value > 0)
    .sort((a, b) => b.value - a.value);
}

/** Fallback: extrai fatias do snapshot `despesas_por_categoria` quando o
 *  backend ainda não emitiu `despesa_datasets`. PeriodToggle vira no-op. */
function fallbackFromAggregate(
  raw: Record<string, number> | undefined,
): readonly CategoryRow[] {
  if (!raw) return [];
  return Object.entries(raw)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({ key, label: humanize(key), value }))
    .sort((a, b) => b.value - a.value);
}

function buildContext(slices: readonly CategoryRow[], total: number): string {
  if (slices.length === 0) return "Sem dados de despesa no período selecionado.";
  return `Distribuição das despesas totais (${fmtBRL(total)}) entre ${slices.length} ${
    slices.length === 1 ? "categoria" : "categorias"
  }, destacando a composição de gastos e oportunidades de otimização.`;
}

function buildFallbackConclusion(slices: readonly CategoryRow[], total: number): string {
  if (slices.length === 0 || total <= 0) return "";
  const top = slices[0];
  const topPct = (top.value / total) * 100;
  const parts = [`${top.label} lidera com ${fmtBRL(top.value)} (${topPct.toFixed(1)}%).`];
  const naoIdent = slices.find((s) => s.key === "nao_identificado");
  const naoIdentPct = naoIdent ? (naoIdent.value / total) * 100 : 0;
  if (naoIdent && naoIdentPct > 10) {
    parts.push(
      `Atenção: 'não identificado' representa ${naoIdentPct.toFixed(1)}% — priorize reclassificação.`,
    );
  }
  return parts.join(" ");
}

/** Datalabel: `R$ Xk` se fatia ≥ 5% — paridade EXEMPLO_DE_RELATORIO.html:7966-7979. */
function dataLabelFormatter(value: number, pct: number): string {
  return pct >= 5 ? `R$ ${(value / 1000).toFixed(0)}k` : "";
}

const CONTEXT_STYLE = {
  fontSize: "var(--report-font-size-base, 13px)",
  color: "var(--surface-muted-foreground)",
  margin: "0 0 12px",
  lineHeight: 1.5,
} as const;

export interface DespesasDoughnutChartProps {
  readonly fluxo: FluxoCaixaSummary | undefined;
  readonly conclusion?: string;
}

function useDespesaSlices(
  fluxo: FluxoCaixaSummary | undefined,
  start: number,
  end: number,
): readonly CategoryRow[] {
  const det = fluxo?.receita_despesa_mensal_detalhado;
  const datasets = det?.despesa_datasets;
  const aggregate = fluxo?.despesas_por_categoria;
  return useMemo(() => {
    if (datasets && datasets.length > 0) return buildSlices(datasets, start, end);
    return fallbackFromAggregate(aggregate);
  }, [datasets, aggregate, start, end]);
}

/** v2.E.5 — Chart "Despesas por Categoria" (Chart.js doughnut + datalabels).
 *
 * Migra de Recharts para Chart.js primitives. Consome `despesa_datasets`
 * (séries mensais por categoria) para que `<PeriodToggle>` recalcule
 * fatias somando dentro da janela. Datalabels mostram `R$ Xk` em fatias
 * ≥ 5% do total. Print: toggle escondido, fixa 12m. */
export function DespesasDoughnutChart({
  fluxo,
  conclusion,
}: DespesasDoughnutChartProps) {
  const isPrint = useIsPrint();
  const theme = useChartTheme();
  const [period, setPeriod] = useState<Period>("12m");
  const effectivePeriod: Period = isPrint ? "12m" : period;
  const labels = fluxo?.receita_despesa_mensal_detalhado?.labels ?? [];
  const window = usePeriodWindow(labels, effectivePeriod);
  const slices = useDespesaSlices(fluxo, window.start, window.end);
  const total = useMemo(() => slices.reduce((acc, s) => acc + s.value, 0), [slices]);
  const palette = theme.categorical;
  const donutData = useMemo(
    () =>
      slices.map((s, i) => ({
        label: s.label,
        value: s.value,
        color: palette[i % palette.length],
      })),
    [slices, palette],
  );

  if (slices.length === 0) return null;

  const finalConclusion = conclusion ?? buildFallbackConclusion(slices, total) ?? undefined;
  const hasDatasets =
    (fluxo?.receita_despesa_mensal_detalhado?.despesa_datasets?.length ?? 0) > 0;

  return (
    <ReportCard variant="neutral" title="Despesas por Categoria" conclusion={finalConclusion}>
      <p className="chart-context" style={CONTEXT_STYLE}>
        {buildContext(slices, total)}
      </p>
      {!isPrint && hasDatasets ? (
        <PeriodToggle value={period} onChange={setPeriod} periodLabel={window.label} />
      ) : null}
      <div className="w-full" data-chart-id="despesas_doughnut">
        <ChartDonut
          data={donutData}
          cutout="50%"
          showDataLabels
          dataLabelFormatter={dataLabelFormatter}
          formatValue={fmtBRL}
          height={288}
          ariaLabel="Despesas por categoria"
        />
      </div>
    </ReportCard>
  );
}

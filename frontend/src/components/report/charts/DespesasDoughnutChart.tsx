"use client";

import { useMemo, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { ReportCard } from "../ReportCard";
import { Alert } from "../ui/Alert";
import { ChartDonut } from "./primitives/ChartDonut";
import { useChartTheme } from "./primitives/useChartTheme";
import { fmtBRL, formatRangeHumano } from "./_shared";
import { PeriodToggle, type Period } from "../ui/PeriodToggle";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { useIsPrint } from "../hooks/useIsPrint";
import {
  isNaoIdentificadoKey,
  NAO_IDENTIFICADO_THRESHOLD_PCT,
} from "../utils/dataQualitySignals";
import {
  humanizeCategoryLabel,
  isAporteInvestimentoKey,
} from "@/lib/categoryLabels";
import type { FluxoCaixaSummary, ChartSeries } from "@/types/report-analysis";

interface CategoryRow {
  readonly key: string;
  readonly label: string;
  readonly value: number;
}

function sumWindow(data: readonly number[], start: number, end: number): number {
  let total = 0;
  for (let i = start; i < end && i < data.length; i++) total += data[i] ?? 0;
  return total;
}

/** Soma cada `despesa_dataset[i].data[start..end)` em uma fatia. Categorias
 *  com soma > 0 são ordenadas desc; chave estável vem do `label` original.
 *  A37.l14 (PD-10 · ADR-333): aporte é poupança, não consumo — fica fora
 *  do doughnut (o `despesa_total` do payload segue intacto). */
function buildSlices(
  datasets: readonly ChartSeries[] | undefined,
  start: number,
  end: number,
): readonly CategoryRow[] {
  if (!datasets || datasets.length === 0) return [];
  return datasets
    .filter((ds) => !isAporteInvestimentoKey(ds.label))
    .map((ds) => ({
      key: ds.label,
      label: humanizeCategoryLabel(ds.label),
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
    .filter(([key, v]) => v > 0 && !isAporteInvestimentoKey(key))
    .map(([key, value]) => ({ key, label: humanizeCategoryLabel(key), value }))
    .sort((a, b) => b.value - a.value);
}

/** ADR-306 D1 (A40.l3) — o total é da janela RENDERIZADA; sem o range, o leitor
 * o confunde com o total do período completo citado na conclusão. */
function buildContext(
  slices: readonly CategoryRow[],
  total: number,
  rangeLabel: string,
): string {
  if (slices.length === 0) return "Sem dados de despesa no período selecionado.";
  const escopo = rangeLabel ? ` na janela exibida (${rangeLabel})` : "";
  return `Distribuição das despesas totais (${fmtBRL(total)})${escopo} entre ${slices.length} ${
    slices.length === 1 ? "categoria" : "categorias"
  }, destacando a composição de gastos e oportunidades de otimização.`;
}

function buildFallbackConclusion(slices: readonly CategoryRow[], total: number): string {
  if (slices.length === 0 || total <= 0) return "";
  const top = slices[0];
  const topPct = (top.value / total) * 100;
  return `${top.label} lidera com ${fmtBRL(top.value)} (${topPct.toFixed(1)}%).`;
}

/** A28.l9 — share da fatia "não identificado" na janela ativa (0..100). */
function naoIdentificadoPct(slices: readonly CategoryRow[], total: number): number {
  if (total <= 0) return 0;
  const alvo = slices
    .filter((s) => isNaoIdentificadoKey(s.key))
    .reduce((acc, s) => acc + s.value, 0);
  return (alvo / total) * 100;
}

/** Datalabel: `R$ Xk` se fatia ≥ 5% — paridade EXEMPLO_DE_RELATORIO.html:7966-7979.
 * Exceção A28.l9: "não identificado" sempre exibe datalabel (sinal de
 * qualidade não pode desaparecer quando a fatia é pequena). */
function dataLabelFormatter(value: number, pct: number, label: string): string {
  if (isNaoIdentificadoKey(label)) return `R$ ${(value / 1000).toFixed(0)}k`;
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
  // A28.l9 — "não identificado" sai da paleta categórica: cinza neutro
  // (token muted) sinaliza "sem categoria", não uma categoria a mais.
  const donutData = useMemo(() => {
    let paletteIdx = 0;
    return slices.map((s) => ({
      label: s.label,
      value: s.value,
      color: isNaoIdentificadoKey(s.key)
        ? theme.textMuted
        : palette[paletteIdx++ % palette.length],
    }));
  }, [slices, palette, theme.textMuted]);

  if (slices.length === 0) return null;

  const finalConclusion = conclusion ?? buildFallbackConclusion(slices, total) ?? undefined;
  const hasDatasets =
    (fluxo?.receita_despesa_mensal_detalhado?.despesa_datasets?.length ?? 0) > 0;
  const naoIdentPct = naoIdentificadoPct(slices, total);

  return (
    <ReportCard variant="neutral" title="Despesas por Categoria" conclusion={finalConclusion}>
      <p className="chart-context" style={CONTEXT_STYLE}>
        {buildContext(slices, total, formatRangeHumano(window.label))}
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
      {naoIdentPct > NAO_IDENTIFICADO_THRESHOLD_PCT && (
        <NaoIdentificadoAlert pct={naoIdentPct} />
      )}
    </ReportCard>
  );
}

/** A28.l9 — sinal persistente (não some na conclusão condicional) quando
 * "não identificado" passa do limiar de 10% na janela ativa. */
function NaoIdentificadoAlert({ pct }: { pct: number }) {
  return (
    <div className="mt-3" data-testid="despesas-nao-identificado-alert">
      <Alert
        severity="warning"
        icon={<AlertTriangle className="h-4 w-4" aria-hidden="true" />}
      >
        <p>
          Despesas não identificadas somam {pct.toFixed(1).replace(".", ",")}% do total
          na janela — a distribuição acima subestima as demais categorias.
          Reclassificar devolve precisão ao gráfico.
        </p>
      </Alert>
    </div>
  );
}

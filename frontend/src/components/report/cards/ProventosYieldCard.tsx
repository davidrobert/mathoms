"use client";

import type { ProventosAtivoData } from "@/types/report-analysis";
import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";

interface ProventosYieldCardProps {
  data: readonly ProventosAtivoData[] | null | undefined;
}

const CARD_TITLE = "Proventos por ativo — dividendos, JCP e FIIs";

/**
 * A33.l4 (ADR-238 §L4) — renda de proventos dos informes anuais em S3.
 *
 * Hierarquia de métricas (design 2026-07-07): "Yield sobre custo" é o
 * primário (hero); "Yield sobre valor atual" é secundário atenuado e SEMPRE
 * renderiza com o rótulo no mesmo bloco do número — nunca um % solto. Sem
 * custo nem valor de mercado, só renda absoluta BRL (métrica errada é pior
 * que ausente). Oculto quando o workspace não tem informe de proventos.
 */
export function ProventosYieldCard({ data }: ProventosYieldCardProps) {
  const rows = data ?? [];
  if (rows.length === 0) return null;

  const anoBase = Math.max(...rows.map((r) => r.ano_base));
  const doAno = rows.filter((r) => r.ano_base === anoBase);
  const agg = aggregate(doAno);

  return (
    <ReportCard size="full" variant="feature" title={CARD_TITLE}>
      <p className="-mt-2 mb-4 text-xs leading-snug text-[var(--surface-muted-foreground)]">
        Informes de proventos das corretoras/companhias — ano-base {anoBase}.
        Renda líquida de IR retido na fonte.
        <sup>1</sup>
      </p>
      <ProventosHero agg={agg} />
      <ProventosTable rows={doAno} />
      <ProventosFootnote />
    </ReportCard>
  );
}

// ───────────────────────── Agregação ───────────────────────────────────────

interface ProventosAggregate {
  rendaLiquidaAnual: number;
  yieldSobreCusto: number | null;
  yieldSobreValorAtual: number | null;
}

/** Yields agregados pareiam numerador e denominador dos MESMOS ativos —
 * ativo sem custo fica fora do yield sobre custo (e idem p/ valor atual). */
function aggregate(rows: readonly ProventosAtivoData[]): ProventosAggregate {
  const rendaLiquidaAnual = sum(rows.map((r) => r.renda_liquida_brl));
  return {
    rendaLiquidaAnual,
    yieldSobreCusto: ratioPct(rows, (r) => r.custo_total_brl),
    yieldSobreValorAtual: ratioPct(rows, (r) => r.valor_mercado_brl),
  };
}

function ratioPct(
  rows: readonly ProventosAtivoData[],
  denomOf: (r: ProventosAtivoData) => number | null,
): number | null {
  const pareados = rows.filter((r) => denomOf(r) !== null && (denomOf(r) as number) > 0);
  const denom = sum(pareados.map((r) => denomOf(r) as number));
  if (denom <= 0) return null;
  return (sum(pareados.map((r) => r.renda_liquida_brl)) / denom) * 100;
}

function sum(values: readonly number[]): number {
  return values.reduce((acc, v) => acc + v, 0);
}

function fmtPct(pct: number): string {
  return `${pct.toFixed(2).replace(".", ",")}%`;
}

// ───────────────────────── Hero ─────────────────────────────────────────────

function ProventosHero({ agg }: { agg: ProventosAggregate }) {
  return (
    <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
      <PrimaryMetric agg={agg} />
      <div className="flex flex-col gap-2 border-t pt-4 md:border-t-0 md:border-l md:pl-6 md:pt-0 border-[var(--surface-border)]">
        <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Renda líquida no ano
        </p>
        <MonetaryValue value={agg.rendaLiquidaAnual} size="hero" />
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          ≈ <MonetaryValue value={agg.rendaLiquidaAnual / 12} size="body" /> por mês
        </p>
      </div>
    </div>
  );
}

/** Primário: yield sobre custo. Sem custo, "yield sobre valor atual" assume o
 * posto MAS mantém rótulo distinto + micro-legenda (nunca vira "yield" genérico).
 * Sem nenhum denominador: nada de % — a renda absoluta (coluna ao lado) basta. */
function PrimaryMetric({ agg }: { agg: ProventosAggregate }) {
  if (agg.yieldSobreCusto !== null) {
    return (
      <div className="flex flex-col gap-2">
        <YieldSobreCusto pct={agg.yieldSobreCusto} />
        {agg.yieldSobreValorAtual !== null && (
          <YieldSobreValorAtual pct={agg.yieldSobreValorAtual} />
        )}
      </div>
    );
  }
  if (agg.yieldSobreValorAtual !== null) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Yield sobre valor atual
        </p>
        <p
          className="font-mono text-4xl font-semibold tabular-nums leading-none"
          aria-label={ariaValorAtual(agg.yieldSobreValorAtual)}
        >
          {fmtPct(agg.yieldSobreValorAtual)}
          <span className="ml-2 text-xl text-[var(--surface-muted-foreground)]">a.a.</span>
        </p>
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          renda anual ÷ valor de mercado em 31/12 — sem custo de aquisição no informe
        </p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        Renda absoluta
      </p>
      <p className="text-sm text-[var(--surface-foreground)]">
        O informe não traz custo de aquisição nem valor de mercado — exibimos a renda em
        R$, sem yield.<sup>1</sup>
      </p>
    </div>
  );
}

function YieldSobreCusto({ pct }: { pct: number }) {
  return (
    <>
      <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        Yield sobre custo
      </p>
      <p
        className="font-mono text-4xl font-semibold tabular-nums leading-none"
        aria-label={`Yield sobre custo: ${pct.toFixed(2).replace(".", ",")} por cento, renda sobre custo de aquisição`}
      >
        {fmtPct(pct)}
        <span className="ml-2 text-xl text-[var(--surface-muted-foreground)]">a.a.</span>
      </p>
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        renda anual ÷ o que você pagou<sup>1</sup>
      </p>
    </>
  );
}

/** Secundário atenuado — 3 eixos simultâneos (tamanho + peso + rótulo); o
 * rótulo textual completo fica no MESMO bloco do número, nunca % solto. */
function YieldSobreValorAtual({ pct }: { pct: number }) {
  return (
    <p
      className="text-sm text-[var(--surface-muted-foreground)]"
      aria-label={ariaValorAtual(pct)}
    >
      Yield sobre valor atual:{" "}
      <span className="font-mono tabular-nums">{fmtPct(pct)}</span> — renda anual ÷ valor
      de mercado em 31/12
    </p>
  );
}

function ariaValorAtual(pct: number): string {
  return `Yield sobre valor atual: ${pct.toFixed(2).replace(".", ",")} por cento, renda sobre valor de mercado em 31 de dezembro`;
}

// ───────────────────────── Tabela por ativo ────────────────────────────────

function ProventosTable({ rows }: { rows: readonly ProventosAtivoData[] }) {
  const ordered = [...rows].sort((a, b) => b.renda_liquida_brl - a.renda_liquida_brl);
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">
          Proventos por ativo ordenados por renda líquida descendente — yields sobre custo
          e sobre valor atual quando o informe traz os denominadores
        </caption>
        <thead className="text-[var(--surface-muted-foreground)]">
          <tr className="text-left">
            <th className="py-1 pr-2 font-normal" scope="col">
              Ativo
            </th>
            <th className="py-1 pr-2 text-right font-normal" scope="col">
              Renda líquida
            </th>
            <th className="py-1 pr-2 text-right font-normal" scope="col">
              IR retido
            </th>
            <th className="py-1 pr-2 text-right font-normal" scope="col">
              Yield sobre custo
            </th>
            <th className="py-1 text-right font-normal" scope="col">
              Yield sobre valor atual
            </th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((r) => (
            <ProventosRow key={`${r.ticker}-${r.ano_base}`} row={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProventosRow({ row }: { row: ProventosAtivoData }) {
  return (
    <tr className="border-t border-[var(--surface-border)]">
      <td className="py-2 pr-2 font-mono">{row.ticker}</td>
      <td className="py-2 pr-2 text-right font-mono tabular-nums">
        <MonetaryValue value={row.renda_liquida_brl} />
      </td>
      <td className="py-2 pr-2 text-right font-mono tabular-nums">
        <MonetaryValue value={row.ir_retido_brl} />
      </td>
      <td className="py-2 pr-2 text-right font-mono tabular-nums">
        <YieldCell pct={row.yield_on_cost_pct} kind="custo" ticker={row.ticker} />
      </td>
      <td className="py-2 text-right font-mono tabular-nums">
        <YieldCell pct={row.yield_on_market_pct} kind="valor-atual" ticker={row.ticker} />
      </td>
    </tr>
  );
}

/** Célula de yield — aria-label carrega o denominador mesmo com o rótulo
 * visual no cabeçalho da coluna (gate UX: % nunca sem rótulo junto). */
function YieldCell({
  pct,
  kind,
  ticker,
}: {
  pct: number | null;
  kind: "custo" | "valor-atual";
  ticker: string;
}) {
  if (pct === null) {
    return <span className="text-[var(--surface-muted-foreground)]">—</span>;
  }
  const denominador =
    kind === "custo"
      ? "renda sobre custo de aquisição"
      : "renda sobre valor de mercado em 31 de dezembro";
  const rotulo = kind === "custo" ? "Yield sobre custo" : "Yield sobre valor atual";
  return (
    <span
      aria-label={`${rotulo} de ${ticker}: ${pct.toFixed(2).replace(".", ",")} por cento, ${denominador}`}
    >
      {fmtPct(pct)}
    </span>
  );
}

// ───────────────────────── Footnote (D8 + design 2026-07-07) ───────────────

function ProventosFootnote() {
  return (
    <p className="mt-4 text-xs text-[var(--surface-muted-foreground)]">
      <sup>1</sup> Renda líquida = proventos recebidos − IR retido na fonte (JCP tributado
      em 15%; dividendos e rendimentos de FII isentos; bonificação é ajuste de custo, não
      renda). Yield sobre custo mede a renda em relação ao valor que você investiu — é o
      retorno real do seu capital. Yield sobre valor atual usa o preço de mercado em 31/12
      como base e tende a ser menor quando o ativo valorizou; não representa o retorno do
      que você aplicou. Cálculo informativo. Confira com seu contador antes de declarar.
      Mathoms não substitui orientação tributária.
    </p>
  );
}

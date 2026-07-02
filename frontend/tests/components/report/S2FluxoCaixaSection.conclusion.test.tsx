/**
 * Regressão audit-vault r4 (F13) — wiring de conclusion ids em S2.
 *
 * Bug: o call site passava `receita_fonte`/`despesas_categoria` a
 * `getConclusion(...)`, mas BUILDERS/FALLBACKS de conclusionUtils.ts (e o
 * YAML canônico chart_conclusions.yaml) só conhecem
 * `receita_bar`/`despesas_doughnut` — os dois charts renderizavam sem
 * conclusão em runtime. Aqui mockamos os charts para capturar a prop
 * `conclusion` real produzida pela seção (conclusionUtils roda de verdade).
 * Gate estático correspondente: dev/check_chart_conclusion_parity.py regra 4.
 */
import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

const conclusions: Record<string, string | undefined> = {};

vi.mock("@/components/report/charts/ReceitaBarChart", () => ({
  ReceitaBarChart: (props: { conclusion?: string }) => {
    conclusions.receita = props.conclusion;
    return null;
  },
}));
vi.mock("@/components/report/charts/DespesasDoughnutChart", () => ({
  DespesasDoughnutChart: (props: { conclusion?: string }) => {
    conclusions.despesas = props.conclusion;
    return null;
  },
}));
vi.mock("@/components/report/charts/FluxoMensalChart", () => ({
  FluxoMensalChart: () => null,
}));
vi.mock("@/components/report/charts/ReceitaDespesaMensalChart", () => ({
  ReceitaDespesaMensalChart: () => null,
}));
vi.mock("@/components/report/cards", () => ({
  ConsumoConscienteCard: () => null,
  DiagnosticoComportamentalCard: () => null,
  EquilibrioCerbasiCard: () => null,
  OrcamentoProspectivoCard: () => null,
}));
vi.mock("@/components/report/SectionSnapshotDiff", () => ({
  SectionSnapshotDiff: () => null,
}));

import { S2FluxoCaixaSection } from "@/components/report/sections/S2FluxoCaixaSection";
import type { ReportAnalysisData } from "@/lib/api";

const data = {
  fluxo_caixa: {
    por_fonte: { receita_clt: 9000, receita_pj: 3000 },
    despesas_por_categoria: { moradia: 4000, alimentacao: 1000 },
  },
} as unknown as ReportAnalysisData;

describe("<S2FluxoCaixaSection /> — conclusion ids (audit-vault r4)", () => {
  it("passa conclusões derivadas de receita_bar/despesas_doughnut aos charts", () => {
    render(<S2FluxoCaixaSection data={data} />);
    expect(conclusions.receita).toBe("CLT lidera as receitas (75%).");
    expect(conclusions.despesas).toBe(
      "Moradia concentra 80% do gasto recorrente.",
    );
  });

  it("prioriza narrativa E5.N quando presente sob o id canônico", () => {
    const withNarrativa = {
      ...data,
      narrativas: { receita_bar: { conclusion: "Texto E5.N." } },
    } as unknown as ReportAnalysisData;
    render(<S2FluxoCaixaSection data={withNarrativa} />);
    expect(conclusions.receita).toBe("Texto E5.N.");
  });
});

/**
 * ADR-117/122 · Fase 9 — testes das seções USA (U1–U4).
 *
 * Cobre wire-up do SectionSummary + fallback derivado + ChartConclusion
 * fallback. Mantido enxuto — os derivadores em si têm coverage em
 * dataAdapters.test.ts.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  U1MudancaEuaSection,
  U2GreenCardSection,
  U3NclexSection,
  U4SimulacaoMarianaSection,
} from "@/components/report/sections/UsaSections";
import type { ReportAnalysisData } from "@/lib/api";

function emptyData(): ReportAnalysisData {
  return {} as ReportAnalysisData;
}

describe("U1MudancaEuaSection", () => {
  it("renderiza title e fallback summary quando narrativas vazias", () => {
    render(<U1MudancaEuaSection data={emptyData()} />);
    expect(screen.getByText(/Mudança EUA/)).toBeInTheDocument();
    expect(
      screen.getByText(/Estrutura F1\/F2 e custos da transição/),
    ).toBeInTheDocument();
  });

  it("usa narrativa quando presente (sem fallback)", () => {
    const data = {
      narrativas: {
        U1: { context: "Contexto customizado de mudança." },
      },
    } as unknown as ReportAnalysisData;
    render(<U1MudancaEuaSection data={data} />);
    expect(
      screen.getByText("Contexto customizado de mudança."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Estrutura F1\/F2 e custos da transição/),
    ).not.toBeInTheDocument();
  });
});

describe("U2GreenCardSection", () => {
  it("renderiza fallback Green Card + chart stub", () => {
    render(<U2GreenCardSection data={emptyData()} />);
    expect(screen.getByText(/Green Card EB2-NIW/)).toBeInTheDocument();
  });
});

describe("U3NclexSection", () => {
  it("renderiza fallback NCLEX + card default", () => {
    render(<U3NclexSection data={emptyData()} />);
    expect(screen.getByText(/Roadmap para o NCLEX-RN\./)).toBeInTheDocument();
    expect(
      screen.getByText(/Roadmap de licenciamento NCLEX-RN/),
    ).toBeInTheDocument();
  });
});

describe("U4SimulacaoMarianaSection", () => {
  it("renderiza fallback + tabela de cenários quando presente (ADR-166: chave cenarios_conjuge)", () => {
    const data = {
      cenarios_conjuge: {
        labels: ["Cenário A", "Cenário B"],
        aportes: [1000, 2000],
        prazos_if: [20.5, 15.2],
        anos_if: [2046, 2041],
      },
    } as unknown as ReportAnalysisData;
    render(<U4SimulacaoMarianaSection data={data} />);
    expect(
      screen.getByText(/Cenários de independência financeira do cônjuge/),
    ).toBeInTheDocument();
    expect(screen.getByText("Cenário A")).toBeInTheDocument();
    expect(screen.getByText("Cenário B")).toBeInTheDocument();
    expect(screen.getByText("20.5")).toBeInTheDocument();
  });

  it("omite tabela quando não há cenários", () => {
    render(<U4SimulacaoMarianaSection data={emptyData()} />);
    expect(screen.queryByText("Cenários Comparativos")).not.toBeInTheDocument();
  });
});

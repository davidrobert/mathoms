import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import type { ProtectionBundle } from "@/components/report/cards";
import { S9RiscosSection } from "@/components/report/sections/S9RiscosSection";
import {
  hasRealProtectionInputs,
  protectionSectionState,
} from "@/components/report/sections/s9ProtectionInputs";
import type { ReportAnalysisData } from "@/lib/api/reports";

function makeBundle(overrides: Partial<ProtectionBundle> = {}): ProtectionBundle {
  return {
    policies: [],
    gap_analysis: {},
    recommendations: [],
    auto_inferred_risks: [],
    calculation_status: {},
    methodology_thresholds: {},
    has_us_exposure: null,
    adapter_version: 3,
    ...overrides,
  };
}

function makeData(overrides: Partial<ReportAnalysisData> = {}): ReportAnalysisData {
  return {
    narrativas: { charts: { bubble_riscos: { data_state: "empty" } } },
    ...overrides,
  } as ReportAnalysisData;
}

describe("hasRealProtectionInputs", () => {
  it("é falso sem bundle, sem apólice e sem cálculo", () => {
    expect(hasRealProtectionInputs(undefined)).toBe(false);
    expect(hasRealProtectionInputs(makeBundle())).toBe(false);
  });

  it("é verdadeiro com apólice ou gap computado", () => {
    expect(
      hasRealProtectionInputs(
        makeBundle({
          policies: [
            {
              id: "p1",
              category: "vida",
              coverage_brl: 100000,
              starts_at: "2026-01-01",
              status: "Ativa",
            },
          ],
        }),
      ),
    ).toBe(true);
    expect(
      hasRealProtectionInputs(
        makeBundle({
          gap_analysis: { vida: { actual_brl: 0, ideal_brl: 4500000, gap_brl: 4500000 } },
        }),
      ),
    ).toBe(true);
  });
});

describe("<S9RiscosSection /> — empty só sem insumo real (A40.l35)", () => {
  it("declara ausência nomeando o insumo, sem afirmar que o cliente está descoberto", () => {
    render(<S9RiscosSection data={makeData()} />);
    expect(screen.getByText(/Ainda não temos insumo para analisar seus riscos/)).toBeInTheDocument();
    expect(screen.getByText(/Isto não afirma que você está descoberto/)).toBeInTheDocument();
  });

  it("não esconde a seção só porque o bubble_riscos está empty", () => {
    const data = makeData({
      protection_bundle: makeBundle({
        policies: [
          {
            id: "p1",
            category: "vida",
            coverage_brl: 100000,
            starts_at: "2026-01-01",
            status: "Ativa",
          },
        ],
      }),
    });
    render(<S9RiscosSection data={data} />);
    expect(
      screen.queryByText(/Ainda não temos insumo para analisar seus riscos/),
    ).not.toBeInTheDocument();
  });
});

describe("estado parcial — as duas fontes (A40.l73 · ADR-395)", () => {
  const documentary = {
    active_policies_count: 2,
    insurers: ["Seguradora Alfa", "Seguradora Beta"],
    earliest_coverage_end: "2027-03-31",
    unconfirmed_categories: ["vida"],
  };

  function partialData() {
    return makeData({ protection_bundle: makeBundle({ documentary_coverage: documentary }) });
  }

  it("classifica como parcial quando só o documento trouxe apólice", () => {
    expect(protectionSectionState(makeBundle({ documentary_coverage: documentary }))).toBe(
      "parcial",
    );
  });

  it("classifica como nao_apurado quando nenhuma fonte trouxe evidência", () => {
    expect(protectionSectionState(makeBundle())).toBe("nao_apurado");
    expect(protectionSectionState(undefined)).toBe("nao_apurado");
  });

  it("classifica como apurado quando o cadastro sustenta cálculo", () => {
    expect(
      protectionSectionState(
        makeBundle({
          documentary_coverage: documentary,
          calculation_status: {
            vida: { status: "computed", missing_inputs: [], reason: "ok" },
          },
        }),
      ),
    ).toBe("apurado");
  });

  it("não imprime a copy de vazio quando o documento tem apólice", () => {
    render(<S9RiscosSection data={partialData()} />);
    expect(screen.queryByText(/Ainda não temos insumo/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sem riscos cadastrados/i)).not.toBeInTheDocument();
  });

  it("nomeia as apólices identificadas e declara o gap retido", () => {
    render(<S9RiscosSection data={partialData()} />);
    const bloco = screen.getByTestId("s9-cobertura-nao-confirmada");
    expect(bloco).toHaveTextContent("2 apólices vigentes");
    expect(bloco).toHaveTextContent("Seguradora Alfa e Seguradora Beta");
    expect(bloco).toHaveTextContent(/gap de Vida está retido/);
    expect(bloco).toHaveTextContent("2027-03-31");
  });

  it("não afirma adequação nem ausência de cobertura", () => {
    render(<S9RiscosSection data={partialData()} />);
    expect(screen.getByTestId("s9-cobertura-nao-confirmada")).toHaveTextContent(
      /não afirma que sua cobertura é adequada nem que falta cobertura/,
    );
  });

  it("apólice de bem não silencia vida, invalidez nem sucessão", () => {
    const soBens = { ...documentary, unconfirmed_categories: [] };
    render(
      <S9RiscosSection
        data={makeData({ protection_bundle: makeBundle({ documentary_coverage: soBens }) })}
      />,
    );
    expect(screen.getByTestId("s9-cobertura-nao-confirmada")).toHaveTextContent(
      /Nenhuma delas confirma cobertura de vida, invalidez ou sucessão/,
    );
  });

  it("estado parcial não renderiza os cards de gap do cadastro", () => {
    render(<S9RiscosSection data={partialData()} />);
    expect(screen.queryByTestId("hero-gap-actual")).not.toBeInTheDocument();
  });
});

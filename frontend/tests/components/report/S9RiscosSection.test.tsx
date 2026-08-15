import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import type { ProtectionBundle } from "@/components/report/cards";
import { S9RiscosSection } from "@/components/report/sections/S9RiscosSection";
import { hasRealProtectionInputs } from "@/components/report/sections/s9ProtectionInputs";
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
  it("mostra empty state quando o snapshot não trouxe bundle", () => {
    render(<S9RiscosSection data={makeData()} />);
    expect(
      screen.getByText(/Mapeie seus riscos críticos para destravar esta seção/),
    ).toBeInTheDocument();
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
      screen.queryByText(/Mapeie seus riscos críticos para destravar esta seção/),
    ).not.toBeInTheDocument();
  });
});

/**
 * W5-T02 (v2.E.9) — specs do `<WaterfallIfChart>` (Chart.js waterfall).
 *
 * Cobre: empty state (meta ausente), steps Atual/Gap/Meta com floating
 * bars ([base, top]), fallback de gap = meta - atual e parágrafo de
 * progresso pt-BR. Não testa render visual do canvas (contrato em
 * chartPrimitives.test.tsx).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { WaterfallIfChart } from "@/components/report/charts/WaterfallIfChart";
import type { PatrimonioData } from "@/types/report-analysis";

// react-chartjs-2 quebra em jsdom sem pkg `canvas`. Mock dá dump dos
// pares [base, top] que o ChartWaterfall calcula por step.
vi.mock("react-chartjs-2", () => ({
  Chart: ({
    data,
  }: {
    data: {
      labels?: readonly string[];
      datasets: readonly { data: readonly unknown[] }[];
    };
  }) => (
    <div data-testid="chart-mock">
      {(data.labels ?? []).map((lbl, i) => (
        <span
          key={String(lbl)}
          data-step={String(lbl)}
          data-range={JSON.stringify(data.datasets[0]?.data[i])}
        />
      ))}
    </div>
  ),
}));

const PATRIMONIO: PatrimonioData = { investivel_efetivo: 300000 };

function getSteps(): Record<string, readonly number[]> {
  const out: Record<string, readonly number[]> = {};
  for (const el of document.querySelectorAll("[data-step]")) {
    out[el.getAttribute("data-step") ?? ""] = JSON.parse(
      el.getAttribute("data-range") ?? "[]",
    ) as readonly number[];
  }
  return out;
}

describe("<WaterfallIfChart />", () => {
  it("renderiza empty state quando meta não configurada", () => {
    render(<WaterfallIfChart patrimonio={PATRIMONIO} goals={undefined} />);
    expect(screen.getByText(/Meta de IF não configurada/)).toBeInTheDocument();
  });

  it("renderiza waterfall Atual (pilar) / Gap (floating) / Meta (pilar)", () => {
    render(
      <WaterfallIfChart
        patrimonio={PATRIMONIO}
        goals={{ if_meta: 1000000, if_gap: 700000, if_pct: 30 }}
      />,
    );
    expect(getSteps()).toEqual({
      Atual: [0, 300000],
      Gap: [300000, 1000000],
      Meta: [0, 1000000],
    });
  });

  it("deriva gap e pct quando goals traz apenas if_meta", () => {
    render(<WaterfallIfChart patrimonio={PATRIMONIO} goals={{ if_meta: 1200000 }} />);
    expect(getSteps().Gap).toEqual([300000, 1200000]);
    expect(screen.getByText("25,0%")).toBeInTheDocument();
  });

  it("propaga conclusion para o ReportCard", () => {
    render(
      <WaterfallIfChart
        patrimonio={PATRIMONIO}
        goals={{ if_meta: 1000000 }}
        conclusion="Faltam R$ 700 mil para a meta."
      />,
    );
    expect(screen.getByText(/Faltam R\$ 700 mil/)).toBeInTheDocument();
  });
});

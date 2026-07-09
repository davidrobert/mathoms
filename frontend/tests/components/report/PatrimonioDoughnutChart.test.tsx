/**
 * W5-T02 (v2.E.9) — specs do `<PatrimonioDoughnutChart>` (Chart.js donut).
 *
 * Cobre: empty state, filtro de valores <= 0, fallback
 * composicao → tabela_categorias e conclusion prop. Não testa render
 * visual do canvas (Chart.js precisa do pkg `canvas` em jsdom —
 * chartPrimitives.test.tsx já estabelece esse contrato).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { PatrimonioDoughnutChart } from "@/components/report/charts/PatrimonioDoughnutChart";
import type { PatrimonioData } from "@/types/report-analysis";

// react-chartjs-2 quebra em jsdom sem pkg `canvas`. Mock com div + label
// dump para introspeção das fatias.
vi.mock("react-chartjs-2", () => ({
  Chart: ({
    data,
  }: {
    data: {
      labels?: readonly string[];
      datasets: readonly { data: readonly number[] }[];
    };
  }) => (
    <div data-testid="chart-mock">
      {(data.labels ?? []).map((lbl, i) => (
        <span key={lbl} data-slice={lbl} data-value={data.datasets[0]?.data[i] ?? 0}>
          {lbl}={data.datasets[0]?.data[i] ?? 0}
        </span>
      ))}
    </div>
  ),
}));

const COMPOSICAO: PatrimonioData = {
  composicao: [
    { categoria: "Investimentos", valor: 500000, pct: 62.5 },
    { categoria: "Imóveis", valor: 300000, pct: 37.5 },
    { categoria: "Dívidas", valor: -50000, pct: 0 },
  ],
};

function getSlices(): Record<string, number> {
  const out: Record<string, number> = {};
  for (const el of document.querySelectorAll("[data-slice]")) {
    out[el.getAttribute("data-slice") ?? ""] = Number(el.getAttribute("data-value") ?? "0");
  }
  return out;
}

describe("<PatrimonioDoughnutChart />", () => {
  it("renderiza empty state sem dados", () => {
    render(<PatrimonioDoughnutChart patrimonio={undefined} />);
    expect(screen.getByText(/Sem dados suficientes/)).toBeInTheDocument();
  });

  it("renderiza fatias de composicao, filtrando valores <= 0", () => {
    render(<PatrimonioDoughnutChart patrimonio={COMPOSICAO} />);
    expect(getSlices()).toEqual({ Investimentos: 500000, "Imóveis": 300000 });
  });

  it("cai para tabela_categorias quando composicao ausente", () => {
    render(
      <PatrimonioDoughnutChart
        patrimonio={{ tabela_categorias: [{ categoria: "Caixa", valor: 10000, pct: 100 }] }}
      />,
    );
    expect(getSlices()).toEqual({ Caixa: 10000 });
  });

  it("propaga conclusion para o ReportCard", () => {
    render(
      <PatrimonioDoughnutChart patrimonio={COMPOSICAO} conclusion="Concentração em investimentos." />,
    );
    expect(screen.getByText(/Concentração em investimentos\./)).toBeInTheDocument();
  });
});

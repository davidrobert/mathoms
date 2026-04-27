/**
 * v2.E.5 — specs do `<DespesasDoughnutChart>` (Chart.js doughnut + PeriodToggle).
 *
 * Cobre: render do chart-context, toggle muda fatias somando datasets dentro
 * da janela, fallback para `despesas_por_categoria` (toggle oculto), null em
 * dataset vazio, conclusion prop > derivada > sem render. Não testa render
 * visual do canvas (Chart.js precisa de `canvas` npm pkg que não está
 * instalado — chartPrimitives.test.tsx já estabelece esse contrato).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DespesasDoughnutChart } from "@/components/report/charts/DespesasDoughnutChart";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

// react-chartjs-2 quebra em jsdom sem pkg `canvas`. Mock com div + label
// dump para introspeção do conteúdo das fatias.
vi.mock("react-chartjs-2", () => ({
  Chart: ({
    data,
  }: {
    data: {
      labels?: readonly string[];
      datasets: readonly {
        data: readonly number[];
        backgroundColor?: readonly string[] | string;
      }[];
    };
  }) => {
    const ds = data.datasets[0];
    const bgArr = Array.isArray(ds?.backgroundColor)
      ? (ds!.backgroundColor as readonly string[])
      : [];
    return (
      <div data-testid="chart-mock" data-bg-colors={JSON.stringify(bgArr)}>
        {(data.labels ?? []).map((lbl, i) => (
          <span key={lbl} data-slice={lbl} data-value={ds?.data[i] ?? 0}>
            {lbl}={ds?.data[i] ?? 0}
          </span>
        ))}
      </div>
    );
  },
}));

const FLUXO_WITH_DATASETS: FluxoCaixaSummary = {
  receita_despesa_mensal_detalhado: {
    labels: ["26/01", "26/02", "26/03", "26/04"],
    despesa_datasets: [
      { label: "moradia", data: [100, 100, 100, 100] },
      { label: "alimentacao", data: [50, 50, 50, 50] },
      { label: "nao_identificado", data: [200, 200, 200, 200] },
    ],
  },
};

const FLUXO_AGGREGATE_ONLY: FluxoCaixaSummary = {
  despesas_por_categoria: {
    moradia: 1000,
    alimentacao: 500,
    transporte: 200,
  },
};

function getSlices(): Record<string, number> {
  const out: Record<string, number> = {};
  for (const el of document.querySelectorAll("[data-slice]")) {
    const k = el.getAttribute("data-slice") ?? "";
    out[k] = Number(el.getAttribute("data-value") ?? "0");
  }
  return out;
}

describe("<DespesasDoughnutChart />", () => {
  it("retorna null quando não há despesa nem datasets", () => {
    const { container } = render(<DespesasDoughnutChart fluxo={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza chart-context com total e número de categorias", () => {
    render(<DespesasDoughnutChart fluxo={FLUXO_WITH_DATASETS} />);
    const ctx = document.querySelector(".chart-context");
    // 12m: soma de 4 meses = (100+50+200) * 4 = 1.400
    expect(ctx?.textContent).toMatch(/Distribuição das despesas totais/);
    expect(ctx?.textContent).toMatch(/3 categorias/);
  });

  it("renderiza PeriodToggle quando há datasets, oculta no fallback agregado", () => {
    const { rerender } = render(<DespesasDoughnutChart fluxo={FLUXO_WITH_DATASETS} />);
    expect(screen.queryByRole("tablist")).toBeInTheDocument();

    rerender(<DespesasDoughnutChart fluxo={FLUXO_AGGREGATE_ONLY} />);
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("ordena fatias por valor desc", () => {
    render(<DespesasDoughnutChart fluxo={FLUXO_WITH_DATASETS} />);
    const slices = getSlices();
    // 12m default: nao_identificado=800 > moradia=400 > alimentacao=200
    const labels = Object.keys(slices);
    expect(labels[0]).toBe("Não identificado");
    expect(labels[1]).toBe("Moradia");
    expect(labels[2]).toBe("Alimentação");
  });

  it("toggle 3M recalcula fatias somando últimos 3 meses dos datasets", async () => {
    const user = userEvent.setup();
    render(<DespesasDoughnutChart fluxo={FLUXO_WITH_DATASETS} />);

    // 12m default: moradia = 100*4 = 400
    expect(getSlices()["Moradia"]).toBe(400);

    await user.click(screen.getByRole("tab", { name: "3M" }));

    // 3M: últimos 3 meses → moradia = 100*3 = 300
    const slicesAfter = getSlices();
    expect(slicesAfter["Moradia"]).toBe(300);
    expect(slicesAfter["Alimentação"]).toBe(150);
    expect(slicesAfter["Não identificado"]).toBe(600);
  });

  it("renderiza conclusion prop quando passada", () => {
    render(
      <DespesasDoughnutChart
        fluxo={FLUXO_WITH_DATASETS}
        conclusion="Conclusão custom v2.E.5"
      />,
    );
    expect(screen.getByText("Conclusão custom v2.E.5")).toBeInTheDocument();
  });

  it("deriva conclusion default a partir do top da categoria", () => {
    render(<DespesasDoughnutChart fluxo={FLUXO_WITH_DATASETS} />);
    // top: nao_identificado, 800/1400 = 57.1% → também acende alerta >10%
    const matches = screen.getAllByText(/Não identificado lidera com/);
    expect(matches.length).toBeGreaterThan(0);
    expect(screen.getByText(/priorize reclassificação/)).toBeInTheDocument();
  });

  it("usa fallback `despesas_por_categoria` quando datasets ausentes", () => {
    render(<DespesasDoughnutChart fluxo={FLUXO_AGGREGATE_ONLY} />);
    const slices = getSlices();
    expect(slices["Moradia"]).toBe(1000);
    expect(slices["Alimentação"]).toBe(500);
    expect(slices["Transporte"]).toBe(200);
  });

  // Regressão: cores de cada fatia precisam vir resolvidas (hex/rgb) —
  // nunca string literal "var(--chart-N)". Bug histórico (de2c00a / 9ce3ce2):
  // com `pickColorByIndex` retornando "var(--chart-N)" e Chart.js sem
  // resolver CSS vars no canvas, todas as fatias do donut renderizavam em
  // preto. Fix migra para `useChartTheme().categorical` (resolve via
  // getComputedStyle; em jsdom usa LIGHT_FALLBACK = hex literais).
  it("backgroundColor de cada fatia é hex/rgb resolvido — nunca 'var(...)' literal", () => {
    render(<DespesasDoughnutChart fluxo={FLUXO_WITH_DATASETS} />);
    const chart = screen.getByTestId("chart-mock");
    const bgColors: ReadonlyArray<string> = JSON.parse(
      chart.getAttribute("data-bg-colors") ?? "[]",
    );
    // 3 fatias com value > 0 em FLUXO_WITH_DATASETS
    expect(bgColors).toHaveLength(3);
    bgColors.forEach((c) => {
      expect(c).toBeTruthy();
      expect(c.startsWith("var(")).toBe(false);
    });
  });

  it("filtra categorias com value <= 0", () => {
    const fluxo: FluxoCaixaSummary = {
      receita_despesa_mensal_detalhado: {
        labels: ["26/01", "26/02"],
        despesa_datasets: [
          { label: "moradia", data: [100, 100] },
          { label: "saude", data: [0, 0] },
        ],
      },
    };
    render(<DespesasDoughnutChart fluxo={fluxo} />);
    const slices = getSlices();
    expect(slices["Moradia"]).toBeDefined();
    expect(slices["Saúde"]).toBeUndefined();
  });
});

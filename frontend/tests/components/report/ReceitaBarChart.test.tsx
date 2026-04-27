/**
 * v2.E.4 — specs do `<ReceitaBarChart>` migrado para Chart.js.
 *
 * Cobre: agregação de `receita_datasets[]` por janela do PeriodToggle,
 * ordenação desc por total, estabilidade de cor entre renders, oculta
 * toggle em print mode, fallback de conclusion gerado client-side.
 *
 * Mocka `ChartBar` (primitives) — Chart.js não roda em jsdom (canvas pkg
 * não instalado, ver `frontend/tests/setup.ts`).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { ChartSeries as ChartPrimitiveSeries } from "@/components/report/charts/primitives/types";

interface CapturedRender {
  series: readonly ChartPrimitiveSeries[];
  labels: readonly string[];
}

const captures: CapturedRender[] = [];

vi.mock("@/components/report/charts/primitives/ChartBar", () => ({
  ChartBar: (props: {
    readonly labels: readonly string[];
    readonly series: readonly ChartPrimitiveSeries[];
  }) => {
    captures.push({ labels: props.labels, series: props.series });
    return (
      <div data-testid="chart-bar-mock">
        {props.series.map((s) => (
          <span key={s.label} data-testid="series-item" data-color={s.color}>
            {s.label}:{s.data[0]}
          </span>
        ))}
      </div>
    );
  },
}));

import { ReceitaBarChart } from "@/components/report/charts/ReceitaBarChart";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

function buildFluxo(): FluxoCaixaSummary {
  // 12 meses de dados; 3 fontes com totais diferentes para validar ordenação.
  const labels = Array.from({ length: 12 }, (_, i) => {
    const m = String((i % 12) + 1).padStart(2, "0");
    return `26/${m}`;
  });
  return {
    receita_despesa_mensal_detalhado: {
      labels,
      receita_datasets: [
        { label: "receita_clt", data: Array(12).fill(10000) },        // total 12 m: 120k
        { label: "receita_pj", data: Array(12).fill(5000) },          // total 12 m: 60k
        { label: "receita_aluguel", data: Array(12).fill(2000) },     // total 12 m: 24k
      ],
    },
  };
}

describe("<ReceitaBarChart /> v2.E.4", () => {
  it("agrega receita_datasets em totais por fonte (janela 12m default)", () => {
    captures.length = 0;
    render(<ReceitaBarChart fluxo={buildFluxo()} />);
    const last = captures.at(-1);
    expect(last).toBeDefined();
    expect(last!.series).toHaveLength(3);
    expect(last!.series[0].label).toBe("Receita Clt");
    expect(last!.series[0].data[0]).toBe(120000);
    expect(last!.series[1].label).toBe("Receita Pj");
    expect(last!.series[1].data[0]).toBe(60000);
    expect(last!.series[2].label).toBe("Receita Aluguel");
    expect(last!.series[2].data[0]).toBe(24000);
  });

  it("recalcula totais ao mudar period (3M usa apenas últimos 3 meses)", async () => {
    captures.length = 0;
    const user = userEvent.setup();
    render(<ReceitaBarChart fluxo={buildFluxo()} />);

    await user.click(screen.getByRole("tab", { name: "3M" }));
    const last = captures.at(-1);
    expect(last).toBeDefined();
    // 3 meses × 10k = 30k para CLT
    expect(last!.series[0].data[0]).toBe(30000);
    expect(last!.series[1].data[0]).toBe(15000);
    expect(last!.series[2].data[0]).toBe(6000);
  });

  it("ordena fontes por total desc — fonte líder muda quando dados invertem", () => {
    captures.length = 0;
    const fluxo: FluxoCaixaSummary = {
      receita_despesa_mensal_detalhado: {
        labels: ["26/01", "26/02"],
        receita_datasets: [
          { label: "fonte_pequena", data: [100, 100] },
          { label: "fonte_grande", data: [9000, 9000] },
        ],
      },
    };
    render(<ReceitaBarChart fluxo={fluxo} />);
    const last = captures.at(-1);
    expect(last!.series[0].label).toBe("Fonte Grande");
    expect(last!.series[1].label).toBe("Fonte Pequena");
  });

  it("cor por fonte é estável entre renders (mesmo índice → mesma cor)", () => {
    captures.length = 0;
    const fluxo = buildFluxo();
    const { rerender } = render(<ReceitaBarChart fluxo={fluxo} />);
    const first = captures.at(-1)!;
    rerender(<ReceitaBarChart fluxo={fluxo} />);
    const second = captures.at(-1)!;
    expect(second.series.map((s) => s.color)).toEqual(first.series.map((s) => s.color));
  });

  it("filtra fontes com total zero", () => {
    captures.length = 0;
    const fluxo: FluxoCaixaSummary = {
      receita_despesa_mensal_detalhado: {
        labels: ["26/01", "26/02"],
        receita_datasets: [
          { label: "ativa", data: [100, 100] },
          { label: "zerada", data: [0, 0] },
        ],
      },
    };
    render(<ReceitaBarChart fluxo={fluxo} />);
    const last = captures.at(-1)!;
    expect(last.series).toHaveLength(1);
    expect(last.series[0].label).toBe("Ativa");
  });

  it("retorna null quando não há datasets", () => {
    captures.length = 0;
    const { container } = render(<ReceitaBarChart fluxo={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza chart-context com top fontes e total formatado", () => {
    render(<ReceitaBarChart fluxo={buildFluxo()} />);
    const ctx = document.querySelector("[data-chart-context]");
    expect(ctx).toBeInTheDocument();
    expect(ctx?.textContent).toMatch(/Composição da receita total/);
    expect(ctx?.textContent).toMatch(/Receita Clt/);
  });

  it("usa conclusion vinda da prop quando fornecida", () => {
    render(<ReceitaBarChart fluxo={buildFluxo()} conclusion="Texto custom backend" />);
    expect(screen.getByText("Texto custom backend")).toBeInTheDocument();
  });

  // Regressão: cor de cada série precisa vir resolvida (hex/rgb) — nunca
  // string literal "var(--chart-N)". Bug histórico (de2c00a/9ce3ce2): com
  // `pickColorByIndex` retornando "var(--chart-N)" e Chart.js sem resolver
  // CSS vars no canvas, todas as barras renderizavam em preto. Fix consome
  // `useChartTheme().categorical` (resolve por getComputedStyle / fallback
  // hex). Em jsdom, fallback retorna hex literais do `LIGHT_FALLBACK`.
  it("cor de cada série é hex/rgb resolvido — nunca 'var(...)' literal", () => {
    captures.length = 0;
    render(<ReceitaBarChart fluxo={buildFluxo()} />);
    const last = captures.at(-1)!;
    expect(last.series.length).toBeGreaterThan(0);
    last.series.forEach((s) => {
      expect(s.color).toBeTruthy();
      expect(s.color!.startsWith("var(")).toBe(false);
    });
  });

  it("oculta PeriodToggle em print mode", () => {
    const original = window.matchMedia;
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
    try {
      render(<ReceitaBarChart fluxo={buildFluxo()} />);
      expect(screen.queryByRole("tab", { name: "3M" })).toBeNull();
    } finally {
      Object.defineProperty(window, "matchMedia", {
        writable: true,
        configurable: true,
        value: original,
      });
    }
  });
});

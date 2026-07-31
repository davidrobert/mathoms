/**
 * v2.E.3 — specs do `<FluxoMensalChart>` migrado para Chart.js.
 *
 * Cobre: render do toggle + chart-context auto-gerado, click no toggle
 * recalcula a janela e o texto, fallback de chart-conclusion quando o
 * `narrativas` não traz texto, retorno `null` quando não há labels.
 *
 * Canvas Chart.js é mockado — jsdom não tem `HTMLCanvasElement.getContext`
 * e o objetivo é validar markup + state, não pixel rendering.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FluxoMensalChart } from "@/components/report/charts/FluxoMensalChart";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

vi.mock("react-chartjs-2", () => ({
  Chart: ({
    "aria-label": ariaLabel,
    data,
  }: {
    "aria-label"?: string;
    data?: { datasets?: Array<{ backgroundColor?: string }> };
  }) => (
    <div
      data-testid="chart-mock"
      aria-label={ariaLabel}
      data-bg-colors={JSON.stringify(
        (data?.datasets ?? []).map((d) => d.backgroundColor ?? null),
      )}
    />
  ),
}));

/** Bloco `full` (14 meses) — só ele é lido quando `janela_12m` está ausente. */
function buildFluxoFullOnly(): FluxoCaixaSummary {
  const labels = Array.from({ length: 14 }, (_, i) => {
    const month = ((i + 2) % 12) + 1;
    const year = 25 + Math.floor((i + 2) / 12);
    return `${String(year).padStart(2, "0")}/${String(month).padStart(2, "0")}`;
  });
  const totais_receita = Array.from({ length: 14 }, () => 70_000);
  const totais_despesa = Array.from({ length: 14 }, () => 58_000);
  return {
    janela: "full",
    janela_meses: 14,
    receita_recorrente_mensal: 68_949,
    despesa_mensal_media: 57_607,
    receita_despesa_mensal_detalhado: { labels, totais_receita, totais_despesa },
  };
}

/** ADR-306 D1 (A40.l3) — `janela_12m` divergente do bloco `full`: todo texto
 * rotulado "últimos 12 meses" tem de citar 72.000/55.000, nunca 68.949/57.607. */
function buildFluxo(): FluxoCaixaSummary {
  return {
    ...buildFluxoFullOnly(),
    janela_12m: {
      janela: "12m",
      janela_meses: 12,
      n_meses: 12,
      periodo: "2025-04 a 2026-03",
      receita_recorrente_mensal: 72_000,
      despesa_mensal_media: 55_000,
      taxa_poupanca_recorrente: 20.5,
    },
  };
}

describe("<FluxoMensalChart />", () => {
  it("retorna null quando não há labels", () => {
    const { container } = render(<FluxoMensalChart fluxo={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza title, chart-context, PeriodToggle e canvas mock", () => {
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    expect(screen.getByText("Fluxo de Caixa Mensal")).toBeInTheDocument();
    const ctx = document.querySelector("[data-chart-context]");
    expect(ctx?.textContent).toContain("Janela dos últimos 12 meses");
    // ADR-306 D1: rótulo 12m ⇒ agregado de `janela_12m`, nunca do bloco full.
    expect(ctx?.textContent).toMatch(/R\$\s?72\.000/);
    expect(ctx?.textContent).toMatch(/R\$\s?55\.000/);
    expect(ctx?.textContent).not.toMatch(/R\$\s?68\.949/);
    expect(ctx?.textContent).not.toMatch(/R\$\s?57\.607/);
    expect(screen.getByTestId("chart-mock")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "12M" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("sem janela_12m: agregado full é citado com rótulo de período completo", () => {
    render(<FluxoMensalChart fluxo={buildFluxoFullOnly()} />);
    const ctx = document.querySelector("[data-chart-context]");
    expect(ctx?.textContent).toMatch(/todo o período analisado \(14 meses\)/i);
    expect(ctx?.textContent).toMatch(/R\$\s?68\.949/);
    expect(ctx?.textContent).not.toMatch(/R\$\s?72\.000/);
  });

  it("toggle 3M reduz a janela e omite o agregado (payload não tem bloco 3m)", async () => {
    const user = userEvent.setup();
    render(<FluxoMensalChart fluxo={buildFluxo()} />);

    await user.click(screen.getByRole("tab", { name: "3M" }));

    const ctx = document.querySelector("[data-chart-context]");
    expect(ctx?.textContent).toContain("Janela dos últimos 3 meses");
    // Derivar média de `totais_receita` trocaria receita bruta por recorrente.
    expect(ctx?.textContent).not.toMatch(/R\$\s?72\.000/);
    expect(ctx?.textContent).not.toMatch(/R\$\s?68\.949/);
  });

  it("usa prop conclusion quando passada", () => {
    render(
      <FluxoMensalChart fluxo={buildFluxo()} conclusion="Texto custom de conclusão." />,
    );
    expect(screen.getByText("Texto custom de conclusão.")).toBeInTheDocument();
  });

  it("gera fallback de conclusão com sobra e taxa canônicas de 12m", () => {
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    // sobra = 72000 - 55000 = 17000 (bloco 12m), não 68949 - 57607 = 11342.
    const text = document.body.textContent ?? "";
    expect(text).toMatch(/Saldo recorrente mensal de R\$\s?17\.000/);
    expect(text).not.toMatch(/R\$\s?11\.342/);
    // Taxa é lida de `taxa_poupanca_recorrente` (ex-aporte, ADR-333), nunca
    // recomputada de despesa_mensal_media — (72000-55000)/72000 = 23,6%.
    expect(text).toContain("Taxa de poupança recorrente de 20,5%");
    expect(text).not.toContain("23,6%");
  });

  it("sem janela_12m: fallback rotula o período completo e não inventa taxa", () => {
    render(<FluxoMensalChart fluxo={buildFluxoFullOnly()} />);
    const text = document.body.textContent ?? "";
    expect(text).toMatch(/Saldo recorrente mensal de R\$\s?11\.342/);
    expect(text).toMatch(/todo o período analisado \(14 meses\)/i);
    expect(text).not.toContain("Taxa de poupança");
  });
});

// ─── Regressão: cores resolvidas (nunca "var(...)") ───
// Bug histórico: receita/despesa passavam {color: "var(--semantic-gain)"}
// literal — Chart.js não resolve CSS vars no canvas → barras ficavam pretas
// em produção. Fix consome useChartTheme().semantic.{gain,loss} (hex
// resolvido via getComputedStyle).
describe("<FluxoMensalChart /> · cores resolvidas (anti-regressão)", () => {
  it("backgroundColor de receita e despesa é cor concreta (hex/rgb), nunca 'var(...)'", () => {
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    const chart = screen.getByTestId("chart-mock");
    const bgColors: ReadonlyArray<string | null> = JSON.parse(
      chart.getAttribute("data-bg-colors") ?? "[]",
    );
    expect(bgColors).toHaveLength(2);
    bgColors.forEach((c) => {
      expect(c).toBeTruthy();
      expect(c!.startsWith("var(")).toBe(false);
    });
  });
});

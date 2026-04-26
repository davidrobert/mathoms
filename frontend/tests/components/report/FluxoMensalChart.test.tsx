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
  Chart: ({ "aria-label": ariaLabel }: { "aria-label"?: string }) => (
    <div data-testid="chart-mock" aria-label={ariaLabel} />
  ),
}));

function buildFluxo(): FluxoCaixaSummary {
  const labels = Array.from({ length: 14 }, (_, i) => {
    const month = ((i + 2) % 12) + 1;
    const year = 25 + Math.floor((i + 2) / 12);
    return `${String(year).padStart(2, "0")}/${String(month).padStart(2, "0")}`;
  });
  const totais_receita = Array.from({ length: 14 }, () => 70_000);
  const totais_despesa = Array.from({ length: 14 }, () => 58_000);
  return {
    receita_recorrente_mensal: 68_949,
    despesa_mensal_media: 57_607,
    receita_despesa_mensal_detalhado: { labels, totais_receita, totais_despesa },
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
    expect(ctx?.textContent).toMatch(/R\$\s?68\.949/);
    expect(ctx?.textContent).toMatch(/R\$\s?57\.607/);
    expect(screen.getByTestId("chart-mock")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "12M" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("toggle 3M reduz a janela do chart-context", async () => {
    const user = userEvent.setup();
    render(<FluxoMensalChart fluxo={buildFluxo()} />);

    await user.click(screen.getByRole("tab", { name: "3M" }));

    const ctx = document.querySelector("[data-chart-context]");
    expect(ctx?.textContent).toContain("Janela dos últimos 3 meses");
  });

  it("usa prop conclusion quando passada", () => {
    render(
      <FluxoMensalChart fluxo={buildFluxo()} conclusion="Texto custom de conclusão." />,
    );
    expect(screen.getByText("Texto custom de conclusão.")).toBeInTheDocument();
  });

  it("gera fallback de conclusão com taxa de poupança quando prop ausente", () => {
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    // saldo = 68949 - 57607 = 11342; taxa = 11342 / 68949 ≈ 16.4%
    const text = document.body.textContent ?? "";
    expect(text).toMatch(/Saldo recorrente mensal de R\$\s?11\.342/);
    expect(text).toContain("Taxa de poupança recorrente de 16,4%");
  });
});

/**
 * v2.E.3 — specs do `<FluxoMensalChart>` migrado para Chart.js.
 *
 * Cobre: render do toggle + chart-context auto-gerado, click no toggle
 * recalcula a janela e o texto, fallback de chart-conclusion quando o
 * `narrativas` não traz texto, retorno `null` quando não há labels, e o nome,
 * a cor e o tooltip da série bruta de saídas (ADR-333).
 *
 * Canvas Chart.js é mockado — jsdom não tem `HTMLCanvasElement.getContext`
 * e o objetivo é validar markup + state, não pixel rendering.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FluxoMensalChart } from "@/components/report/charts/FluxoMensalChart";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

type TooltipLabel = (ctx: {
  parsed: { y: number };
  dataset: { label?: string };
}) => string;

interface CapturedOptions {
  plugins?: { tooltip?: { callbacks?: { label?: TooltipLabel } } };
  scales?: { y?: { ticks?: { callback?: (v: number) => string } } };
}

const captured = vi.hoisted(() => ({ options: null as unknown }));

vi.mock("react-chartjs-2", () => ({
  Chart: ({
    "aria-label": ariaLabel,
    data,
    options,
  }: {
    "aria-label"?: string;
    data?: {
      datasets?: Array<{ label?: string; data?: number[]; backgroundColor?: string }>;
    };
    options?: unknown;
  }) => {
    captured.options = options;
    return (
      <div
        data-testid="chart-mock"
        aria-label={ariaLabel}
        data-bg-colors={JSON.stringify(
          (data?.datasets ?? []).map((d) => d.backgroundColor ?? null),
        )}
        data-series={JSON.stringify(
          (data?.datasets ?? []).map((d) => ({ label: d.label, data: d.data })),
        )}
      />
    );
  },
}));

function capturedOptions(): CapturedOptions {
  return captured.options as CapturedOptions;
}

function renderedSeries(): Array<{ label: string; data: number[] }> {
  return JSON.parse(screen.getByTestId("chart-mock").getAttribute("data-series") ?? "[]");
}

function renderedColors(): Array<string | null> {
  return JSON.parse(screen.getByTestId("chart-mock").getAttribute("data-bg-colors") ?? "[]");
}

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
    // Contagem e range vêm do MESMO lugar: as barras desenhadas.
    expect(ctx?.textContent).toBe("No gráfico: 12 meses (mai/25 a abr/26).");
    expect(screen.getByTestId("chart-mock")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "12M" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("contexto não cita agregado — a base rotulada vive só na conclusão", () => {
    // O contexto repetia a média que a conclusão `fluxo_mensal` já declara, e com
    // ela o "aportes incluídos": dois números iguais duas vezes no mesmo card.
    for (const fluxo of [buildFluxo(), buildFluxoFullOnly()]) {
      const { unmount } = render(<FluxoMensalChart fluxo={fluxo} />);
      const ctx = document.querySelector("[data-chart-context]")?.textContent ?? "";
      expect(ctx).toMatch(/^No gráfico: 12 meses/);
      expect(ctx).not.toMatch(/R\$/);
      unmount();
    }
  });

  it("toggle 3M reduz a janela e omite o agregado (payload não tem bloco 3m)", async () => {
    const user = userEvent.setup();
    render(<FluxoMensalChart fluxo={buildFluxo()} />);

    await user.click(screen.getByRole("tab", { name: "3M" }));

    const ctx = document.querySelector("[data-chart-context]");
    expect(ctx?.textContent).toBe("No gráfico: 3 meses (fev/26 a abr/26).");
  });

  it("usa prop conclusion quando passada", () => {
    render(
      <FluxoMensalChart fluxo={buildFluxo()} conclusion="Texto custom de conclusão." />,
    );
    expect(screen.getByText("Texto custom de conclusão.")).toBeInTheDocument();
  });

  it("não inventa conclusão própria — o texto de S2 vem de um builder só", () => {
    // A40.l3 · I7: o componente tinha um `buildFallbackConclusion` que
    // produção NUNCA alcançava (`FALLBACKS.fluxo_mensal` existe ⇒
    // `deriveChartConclusion` nunca devolve null ⇒ a prop é sempre string).
    // Asserts guardando aquele ramo davam cobertura fantasma: foi por isso que
    // a mensalização full sem rótulo do chart irmão passou.
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    expect(document.querySelector("[data-chart-conclusion]")).toBeNull();
  });
});

// ─── ADR-333: a série bruta inclui o aporte ───
// `totais_despesa` é o `_total` mensal BRUTO (aporte incluído). "Despesa" em
// vermelho nomeava, na mesma S2, a base da rosca que tira o aporte, e lia a
// poupança como perda. Mesmo nome do `/plano` (#2202).
describe("<FluxoMensalChart /> · série de saídas (ADR-333)", () => {
  it("nomeia as séries 'Receitas' e 'Saídas (inclui aportes)', saídas abaixo do zero", () => {
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    const [receitas, saidas] = renderedSeries();
    expect(receitas.label).toBe("Receitas");
    expect(saidas.label).toBe("Saídas (inclui aportes)");
    expect(receitas.data.every((v) => v > 0)).toBe(true);
    expect(saidas.data.every((v) => v < 0)).toBe(true);
    expect(renderedSeries().map((s) => s.label).join(" ")).not.toMatch(/despesa/i);
  });

  it("saídas em neutro, nunca na cor de perda", () => {
    // jsdom sem CSS ⇒ useChartTheme cai no LIGHT_FALLBACK dos tokens:
    // gain #15803D, loss #B91C1C, neutral (`--semantic-neutral-financial`) #64748B.
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    const [corReceitas, corSaidas] = renderedColors();
    expect(corReceitas).toBe("#15803D");
    expect(corSaidas).toBe("#64748B");
    expect(corSaidas).not.toBe("#B91C1C");
  });

  it("tooltip mostra o valor absoluto; o eixo mantém o sinal", () => {
    // O nome já dá a direção, e "-R$" é reservado ao vermelho (COPY §4.1). No
    // eixo o sinal fica: em P&B ele e a posição são o que separa as séries.
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    const options = capturedOptions();
    const label = options.plugins?.tooltip?.callbacks?.label;
    const tick = options.scales?.y?.ticks?.callback;
    expect(
      label?.({ parsed: { y: -55_000 }, dataset: { label: "Saídas (inclui aportes)" } }),
    ).toMatch(/^Saídas \(inclui aportes\): R\$\s?55\.000$/);
    expect(tick?.(-50_000)).toMatch(/^-R\$\s?50\.000$/);
  });

  it("aria-label descreve a direção e o aporte, sem 'despesa'", () => {
    render(<FluxoMensalChart fluxo={buildFluxo()} />);
    expect(screen.getByTestId("chart-mock")).toHaveAttribute(
      "aria-label",
      "Fluxo de caixa mensal: receitas acima do zero; saídas, aportes incluídos, abaixo.",
    );
  });
});

// ─── Regressão: cores resolvidas (nunca "var(...)") ───
// Bug histórico: receita/despesa passavam {color: "var(--semantic-gain)"}
// literal — Chart.js não resolve CSS vars no canvas → barras ficavam pretas
// em produção. Fix consome useChartTheme().semantic.{gain,loss} (hex
// resolvido via getComputedStyle).
describe("<FluxoMensalChart /> · cores resolvidas (anti-regressão)", () => {
  it("backgroundColor de receitas e saídas é cor concreta (hex/rgb), nunca 'var(...)'", () => {
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

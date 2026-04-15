/**
 * F9 · F1.1 — Smoke tests do ReportShell nativo.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ReportModeProvider } from "@/components/report/ReportModeProvider";
import { ReportShell } from "@/components/report/ReportShell";
import type { UseReportDataState } from "@/hooks/useReportData";
import type { ReportAnalysisData } from "@/lib/api";

function wrap(ui: React.ReactNode) {
  return (
    <TooltipProvider>
      <ReportModeProvider initialMode="estrategico">{ui}</ReportModeProvider>
    </TooltipProvider>
  );
}

const SAMPLE_DATA: ReportAnalysisData = {
  periodo_dados: "202601-202604",
  patrimonio: { bruto: 1_000_000 },
  score: { valor: 82, max: 100, classificacao: "Muito Bom" },
};

describe("ReportShell", () => {
  it("renderiza header, TOC e áreas principais em sucesso", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          reportTitle="Relatório Família Teste"
          dataState={state}
        />,
      ),
    );

    // Título aparece no header + no hero do article
    expect(screen.getAllByText("Relatório Família Teste").length).toBeGreaterThan(0);
    expect(screen.getByText(/202601-202604/)).toBeInTheDocument();
  });

  it("mostra seletor de modo (estratégico/tático/EUA)", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell reportId="r1" reportTitle="Rel" dataState={state} />,
      ),
    );
    expect(
      screen.getByRole("tab", { name: "Estratégico", selected: true }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Tático" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "EUA" })).toBeInTheDocument();
  });

  it("renderiza seções do layout como stubs enquanto não migrados", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell reportId="r1" reportTitle="Rel" dataState={state} />,
      ),
    );
    // Usa getAllByText pq "Patrimônio" aparece em título + card_ids listados
    const matches = screen.getAllByText(/Patrimônio/i);
    expect(matches.length).toBeGreaterThan(0);
    // O stub mostra mensagem padronizada — uma por seção no layout estratégico
    expect(
      screen.getAllByText(/Conteúdo em migração/).length,
    ).toBeGreaterThan(0);
  });

  it("mostra mensagem de erro quando o fetch falha", () => {
    const state: UseReportDataState = {
      status: "error",
      error: new Error("boom"),
    };
    render(
      wrap(
        <ReportShell reportId="r1" reportTitle="Rel" dataState={state} />,
      ),
    );
    expect(
      screen.getByText(/Não foi possível carregar os dados/),
    ).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("mostra spinner em loading", () => {
    const state: UseReportDataState = { status: "loading" };
    const { container } = render(
      wrap(
        <ReportShell reportId="r1" reportTitle="Rel" dataState={state} />,
      ),
    );
    expect(container.querySelector(".animate-spin")).toBeTruthy();
  });
});

describe("MonetaryValue", () => {
  it("formata BRL com font-mono e tabular-nums", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={1234567.89} />);
    const span = container.querySelector("span");
    expect(span).not.toBeNull();
    expect(span!.className).toMatch(/font-mono/);
    expect(span!.className).toMatch(/tabular-nums/);
    // pt-BR: ponto milhar + vírgula decimal
    expect(span!.textContent).toMatch(/1\.234\.567,89/);
  });

  it("renderiza — para null", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={null} />);
    expect(container.textContent).toBe("—");
  });

  it("colore e prefixa sinal com signed", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={500} signed />);
    const span = container.querySelector("span");
    expect(span!.className).toMatch(/text-gain/);
    expect(span!.textContent?.startsWith("+")).toBe(true);
  });

  it("compact renderiza notação abreviada", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={1_500_000} compact />);
    // "R$ 1,5 mi" (pt-BR) ou variação do ICU
    expect(container.textContent).toMatch(/1,5\s?mi/);
  });
});

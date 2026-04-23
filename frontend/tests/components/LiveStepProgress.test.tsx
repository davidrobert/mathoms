/**
 * ADR-119 — Contrato LiveStep. Testes do renderer uniforme.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { LiveStepProgress } from "@/app/(app)/pipeline/_components/LiveStepProgress";
import type { PipelineStageActivity } from "@/lib/api";

const base = (over: Partial<PipelineStageActivity> = {}): PipelineStageActivity => ({
  stage: "E1.5",
  ...over,
});

describe("<LiveStepProgress />", () => {
  it("renderiza nada quando não há counter, message nem item", () => {
    const { container } = render(<LiveStepProgress activity={base()} />);
    expect(container.firstChild).toBeNull();
  });

  it("mostra contador 'Item X de Y' quando itemsTotal > 0", () => {
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 2, itemsTotal: 5 })}
      />,
    );
    expect(screen.getByText("Item 3 de 5")).toBeInTheDocument();
    expect(screen.getByText("2/5")).toBeInTheDocument();
  });

  it("barra de progresso usa peso da fase (awaiting_llm=0.4)", () => {
    // done=2, phase=awaiting_llm → (2 + 0.4)/5 = 48%
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 2, itemsTotal: 5, phase: "awaiting_llm" })}
      />,
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "48");
  });

  it("barra de progresso = 100% quando finalizing no último item", () => {
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 4, itemsTotal: 5, phase: "finalizing" })}
      />,
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "100");
  });

  it("renderiza label PT-BR fixa da fase (awaiting_llm → 'Consultando IA…')", () => {
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 0, itemsTotal: 3, phase: "awaiting_llm" })}
      />,
    );
    expect(screen.getByText("Consultando IA…")).toBeInTheDocument();
  });

  it("usa activity.message como fallback quando não há phase (compat emissores antigos)", () => {
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 0, itemsTotal: 3, message: "Extraindo…" })}
      />,
    );
    expect(screen.getByText("Extraindo…")).toBeInTheDocument();
  });

  it("exibe currentItem truncado (font-mono)", () => {
    render(
      <LiveStepProgress
        activity={base({
          itemsDone: 1,
          itemsTotal: 3,
          currentItem: "declaracao_irpf_2024_david.pdf",
        })}
      />,
    );
    const el = screen.getByTitle("declaracao_irpf_2024_david.pdf");
    expect(el).toHaveTextContent("declaracao_irpf_2024_david.pdf");
  });

  it("degrada: sem itemsTotal, mostra só displayItem + message", () => {
    render(
      <LiveStepProgress
        activity={base({ file: "extrato.pdf", message: "Processando…" })}
      />,
    );
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.getByText("Processando…")).toBeInTheDocument();
    expect(screen.getByTitle("extrato.pdf")).toBeInTheDocument();
  });

  it("mostra 'X / ~Y est.' quando elapsedMs + estimatedDurationMs vêm", () => {
    render(
      <LiveStepProgress
        activity={base({
          itemsDone: 2,
          itemsTotal: 5,
          phase: "awaiting_llm",
          estimatedDurationMs: 60_000,
        })}
        elapsedMs={30_000}
      />,
    );
    expect(screen.getByText("30s / ~1m est.")).toBeInTheDocument();
  });

  it("pinta estimativa em warning quando elapsed > estimated", () => {
    render(
      <LiveStepProgress
        activity={base({
          itemsDone: 2,
          itemsTotal: 5,
          phase: "awaiting_llm",
          estimatedDurationMs: 60_000,
        })}
        elapsedMs={120_000}
      />,
    );
    const est = screen.getByText("2m / ~1m est.");
    expect(est).toHaveClass("text-warning");
  });

  it("omite estimativa quando estimatedDurationMs não vem (poucos runs históricos)", () => {
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 1, itemsTotal: 3, phase: "preparing" })}
        elapsedMs={10_000}
      />,
    );
    expect(screen.queryByText(/est\./)).not.toBeInTheDocument();
  });

  it("stalled=true troca dot pulsante por ícone de alerta + mensagem 'sem sinal há X'", () => {
    render(
      <LiveStepProgress
        activity={base({ itemsDone: 1, itemsTotal: 3, phase: "awaiting_llm" })}
        stalled
        stalledForMs={240_000}
      />,
    );
    expect(screen.getByLabelText("Sem sinal do servidor")).toBeInTheDocument();
    expect(screen.getByText(/sem sinal há 4m/)).toBeInTheDocument();
  });

  it("aria-live='polite' no contador permite leitura por screen reader sem interromper", () => {
    render(<LiveStepProgress activity={base({ itemsDone: 0, itemsTotal: 2 })} />);
    const counter = screen.getByText("Item 1 de 2");
    expect(counter).toHaveAttribute("aria-live", "polite");
  });
});

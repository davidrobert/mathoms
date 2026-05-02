/**
 * Caminho A · stop-gap (track_pipeline_review_quick_unblock).
 * Card mostrado quando run pausa em `needs_review`. Cobertura:
 *  - copy nova ("Erros de validação")
 *  - lista de validation_errors em font-mono
 *  - aprovar/cancelar disparam handlers e respeitam loading
 *  - parser tolerante a `\n` e `; `
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  NeedsReviewCard,
  parseValidationErrors,
} from "@/app/(app)/pipeline/_components/NeedsReviewCard";
import type { StageReviewResponse } from "@/lib/api";

function makeReview(over: Partial<StageReviewResponse> = {}): StageReviewResponse {
  return {
    id: "rev-1",
    pipeline_run_id: "run-1",
    stage: "extract_irpf_full",
    status: "pending",
    original_output_json: null,
    edited_output_json: null,
    validation_errors: null,
    reviewer_notes: null,
    created_at: "2026-05-02T00:00:00Z",
    reviewed_at: null,
    ...over,
  };
}

describe("parseValidationErrors", () => {
  it("retorna [] para null/undefined/string vazia", () => {
    expect(parseValidationErrors(null)).toEqual([]);
    expect(parseValidationErrors(undefined)).toEqual([]);
    expect(parseValidationErrors("")).toEqual([]);
  });

  it("split por \\n", () => {
    expect(parseValidationErrors("a\nb\nc")).toEqual(["a", "b", "c"]);
  });

  it("split por '; ' e trim", () => {
    expect(parseValidationErrors("a; b;  c")).toEqual(["a", "b", "c"]);
  });

  it("ignora linhas em branco", () => {
    expect(parseValidationErrors("a\n\n\nb")).toEqual(["a", "b"]);
  });
});

describe("<NeedsReviewCard />", () => {
  const baseProps = {
    runId: "run-1",
    pausedAtStage: "extract_irpf_full",
    pendingReviews: [] as StageReviewResponse[],
    resuming: false,
    cancelling: false,
    onResume: () => {},
    onCancel: () => {},
  };

  it("renderiza título com nome do stage e copy honesta", () => {
    render(<NeedsReviewCard {...baseProps} />);
    expect(
      screen.getByRole("heading", { name: /Erros de validação na etapa/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Aprovar não revisa o output/i),
    ).toBeInTheDocument();
  });

  it("renderiza lista de validation_errors em font-mono quando há erros", () => {
    const reviews = [
      makeReview({
        validation_errors: "campo X é obrigatório\ncampo Y inválido",
      }),
    ];
    render(<NeedsReviewCard {...baseProps} pendingReviews={reviews} />);

    expect(screen.getByText(/2 erros de validação/i)).toBeInTheDocument();
    const list = screen.getByRole("list");
    expect(list).toHaveClass("font-mono");
    expect(screen.getByText("campo X é obrigatório")).toBeInTheDocument();
    expect(screen.getByText("campo Y inválido")).toBeInTheDocument();
  });

  it("agrega erros de múltiplos pendingReviews", () => {
    const reviews = [
      makeReview({ id: "r1", validation_errors: "a\nb" }),
      makeReview({ id: "r2", validation_errors: "c" }),
    ];
    render(<NeedsReviewCard {...baseProps} pendingReviews={reviews} />);
    expect(screen.getByText(/3 erros de validação/i)).toBeInTheDocument();
  });

  it("click 'Aprovar mesmo assim' chama onResume", async () => {
    const onResume = vi.fn();
    render(<NeedsReviewCard {...baseProps} onResume={onResume} />);
    await userEvent.click(
      screen.getByRole("button", { name: /Aprovar mesmo assim e continuar/i }),
    );
    expect(onResume).toHaveBeenCalledOnce();
  });

  it("click 'Cancelar execução' chama onCancel", async () => {
    const onCancel = vi.fn();
    render(<NeedsReviewCard {...baseProps} onCancel={onCancel} />);
    await userEvent.click(
      screen.getByRole("button", { name: /Cancelar execução/i }),
    );
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("botão Aprovar mostra spinner e desabilita quando resuming=true", () => {
    render(<NeedsReviewCard {...baseProps} resuming />);
    const btn = screen.getByRole("button", { name: /Aprovando\.\.\./i });
    expect(btn).toBeDisabled();
    // Cancelar também desabilitado durante resume para não criar race.
    const cancelBtn = screen.getByRole("button", { name: /Cancelar execução/i });
    expect(cancelBtn).toBeDisabled();
  });

  it("botão Cancelar mostra spinner e desabilita quando cancelling=true", () => {
    render(<NeedsReviewCard {...baseProps} cancelling />);
    const cancelBtn = screen.getByRole("button", { name: /Cancelando\.\.\./i });
    expect(cancelBtn).toBeDisabled();
    const resumeBtn = screen.getByRole("button", {
      name: /Aprovar mesmo assim e continuar/i,
    });
    expect(resumeBtn).toBeDisabled();
  });
});

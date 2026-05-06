import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { NeedsReviewCard } from "@/app/(app)/pipeline/_components/NeedsReviewCard";

describe("<NeedsReviewCard />", () => {
  it("renderiza com pendingCount=0 sem crash (regressão ADR-158)", () => {
    /**
     * Guard contra o bug que motivou este teste: o refactor que tornou o card
     * um ponteiro deletou o teste antigo e nunca substituiu. Quando page.tsx
     * passou a chamar com `pendingCount` em vez de `pendingReviews`, o
     * componente ainda fazia `pendingReviews.flatMap(...)` e crashava em
     * runtime. Este caso garante que props mínimas renderizam sem TypeError.
     */
    render(
      <NeedsReviewCard
        runId="run-1"
        pausedAtStage={null}
        pendingCount={0}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /revisar agora/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancelar execução/i })).toBeInTheDocument();
  });

  it("pluraliza contagem quando pendingCount > 1", () => {
    render(
      <NeedsReviewCard
        runId="run-1"
        pausedAtStage="extract_irpf_full"
        pendingCount={3}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/3 revisões pendentes/i)).toBeInTheDocument();
  });

  it("usa singular quando pendingCount === 1", () => {
    render(
      <NeedsReviewCard
        runId="run-1"
        pausedAtStage="extract_irpf_full"
        pendingCount={1}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/1 revisão pendente/i)).toBeInTheDocument();
  });

  it('"Revisar agora" aponta para /pipeline/runs/[id]/reviews (ADR-158)', () => {
    render(
      <NeedsReviewCard
        runId="run-abc"
        pausedAtStage="extract_irpf_full"
        pendingCount={1}
        onCancel={vi.fn()}
      />,
    );
    /**
     * Base UI Button renderiza a primitiva `<a>` mas mantém `role="button"`
     * — por isso a query é por `role:"button"`, e validamos `href` no
     * elemento retornado.
     */
    expect(
      screen.getByRole("button", { name: /revisar agora/i }),
    ).toHaveAttribute("href", "/pipeline/runs/run-abc/reviews");
  });

  it("Cancelar execução chama onCancel", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <NeedsReviewCard
        runId="run-1"
        pausedAtStage="extract_irpf_full"
        pendingCount={2}
        onCancel={onCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: /cancelar execução/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});

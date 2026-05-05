import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { FreeTierSkippedBanner } from "@/app/(app)/pipeline/_components/FreeTierSkippedBanner";
import {
  getDismissedFreeTierRunId,
  setDismissedFreeTierRunId,
} from "@/app/(app)/pipeline/_components/dismissedFreeTierBanner";

function clearLocalStorage() {
  setDismissedFreeTierRunId(null);
}

describe("<FreeTierSkippedBanner />", () => {
  beforeEach(() => {
    clearLocalStorage();
  });

  it("renderiza quando há stages skipped_free_tier", () => {
    render(
      <FreeTierSkippedBanner
        runId="run-1"
        skippedStageCount={2}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/2 stages LLM foram pulados/i)).toBeInTheDocument();
  });

  it("usa singular quando skippedStageCount é 1", () => {
    render(
      <FreeTierSkippedBanner
        runId="run-1"
        skippedStageCount={1}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getByText(/1 stage LLM foi pulado/i)).toBeInTheDocument();
  });

  it("não renderiza quando skippedStageCount é 0", () => {
    render(
      <FreeTierSkippedBanner
        runId="run-1"
        skippedStageCount={0}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("não renderiza quando run já foi dispensado (localStorage)", () => {
    setDismissedFreeTierRunId("run-1");
    render(
      <FreeTierSkippedBanner
        runId="run-1"
        skippedStageCount={2}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renderiza para run diferente do dispensado", () => {
    setDismissedFreeTierRunId("run-other");
    render(
      <FreeTierSkippedBanner
        runId="run-new"
        skippedStageCount={2}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("dismiss: persiste runId no localStorage e chama onDismiss", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(
      <FreeTierSkippedBanner
        runId="run-1"
        skippedStageCount={2}
        onDismiss={onDismiss}
      />,
    );

    await user.click(screen.getByRole("button", { name: /fechar aviso/i }));

    expect(getDismissedFreeTierRunId()).toBe("run-1");
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("CTA aponta para /config", () => {
    render(
      <FreeTierSkippedBanner
        runId="run-1"
        skippedStageCount={1}
        onDismiss={vi.fn()}
      />,
    );
    const link = screen.getByRole("link", { name: /faça upgrade/i });
    expect(link).toHaveAttribute("href", "/config");
  });
});

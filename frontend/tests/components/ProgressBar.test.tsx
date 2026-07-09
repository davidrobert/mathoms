/**
 * Tests — A11 W5-T01 — ProgressBar expõe semântica ARIA de progressbar.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ProgressBar } from "@/components/ui/ProgressBar";

describe("ProgressBar", () => {
  it("expõe role progressbar com aria-valuenow/min/max e label", () => {
    render(<ProgressBar value={42} ariaLabel="Progresso da reserva: 42%" />);
    const bar = screen.getByRole("progressbar", {
      name: "Progresso da reserva: 42%",
    });
    expect(bar).toHaveAttribute("aria-valuenow", "42");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("clampa valor acima do máximo (aria e largura)", () => {
    render(<ProgressBar value={137.5} ariaLabel="Progresso da meta" />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "100");
    expect(bar.firstElementChild).toHaveStyle({ width: "100%" });
  });

  it("clampa valor abaixo do mínimo", () => {
    render(<ProgressBar value={-10} ariaLabel="Progresso" />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "0");
    expect(bar.firstElementChild).toHaveStyle({ width: "0%" });
  });

  it("normaliza largura para escala min/max customizada", () => {
    render(<ProgressBar value={3} min={0} max={6} ariaLabel="Meses de reserva" />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuemax", "6");
    expect(bar.firstElementChild).toHaveStyle({ width: "50%" });
  });
});

/**
 * MarketValueStaleness (ADR-227 §D5 · Sprint A15 Onda 5c) — coverage dos limiares.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { MarketValueStaleness } from "@/components/report/MarketValueStaleness";

describe("MarketValueStaleness", () => {
  it("não renderiza nada quando 0-12m", () => {
    const { container } = render(<MarketValueStaleness stalenessDays={300} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza badge warning (12-24m) com texto de meses", () => {
    render(<MarketValueStaleness stalenessDays={400} />);
    expect(screen.getByText(/Atualizado há \d+ meses/i)).toBeInTheDocument();
  });

  it("renderiza badge critical (>24m)", () => {
    render(<MarketValueStaleness stalenessDays={800} />);
    expect(screen.getByText(/Atualização há mais de 2 anos/i)).toBeInTheDocument();
  });
});

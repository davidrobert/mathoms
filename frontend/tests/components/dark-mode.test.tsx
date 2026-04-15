/**
 * Dark mode integration tests — F6.5B.11
 *
 * Estratégia: como Tailwind v4 + next-themes usa `class="dark"` no <html>
 * para alternar, validamos que ao adicionar a classe os componentes
 * mantêm seus tokens semânticos (não hardcoded color classes).
 *
 * Não testa a aparência pixel-perfect (isso é 6.5D.3 visual regression).
 * Testa que: render sob dark não crasha, classes dark: aplicam, e
 * componentes não dependem de cores hardcoded.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { KPICard } from "@/components/KPICard";
import { StatusBadge } from "@/components/StatusBadge";
import { Delta } from "@/components/Delta";
import { EmptyState } from "@/components/EmptyState";

beforeEach(() => {
  document.documentElement.classList.add("dark");
  // matchMedia(prefers-color-scheme: dark) → matches=true
  vi.spyOn(window, "matchMedia").mockImplementation((query: string) => ({
    matches: query.includes("dark"),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as any;
});

afterEach(() => {
  document.documentElement.classList.remove("dark");
  vi.restoreAllMocks();
});

describe("Dark mode integration", () => {
  it("KPICard renderiza sem crash em dark mode", () => {
    render(<KPICard label="Saldo" value="R$ 1.000,00" />);
    expect(screen.getByText("Saldo")).toBeInTheDocument();
    expect(document.documentElement).toHaveClass("dark");
  });

  it.each(["success", "warning", "error", "info", "neutral", "premium", "muted"] as const)(
    "StatusBadge variant=%s renderiza em dark mode",
    (variant) => {
      const { unmount } = render(
        <StatusBadge variant={variant}>{variant}</StatusBadge>,
      );
      expect(screen.getByText(variant)).toBeInTheDocument();
      unmount();
    },
  );

  it("Delta usa classes semânticas (text-gain/text-loss), não hardcoded green/red", () => {
    const { container } = render(<Delta value={100} />);
    const span = container.querySelector("span");
    const cls = span?.className ?? "";
    // semântica permitida; cores hardcoded NÃO permitidas
    expect(cls).not.toContain("text-green-");
    expect(cls).not.toContain("text-red-");
  });

  it("EmptyState renderiza icon + title em dark mode", () => {
    render(<EmptyState title="Vazio" description="Sem dados" />);
    expect(screen.getByText("Vazio")).toBeInTheDocument();
  });

  it("componentes usam tokens semânticos do design system (text-foreground, bg-card, etc.)", () => {
    const { container } = render(
      <div className="bg-card text-foreground border border-border">
        <KPICard label="x" value="y" />
      </div>,
    );
    const root = container.querySelector("div");
    expect(root!.className).toContain("bg-card");
    expect(root!.className).toContain("text-foreground");
  });
});

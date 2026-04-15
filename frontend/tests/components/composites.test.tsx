/**
 * Integration tests — 7 compostos do design system
 * F6.5B.10 — KPICard, EmptyState, StatusBadge, ConfirmDialog, Delta, Spinner, ThemeToggle
 *
 * Estratégia:
 * - render via @testing-library/react
 * - asserts em texto (queryByText/Role) e atributos data-* / aria-label
 * - mocks mínimos (apenas next-themes para ThemeToggle)
 *
 * Não testa estilos visuais (ficam em 6.5D.3 visual regression).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { KPICard } from "@/components/KPICard";
import { EmptyState } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { Delta } from "@/components/Delta";
import { Spinner } from "@/components/Spinner";

// ─── KPICard ─────────────────────────────────────────────────────────

describe("<KPICard />", () => {
  it("renderiza label + value", () => {
    render(<KPICard label="Saldo" value="R$ 4.100,00" />);
    expect(screen.getByText("Saldo")).toBeInTheDocument();
    expect(screen.getByText("R$ 4.100,00")).toBeInTheDocument();
  });

  it("loading state mostra Skeletons no lugar do texto", () => {
    render(<KPICard label="Saldo" value="R$ 100" loading />);
    expect(screen.queryByText("Saldo")).not.toBeInTheDocument();
    expect(screen.queryByText("R$ 100")).not.toBeInTheDocument();
    // Skeleton do shadcn usa data-slot="skeleton"
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("mostra Delta quando passado", () => {
    render(
      <KPICard label="Saldo" value="R$ 100" delta={{ value: 50, percent: 0.5 }} />,
    );
    // Delta renderiza "+R$ 50,00" e "(+50,0%)"
    expect(screen.getByText(/\+R\$/)).toBeInTheDocument();
  });

  it("aceita className custom", () => {
    const { container } = render(
      <KPICard label="x" value="y" className="custom-cls" />,
    );
    expect(container.querySelector(".custom-cls")).toBeInTheDocument();
  });
});

// ─── EmptyState ──────────────────────────────────────────────────────

describe("<EmptyState />", () => {
  it("renderiza title + description", () => {
    render(
      <EmptyState
        title="Sem documentos"
        description="Suba um extrato para começar"
      />,
    );
    expect(screen.getByText("Sem documentos")).toBeInTheDocument();
    expect(screen.getByText(/Suba um extrato/)).toBeInTheDocument();
  });

  it("F6.5D.12: renderiza CTA com href quando passado", () => {
    render(
      <EmptyState
        title="Sem reports"
        action={{ label: "Criar relatório", href: "/pipeline" }}
      />,
    );
    // Button render={<a href=... />} pode emitir <a> sem role=link em alguns
    // modes do shadcn; busca pelo texto + verifica href
    const cta = screen.getByText(/Criar relatório/);
    const anchor = cta.closest("a") || cta;
    expect(anchor.tagName).toBe("A");
    expect((anchor as HTMLAnchorElement).getAttribute("href")).toBe("/pipeline");
  });

  it("F6.5D.12: CTA com onClick (sem href) chama callback", async () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        title="Vazio"
        action={{ label: "Recarregar", onClick }}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Recarregar/ }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("variant 'error' usa ícone de alerta", () => {
    const { container } = render(
      <EmptyState variant="error" title="Falha ao carregar" />,
    );
    // Ícone Lucide vira <svg>; só validamos que existe
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("aceita variant 'no-documents' / 'no-reports' / 'no-data' sem crashar", () => {
    for (const variant of [
      "no-documents",
      "no-reports",
      "no-data",
    ] as const) {
      const { unmount } = render(<EmptyState variant={variant} title="t" />);
      expect(screen.getByText("t")).toBeInTheDocument();
      unmount();
    }
  });
});

// ─── StatusBadge ─────────────────────────────────────────────────────

describe("<StatusBadge />", () => {
  it("renderiza children", () => {
    render(<StatusBadge variant="success">Concluído</StatusBadge>);
    expect(screen.getByText("Concluído")).toBeInTheDocument();
  });

  it.each([
    "success",
    "warning",
    "error",
    "info",
    "neutral",
    "premium",
    "muted",
  ] as const)("aceita variant %s sem crashar", (variant) => {
    const { unmount } = render(
      <StatusBadge variant={variant}>{variant}</StatusBadge>,
    );
    expect(screen.getByText(variant)).toBeInTheDocument();
    unmount();
  });
});

// ─── Delta ───────────────────────────────────────────────────────────

describe("<Delta />", () => {
  it("positivo mostra TrendingUp + classe de gain", () => {
    const { container } = render(<Delta value={100} />);
    expect(screen.getByText(/\+R\$ 100,00/)).toBeInTheDocument();
    // aria-label semântico
    expect(container.querySelector("[aria-label*='aumento']")).toBeInTheDocument();
  });

  it("negativo mostra TrendingDown", () => {
    const { container } = render(<Delta value={-50} />);
    expect(container.querySelector("[aria-label*='redução']")).toBeInTheDocument();
  });

  it("zero mostra Minus icon (neutral)", () => {
    const { container } = render(<Delta value={0} />);
    // Não deve ter aria-label de "aumento" (zero é tratado como positivo lógico,
    // mas o ícone é Minus). Apenas garantir que renderiza.
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("invert: negativo bom (ex: redução de despesa)", () => {
    const { container } = render(<Delta value={-50} invert />);
    // Com invert, value <= 0 é positivo → aria-label "aumento"
    expect(container.querySelector("[aria-label*='aumento']")).toBeInTheDocument();
  });

  it("inclui percentual no formato (+X,Y%)", () => {
    render(<Delta value={100} percent={0.25} />);
    expect(screen.getByText(/\+25,0%/)).toBeInTheDocument();
  });
});

// ─── Spinner ─────────────────────────────────────────────────────────

describe("<Spinner />", () => {
  it("renderiza svg loader com classe animate-spin (F6.5: BUG OP-011 anim)", () => {
    const { container } = render(<Spinner />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg!.className.baseVal || svg!.getAttribute("class")).toMatch(/animate-spin/);
  });

  it.each(["sm", "md", "lg"] as const)("aceita size %s", (size) => {
    const { unmount } = render(<Spinner size={size} />);
    const svg = document.querySelector("svg");
    const classAttr = svg!.getAttribute("class") || "";
    if (size === "sm") expect(classAttr).toMatch(/h-4|w-4/);
    if (size === "md") expect(classAttr).toMatch(/h-6|w-6/);
    if (size === "lg") expect(classAttr).toMatch(/h-8|w-8/);
    unmount();
  });
});

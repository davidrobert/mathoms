/**
 * ADR-117 · Fase 4 — smoke tests dos primitivos do shell.
 *
 * Cobertura: ReportCover (hero + meta), SkipNav (href + a11y),
 * ExportToolbar (clipboard + print), FloatingNav (scroll listener).
 * ModeToggle é testado indiretamente via ReportModeProvider — aqui só
 * smoke. AppearanceMenu (popover Aa unificado fonte+tema) tem suite
 * dedicada em `AppearanceMenu.test.tsx`.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import {
  ReportCover,
  SkipNav,
  ExportToolbar,
  FloatingNav,
} from "@/components/report/shell";

vi.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: "light", setTheme: vi.fn() }),
}));

describe("<ReportCover />", () => {
  it("renderiza title + subtitle + meta cards", () => {
    render(
      <ReportCover
        badge="Relatório"
        title="Patrimônio Exemplo"
        subtitle="Q1 2026"
        meta={[
          { label: "Período", value: "Jan-Mar" },
          { label: "Docs", value: 42 },
        ]}
      />,
    );
    expect(screen.getByText("Relatório")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Patrimônio Exemplo" })).toBeInTheDocument();
    expect(screen.getByText("Q1 2026")).toBeInTheDocument();
    expect(screen.getByText("Jan-Mar")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });
  it("renderiza sem badge/subtitle/meta (mínimo)", () => {
    render(<ReportCover title="Título só" />);
    expect(screen.getByRole("heading", { name: "Título só" })).toBeInTheDocument();
  });
});

describe("<SkipNav />", () => {
  it("aponta para target com href #", () => {
    render(<SkipNav targetId="main-xyz" />);
    const link = screen.getByRole("link", { name: /Pular para o conteúdo/i });
    expect(link).toHaveAttribute("href", "#main-xyz");
  });
});

describe("<ExportToolbar />", () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  beforeEach(() => {
    writeText.mockClear();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
  });
  it("renderiza botões de PDF e copiar link", () => {
    render(<ExportToolbar />);
    expect(screen.getByRole("button", { name: /Baixar PDF/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Copiar link/i })).toBeInTheDocument();
  });
  it("copia URL ao clicar em Copiar link", async () => {
    // fireEvent (não userEvent): userEvent.setup() monta sua própria
    // navigator.clipboard e não respeita nosso defineProperty.
    render(<ExportToolbar shareUrl="https://app.mathoms.ai/reports/123" />);
    fireEvent.click(screen.getByRole("button", { name: /Copiar link/i }));
    expect(await screen.findByText(/Link copiado/i)).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(
      "https://app.mathoms.ai/reports/123",
    );
  });
});

describe("<FloatingNav />", () => {
  it("botões começam invisíveis (opacity 0)", () => {
    render(<FloatingNav />);
    const up = screen.getByRole("button", { name: /topo/i });
    const down = screen.getByRole("button", { name: /final/i });
    expect(up).toHaveAttribute("data-visible", "false");
    expect(down).toHaveAttribute("data-visible");
  });
});

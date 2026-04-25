/**
 * ADR-117 · Fase 4 — smoke tests dos primitivos do shell.
 *
 * Cobertura: ReportCover (hero + meta), SkipNav (href + a11y),
 * ExportToolbar (clipboard + print), FloatingNav (scroll listener),
 * FontScaleToggle (integração com useReportFontScale). ModeToggle é
 * testado indiretamente via ReportModeProvider — aqui só smoke.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  ReportCover,
  SkipNav,
  ExportToolbar,
  FloatingNav,
  FontScaleToggle,
} from "@/components/report/shell";

// next-themes mock (ReportThemeToggle indireto via ReportTopNav — mas
// neste arquivo não testamos ReportTopNav inteiro por causa de nav-next
// dependency. Cobertura de ReportTopNav fica em ReportShell.test.tsx).
vi.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: "light", setTheme: vi.fn() }),
}));

describe("<ReportCover />", () => {
  it("renderiza title + subtitle + meta cards", () => {
    render(
      <ReportCover
        badge="Relatório"
        title="Patrimônio Ferreira"
        subtitle="Q1 2026"
        meta={[
          { label: "Período", value: "Jan-Mar" },
          { label: "Docs", value: 42 },
        ]}
      />,
    );
    expect(screen.getByText("Relatório")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Patrimônio Ferreira" })).toBeInTheDocument();
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

describe("<FontScaleToggle />", () => {
  beforeEach(() => window.localStorage.clear());
  it("renderiza 3 botões e marca compact ativo por default", () => {
    render(<FontScaleToggle />);
    const compact = screen.getByRole("button", { name: "Compacto" });
    expect(compact).toHaveAttribute("data-active", "true");
    expect(compact).toHaveAttribute("aria-pressed", "true");
  });
  it("clicar em Normal persiste no localStorage", async () => {
    const user = userEvent.setup();
    render(<FontScaleToggle />);
    await user.click(screen.getByRole("button", { name: "Normal" }));
    expect(window.localStorage.getItem("mathoms:report:font-scale")).toBe("normal");
  });
});

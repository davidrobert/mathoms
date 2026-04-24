/**
 * F9 · Smoke tests do ReportShell nativo.
 */
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ReportModeProvider } from "@/components/report/ReportModeProvider";
import { ReportShell } from "@/components/report/ReportShell";
import type { UseReportDataState } from "@/hooks/useReportData";
import type { ReportAnalysisData } from "@/lib/api";

vi.mock("@/lib/WorkspaceProvider", () => ({
  WorkspaceProvider: ({ children }: { children: ReactNode }) => (
    <>{children}</>
  ),
  useWorkspace: () => ({
    workspace: {
      id: "ws-test",
      name: "Workspace",
      family_surname: "Teste",
      role: "owner" as const,
      joined_at: "2026-01-01T00:00:00.000Z",
    },
    workspaces: [],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

// F3.2: ReportModeProvider uses next/navigation hooks — mock them in test env
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/reports/test-id",
}));

function wrap(ui: React.ReactNode) {
  return (
    <TooltipProvider>
      <ReportModeProvider initialMode="estrategico">{ui}</ReportModeProvider>
    </TooltipProvider>
  );
}

const SAMPLE_DATA: ReportAnalysisData = {
  periodo_dados: "202601-202604",
  patrimonio: { bruto: 1_000_000 },
  score: { valor: 82, max: 100, classificacao: "Muito Bom" },
};

describe("ReportShell", () => {
  it("renderiza header, TOC e áreas principais em sucesso", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test" reportTitle="Relatório Família Teste"
          dataState={state}
          reportPeriod="2026-Q1"
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );

    // Título aparece no header + no hero do article
    expect(screen.getAllByText("Relatório Família Teste").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/202601-202604/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("note", { name: /Origem dos dados do relatório/i })).toBeInTheDocument();
    expect(screen.getByText(/Período:/)).toBeInTheDocument();
  });

  it("mostra link da execução do pipeline quando pipelineRunId está definido (F11.4a)", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    const runId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test" reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
          pipelineRunId={runId}
        />,
      ),
    );
    const link = screen.getByRole("link", { name: "aaaaaaaa…" });
    expect(link).toHaveAttribute("href", `/pipeline?run=${encodeURIComponent(runId)}`);
  });

  it("mostra seletor de modo (estratégico/tático/EUA)", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test" reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    expect(
      screen.getByRole("tab", { name: "Estratégico", selected: true }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Tático" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "EUA" })).toBeInTheDocument();
  });

  it("renderiza seções migradas sem stubs no modo estratégico", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test" reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    // S1 "Patrimônio" deve aparecer como seção real (não stub)
    const matches = screen.getAllByText(/Patrimônio/i);
    expect(matches.length).toBeGreaterThan(0);
    // S1-S10 todas migradas: nenhum stub no modo estratégico
    expect(screen.queryAllByText(/Conteúdo em migração/).length).toBe(0);
  });

  it("mostra mensagem de erro quando o fetch falha", () => {
    const state: UseReportDataState = {
      status: "error",
      error: new Error("boom"),
    };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test" reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    expect(
      screen.getByText(/Não foi possível carregar os dados/),
    ).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("mostra spinner em loading", () => {
    const state: UseReportDataState = { status: "loading" };
    const { container } = render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test" reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    expect(container.querySelector(".animate-spin")).toBeTruthy();
  });
});

describe("MonetaryValue", () => {
  it("formata BRL com font-mono e tabular-nums", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={1234567.89} />);
    const span = container.querySelector("span");
    expect(span).not.toBeNull();
    expect(span!.className).toMatch(/font-mono/);
    expect(span!.className).toMatch(/tabular-nums/);
    // pt-BR: ponto milhar + vírgula decimal
    expect(span!.textContent).toMatch(/1\.234\.567,89/);
  });

  it("renderiza — para null", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={null} />);
    expect(container.textContent).toBe("—");
  });

  it("colore e prefixa sinal com signed", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={500} signed />);
    const span = container.querySelector("span");
    expect(span!.className).toMatch(/text-gain/);
    expect(span!.textContent?.startsWith("+")).toBe(true);
  });

  it("compact renderiza notação abreviada", async () => {
    const { MonetaryValue } = await import("@/components/report/MonetaryValue");
    const { container } = render(<MonetaryValue value={1_500_000} compact />);
    // "R$ 1,5 mi" (pt-BR) ou variação do ICU
    expect(container.textContent).toMatch(/1,5\s?mi/);
  });
});

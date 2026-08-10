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
  WorkspaceProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
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
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Relatório Família Teste"
          dataState={state}
          reportPeriod="2026-Q1"
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );

    // Título aparece no header + no hero do article
    expect(
      screen.getAllByText("Relatório Família Teste").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/202601-202604/).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(
      screen.getByRole("note", { name: /Origem dos dados do relatório/i }),
    ).toBeInTheDocument();
  });

  it("mostra link da execução do pipeline quando pipelineRunId está definido (F11.4a)", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    const runId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
          pipelineRunId={runId}
        />,
      ),
    );
    const link = screen.getByRole("link", { name: "aaaaaaaa…" });
    expect(link).toHaveAttribute(
      "href",
      `/pipeline?run=${encodeURIComponent(runId)}`,
    );
  });

  it("oculta seletor de modo quando há apenas um modo visível", () => {
    // ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA removido.
    // Modo Estratégico é único — `ReportActions` auto-oculta o tablist
    // (VISIBLE_MODES.length === 1). Reativar exige adicionar entry em VISIBLE_MODES.
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    expect(
      screen.queryByRole("tablist", { name: "Modo de visualização" }),
    ).toBeNull();
    expect(screen.queryByRole("tab", { name: "Estratégico" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Tático" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "EUA" })).toBeNull();
  });

  it("renderiza seções migradas sem stubs no modo estratégico", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
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
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
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

  it("usa periodo_dados do snapshot no card 'Período de referência' quando reportPeriod é null", () => {
    const data: ReportAnalysisData = {
      ...SAMPLE_DATA,
      periodo_dados: "2023-01 a 2026-04",
    };
    const state: UseReportDataState = { status: "success", data };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    const label = screen.getByText("Período de referência");
    const valueEl = label.nextElementSibling;
    expect(valueEl?.textContent).toBe("jan 2023 — abr 2026");
  });

  it("formato 'Gerado em' no cover: dia mês abreviado ano, hh'h'mm (v2.F.3b)", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    const label = screen.getByText("Gerado em");
    const valueEl = label.nextElementSibling;
    // "DD mmm YYYY, HHhMM" — não asseramos timezone (depende do runner)
    expect(valueEl?.textContent).toMatch(
      /^\d{2}\s(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s2026,\s\d{2}h\d{2}$/,
    );
  });

  it("badge dinâmico: 'Relatório · Família X' quando familySurname presente", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
          familySurname="Andrade Silva"
        />,
      ),
    );
    expect(
      screen.getByText("Relatório · Família Andrade Silva"),
    ).toBeInTheDocument();
    expect(screen.getByText("Família")).toBeInTheDocument();
    expect(screen.getByText("Andrade Silva")).toBeInTheDocument();
  });

  it("degradação graciosa sem familySurname: badge fallback + sem card 'Família'", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    expect(screen.getByText("Relatório Patrimonial")).toBeInTheDocument();
    // o card "Família" não deve existir
    expect(screen.queryByText("Família")).not.toBeInTheDocument();
  });

  it("título e subtítulo estáticos no cover (v2.F.3b)", () => {
    const state: UseReportDataState = { status: "success", data: SAMPLE_DATA };
    render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel da família"
          dataState={state}
          reportPeriod={null}
          reportCreatedAt="2026-04-17T12:00:00.000Z"
        />,
      ),
    );
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Planejamento Financeiro",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Pessoal e Patrimonial")).toBeInTheDocument();
  });

  it("mostra spinner em loading", () => {
    const state: UseReportDataState = { status: "loading" };
    const { container } = render(
      wrap(
        <ReportShell
          reportId="r1"
          workspaceId="ws-test"
          runOutcome="complete"
          reportTitle="Rel"
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
    // "R$ 1,5 mi" / "R$ 1,50 mi" (pt-BR) ou variação do ICU
    expect(container.textContent).toMatch(/1,50?\s?mi/);
  });
});

// A40.l7 §Insumos 2 — o heading era digitado em cada seção enquanto o índice
// lia o YAML, e 6 divergiam. Estes testes travam a derivação: sem eles, mudar
// o título do YAML muda o índice e deixa o heading para trás, em silêncio (a
// suíte inteira passou verde na primeira medição desta lane).
describe("sectionHeading — heading e índice saem da mesma fonte", () => {
  it("seção comum usa o título do YAML sem prefixo", async () => {
    const { sectionHeading, buildTitleMap } = await import(
      "@/components/report/utils/sectionTitles"
    );
    const { LAYOUT } = await import("@/generated/report-layout");

    for (const s of LAYOUT.estrategico.sections) {
      expect(sectionHeading(s.id)).toBe(buildTitleMap()[s.id]);
      expect(sectionHeading(s.id)).toBe(s.title);
    }
  });

  it("apêndice compõe 'Apêndice X — ' e preserva o título nu por trás", async () => {
    const { sectionHeading, buildTitleMap } = await import(
      "@/components/report/utils/sectionTitles"
    );
    const { LAYOUT } = await import("@/generated/report-layout");

    const apendices = LAYOUT.estrategico.appendices ?? [];
    expect(apendices.length).toBeGreaterThan(0);
    for (const a of apendices) {
      expect(sectionHeading(a.id)).toMatch(/^Apêndice [A-Z] — /);
      expect(sectionHeading(a.id).endsWith(a.title)).toBe(true);
      // O prefixo é composto no render; no mapa que alimenta nav/ToC o título
      // segue nu — com ele no mapa, `shortLabel` cortaria em " — " e o TopNav
      // mostraria só "Apêndice B" ao lado do badge que já diz "B".
      expect(buildTitleMap()[a.id]).toBe(a.title);
    }
  });

  it("V0 é renderizada pelo shell e mesmo assim resolve título", async () => {
    const { sectionHeading } = await import("@/components/report/utils/sectionTitles");
    expect(sectionHeading("V0")).toBe("O que mudou");
  });
});

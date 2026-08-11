/**
 * Superfícies de sugestão no relatório (PLAN-suggestion-lifecycle F5).
 *
 * O relatório é snapshot; o inbox é live. Estes testes guardam as duas
 * fronteiras: o fechamento "Próximos passos" nunca lista o inbox (só
 * contagens + 1 CTA), e o callout inline só mostra sugestões nascidas
 * do relatório em exibição quando `reportId` é fornecido.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  SuggestionCalloutInline,
  SuggestionCalloutSummary,
} from "@/components/report/sections/SuggestionCallout";
import type { Suggestion } from "@/lib/api";

const useSuggestionsMock = vi.fn();

vi.mock("@/hooks/useSuggestions", () => ({
  useSuggestions: (...args: unknown[]) => useSuggestionsMock(...args),
}));

function makeSuggestion(overrides: Partial<Suggestion> = {}): Suggestion {
  return {
    id: "sug-1",
    workspace_id: "ws-1",
    report_id: "rep-1",
    section_id: "S2",
    kind: "reserva_insuficiente",
    category: "protecao",
    origin: "deterministic",
    severity: "warning",
    title: "Reserva de emergência abaixo do alvo",
    rationale: "Cobertura menor que o alvo definido no plano.",
    amount_brl: null,
    dedup_key: "a".repeat(64),
    status: "Pendente",
    accepted_decision_id: null,
    accepted_decision_code: null,
    dismissed_reason: null,
    accepted_at: null,
    dismissed_at: null,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}

function mockPendentes(suggestions: Suggestion[], loading = false) {
  useSuggestionsMock.mockReturnValue({
    suggestions,
    loading,
    error: "",
    reload: vi.fn(),
    accept: vi.fn(),
    modify: vi.fn(),
    dismiss: vi.fn(),
    regenerate: vi.fn(),
  });
}

describe("SuggestionCalloutSummary", () => {
  it("mostra só contagens + CTA único, sem listar sugestões", () => {
    mockPendentes([
      makeSuggestion({
        id: "s1",
        severity: "danger",
        title: "Título danger A",
      }),
      makeSuggestion({
        id: "s2",
        severity: "danger",
        title: "Título danger B",
      }),
      makeSuggestion({
        id: "s3",
        severity: "warning",
        title: "Título warning",
      }),
      makeSuggestion({ id: "s4", severity: "info", title: "Título info A" }),
      makeSuggestion({ id: "s5", severity: "info", title: "Título info B" }),
    ]);
    const { container } = render(
      <SuggestionCalloutSummary workspaceId="ws-1" />,
    );

    expect(
      screen.getByRole("heading", { name: "Próximos passos" }),
    ).toBeInTheDocument();
    expect(container.textContent).toContain(
      "3 ações aguardam sua decisão — e 2 sugestões informativas.",
    );

    // Fechamento sem lista: nenhum <ul>/<li> e nenhum título de sugestão.
    expect(container.querySelector("ul, ol, li")).toBeNull();
    expect(screen.queryByText("Título danger A")).not.toBeInTheDocument();
    expect(screen.queryByText("Título warning")).not.toBeInTheDocument();

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveTextContent("Revisar em /acao");
    expect(links[0]).toHaveAttribute("href", "/acao?tab=inbox");
  });

  it("adapta singular e omite o apêndice informativo quando não há info", () => {
    mockPendentes([makeSuggestion({ severity: "danger" })]);
    const { container } = render(
      <SuggestionCalloutSummary workspaceId="ws-1" />,
    );
    expect(container.textContent).toContain("1 ação aguarda sua decisão.");
    expect(container.textContent).not.toContain("informativa");
  });

  it("retorna null sem sugestões pendentes", () => {
    mockPendentes([]);
    const { container } = render(
      <SuggestionCalloutSummary workspaceId="ws-1" />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("preserva a âncora e a associação heading↔section", () => {
    mockPendentes([makeSuggestion()]);
    const { container } = render(
      <SuggestionCalloutSummary workspaceId="ws-1" />,
    );
    const section = container.querySelector("section#proximos-passos");
    expect(section).not.toBeNull();
    expect(section).toHaveAttribute("aria-labelledby", "proximos-passos-title");
  });
});

describe("SuggestionCalloutInline", () => {
  const doSuggestions = [
    makeSuggestion({
      id: "s1",
      report_id: "rep-1",
      title: "Do relatório atual",
    }),
    makeSuggestion({
      id: "s2",
      report_id: "rep-2",
      title: "De outro relatório",
    }),
    makeSuggestion({ id: "s3", report_id: null, title: "Sem report_id" }),
  ];

  it("com reportId, só sugestões do relatório-fonte aparecem (null não passa)", () => {
    mockPendentes(doSuggestions);
    render(
      <SuggestionCalloutInline
        sectionId="S2"
        workspaceId="ws-1"
        reportId="rep-1"
      />,
    );
    expect(screen.getByText("Do relatório atual")).toBeInTheDocument();
    expect(screen.queryByText("De outro relatório")).not.toBeInTheDocument();
    expect(screen.queryByText("Sem report_id")).not.toBeInTheDocument();
    expect(screen.getAllByRole("note")).toHaveLength(1);
  });

  it("sem reportId, mantém o comportamento legado (todas da seção)", () => {
    mockPendentes(doSuggestions);
    render(<SuggestionCalloutInline sectionId="S2" workspaceId="ws-1" />);
    expect(screen.getAllByRole("note")).toHaveLength(3);
  });

  it("filtro por seção continua valendo sob reportId", () => {
    mockPendentes([
      makeSuggestion({ id: "s1", report_id: "rep-1", section_id: "S7" }),
    ]);
    const { container } = render(
      <SuggestionCalloutInline
        sectionId="S2"
        workspaceId="ws-1"
        reportId="rep-1"
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

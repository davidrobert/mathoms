/**
 * ADR-117/122 · Fase 10 — testes dos Apêndices A–E.
 *
 * Cobre fallback summary, renderização de dados quando presentes e empty
 * state quando ausentes.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ApendiceASection } from "@/components/report/sections/ApendiceASection";
import {
  ApendiceBSection,
  ApendiceCSection,
  ApendiceDSection,
  ApendiceESection,
} from "@/components/report/sections/ApendicesSections";
import type { ReportAnalysisData } from "@/lib/api";

function emptyData(): ReportAnalysisData {
  return {} as ReportAnalysisData;
}

describe("ApendiceASection", () => {
  it("renderiza glossário e categorias sem data", () => {
    render(<ApendiceASection />);
    expect(screen.getByText(/Apêndice A/)).toBeInTheDocument();
    expect(screen.getByText(/Glossário de Termos Financeiros/)).toBeInTheDocument();
    expect(screen.getByText(/Categorias Patrimoniais/)).toBeInTheDocument();
  });

  it("renderiza fallback summary quando data presente sem narrativa", () => {
    render(<ApendiceASection data={emptyData()} />);
    expect(
      screen.getByText(/Glossário de termos financeiros e categorias/),
    ).toBeInTheDocument();
  });
});

describe("ApendiceBSection", () => {
  it("renderiza fallback + metodologias com data vazia", () => {
    render(<ApendiceBSection data={emptyData()} />);
    expect(screen.getByText(/Apêndice B/)).toBeInTheDocument();
    expect(screen.getByText(/Metas vigentes neste ciclo/)).toBeInTheDocument();
    expect(
      screen.getByText(/Nenhuma meta vigente neste ciclo/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Bruno Perini/)).toBeInTheDocument();
    expect(screen.getByText(/Gustavo Cerbasi/)).toBeInTheDocument();
  });

  it("lista metas vigentes humanizadas a partir do snapshot", () => {
    const data = {
      goals: {
        premissas_snapshot: {
          schema: 1,
          captured_at: "2026-05-06T13:17:05.995102+00:00",
          goals_json_sha256:
            "1cd0f0c15dd5097769280f6357c9928a98a1ac8b83add4847a689232445c1b38",
          active_goals: [
            {
              type: "APORTE_MENSAL",
              id: "501e998a-5515-46f2-b35d-f5a6c8759059",
              effective_from: "2026-04-27",
            },
            {
              type: "DOLARIZACAO",
              id: "faaf754c-4718-43bd-90fd-d183edcf213c",
              effective_from: "2026-04-27",
            },
            {
              type: "INDEPENDENCIA_FINANCEIRA",
              id: "8e574a00-f246-4138-a7bf-75445b3f1332",
              effective_from: "2026-04-26",
            },
          ],
        },
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceBSection data={data} />);
    expect(screen.getByText("Aporte mensal")).toBeInTheDocument();
    expect(screen.getByText("Dolarização da carteira")).toBeInTheDocument();
    expect(screen.getByText("Independência Financeira")).toBeInTheDocument();
    expect(screen.getAllByText(/Vigente desde 27\/04\/2026/)).toHaveLength(2);
    expect(screen.getByText(/Vigente desde 26\/04\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/Snapshot capturado em/)).toBeInTheDocument();
    expect(screen.queryByText(/1cd0f0c15dd5097769280f6357c9928a/)).toBeNull();
    expect(screen.queryByText(/goals_json_sha256/)).toBeNull();
  });

  it("mostra empty state quando snapshot existe mas active_goals vazio", () => {
    const data = {
      goals: {
        premissas_snapshot: {
          schema: 1,
          captured_at: "2026-05-06T13:17:05.995102+00:00",
          goals_json_sha256: null,
          active_goals: [],
        },
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceBSection data={data} />);
    expect(
      screen.getByText(/Nenhuma meta vigente neste ciclo/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Snapshot capturado em/)).toBeInTheDocument();
  });
});

describe("ApendiceCSection", () => {
  it("mostra empty state quando sem cenários", () => {
    render(<ApendiceCSection data={emptyData()} />);
    expect(
      screen.getByText(/Sem cenários alternativos registrados/),
    ).toBeInTheDocument();
  });

  it("renderiza tabela de cenários quando cenarios_conjuge presente (ADR-166)", () => {
    const data = {
      cenarios_conjuge: {
        labels: ["Base", "Stress"],
        aportes: [5000, 3000],
        prazos_if: [12.3, 18.7],
        anos_if: [2038, 2044],
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceCSection data={data} />);
    expect(screen.getByText("Base")).toBeInTheDocument();
    expect(screen.getByText("Stress")).toBeInTheDocument();
    expect(screen.getByText("12.3")).toBeInTheDocument();
  });
});

describe("ApendiceDSection", () => {
  it("lista metodologias e indica lineage ausente", () => {
    render(<ApendiceDSection data={emptyData()} />);
    expect(screen.getByText(/Apêndice D/)).toBeInTheDocument();
    expect(screen.getByText(/Bruno Perini/)).toBeInTheDocument();
    expect(
      screen.getByText(/Sem informação de lineage disponível/),
    ).toBeInTheDocument();
  });

  it("mostra pipeline_run_id e contagem de documentos quando lineage existe", () => {
    const data = {
      _report_lineage: {
        pipeline_run_id: "run-abc-123",
        source_document_count: 7,
        source_document_ids: [],
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceDSection data={data} />);
    expect(screen.getByText("run-abc-123")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });
});

describe("ApendiceESection", () => {
  it("primeiro relatório (changelog ausente) mostra copy de primeiro ciclo", () => {
    render(<ApendiceESection data={emptyData()} />);
    expect(
      screen.getByText(/Primeiro relatório do workspace/),
    ).toBeInTheDocument();
  });

  it("changelog null (sem ciclo anterior) usa copy de primeiro relatório", () => {
    const data = { changelog: null } as unknown as ReportAnalysisData;
    render(<ApendiceESection data={data} />);
    expect(
      screen.getByText(/Primeiro relatório do workspace/),
    ).toBeInTheDocument();
  });

  it("changelog vazio (nada acima do threshold) usa copy de sem mudança material", () => {
    const data = { changelog: [] } as unknown as ReportAnalysisData;
    render(<ApendiceESection data={data} />);
    expect(
      screen.getByText(/Nenhuma mudança material desde o último relatório/),
    ).toBeInTheDocument();
  });

  it("renderiza SnapshotChangelogList consolidado quando data.changelog tem entries (v2.8 · ADR-148)", () => {
    const data = {
      changelog: [
        {
          section_id: "S1",
          summary: "Patrimônio Líquido avançou 20,0% no mês",
          delta_signal: "up",
          delta_pct: 20,
        },
        {
          section_id: "T5",
          summary: "Despesas Totais subiu 8,5% no mês",
          delta_signal: "up",
          delta_pct: 8.5,
        },
      ],
    } as unknown as ReportAnalysisData;
    render(<ApendiceESection data={data} />);
    expect(
      screen.getByText("Patrimônio Líquido avançou 20,0% no mês"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Despesas Totais subiu 8,5% no mês"),
    ).toBeInTheDocument();
  });
});

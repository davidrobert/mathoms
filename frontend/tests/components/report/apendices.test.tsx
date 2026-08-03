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
  it("renderiza glossário e categorias com data vazia", () => {
    render(<ApendiceASection data={emptyData()} />);
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
  it("renderiza fallback + pilares metodológicos com data vazia", () => {
    render(<ApendiceBSection data={emptyData()} />);
    expect(screen.getByText(/Apêndice B/)).toBeInTheDocument();
    expect(screen.getByText(/Metas vigentes neste ciclo/)).toBeInTheDocument();
    expect(
      screen.getByText(/Nenhuma meta vigente neste ciclo/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Patrimônio gerador de renda/)).toBeInTheDocument();
    expect(screen.getByText(/Equilíbrio entre presente e futuro/)).toBeInTheDocument();
    expect(screen.getByText(/Alocação contracíclica/)).toBeInTheDocument();
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

  it("filtra tipos não-canônicos do snapshot (ADR-180 — sem PLANNING_CONTEXT)", () => {
    const data = {
      goals: {
        premissas_snapshot: {
          schema: 1,
          captured_at: "2026-05-06T13:17:05.995102+00:00",
          goals_json_sha256: null,
          active_goals: [
            {
              type: "INDEPENDENCIA_FINANCEIRA",
              id: "goal-canonical",
              effective_from: "2026-04-26",
            },
            {
              type: "PLANNING_CONTEXT",
              id: "goal-legacy",
              effective_from: "2025-11-01",
            },
          ],
        },
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceBSection data={data} />);
    expect(screen.getByText("Independência Financeira")).toBeInTheDocument();
    expect(screen.queryByText(/PLANNING_CONTEXT/)).toBeNull();
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

describe("ApendiceCSection (ADR-167 · A8.4 PR3)", () => {
  it("retorna null (hide-when-empty) quando sem cenários e sem milhas", () => {
    const { container } = render(<ApendiceCSection data={emptyData()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza visualização comparativa base vs estresse quando cenarios_conjuge presente", () => {
    const data = {
      cenarios_conjuge: {
        labels: ["Sem renda do cônjuge"],
        aportes: [18500],
        prazos_if: [19.5],
        anos_if: [2046],
        premissas: { aporte_base: 12000 },
      },
      goals: { prazo_anos_realista: 14.2, ano_if: 2040 },
    } as unknown as ReportAnalysisData;
    render(<ApendiceCSection data={data} />);
    expect(screen.getByText(/Apêndice C — Cenários de Estresse/)).toBeInTheDocument();
    expect(
      screen.getByText(/Premissa testada: Sem renda do cônjuge/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Cenário base/)).toBeInTheDocument();
    expect(screen.getByText(/Cenário de estresse/)).toBeInTheDocument();
    expect(screen.getByText(/Leitura:/)).toBeInTheDocument();
  });

  it("A37.l10 PD-09 — coluna base exibe prazo/ano do payload real (prazo_anos_realista/ano_if)", () => {
    const data = {
      cenarios_conjuge: {
        labels: ["Sem renda do cônjuge"],
        aportes: [12000],
        prazos_if: [19.5],
        anos_if: [2046],
        premissas: { aporte_base: 20000 },
      },
      goals: { prazo_anos_realista: 14.2, ano_if: 2040 },
    } as unknown as ReportAnalysisData;
    render(<ApendiceCSection data={data} />);
    expect(screen.getByText("14a 2m")).toBeInTheDocument();
    expect(screen.getByText("2040")).toBeInTheDocument();
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).not.toMatch(/Leitura:\s*\./);
  });

  it("A37.l10 PD-09 — sentinela 999 no goals degrada coluna base para '—'", () => {
    const data = {
      cenarios_conjuge: {
        labels: ["Sem renda do cônjuge"],
        aportes: [12000],
        prazos_if: [19.5],
        anos_if: [2046],
        premissas: { aporte_base: 20000 },
      },
      goals: { prazo_anos_realista: 999, ano_if: 3025 },
    } as unknown as ReportAnalysisData;
    render(<ApendiceCSection data={data} />);
    expect(screen.queryByText("999a")).toBeNull();
    expect(screen.queryByText("3025")).toBeNull();
  });

  it("prazo ausente (null) no goals degrada coluna base para '—'", () => {
    // Forma atual da não-convergência; o caso 999 acima cobre artefatos E5
    // persistidos antes da troca da sentinela por ausência explícita.
    const data = {
      cenarios_conjuge: {
        labels: ["Sem renda do cônjuge"],
        aportes: [12000],
        prazos_if: [19.5],
        anos_if: [2046],
        premissas: { aporte_base: 20000 },
      },
      goals: { prazo_anos_realista: null, ano_if: null },
    } as unknown as ReportAnalysisData;
    render(<ApendiceCSection data={data} />);
    expect(screen.queryByText("999a")).toBeNull();
    expect(screen.queryByText("3025")).toBeNull();
    expect(screen.queryByText("nulla")).toBeNull();
  });

  it("renderiza copy não-alarmista no subtítulo (CVM/Susep)", () => {
    const data = {
      cenarios_conjuge: {
        labels: ["Sem renda do cônjuge"],
        aportes: [10000],
        prazos_if: [15],
        anos_if: [2041],
        premissas: { aporte_base: 8000 },
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceCSection data={data} />);
    expect(screen.getByText(/Não são previsões/)).toBeInTheDocument();
    expect(screen.getByText(/testes de resiliência/)).toBeInTheDocument();
  });
});

describe("ApendiceDSection", () => {
  it("lista pilares metodológicos e indica lineage ausente", () => {
    render(<ApendiceDSection data={emptyData()} />);
    expect(screen.getByText(/Apêndice D/)).toBeInTheDocument();
    expect(screen.getByText(/Patrimônio gerador de renda/)).toBeInTheDocument();
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
  it("renderiza seção forward-looking sem card Histórico de Ciclos", () => {
    render(<ApendiceESection data={emptyData()} />);
    expect(screen.getByText(/Apêndice E/)).toBeInTheDocument();
    expect(screen.queryByText(/Histórico de Ciclos/)).toBeNull();
    expect(screen.queryByText(/Primeiro relatório do workspace/)).toBeNull();
  });

  it("changelog populado NÃO renderiza no APP_E (anti-regressão de duplicação — TRACK-remove-historico-ciclos-app-e)", () => {
    const data = {
      changelog: [
        {
          section_id: "S1",
          summary:
            "Patrimônio líquido cresceu R$ 200.000,00 desde o relatório anterior (+20,0%)",
          delta_signal: "up",
          delta_pct: 20,
        },
      ],
    } as unknown as ReportAnalysisData;
    render(<ApendiceESection data={data} />);
    expect(
      screen.queryByText(/Patrimônio líquido cresceu R\$ 200\.000,00/),
    ).toBeNull();
    expect(screen.queryByText(/Histórico de Ciclos/)).toBeNull();
  });

  it("renderiza fallback summary quando narrativas ausentes", () => {
    render(<ApendiceESection data={emptyData()} />);
    expect(screen.getByText("Próximos passos do roadmap.")).toBeInTheDocument();
  });
});

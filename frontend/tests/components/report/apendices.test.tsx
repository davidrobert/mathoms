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
    expect(
      screen.getByText(/Premissas econômicas não registradas/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Bruno Perini/)).toBeInTheDocument();
    expect(screen.getByText(/Gustavo Cerbasi/)).toBeInTheDocument();
  });

  it("lista snapshot de premissas quando presente em goals", () => {
    const data = {
      goals: {
        premissas_snapshot: { inflacao: "4.5%", selic: "14.25%" },
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceBSection data={data} />);
    expect(screen.getByText("inflacao")).toBeInTheDocument();
    expect(screen.getByText("4.5%")).toBeInTheDocument();
    expect(screen.getByText("selic")).toBeInTheDocument();
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
      goals: { if_prazo_anos: 14.2, if_ano: 2040 },
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

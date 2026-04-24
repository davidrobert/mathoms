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

describe("ApendiceCSection", () => {
  it("mostra empty state quando sem cenários", () => {
    render(<ApendiceCSection data={emptyData()} />);
    expect(
      screen.getByText(/Sem cenários alternativos registrados/),
    ).toBeInTheDocument();
  });

  it("renderiza tabela de cenários quando cenarios_mariana presente", () => {
    const data = {
      cenarios_mariana: {
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
  it("mostra empty state quando sem changelog", () => {
    render(<ApendiceESection data={emptyData()} />);
    expect(screen.getByText(/Sem histórico de ciclos ainda/)).toBeInTheDocument();
  });

  it("renderiza ChangelogList quando narrativas.changelog presente", () => {
    const data = {
      narrativas: {
        changelog: {
          ciclo: "Ciclo Abr/2026",
          entries: [
            { id: "e1", headline: "Reserva atingiu 12 meses", severity: "highlight" },
            { id: "e2", headline: "Alocação ajustada +5% IPCA+" },
          ],
        },
      },
    } as unknown as ReportAnalysisData;
    render(<ApendiceESection data={data} />);
    expect(screen.getByText("Ciclo Abr/2026")).toBeInTheDocument();
    expect(screen.getByText("Reserva atingiu 12 meses")).toBeInTheDocument();
    expect(screen.getByText("Alocação ajustada +5% IPCA+")).toBeInTheDocument();
  });
});

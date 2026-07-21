/**
 * Tests — ADR-219 wave 3 · APP_B renderiza `premissas_economicas`.
 *
 * Cobre:
 * - Empty state (premissas ausentes em runs antigos).
 * - Status badge `completo` vs `parcial`.
 * - Linhas `indisponivel` renderizam warn em vez de números.
 * - `workspace_override` recebe badge dedicado.
 * - Labels editoriais resolvem código AUVP → nome amigável.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ApendiceBSection } from "@/components/report/sections/ApendicesSections";
import type {
  PremissasEconomicasClassRow,
  PremissasEconomicasData,
  ReportAnalysisData,
} from "@/lib/api";

function makeRow(overrides: Partial<PremissasEconomicasClassRow> = {}): PremissasEconomicasClassRow {
  return {
    classe_auvp: "rf_pos",
    status: "emitted",
    retorno_real_esperado_pct_anual: "3.500",
    sigma_anual_pct: "1.500",
    fonte: "test source",
    fonte_origem: "global",
    effective_from: "2026-01-01",
    justificativa: null,
    razao_indisponivel: null,
    ...overrides,
  };
}

function makePremissas(
  rows: PremissasEconomicasClassRow[],
  status: "completo" | "parcial" = "completo",
): PremissasEconomicasData {
  return {
    status,
    snapshot_at: "2026-05-15T12:00:00Z",
    classes: rows,
  };
}

function makeData(overrides: Partial<ReportAnalysisData> = {}): ReportAnalysisData {
  return {
    periodo_dados: "2026",
    data_analise: "2026-05-15",
    goals: {},
    ...overrides,
  };
}

describe("ApendiceBSection — premissas_economicas (ADR-219)", () => {
  it("renderiza empty state quando premissas ausentes (runs antigos)", () => {
    render(<ApendiceBSection data={makeData()} />);
    expect(screen.getByText(/Premissas econômicas não disponíveis/i)).toBeInTheDocument();
  });

  it("renderiza badge 'Completo' quando todas as classes têm premissa", () => {
    render(
      <ApendiceBSection
        data={makeData({
          premissas_economicas: makePremissas([makeRow()]),
        })}
      />,
    );
    expect(screen.getByText(/Status: Completo/i)).toBeInTheDocument();
  });

  it("renderiza badge 'Parcial' quando alguma classe está indisponível", () => {
    const rows: PremissasEconomicasClassRow[] = [
      makeRow({ classe_auvp: "rf_pos" }),
      makeRow({
        classe_auvp: "cripto",
        status: "indisponivel",
        retorno_real_esperado_pct_anual: null,
        sigma_anual_pct: null,
        fonte: null,
        fonte_origem: null,
        effective_from: null,
        razao_indisponivel: "Sem premissa para cripto",
      }),
    ];
    render(
      <ApendiceBSection data={makeData({ premissas_economicas: makePremissas(rows, "parcial") })} />,
    );
    expect(screen.getByText(/Status: Parcial/i)).toBeInTheDocument();
    expect(screen.getByText(/projeção parcial nesta classe/i)).toBeInTheDocument();
  });

  it("mostra selo 'Ajuste' em linhas com fonte_origem=workspace_override (A37.l10)", () => {
    render(
      <ApendiceBSection
        data={makeData({
          premissas_economicas: makePremissas([
            makeRow({
              classe_auvp: "acoes_br",
              fonte_origem: "workspace_override",
              justificativa: "perfil agressivo",
            }),
          ]),
        })}
      />,
    );
    expect(screen.getByText(/^Ajuste$/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Override$/i)).toBeNull();
  });

  it("resolve label editorial (snake_case code → nome amigável)", () => {
    render(
      <ApendiceBSection
        data={makeData({
          premissas_economicas: makePremissas([
            makeRow({ classe_auvp: "rf_inflacao" }),
            makeRow({ classe_auvp: "acoes_br" }),
            makeRow({ classe_auvp: "fii" }),
          ]),
        })}
      />,
    );
    expect(screen.getByText("Renda Fixa IPCA+")).toBeInTheDocument();
    expect(screen.getByText("Ações Brasil")).toBeInTheDocument();
    expect(screen.getByText("FIIs")).toBeInTheDocument();
  });

  it("formata retorno e sigma como '%.2f% a.a.'", () => {
    render(
      <ApendiceBSection
        data={makeData({
          premissas_economicas: makePremissas([
            makeRow({
              retorno_real_esperado_pct_anual: "7.000",
              sigma_anual_pct: "22.000",
            }),
          ]),
        })}
      />,
    );
    expect(screen.getByText("7.00% a.a.")).toBeInTheDocument();
    expect(screen.getByText("22.00% a.a.")).toBeInTheDocument();
  });

  it("classe code desconhecido (operador adicionou via console) cai no fallback", () => {
    render(
      <ApendiceBSection
        data={makeData({
          premissas_economicas: makePremissas([makeRow({ classe_auvp: "cripto" })]),
        })}
      />,
    );
    // Não há label editorial pra "cripto" — UI mostra o code cru
    expect(screen.getByText("cripto")).toBeInTheDocument();
  });
});

/**
 * Tests — A33.l4 (ADR-238 §L4) — ProventosYieldCard: hierarquia de métricas
 * do design 2026-07-07 + gates UX objetivos (rótulo obrigatório no yield
 * secundário; sem denominador → renda absoluta sem %).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ProventosYieldCard } from "@/components/report/cards/ProventosYieldCard";
import type { ProventosAtivoData } from "@/types/report-analysis";

function makeAtivo(overrides: Partial<ProventosAtivoData> = {}): ProventosAtivoData {
  return {
    ticker: "ITSA4",
    ano_base: 2024,
    total_proventos_brl: 228.2,
    ir_retido_brl: 21.0,
    renda_liquida_brl: 207.2,
    custo_total_brl: 3738.0,
    valor_mercado_brl: 4351.2,
    yield_on_cost_pct: 5.54,
    yield_on_market_pct: 4.76,
    ...overrides,
  };
}

describe("ProventosYieldCard", () => {
  it("oculta o card quando o workspace não tem informe de proventos", () => {
    const { container } = render(<ProventosYieldCard data={undefined} />);
    expect(container).toBeEmptyDOMElement();
    const empty = render(<ProventosYieldCard data={[]} />);
    expect(empty.container).toBeEmptyDOMElement();
  });

  it("renderiza yield sobre custo como métrica primária com micro-legenda", () => {
    render(<ProventosYieldCard data={[makeAtivo()]} />);
    expect(screen.getAllByText("Yield sobre custo").length).toBeGreaterThan(0);
    expect(
      screen.getByLabelText(/Yield sobre custo: 5,54 por cento, renda sobre custo de aquisição/),
    ).toBeInTheDocument();
    expect(screen.getByText(/renda anual ÷ o que você pagou/)).toBeInTheDocument();
  });

  it("gate UX: todo % de valor atual carrega o rótulo 'Yield sobre valor atual' junto", () => {
    render(<ProventosYieldCard data={[makeAtivo()]} />);
    // Hero secundário + célula da tabela: nenhum % de valor atual sem rótulo.
    const rotulados = screen.getAllByLabelText(/Yield sobre valor atual.*por cento/);
    const ocorrencias = screen.getAllByText(/4,76%/);
    expect(rotulados.length).toBeGreaterThanOrEqual(ocorrencias.length);
    expect(screen.getByText(/renda anual ÷ valor de mercado em 31\/12/)).toBeInTheDocument();
  });

  it("sem custo mas com valor de mercado: 'Yield sobre valor atual' assume o hero SEM virar yield genérico", () => {
    const ativo = makeAtivo({
      custo_total_brl: null,
      yield_on_cost_pct: null,
    });
    render(<ProventosYieldCard data={[ativo]} />);
    // Nenhum yield sobre custo renderizado (hero nem célula) — só o header fixo da tabela.
    expect(screen.queryByLabelText(/renda sobre custo de aquisição/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Yield sobre valor atual/).length).toBeGreaterThan(0);
    expect(screen.getByText(/sem custo de aquisição no informe/)).toBeInTheDocument();
  });

  it("piso seguro: sem custo nem valor de mercado, só renda absoluta em R$ — nenhum %", () => {
    const ativo = makeAtivo({
      custo_total_brl: null,
      valor_mercado_brl: null,
      yield_on_cost_pct: null,
      yield_on_market_pct: null,
    });
    const { container } = render(<ProventosYieldCard data={[ativo]} />);
    expect(screen.getByText("Renda absoluta")).toBeInTheDocument();
    expect(screen.getAllByText(/R\$/).length).toBeGreaterThan(0);
    // Nenhum percentual renderizado em lugar nenhum do card.
    expect(container.textContent).not.toMatch(/\d,\d{2}%/);
  });

  it("tabela ordena por renda líquida e usa '—' quando o denominador falta", () => {
    const semCusto = makeAtivo({
      ticker: "WEGE3",
      renda_liquida_brl: 465.4,
      custo_total_brl: null,
      valor_mercado_brl: null,
      yield_on_cost_pct: null,
      yield_on_market_pct: null,
    });
    render(<ProventosYieldCard data={[makeAtivo(), semCusto]} />);
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("WEGE3"); // maior renda primeiro
    expect(rows[2]).toHaveTextContent("ITSA4");
    expect(rows[1]).toHaveTextContent("—");
  });

  it("filtra para o ano-base mais recente quando há múltiplos anos", () => {
    const antigo = makeAtivo({ ticker: "PETR4", ano_base: 2023 });
    render(<ProventosYieldCard data={[makeAtivo(), antigo]} />);
    expect(screen.getByText(/ano-base 2024/)).toBeInTheDocument();
    expect(screen.queryByText("PETR4")).not.toBeInTheDocument();
  });

  it("footnote D8: disclaimers de JCP líquido e 'não substitui contador' presentes", () => {
    render(<ProventosYieldCard data={[makeAtivo()]} />);
    expect(screen.getByText(/JCP tributado/)).toBeInTheDocument();
    expect(screen.getByText(/não representa o retorno do que você aplicou/)).toBeInTheDocument();
    expect(screen.getByText(/Mathoms não substitui orientação tributária/)).toBeInTheDocument();
  });
});

/**
 * Specs do `<OrcamentoProspectivoCard>` — labels pt-BR de categoria (A37.l6 · PD-03).
 *
 * Regressão guard: o mapa local do card não continha `lazer`, `das_simples`,
 * `folha_pj` e `aporte_investimento`, e o fallback `?? key` vazava snake_case
 * cru para a tabela ao lado de categorias bem rotuladas. Pós-fix, o card
 * consome o mapa único de `@/lib/categoryLabels` com fallback humanizado.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import type { TransactionItem } from "@/lib/api/transactions";

const mockUsePeriodTransactions = vi.fn();

vi.mock("@/hooks/usePeriodTransactions", () => ({
  usePeriodTransactions: (...args: unknown[]) => mockUsePeriodTransactions(...args),
}));

import { OrcamentoProspectivoCard } from "@/components/report/cards/OrcamentoProspectivoCard";
import type { OrcamentoProspectivoData } from "@/types/report-analysis";

function tx(categoria: string, valor: number, data = "2026-04-15"): TransactionItem {
  return {
    data,
    descricao: `mock-${categoria}`,
    valor,
    banco: "itau",
    categoria,
    tipo_conta: "corrente",
    titular: "Titular",
    moeda: "BRL",
    transaction_hash: `${categoria}-${valor}`,
    row_id: `${categoria}-${valor}`,
    is_overridden: false,
  };
}

/** Células de categoria (1ª coluna do body, exceto a linha Total). */
function categoryCellTexts(): string[] {
  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("row").slice(1); // pula thead
  return rows
    .map((row) => within(row).getAllByRole("cell")[0]?.textContent ?? "")
    .filter((text) => text !== "Total");
}

describe("<OrcamentoProspectivoCard />", () => {
  it("humaniza as 4 keys ausentes do mapa antigo (fallback E5 estático)", () => {
    mockUsePeriodTransactions.mockReturnValue({
      transactions: [],
      isLoading: false,
      error: null,
    });

    const orcamento: OrcamentoProspectivoData = {
      categorias: {
        lazer: 400,
        das_simples: 300,
        folha_pj: 200,
        aporte_investimento: 100,
        moradia: 1000,
      },
      total: 2000,
    };

    render(<OrcamentoProspectivoCard orcamento={orcamento} />);

    const table = screen.getByRole("table");
    const body = within(table);
    expect(body.getByText("Lazer")).toBeInTheDocument();
    expect(body.getByText("DAS (Simples Nacional)")).toBeInTheDocument();
    expect(body.getByText("Folha PJ")).toBeInTheDocument();
    expect(body.getByText("Aporte em investimentos")).toBeInTheDocument();
    expect(body.getByText("Moradia")).toBeInTheDocument();

    // Regressão: chave crua snake_case não pode vazar para a UI.
    expect(body.queryByText("lazer")).toBeNull();
    expect(body.queryByText("das_simples")).toBeNull();
    expect(body.queryByText("folha_pj")).toBeNull();
    expect(body.queryByText("aporte_investimento")).toBeNull();
  });

  it("humaniza labels com transações live (mesmo caminho de render)", () => {
    mockUsePeriodTransactions.mockReturnValue({
      transactions: [
        tx("lazer", 400),
        tx("das_simples", 300),
        tx("folha_pj", 200),
        tx("aporte_investimento", 100),
      ],
      isLoading: false,
      error: null,
    });

    render(<OrcamentoProspectivoCard orcamento={undefined} />);

    const body = within(screen.getByRole("table"));
    expect(body.getByText("Lazer")).toBeInTheDocument();
    expect(body.getByText("DAS (Simples Nacional)")).toBeInTheDocument();
    expect(body.getByText("Folha PJ")).toBeInTheDocument();
    expect(body.getByText("Aporte em investimentos")).toBeInTheDocument();
  });

  it("KR-B: nenhum label renderizado contém `_` nem inicia com minúscula-código", () => {
    mockUsePeriodTransactions.mockReturnValue({
      transactions: [],
      isLoading: false,
      error: null,
    });

    // Keys do payload dogfood da superfície (mapa completo + key nova desconhecida).
    const orcamento: OrcamentoProspectivoData = {
      categorias: {
        assinaturas: 10,
        seguros: 10,
        financeiro: 10,
        impostos: 10,
        nao_identificado: 10,
        reserva_desejos: 10,
        transporte: 10,
        financiamentos: 10,
        moradia: 10,
        alimentacao: 10,
        suporte_familiar: 10,
        saude: 10,
        lazer_viagens: 10,
        vestuario: 10,
        educacao: 10,
        servicos_domesticos: 10,
        melhoria_reforma: 10,
        lazer: 10,
        das_simples: 10,
        folha_pj: 10,
        aporte_investimento: 10,
        categoria_futura_desconhecida: 10,
      },
      total: 220,
    };

    render(<OrcamentoProspectivoCard orcamento={orcamento} />);

    const labels = categoryCellTexts();
    expect(labels.length).toBe(22);
    for (const label of labels) {
      expect(label).not.toMatch(/_/);
      expect(label.charAt(0)).not.toMatch(/[a-z]/);
    }
  });
});

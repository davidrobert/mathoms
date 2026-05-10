/**
 * Specs do `<ReceitasFonteCard>` — labels pt-BR para todas as categorias
 * de receita produzidas pelo pipeline (income_origin_resolver
 * `_DEFAULT_STATIC_ORIGINS` + `receita_clt`/`receita_pj`).
 *
 * Regressão guard: chave crua sem entrada em `FONTE_LABELS` aparecia na
 * UI (ex.: "receita_resgate") quando workspace tinha venda de ativo,
 * resgate, FGTS ou restituição.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import type { TransactionItem } from "@/lib/api/transactions";

const mockUsePeriodTransactions = vi.fn();

vi.mock("@/hooks/usePeriodTransactions", () => ({
  usePeriodTransactions: (...args: unknown[]) => mockUsePeriodTransactions(...args),
}));

import { ReceitasFonteCard } from "@/components/report/cards/ReceitasFonteCard";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

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

describe("<ReceitasFonteCard />", () => {
  it("renderiza labels pt-BR para todas as categorias do pipeline (live data)", () => {
    const transactions: TransactionItem[] = [
      tx("receita_clt", 8000),
      tx("receita_pj", 4000),
      tx("receita_aluguel", 3000),
      tx("receita_investimento", 2000),
      tx("receita_resgate", 1500),
      tx("receita_venda_ativo", 1000),
      tx("receita_fgts", 800),
      tx("receita_restituicao", 500),
      tx("outras_receitas", 200),
    ];
    mockUsePeriodTransactions.mockReturnValue({
      transactions,
      isLoading: false,
      error: null,
    });

    render(<ReceitasFonteCard fluxo={undefined} />);

    const table = screen.getByRole("table");
    const body = within(table);
    expect(body.getByText("CLT")).toBeInTheDocument();
    expect(body.getByText("PJ")).toBeInTheDocument();
    expect(body.getByText("Aluguéis")).toBeInTheDocument();
    expect(body.getByText("Rendimentos de Investimento")).toBeInTheDocument();
    expect(body.getByText("Resgates de Aplicações")).toBeInTheDocument();
    expect(body.getByText("Venda de Ativo")).toBeInTheDocument();
    expect(body.getByText("FGTS")).toBeInTheDocument();
    expect(body.getByText("Restituições")).toBeInTheDocument();
    expect(body.getByText("Outras receitas")).toBeInTheDocument();

    // Regressão: nenhuma chave crua de pipeline deve vazar para UI.
    expect(body.queryByText(/^receita_/)).toBeNull();
    expect(body.queryByText("outras_receitas")).toBeNull();
  });

  it("fallback E5 estático (por_fonte) — renderiza labels para todas as categorias", () => {
    mockUsePeriodTransactions.mockReturnValue({
      transactions: [],
      isLoading: false,
      error: null,
    });

    const fluxo: FluxoCaixaSummary = {
      por_fonte: {
        receita_clt: 100000,
        receita_pj: 50000,
        receita_aluguel: 24000,
        receita_investimento: 12000,
        receita_resgate: 8000,
        receita_venda_ativo: 5000,
        receita_fgts: 3000,
        receita_restituicao: 1500,
        outras_receitas: 500,
      },
    };

    render(<ReceitasFonteCard fluxo={fluxo} />);

    const table = screen.getByRole("table");
    const body = within(table);
    for (const label of [
      "CLT",
      "PJ",
      "Aluguéis",
      "Rendimentos de Investimento",
      "Resgates de Aplicações",
      "Venda de Ativo",
      "FGTS",
      "Restituições",
      "Outras receitas",
    ]) {
      expect(body.getByText(label)).toBeInTheDocument();
    }

    // Regressão: chave crua não pode aparecer.
    expect(body.queryByText(/^receita_/)).toBeNull();
  });

  it("categoria desconhecida cai no fallback `?? key` (não quebra a UI)", () => {
    mockUsePeriodTransactions.mockReturnValue({
      transactions: [],
      isLoading: false,
      error: null,
    });

    const fluxo: FluxoCaixaSummary = {
      por_fonte: {
        receita_clt: 5000,
        receita_categoria_nova: 1000,
      },
    };

    render(<ReceitasFonteCard fluxo={fluxo} />);

    const table = screen.getByRole("table");
    const body = within(table);
    expect(body.getByText("CLT")).toBeInTheDocument();
    expect(body.getByText("receita_categoria_nova")).toBeInTheDocument();
  });

  it("render vazio quando não há transações nem por_fonte", () => {
    mockUsePeriodTransactions.mockReturnValue({
      transactions: [],
      isLoading: false,
      error: null,
    });

    render(<ReceitasFonteCard fluxo={undefined} />);

    expect(screen.getByText(/Sem dados de receitas/)).toBeInTheDocument();
  });
});

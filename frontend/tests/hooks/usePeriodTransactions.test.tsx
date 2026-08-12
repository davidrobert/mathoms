/**
 * Specs do `usePeriodTransactions` — sinal de truncagem da janela
 * (A40.l44 PR2 · RV4-07).
 *
 * O hook pede `page_size: 500` e não pagina. A resposta já denunciava a
 * truncagem em `total`, e o cliente jogava fora: os consumidores agregavam
 * só as 500 mais recentes e exibiam média mensal 42% abaixo da real (janela
 * 12M do corpus de dogfood: 1634 lançamentos).
 */
import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import type {
  TransactionItem,
  TransactionListResponse,
} from "@/lib/api/transactions";

const mockListTransactions = vi.fn();

vi.mock("@/lib/api", () => ({
  listTransactions: (...args: unknown[]) => mockListTransactions(...args),
}));

vi.mock("@/lib/WorkspaceProvider", () => ({
  useWorkspace: () => ({ workspace: { id: "ws-1" } }),
}));

import { usePeriodTransactions } from "@/hooks/usePeriodTransactions";

function tx(i: number): TransactionItem {
  return {
    data: "2026-04-15",
    descricao: `mock-${i}`,
    valor: -100,
    banco: "itau",
    categoria: "mercado",
    tipo_conta: "corrente",
    titular: "Titular",
    moeda: "BRL",
    transaction_hash: `h-${i}`,
    row_id: `r-${i}`,
    is_overridden: false,
  };
}

function response(pageCount: number, total: number): TransactionListResponse {
  return {
    transactions: Array.from({ length: pageCount }, (_, i) => tx(i)),
    total,
    page: 1,
    page_size: 500,
    summary: {
      total_receitas: 0,
      total_despesas: 0,
      saldo: 0,
      count: total,
      periodo_inicio: null,
      periodo_fim: null,
    },
  };
}

describe("usePeriodTransactions", () => {
  it("janela maior que a página: isTruncated=true e total é o da janela", async () => {
    mockListTransactions.mockResolvedValue(response(500, 1634));

    const { result } = renderHook(() => usePeriodTransactions("12m"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.transactions).toHaveLength(500);
    expect(result.current.total).toBe(1634);
    expect(result.current.isTruncated).toBe(true);
  });

  it("janela que cabe na página: isTruncated=false", async () => {
    mockListTransactions.mockResolvedValue(response(188, 188));

    const { result } = renderHook(() => usePeriodTransactions("6m"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.total).toBe(188);
    expect(result.current.isTruncated).toBe(false);
  });

  it("erro de rede não deixa total antigo mentir sobre truncagem", async () => {
    mockListTransactions.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => usePeriodTransactions("12m"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.total).toBe(0);
    expect(result.current.isTruncated).toBe(false);
  });
});

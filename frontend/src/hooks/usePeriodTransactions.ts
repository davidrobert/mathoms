"use client";

import { useState, useEffect } from "react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { listTransactions } from "@/lib/api";
import type { TransactionItem } from "@/lib/api";
import { getPeriodDates, type Period } from "@/lib/periodUtils";

interface UsePeriodTransactionsResult {
  transactions: TransactionItem[];
  isLoading: boolean;
  error: string | null;
  /** Lançamentos da janela inteira, incluindo os que não vieram na página. */
  total: number;
  /** `true` quando a janela tem mais lançamentos do que a página trouxe. */
  isTruncated: boolean;
}

/**
 * Busca transações do workspace para o período selecionado.
 * Usa o endpoint GET /transactions com filtros date_from/date_to.
 *
 * Traz **uma** página de 500 e não pagina: janela maior que isso volta
 * `isTruncated=true`, e o consumidor deve declarar a degradação em vez de
 * agregar — somar só as 500 mais recentes derrubava a média mensal do card
 * em 42% na janela 12M do corpus de dogfood (1634 lançamentos · RV4-07).
 *
 * `anchorDate` ancora o fim da janela no último mês com dados do dataset
 * (default: hoje). Sem âncora, dados antigos do workspace caem em janelas
 * vazias relativas a "hoje" e o consumidor degrada para fallback estático.
 */
export function usePeriodTransactions(
  period: Period,
  anchorDate?: Date,
): UsePeriodTransactionsResult {
  const { workspace } = useWorkspace();
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const anchorKey = anchorDate?.getTime();

  useEffect(() => {
    if (!workspace) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const { date_from, date_to } = getPeriodDates(period, anchorDate);

    listTransactions(workspace.id, {
      date_from,
      date_to,
      page_size: 500,
    })
      .then((res) => {
        setTransactions(res.transactions);
        setTotal(res.total);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Erro ao carregar transações.",
        );
        setTransactions([]);
        setTotal(0);
      })
      .finally(() => {
        setIsLoading(false);
      });
    // anchorKey é serialização estável de anchorDate; o objeto Date pode mudar
    // de identidade a cada render do parent sem mudança real de valor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace, period, anchorKey]);

  return {
    transactions,
    isLoading,
    error,
    total,
    isTruncated: total > transactions.length,
  };
}

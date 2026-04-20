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
}

/**
 * Busca transações do workspace para o período selecionado.
 * Usa o endpoint GET /transactions com filtros date_from/date_to.
 * Máximo 500 transações por período (suficiente para uso familiar).
 */
export function usePeriodTransactions(
  period: Period,
): UsePeriodTransactionsResult {
  const { workspace } = useWorkspace();
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const { date_from, date_to } = getPeriodDates(period);

    listTransactions(workspace.id, {
      date_from,
      date_to,
      page_size: 500,
    })
      .then((res) => {
        setTransactions(res.transactions);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Erro ao carregar transações.",
        );
        setTransactions([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [workspace, period]);

  return { transactions, isLoading, error };
}

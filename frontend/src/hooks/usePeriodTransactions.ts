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
    // anchorKey é serialização estável de anchorDate; o objeto Date pode mudar
    // de identidade a cada render do parent sem mudança real de valor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace, period, anchorKey]);

  return { transactions, isLoading, error };
}

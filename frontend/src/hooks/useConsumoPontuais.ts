"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import {
  getConsumoPontuais,
  type ConsumoPontuaisItem,
  type ConsumoPontuaisPeriod,
} from "@/lib/api/reports";

interface UseConsumoPontuaisResult {
  items: ConsumoPontuaisItem[];
  total: number;
  totalValor: number;
  isLoading: boolean;
  error: string | null;
}

/**
 * Busca a lista filtrada de gastos pontuais ≥ R$2k para o período selecionado.
 *
 * Toda a regra (threshold, exclusão de transferências entre contas da
 * família) vive no backend — este hook é só fetch + estado de loading.
 */
export function useConsumoPontuais(
  period: ConsumoPontuaisPeriod,
): UseConsumoPontuaisResult {
  const { workspace } = useWorkspace();
  const [items, setItems] = useState<ConsumoPontuaisItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalValor, setTotalValor] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    getConsumoPontuais(workspace.id, period)
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        setTotalValor(res.total_valor);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Erro ao carregar gastos pontuais.",
        );
        setItems([]);
        setTotal(0);
        setTotalValor(0);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [workspace, period]);

  return { items, total, totalValor, isLoading, error };
}

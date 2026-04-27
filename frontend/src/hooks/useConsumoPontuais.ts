"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import {
  getConsumoPontuais,
  type ConsumoPontuaisItem,
  type ConsumoPontuaisPeriod,
  type ConsumoPontuaisResponse,
} from "@/lib/api/reports";

interface UseConsumoPontuaisResult {
  items: ConsumoPontuaisItem[];
  total: number;
  totalValor: number;
  isLoading: boolean;
  error: string | null;
}

interface ConsumoState {
  items: ConsumoPontuaisItem[];
  total: number;
  totalValor: number;
}

interface FetchHandlers {
  setData: (s: ConsumoState) => void;
  setError: (e: string | null) => void;
  setIsLoading: (b: boolean) => void;
}

const EMPTY: ConsumoState = { items: [], total: 0, totalValor: 0 };

function toState(res: ConsumoPontuaisResponse): ConsumoState {
  // Defensive: API contract guarantees `items` array, mas em ambientes
  // mockados/erros parciais (ex.: route catch-all em testes E2E retornando
  // `{}`) o campo pode vir undefined, causando crash em `pontuais.length`
  // no consumer. Coerce p/ default seguro — protege ErrorBoundary do shell.
  return {
    items: Array.isArray(res.items) ? res.items : [],
    total: typeof res.total === "number" ? res.total : 0,
    totalValor: typeof res.total_valor === "number" ? res.total_valor : 0,
  };
}

function describeError(err: unknown): string {
  return err instanceof Error ? err.message : "Erro ao carregar gastos pontuais.";
}

function applyResolved(
  res: ConsumoPontuaisResponse,
  handlers: FetchHandlers,
): void {
  handlers.setData(toState(res));
  handlers.setError(null);
}

function applyRejected(err: unknown, handlers: FetchHandlers): void {
  handlers.setError(describeError(err));
  handlers.setData(EMPTY);
}

function runFetch(
  workspaceId: string,
  period: ConsumoPontuaisPeriod,
  handlers: FetchHandlers,
): () => void {
  let cancelled = false;
  handlers.setIsLoading(true);
  getConsumoPontuais(workspaceId, period)
    .then((res) => !cancelled && applyResolved(res, handlers))
    .catch((err: unknown) => !cancelled && applyRejected(err, handlers))
    .finally(() => !cancelled && handlers.setIsLoading(false));
  return () => {
    cancelled = true;
  };
}

/** Fetch da lista de gastos pontuais ≥ R$2k já filtrada pelo backend. */
export function useConsumoPontuais(
  period: ConsumoPontuaisPeriod,
): UseConsumoPontuaisResult {
  const { workspace } = useWorkspace();
  const [data, setData] = useState<ConsumoState>(EMPTY);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace) {
      setIsLoading(false);
      return;
    }
    return runFetch(workspace.id, period, { setData, setError, setIsLoading });
  }, [workspace, period]);

  return { ...data, isLoading, error };
}

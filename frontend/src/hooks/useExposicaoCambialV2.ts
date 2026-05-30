"use client";

// ADR-224 PR-D — hook do card Exposição Cambial V2. Carrega data + overrides
// + expõe declare/remove (refetch). Padrão minimal alinhado a useSuggestions
// (sem cache global; cada consumer chama reload).

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  declareLastroOverride as apiDeclare,
  fetchExposicaoCambialV2 as apiFetch, // gitleaks:allow — identificador camelCase, não-segredo (FP generic-api-key, ADR-230 §D3)
  listLastroOverrides as apiList,
  removeLastroOverride as apiRemove,
  type AssetOverrideCommand,
  type AssetOverrideResponse,
  type ExposicaoCambialV2Response,
  type MatchKind,
} from "@/lib/api/exposicaoCambial";

export interface UseExposicaoCambialV2State {
  data: ExposicaoCambialV2Response | null;
  overrides: AssetOverrideResponse[];
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  declare: (command: AssetOverrideCommand) => Promise<AssetOverrideResponse>;
  remove: (matchKind: MatchKind, key: string) => Promise<void>;
}

interface InternalState {
  data: ExposicaoCambialV2Response | null;
  overrides: AssetOverrideResponse[];
  loading: boolean;
  error: string;
}

const INITIAL: InternalState = { data: null, overrides: [], loading: false, error: "" };

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

async function loadAll(workspaceId: string): Promise<InternalState> {
  try {
    const [card, list] = await Promise.all([apiFetch(workspaceId), apiList(workspaceId)]);
    return { data: card, overrides: list.overrides, loading: false, error: "" };
  } catch (err) {
    return { ...INITIAL, error: describeError(err, "Falha ao carregar exposição cambial") };
  }
}

function buildMutators(
  workspaceId: string | null,
  reload: () => Promise<void>,
): { declare: UseExposicaoCambialV2State["declare"]; remove: UseExposicaoCambialV2State["remove"] } {
  const declare = async (command: AssetOverrideCommand) => {
    if (!workspaceId) throw new Error("workspaceId obrigatório");
    const response = await apiDeclare(workspaceId, command);
    await reload();
    return response;
  };
  const remove = async (matchKind: MatchKind, key: string) => {
    if (!workspaceId) return;
    await apiRemove(workspaceId, matchKind, key);
    await reload();
  };
  return { declare, remove };
}

export function useExposicaoCambialV2(workspaceId: string | null): UseExposicaoCambialV2State {
  const [state, setState] = useState<InternalState>(INITIAL);
  const reload = useCallback(async () => {
    if (!workspaceId) return;
    setState((s) => ({ ...s, loading: true, error: "" }));
    setState(await loadAll(workspaceId));
  }, [workspaceId]);
  useEffect(() => {
    void reload();
  }, [reload]);
  const { declare, remove } = buildMutators(workspaceId, reload);
  return { ...state, reload, declare, remove };
}

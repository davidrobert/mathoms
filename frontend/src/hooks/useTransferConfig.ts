"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  getTransferConfig,
  putTransferConfig,
  type TransferConfigData,
} from "@/lib/api";

const EMPTY: TransferConfigData = {
  patterns_pix: [],
  patterns_global: [],
  patterns_bank_specific: {},
  recipients: [],
};

const SUCCESS_MESSAGE =
  "Configurações salvas — próximo relatório gerado já usará as novas regras.";

export interface UseTransferConfigState {
  data: TransferConfigData | null;
  loading: boolean;
  saving: boolean;
  error: string;
  success: string;
  reload: () => Promise<void>;
  save: (next: TransferConfigData) => Promise<void>;
  clearMessages: () => void;
}

interface ReloadDeps {
  workspaceId: string | undefined;
  setData: (d: TransferConfigData | null) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string) => void;
}

interface SaveDeps {
  workspaceId: string | undefined;
  setData: (d: TransferConfigData) => void;
  setSaving: (b: boolean) => void;
  setError: (s: string) => void;
  setSuccess: (s: string) => void;
}

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

async function runReload({ workspaceId, setData, setLoading, setError }: ReloadDeps): Promise<void> {
  if (!workspaceId) {
    setData(EMPTY);
    setLoading(false);
    return;
  }
  setLoading(true);
  setError("");
  try {
    setData(await getTransferConfig(workspaceId));
  } catch (err) {
    setError(describeError(err, "Erro ao carregar configuração de transferências"));
  } finally {
    setLoading(false);
  }
}

async function runSave(deps: SaveDeps, next: TransferConfigData): Promise<void> {
  if (!deps.workspaceId) return;
  deps.setSaving(true);
  deps.setError("");
  deps.setSuccess("");
  try {
    deps.setData(await putTransferConfig(deps.workspaceId, next));
    deps.setSuccess(SUCCESS_MESSAGE);
  } catch (err) {
    deps.setError(describeError(err, "Erro ao salvar configuração"));
    throw err;
  } finally {
    deps.setSaving(false);
  }
}

interface InternalState {
  data: TransferConfigData | null;
  loading: boolean;
  saving: boolean;
  error: string;
  success: string;
  setData: (d: TransferConfigData | null) => void;
  setLoading: (b: boolean) => void;
  setSaving: (b: boolean) => void;
  setError: (s: string) => void;
  setSuccess: (s: string) => void;
}

function useInternalState(): InternalState {
  const [data, setData] = useState<TransferConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  return {
    data,
    loading,
    saving,
    error,
    success,
    setData,
    setLoading,
    setSaving,
    setError,
    setSuccess,
  };
}

function useStableActions(workspaceId: string | undefined, s: InternalState) {
  const reload = useCallback(
    () => runReload({ workspaceId, setData: s.setData, setLoading: s.setLoading, setError: s.setError }),
    [workspaceId, s.setData, s.setLoading, s.setError],
  );
  const save = useCallback(
    (next: TransferConfigData) => runSave({ workspaceId, ...s }, next),
    [workspaceId, s],
  );
  const clearMessages = useCallback(() => {
    s.setError("");
    s.setSuccess("");
  }, [s]);
  return { reload, save, clearMessages };
}

/** Hook de carga + persistência do bloco `transferencias_internas` (ADR-133). */
export function useTransferConfig(workspaceId: string | undefined): UseTransferConfigState {
  const s = useInternalState();
  const { reload, save, clearMessages } = useStableActions(workspaceId, s);
  useEffect(() => {
    void reload();
  }, [reload]);
  const { data, loading, saving, error, success } = s;
  return { data, loading, saving, error, success, reload, save, clearMessages };
}

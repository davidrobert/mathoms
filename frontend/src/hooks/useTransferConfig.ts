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

/** Hook de carga + persistência do bloco `transferencias_internas` (ADR-133). */
export function useTransferConfig(workspaceId: string | undefined): UseTransferConfigState {
  const [data, setData] = useState<TransferConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const reload = useCallback(async () => {
    if (!workspaceId) {
      setData(EMPTY);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await getTransferConfig(workspaceId);
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao carregar configuração de transferências");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const save = useCallback(
    async (next: TransferConfigData) => {
      if (!workspaceId) return;
      setSaving(true);
      setError("");
      setSuccess("");
      try {
        const result = await putTransferConfig(workspaceId, next);
        setData(result);
        setSuccess("Configurações salvas — próximo relatório gerado já usará as novas regras.");
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Erro ao salvar configuração");
        throw err;
      } finally {
        setSaving(false);
      }
    },
    [workspaceId],
  );

  const clearMessages = useCallback(() => {
    setError("");
    setSuccess("");
  }, []);

  return { data, loading, saving, error, success, reload, save, clearMessages };
}

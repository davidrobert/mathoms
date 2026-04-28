"use client";

import { useState } from "react";
import {
  overrideTransactionCategory,
  removeTransactionOverride,
  type TransactionItem,
  ApiError,
} from "@/lib/api";

interface Options {
  workspaceId: string;
  onAfterChange: () => void | Promise<void>;
  onError: (msg: string) => void;
}

export function useCategoryOverride({ workspaceId, onAfterChange, onError }: Options) {
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState("");
  const [savingOverride, setSavingOverride] = useState(false);

  function startEdit(tx: TransactionItem) {
    setEditingRowId(tx.row_id);
    setEditCategory(tx.categoria);
  }

  async function saveOverride(hash: string) {
    if (!editCategory) return;
    setSavingOverride(true);
    try {
      await overrideTransactionCategory(workspaceId, hash, { new_category: editCategory });
      setEditingRowId(null);
      await onAfterChange();
    } catch (err) {
      onError(err instanceof ApiError ? err.detail : "Erro ao salvar override");
    } finally {
      setSavingOverride(false);
    }
  }

  async function clearOverride(hash: string) {
    setSavingOverride(true);
    try {
      await removeTransactionOverride(workspaceId, hash);
      await onAfterChange();
    } catch (err) {
      onError(err instanceof ApiError ? err.detail : "Erro ao remover override");
    } finally {
      setSavingOverride(false);
    }
  }

  return {
    editingRowId,
    editCategory,
    savingOverride,
    setEditingRowId,
    setEditCategory,
    startEdit,
    saveOverride,
    clearOverride,
  };
}

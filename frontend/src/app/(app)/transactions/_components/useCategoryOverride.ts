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
  const [editingHash, setEditingHash] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState("");
  const [savingOverride, setSavingOverride] = useState(false);

  function startEdit(tx: TransactionItem) {
    setEditingHash(tx.transaction_hash);
    setEditCategory(tx.categoria);
  }

  async function saveOverride(hash: string) {
    if (!editCategory) return;
    setSavingOverride(true);
    try {
      await overrideTransactionCategory(workspaceId, hash, { new_category: editCategory });
      setEditingHash(null);
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
    editingHash,
    editCategory,
    savingOverride,
    setEditingHash,
    setEditCategory,
    startEdit,
    saveOverride,
    clearOverride,
  };
}

"use client";

import { useState } from "react";
import {
  overrideTransactionCategory,
  removeTransactionOverride,
  type TransactionItem,
  ApiError,
} from "@/lib/api";

/** Contexto do último override salvo — alimenta toast "Criar regra" (A12 P4). */
export interface LastOverrideContext {
  transactionDescription: string;
  newCategory: string;
}

interface Options {
  workspaceId: string;
  onAfterChange: () => void | Promise<void>;
  onError: (msg: string) => void;
  /** Disparado após save bem-sucedido com contexto. ``undefined`` = sem callback. */
  onSaved?: (ctx: LastOverrideContext) => void;
}

export function useCategoryOverride({
  workspaceId,
  onAfterChange,
  onError,
  onSaved,
}: Options) {
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState("");
  const [editingTxDescription, setEditingTxDescription] = useState("");
  const [savingOverride, setSavingOverride] = useState(false);

  function startEdit(tx: TransactionItem) {
    setEditingRowId(tx.row_id);
    setEditCategory(tx.categoria);
    setEditingTxDescription(tx.descricao);
  }

  async function saveOverride(hash: string) {
    if (!editCategory) return;
    const ctx: LastOverrideContext = {
      transactionDescription: editingTxDescription,
      newCategory: editCategory,
    };
    setSavingOverride(true);
    try {
      await overrideTransactionCategory(workspaceId, hash, { new_category: editCategory });
      setEditingRowId(null);
      await onAfterChange();
      onSaved?.(ctx);
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

import { apiFetch } from "./core";

// ─── Transaction Types ───

export interface TransactionItem {
  data: string;
  descricao: string;
  valor: number;
  banco: string;
  categoria: string;
  origem?: string;
  tipo_conta: string;
  titular: string;
  moeda: string;
  transaction_hash: string;
  is_overridden: boolean;
}

export interface TransactionSummary {
  total_receitas: number;
  total_despesas: number;
  saldo: number;
  count: number;
  periodo_inicio: string | null;
  periodo_fim: string | null;
}

export interface TransactionListResponse {
  transactions: TransactionItem[];
  total: number;
  page: number;
  page_size: number;
  summary: TransactionSummary;
}

export interface TransactionOverrideResponse {
  id: string;
  transaction_hash: string;
  original_category: string;
  new_category: string;
  notes: string | null;
  reviewed: boolean;
  created_at: string;
}

// ─── Transaction API ───

export async function listTransactions(workspaceId: string, params?: {
  member?: string;
  bank?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
  value_min?: number;
  value_max?: number;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<TransactionListResponse> {
  const qp = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qp.set(k, String(v));
    });
  }
  const qs = qp.toString();
  return apiFetch(`/workspaces/${workspaceId}/transactions${qs ? `?${qs}` : ""}`);
}

export async function overrideTransactionCategory(
  workspaceId: string,
  hash: string,
  data: { new_category: string; notes?: string }
): Promise<TransactionOverrideResponse> {
  return apiFetch(`/workspaces/${workspaceId}/transactions/${hash}/override`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function removeTransactionOverride(workspaceId: string, hash: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/transactions/${hash}/override`, { method: "DELETE" });
}

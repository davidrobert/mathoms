import { apiFetch } from "./core";

// ─── Debt agregado de passivo (ADR-227 §D1 · Sprint A15 Onda 4) ───

export type DebtTipo =
  | "financiamento_imobiliario"
  | "consignado"
  | "cdc"
  | "cartao_rotativo"
  | "rotativo"
  | "outro";

export type DebtSource =
  | "baseline_irpf_migration"
  | "user_declared"
  | "open_banking_futuro";

export interface DebtResponse {
  id: string;
  workspace_id: string;
  family_member_id: string | null;
  property_id: string | null;
  tipo: DebtTipo;
  descricao: string | null;
  /** BRL como string decimal (ADR-090). Ex: "300000.00". */
  saldo_devedor_brl: string;
  parcela_mensal_brl: string | null;
  /** % a.a. como string decimal (ex.: "12.50"). */
  taxa_juros_aa: string | null;
  prazo_meses_restantes: number | null;
  data_contratacao: string | null;
  source: DebtSource;
  migration_source_key: string | null;
  needs_review: boolean;
  /** % rateio (0 < pct ≤ 100); default 100 quando property_id setado. */
  percentual_atribuicao_imovel: string | null;
  created_at: string;
  updated_at: string;
}

export interface DebtCreate {
  family_member_id?: string | null;
  property_id?: string | null;
  tipo: DebtTipo;
  descricao?: string | null;
  saldo_devedor_brl: string;
  parcela_mensal_brl?: string | null;
  taxa_juros_aa?: string | null;
  prazo_meses_restantes?: number | null;
  data_contratacao?: string | null;
  source?: DebtSource;
  migration_source_key?: string | null;
  needs_review?: boolean;
  percentual_atribuicao_imovel?: string | null;
}

export interface DebtUpdate {
  family_member_id?: string | null;
  property_id?: string | null;
  tipo?: DebtTipo;
  descricao?: string | null;
  saldo_devedor_brl?: string;
  parcela_mensal_brl?: string | null;
  taxa_juros_aa?: string | null;
  prazo_meses_restantes?: number | null;
  data_contratacao?: string | null;
  percentual_atribuicao_imovel?: string | null;
  needs_review?: boolean;
}

export async function listDebts(
  workspaceId: string,
  options: { needsReview?: boolean } = {},
): Promise<DebtResponse[]> {
  const query = options.needsReview ? "?needs_review=true" : "";
  return apiFetch(`/workspaces/${workspaceId}/debts${query}`);
}

export async function createDebt(
  workspaceId: string,
  body: DebtCreate,
): Promise<DebtResponse> {
  return apiFetch(`/workspaces/${workspaceId}/debts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateDebt(
  workspaceId: string,
  debtId: string,
  body: DebtUpdate,
): Promise<DebtResponse> {
  return apiFetch(`/workspaces/${workspaceId}/debts/${debtId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteDebt(
  workspaceId: string,
  debtId: string,
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/debts/${debtId}`, {
    method: "DELETE",
  });
}

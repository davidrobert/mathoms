import { apiFetch } from "./core";

// ═══════════════════════════════════════════════════════════════════════
// Goals — Meta IF (ADR-073, F8.1)
// Padrão F8+: endpoints escopados por {API_BASE}/workspaces/{ws_id}/...
// ═══════════════════════════════════════════════════════════════════════

export interface IFGoalInputs {
  renda_passiva_mensal_brl: number;
  trs_pct: number;
  retorno_real_anual_pct: number;
  horizonte_anos: number;
  taxa_retirada_conservadora_pct?: number;
}

export interface IFGoalDerived {
  if_meta_brl: number;
  /** Aporte assumindo patrimônio inicial zero (baseline; persistido). */
  aporte_necessario_mensal_brl: number;
  if_meta_conservadora_brl: number;
  /** Quando há patrimônio de referência (ex.: último relatório), aporte para fechar o gap. */
  aporte_mensal_com_patrimonio_atual_brl?: number | null;
  patrimonio_atual_utilizado_brl?: number | null;
}

/** Aporte a exibir: ajustado ao patrimônio conhecido, senão baseline. */
export function ifMonthlyContributionDisplay(d: IFGoalDerived): number {
  return (
    d.aporte_mensal_com_patrimonio_atual_brl ?? d.aporte_necessario_mensal_brl
  );
}

export interface IFGoalResponse {
  id: string;
  workspace_id: string;
  type: "INDEPENDENCIA_FINANCEIRA";
  /** Schema canônico (`config/schemas/goal.if.schema.json`). */
  meta_version: number;
  inputs: IFGoalInputs;
  derived: IFGoalDerived;
  effective_from: string;
  effective_to: string | null;
  is_template: boolean;
  notes: string | null;
  created_by: string | null;
  /** F9 · nome humano do autor (join com users.full_name). */
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface IFGoalHistoryResponse {
  goals: IFGoalResponse[];
  total: number;
}

export interface IFGoalComputeRequest {
  inputs: IFGoalInputs;
  patrimonio_atual_brl?: number;
}

export interface IFGoalComputeResponse {
  derived: IFGoalDerived;
  percentual_conquistado: number | null;
  faltante_brl: number | null;
}

export async function computeIFGoal(
  workspaceId: string,
  body: IFGoalComputeRequest
): Promise<IFGoalComputeResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if/compute`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getIFGoal(
  workspaceId: string
): Promise<IFGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if`);
}

export async function getIFGoalHistory(
  workspaceId: string
): Promise<IFGoalHistoryResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if/history`);
}

export async function upsertIFGoal(
  workspaceId: string,
  inputs: IFGoalInputs,
  notes?: string
): Promise<IFGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if`, {
    method: "PUT",
    body: JSON.stringify({ inputs, notes }),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Goals — Aportes Mensais (F8.5)
// ═══════════════════════════════════════════════════════════════════════

export interface AporteGoalInputs {
  meta_aporte_mensal_brl: number;
  dia_aporte: number;
  periodo_inicio?: string;
  distribuicao?: Record<string, number>;
}

export interface AporteGoalDerived {
  aporte_anual_brl: number;
  distribuicao_pct: Record<string, number>;
}

export interface AporteGoalResponse {
  id: string;
  workspace_id: string;
  type: "APORTE_MENSAL";
  meta_version: number;
  inputs: AporteGoalInputs;
  derived: AporteGoalDerived;
  effective_from: string;
  effective_to: string | null;
  is_template: boolean;
  notes: string | null;
  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AporteGoalHistoryResponse {
  goals: AporteGoalResponse[];
  total: number;
}

export interface AporteGoalComputeResponse {
  derived: AporteGoalDerived;
}

export async function computeAporteGoal(
  workspaceId: string,
  inputs: AporteGoalInputs
): Promise<AporteGoalComputeResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/aportes/compute`, {
    method: "POST",
    body: JSON.stringify({ inputs }),
  });
}

export async function getAporteGoal(
  workspaceId: string
): Promise<AporteGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/aportes`);
}

export async function getAporteGoalHistory(
  workspaceId: string
): Promise<AporteGoalHistoryResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/aportes/history`);
}

export async function upsertAporteGoal(
  workspaceId: string,
  inputs: AporteGoalInputs,
  notes?: string
): Promise<AporteGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/aportes`, {
    method: "PUT",
    body: JSON.stringify({ inputs, notes }),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Goals — Dolarização (F8.5)
// ═══════════════════════════════════════════════════════════════════════

export interface DolarGoalInputs {
  meta_usd: number;
  aporte_mensal_brl: number;
}

export interface DolarGoalDerived {
  horizonte_estimado_meses: number;
}

export interface DolarGoalResponse {
  id: string;
  workspace_id: string;
  type: "DOLARIZACAO";
  meta_version: number;
  inputs: DolarGoalInputs;
  derived: DolarGoalDerived;
  effective_from: string;
  effective_to: string | null;
  is_template: boolean;
  notes: string | null;
  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface DolarGoalHistoryResponse {
  goals: DolarGoalResponse[];
  total: number;
}

export interface DolarGoalComputeResponse {
  derived: DolarGoalDerived;
  cambio_utilizado: number;
}

export async function computeDolarGoal(
  workspaceId: string,
  inputs: DolarGoalInputs,
  cambio_brl_usd?: number
): Promise<DolarGoalComputeResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/dolarizacao/compute`, {
    method: "POST",
    body: JSON.stringify({ inputs, cambio_brl_usd }),
  });
}

export async function getDolarGoal(
  workspaceId: string
): Promise<DolarGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/dolarizacao`);
}

export async function getDolarGoalHistory(
  workspaceId: string
): Promise<DolarGoalHistoryResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/dolarizacao/history`);
}

export async function upsertDolarGoal(
  workspaceId: string,
  inputs: DolarGoalInputs,
  notes?: string
): Promise<DolarGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/dolarizacao`, {
    method: "PUT",
    body: JSON.stringify({ inputs, notes }),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Goals — Alocação-Alvo (F8.5)
// ═══════════════════════════════════════════════════════════════════════

export interface AlocacaoGoalInputs {
  renda_fixa_pct: number;
  acoes_pct: number;
  imoveis_reits_pct: number;
  liquidez_usd_pct: number;
  instrumentos_rf?: string;
  instrumentos_rv?: string;
  rebalanceamento?: string;
}

export interface AlocacaoGoalDerived {
  soma_percentuais: number;
}

export interface AlocacaoGoalResponse {
  id: string;
  workspace_id: string;
  type: "ALOCACAO_ALVO";
  meta_version: number;
  inputs: AlocacaoGoalInputs;
  derived: AlocacaoGoalDerived;
  effective_from: string;
  effective_to: string | null;
  is_template: boolean;
  notes: string | null;
  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlocacaoGoalHistoryResponse {
  goals: AlocacaoGoalResponse[];
  total: number;
}

export interface AlocacaoGoalComputeResponse {
  derived: AlocacaoGoalDerived;
  valido: boolean;
}

export async function computeAlocacaoGoal(
  workspaceId: string,
  inputs: AlocacaoGoalInputs
): Promise<AlocacaoGoalComputeResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/alocacao/compute`, {
    method: "POST",
    body: JSON.stringify({ inputs }),
  });
}

export async function getAlocacaoGoal(
  workspaceId: string
): Promise<AlocacaoGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/alocacao`);
}

export async function getAlocacaoGoalHistory(
  workspaceId: string
): Promise<AlocacaoGoalHistoryResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/alocacao/history`);
}

export async function upsertAlocacaoGoal(
  workspaceId: string,
  inputs: AlocacaoGoalInputs,
  notes?: string
): Promise<AlocacaoGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/alocacao`, {
    method: "PUT",
    body: JSON.stringify({ inputs, notes }),
  });
}

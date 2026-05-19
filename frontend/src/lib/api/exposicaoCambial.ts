// ADR-224 PR-C — client TypeScript do endpoint Exposição Cambial V2 + overrides per-workspace.
//
// Use:
//   const data = await fetchExposicaoCambialV2(workspaceId);
//   await declareLastroOverride(workspaceId, { match_kind: "ticker", asset_match_key: "IVVB11", lastro_moeda: "BRL" });
//   await removeLastroOverride(workspaceId, "ticker", "IVVB11");

import { apiFetch } from "./core";

export type LastroMoeda = "BRL" | "USD" | "EUR" | "MIXED" | "OTHER";
export type MatchKind = "ticker" | "cnpj" | "description";
export type LastroSource = "override" | "catalog" | "fallback_classe";
export type ExposicaoCambialTier = "verde" | "amarelo" | "vermelho" | "empty";

export interface ExposicaoCambialPorMoeda {
  moeda: string;
  /** Decimal string no wire (ADR-090); o frontend parseFloat para render numérico. */
  valor_brl: string;
  share_pct: number;
}

export interface ExposicaoCambialAtivo {
  nome: string;
  moeda: string;
  /** Decimal string no wire (ADR-090). */
  valor_brl: string;
  tipo: string;
  lastro_source: LastroSource;
}

export interface ExposicaoCambialV2Response {
  workspace_id: string;
  /** Decimal string no wire (ADR-090). */
  total_brl: string;
  pct_investivel_financeiro: number;
  por_moeda: ExposicaoCambialPorMoeda[];
  tier: ExposicaoCambialTier;
  ativos_contribuintes: ExposicaoCambialAtivo[];
  catalog_version: number;
  source_run_id: string | null;
  computed_at: string;
}

export interface AssetOverrideCommand {
  match_kind: MatchKind;
  asset_match_key: string;
  lastro_moeda: LastroMoeda;
}

export interface AssetOverrideResponse {
  id: string;
  workspace_id: string;
  match_kind: MatchKind;
  asset_match_key: string;
  lastro_moeda: LastroMoeda;
  override_source: string;
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
}

export interface AssetOverrideListResponse {
  workspace_id: string;
  overrides: AssetOverrideResponse[];
}

const BASE = (ws: string) => `/workspaces/${encodeURIComponent(ws)}/cards/exposicao-cambial`;

export function fetchExposicaoCambialV2(
  workspaceId: string
): Promise<ExposicaoCambialV2Response> {
  return apiFetch<ExposicaoCambialV2Response>(BASE(workspaceId));
}

export function listLastroOverrides(workspaceId: string): Promise<AssetOverrideListResponse> {
  return apiFetch<AssetOverrideListResponse>(`${BASE(workspaceId)}/overrides`);
}

export function declareLastroOverride(
  workspaceId: string,
  command: AssetOverrideCommand
): Promise<AssetOverrideResponse> {
  return apiFetch<AssetOverrideResponse>(`${BASE(workspaceId)}/overrides`, {
    method: "POST",
    body: JSON.stringify(command),
  });
}

export function removeLastroOverride(
  workspaceId: string,
  matchKind: MatchKind,
  assetMatchKey: string
): Promise<void> {
  return apiFetch<void>(
    `${BASE(workspaceId)}/overrides/${encodeURIComponent(matchKind)}/${encodeURIComponent(
      assetMatchKey
    )}`,
    { method: "DELETE" }
  );
}

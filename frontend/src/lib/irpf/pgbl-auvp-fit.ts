/**
 * ADR-195 · A12 — PGBL: threshold AUVP modula variante visual no estado
 * `capacidade_disponivel` do card `IrpfPgblCapacidadeCard`.
 *
 * Função pura, sem dependência de React, testável isoladamente.
 * Decisão determinística sobre `kpis.aliquota_sobre_tributavel_pct`
 * com thresholds X=20% (aderente) e Y=12% (abaixo) fixados pela
 * decisão G0 financial-planner (ADR-195 §3.1, §6.1).
 *
 * Não cruza linha ADR-157: nenhuma recomendação de produto, banco ou
 * regime; só modulação de **intensidade visual** dentro do estado já
 * tipificado por ADR-189.
 */

import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

export type AuvpFitTier =
  | "auvp_aderente"
  | "neutro"
  | "abaixo"
  | "indeterminado";

export interface AuvpFitResult {
  tier: AuvpFitTier;
  /** Alíquota efetiva sobre tributável (0–100) ou null se indisponível. */
  aliquota: number | null;
  reason: string;
}

/** ADR-195 §3 D2 — thresholds canônicos. Mudança requer nova ADR. */
export const AUVP_ADERENTE_THRESHOLD_PCT = 20;
export const AUVP_ABAIXO_THRESHOLD_PCT = 12;

function indeterminado(reason: string): AuvpFitResult {
  return { tier: "indeterminado", aliquota: null, reason };
}

function tierResult(tier: AuvpFitTier, aliquota: number, reason: string): AuvpFitResult {
  return { tier, aliquota, reason };
}

function classifyByAliquota(aliquota: number): AuvpFitResult {
  const X = AUVP_ADERENTE_THRESHOLD_PCT;
  const Y = AUVP_ABAIXO_THRESHOLD_PCT;
  if (aliquota >= X) {
    return tierResult("auvp_aderente", aliquota, `aliquota_efetiva (${aliquota}%) >= ${X}%`);
  }
  if (aliquota >= Y) {
    return tierResult("neutro", aliquota, `${Y}% <= aliquota_efetiva (${aliquota}%) < ${X}%`);
  }
  return tierResult("abaixo", aliquota, `aliquota_efetiva (${aliquota}%) < ${Y}%`);
}

export function evaluatePgblAuvpFit(kpis: IrpfKpis): AuvpFitResult {
  if (kpis.pgbl_status !== "capacidade_disponivel") {
    return indeterminado("pgbl_status diferente de capacidade_disponivel");
  }
  const aliquota = parseDecimalString(kpis.aliquota_sobre_tributavel_pct);
  if (aliquota === null || aliquota < 0) {
    return indeterminado("aliquota_sobre_tributavel_pct ausente ou inválida");
  }
  return classifyByAliquota(aliquota);
}

/**
 * ADR-157 · IRPF Full Schema · UI lane.
 * ADR-189 · Diagnóstico PGBL tipificado (4 estados): adiciona
 * `pgbl_status`, `pgbl_aportado_brl`, `pgbl_teto_brl`.
 *
 * Tipos do shape `irpf_kpis` produzido por `IRPFAnalyzer` no E5
 * (scripts/e5_analyze.py::_e5_kpis_from_analyzer). Valores monetários e
 * percentuais chegam como Decimal-string para preservar precisão e devem
 * ser parseados no call-site (parseDecimalString abaixo).
 */

export type PgblStatus =
  | "capacidade_disponivel"
  | "modelo_simplificado"
  | "no_teto"
  | "sem_renda_tributavel";

const PGBL_STATUS_VALUES: ReadonlyArray<PgblStatus> = [
  "capacidade_disponivel",
  "modelo_simplificado",
  "no_teto",
  "sem_renda_tributavel",
];

export interface IrpfKpis {
  ano_base: number;
  anos_disponiveis: number[];
  renda_anual_familiar_brl: string;
  renda_liquida_familiar_brl: string;
  ir_pago_total_brl: string;
  aliquota_sobre_tributavel_pct: string;
  aliquota_sobre_total_pct: string;
  pgbl_capacidade_dedutivel_brl: string;
  pgbl_status: PgblStatus;
  pgbl_aportado_brl: string;
  pgbl_teto_brl: string;
  split_trabalho_brl: string;
  split_capital_brl: string;
  evolucao_renda_anos: Record<string, string>;
}

const STRING_FIELDS: ReadonlyArray<keyof IrpfKpis> = [
  "renda_anual_familiar_brl",
  "renda_liquida_familiar_brl",
  "ir_pago_total_brl",
  "aliquota_sobre_tributavel_pct",
  "aliquota_sobre_total_pct",
  "pgbl_capacidade_dedutivel_brl",
  "pgbl_aportado_brl",
  "pgbl_teto_brl",
  "split_trabalho_brl",
  "split_capital_brl",
];

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isNumberArray(v: unknown): v is number[] {
  return Array.isArray(v) && v.every((x) => typeof x === "number");
}

function isStringRecord(v: unknown): v is Record<string, string> {
  if (!isPlainObject(v)) return false;
  return Object.values(v).every((x) => typeof x === "string");
}

export function isIrpfKpis(value: unknown): value is IrpfKpis {
  if (!isPlainObject(value)) return false;
  if (typeof value["ano_base"] !== "number") return false;
  if (!isNumberArray(value["anos_disponiveis"])) return false;
  if (!isStringRecord(value["evolucao_renda_anos"])) return false;
  for (const key of STRING_FIELDS) {
    if (typeof value[key] !== "string") return false;
  }
  const status = value["pgbl_status"];
  if (typeof status !== "string" || !PGBL_STATUS_VALUES.includes(status as PgblStatus)) {
    return false;
  }
  return true;
}

/** Converte Decimal-string ("1234.56") para number, preservando NaN-safety.
 *  Retorna null para strings inválidas — caller decide fallback. */
export function parseDecimalString(s: string): number | null {
  if (typeof s !== "string" || s.length === 0) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

import type { RebalanceamentoModo } from "@/lib/api";
import {
  ALOCACAO_CLASSES,
  ALOCACAO_CLASS_KEYS,
  type AlocacaoClassKey,
} from "@/lib/alocacaoClasses";

/** Percentuais das 7 classes v2 — chaves vêm da fonte única `alocacaoClasses`. */
export type Pcts = Record<AlocacaoClassKey, number>;

export const PCT_KEYS: readonly AlocacaoClassKey[] = ALOCACAO_CLASS_KEYS;

export function sumPcts(pcts: Pcts): number {
  return PCT_KEYS.reduce((acc, key) => acc + pcts[key], 0);
}

/** Joga o resíduo de `100 − Σ(outras)` em `caixa_pct` (ADR-141 emenda item 11). */
export function completeWithCaixa(pcts: Pcts): Pcts {
  const outras = PCT_KEYS.filter((k) => k !== "caixa_pct").reduce(
    (acc, key) => acc + pcts[key],
    0,
  );
  return { ...pcts, caixa_pct: Math.max(0, 100 - outras) };
}

// Totais por família preservados dos presets v1:
// Conservador RF60/RV20/FIIs10/Caixa10 · Moderado RF40/RV30/FIIs15/Caixa15
// · Agressivo RF25/RV45/FIIs15/Caixa15.
export const PRESETS: Record<string, Pcts> = {
  Conservador: {
    rf_pos_pct: 30,
    rf_pre_pct: 15,
    rf_ipca_pct: 15,
    acoes_br_pct: 14,
    acoes_int_pct: 6,
    fiis_pct: 10,
    caixa_pct: 10,
  },
  Moderado: {
    rf_pos_pct: 20,
    rf_pre_pct: 10,
    rf_ipca_pct: 10,
    acoes_br_pct: 20,
    acoes_int_pct: 10,
    fiis_pct: 15,
    caixa_pct: 15,
  },
  Agressivo: {
    rf_pos_pct: 10,
    rf_pre_pct: 5,
    rf_ipca_pct: 10,
    acoes_br_pct: 30,
    acoes_int_pct: 15,
    fiis_pct: 15,
    caixa_pct: 15,
  },
};

/** Legenda/barra — derivada da fonte única (`AlocacaoBar`, `AlocacaoSummary`). */
export const CLASS_META: readonly {
  key: AlocacaoClassKey;
  label: string;
  color: string;
}[] = ALOCACAO_CLASSES.map((c) => ({
  key: c.id,
  label: c.label,
  color: c.colorVar,
}));

// ── Rebalanceamento: 3 escolhas agrupadas (ADR-141 emenda item 11) ──────
// "No aporte" (default AUVP) · "Periódico" (trimestral/semestral/anual) ·
// "Por gatilho" (5%/10%). Strings legadas mapeiam para o enum canônico.

export type RebalGroupId = "por_aporte" | "periodico" | "gatilho";

export interface RebalGroup {
  id: RebalGroupId;
  label: string;
  recommended?: boolean;
  /** Grupo de escolha única (por_aporte). */
  value?: RebalanceamentoModo;
  /** Grupo com sub-seleção (periódico, gatilho). */
  options?: readonly { value: RebalanceamentoModo; label: string }[];
  /** Modo assumido ao selecionar o grupo sem escolher a sub-opção. */
  defaultValue?: RebalanceamentoModo;
}

export const REBAL_GROUPS: readonly RebalGroup[] = [
  {
    id: "por_aporte",
    label: "No aporte",
    recommended: true,
    value: "por_aporte",
  },
  {
    id: "periodico",
    label: "Periódico",
    options: [
      { value: "trimestral", label: "Trimestral" },
      { value: "semestral", label: "Semestral" },
      { value: "anual", label: "Anual" },
    ],
    defaultValue: "trimestral",
  },
  {
    id: "gatilho",
    label: "Por gatilho",
    options: [
      { value: "trigger_5pct", label: "5%" },
      { value: "trigger_10pct", label: "10%" },
    ],
    defaultValue: "trigger_5pct",
  },
];

/** Grupo ao qual um modo pertence — resolve o enum legado para a UI agrupada. */
export function rebalGroupOf(modo: RebalanceamentoModo): RebalGroupId {
  if (modo === "por_aporte") return "por_aporte";
  if (modo === "trigger_5pct" || modo === "trigger_10pct") return "gatilho";
  return "periodico";
}

import type { RebalanceamentoModo } from "@/lib/api";
import { REBALANCEAMENTO_MODO_LABELS } from "@/lib/goalPremissas";

export interface Pcts {
  rf_pos_pct: number;
  rf_pre_pct: number;
  rf_ipca_pct: number;
  acoes_br_pct: number;
  acoes_int_pct: number;
  fiis_pct: number;
  caixa_pct: number;
}

export const PCT_KEYS = [
  "rf_pos_pct",
  "rf_pre_pct",
  "rf_ipca_pct",
  "acoes_br_pct",
  "acoes_int_pct",
  "fiis_pct",
  "caixa_pct",
] as const satisfies readonly (keyof Pcts)[];

export function sumPcts(pcts: Pcts): number {
  return PCT_KEYS.reduce((acc, key) => acc + pcts[key], 0);
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

export const REBAL_OPTIONS: readonly {
  value: RebalanceamentoModo;
  label: string;
}[] = (Object.keys(REBALANCEAMENTO_MODO_LABELS) as RebalanceamentoModo[]).map(
  (value) => ({ value, label: REBALANCEAMENTO_MODO_LABELS[value] }),
);

/** Cores categóricas do design system (mesma sequência do MathomPieChart). */
export const CLASS_META: readonly {
  key: keyof Pcts;
  label: string;
  color: string;
}[] = [
  { key: "rf_pos_pct", label: "RF · Pós", color: "var(--chart-1)" },
  { key: "rf_pre_pct", label: "RF · Pré", color: "var(--chart-2)" },
  { key: "rf_ipca_pct", label: "RF · IPCA+", color: "var(--chart-3)" },
  { key: "acoes_br_pct", label: "Ações BR", color: "var(--chart-4)" },
  { key: "acoes_int_pct", label: "Ações Int.", color: "var(--chart-5)" },
  { key: "fiis_pct", label: "FIIs", color: "var(--chart-6)" },
  { key: "caixa_pct", label: "Caixa", color: "var(--chart-7)" },
];

/**
 * Fonte única das 7 classes AUVP da alocação-alvo v2 (ADR-141 §Emenda item 11).
 *
 * Espelhada no backend por `ALOCACAO_V2_CLASSES`
 * (`backend/app/schemas/dto/goal/alocacao.py`); ambos têm paridade travada
 * contra `config/schemas/goal.alocacao_alvo.v2.schema.json` por teste
 * (`alocacaoClasses.test.ts` + `test_alocacao_classes_parity.py`).
 *
 * `id` é exatamente a chave do input v2 no schema — muda aqui, quebra o
 * teste de paridade.
 */

export type AlocacaoClassKey =
  | "rf_pos_pct"
  | "rf_pre_pct"
  | "rf_ipca_pct"
  | "acoes_br_pct"
  | "acoes_int_pct"
  | "fiis_pct"
  | "caixa_pct";

export type AlocacaoFamilyId =
  "renda_fixa" | "renda_variavel" | "imobiliario" | "liquidez";

export interface AlocacaoClass {
  /** Chave do input v2 (schema goal.alocacao_alvo.v2). */
  id: AlocacaoClassKey;
  /** Rótulo curto para inputs, legendas e barras. */
  label: string;
  /** Rótulo descritivo para tooltips e resumo. */
  labelFull: string;
  /** Cor categórica do design system (nunca hex literal — ADR-076). */
  colorVar: string;
  family: AlocacaoFamilyId;
}

export const ALOCACAO_CLASSES: readonly AlocacaoClass[] = [
  {
    id: "rf_pos_pct",
    label: "RF · Pós",
    labelFull: "Renda fixa pós-fixada",
    colorVar: "var(--chart-1)",
    family: "renda_fixa",
  },
  {
    id: "rf_pre_pct",
    label: "RF · Pré",
    labelFull: "Renda fixa prefixada",
    colorVar: "var(--chart-2)",
    family: "renda_fixa",
  },
  {
    id: "rf_ipca_pct",
    label: "RF · IPCA+",
    labelFull: "Renda fixa atrelada à inflação",
    colorVar: "var(--chart-3)",
    family: "renda_fixa",
  },
  {
    id: "acoes_br_pct",
    label: "Ações BR",
    labelFull: "Ações e ETFs Brasil",
    colorVar: "var(--chart-4)",
    family: "renda_variavel",
  },
  {
    id: "acoes_int_pct",
    label: "Ações Int.",
    labelFull: "Ações e ETFs internacionais",
    colorVar: "var(--chart-5)",
    family: "renda_variavel",
  },
  {
    id: "fiis_pct",
    label: "FIIs",
    labelFull: "Fundos imobiliários (tijolo + papel)",
    colorVar: "var(--chart-6)",
    family: "imobiliario",
  },
  {
    id: "caixa_pct",
    label: "Caixa",
    labelFull: "Caixa e moeda estrangeira líquida",
    colorVar: "var(--chart-7)",
    family: "liquidez",
  },
] as const;

export const ALOCACAO_CLASS_KEYS: readonly AlocacaoClassKey[] =
  ALOCACAO_CLASSES.map((c) => c.id);

export interface AlocacaoFamily {
  id: AlocacaoFamilyId;
  label: string;
  classes: readonly AlocacaoClass[];
}

const FAMILY_LABELS: Record<AlocacaoFamilyId, string> = {
  renda_fixa: "Renda fixa",
  renda_variavel: "Renda variável",
  imobiliario: "Imobiliário",
  liquidez: "Liquidez",
};

/** Famílias na ordem canônica, cada uma com suas classes (também ordenadas). */
export const ALOCACAO_FAMILIES: readonly AlocacaoFamily[] = (
  Object.keys(FAMILY_LABELS) as AlocacaoFamilyId[]
).map((id) => ({
  id,
  label: FAMILY_LABELS[id],
  classes: ALOCACAO_CLASSES.filter((c) => c.family === id),
}));

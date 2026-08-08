import type { PremissasEconomicasData, ReportAnalysisData } from "@/lib/api";
import type {
  FluxoCaixaSummary,
  RealEstateData,
  RealEstateExcludedProperty,
} from "@/types/report-analysis";

/** A28.l9 — derivação pura dos sinais de qualidade de dados do relatório.
 *
 * Consolida degradações que já existem no payload E5 (espalhadas em cards
 * individuais) numa estrutura única para o `<ReportDataQualityBanner/>`.
 * Sem I/O: a contagem de documentos needs_review chega por parâmetro
 * (hook `useNeedsReviewCount`).
 */

/** Limiar (%) de despesas não classificadas que dispara o sinal. */
export const NAO_IDENTIFICADO_THRESHOLD_PCT = 10;

/** Reconhece a categoria "não identificado" em qualquer grafia do wire.
 *
 * O E5 emite a chave crua `nao_identificado` em `despesas_por_categoria`,
 * mas `despesa_datasets[].label` chega title-cased ("Nao Identificado") —
 * matching por string exata fura no caminho de datasets.
 */
export function isNaoIdentificadoKey(key: string): boolean {
  const norm = key
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[\s_]+/g, "_");
  return norm === "nao_identificado";
}

export interface NaoIdentificadoShare {
  readonly valor: number;
  /** Percentual absoluto do total de despesas (23.4 = 23,4%). */
  readonly pct: number;
}

/** Valor + share de despesas não classificadas na janela completa.
 *
 * Preferência: agregado `despesas_por_categoria`; fallback soma
 * `despesa_datasets`. Retorna `null` sem dado de despesa por categoria.
 */
export function computeNaoIdentificadoShare(
  fluxo: FluxoCaixaSummary | undefined,
): NaoIdentificadoShare | null {
  const fromAggregate = shareFromAggregate(fluxo?.despesas_por_categoria);
  if (fromAggregate) return fromAggregate;
  return shareFromDatasets(fluxo);
}

function shareFromAggregate(
  agg: Record<string, number> | undefined,
): NaoIdentificadoShare | null {
  if (!agg) return null;
  let total = 0;
  let alvo = 0;
  for (const [key, value] of Object.entries(agg)) {
    if (typeof value !== "number" || !(value > 0)) continue;
    total += value;
    if (isNaoIdentificadoKey(key)) alvo += value;
  }
  if (total <= 0) return null;
  return { valor: alvo, pct: (alvo / total) * 100 };
}

function shareFromDatasets(
  fluxo: FluxoCaixaSummary | undefined,
): NaoIdentificadoShare | null {
  const datasets = fluxo?.receita_despesa_mensal_detalhado?.despesa_datasets;
  if (!datasets || datasets.length === 0) return null;
  let total = 0;
  let alvo = 0;
  for (const ds of datasets) {
    const sum = ds.data.reduce((acc, v) => acc + (v ?? 0), 0);
    total += sum;
    if (isNaoIdentificadoKey(ds.label)) alvo += sum;
  }
  if (total <= 0) return null;
  return { valor: alvo, pct: (alvo / total) * 100 };
}

export interface PremissasDegrade {
  /** `indisponivel` = todas as classes sem premissa vigente; senão `parcial`. */
  readonly status: "parcial" | "indisponivel";
  readonly classesIndisponiveis: number;
  readonly classesTotal: number;
}

/** Sinal de premissas econômicas em fallback (ADR-219).
 *
 * Bloco ausente (run pré-ADR-219) NÃO dispara sinal — a UI já degrada com
 * empty state no Apêndice B; punir relatórios antigos aqui só gera ruído.
 */
export function computePremissasDegrade(
  premissas: PremissasEconomicasData | undefined,
): PremissasDegrade | null {
  if (!premissas) return null;
  const classes = premissas.classes ?? [];
  const indisponiveis = classes.filter((c) => c.status === "indisponivel").length;
  if (premissas.status === "completo" && indisponiveis === 0) return null;
  const allDown = classes.length > 0 && indisponiveis === classes.length;
  return {
    status: allDown ? "indisponivel" : "parcial",
    classesIndisponiveis: indisponiveis,
    classesTotal: classes.length,
  };
}

/** Imóveis fora do módulo de yield por classificação pendente (ADR-216 D8).
 * `classification === "desconhecido"` = usuário ainda não rotulou. */
export function pendingClassificationProperties(
  realEstate: RealEstateData | null | undefined,
): readonly RealEstateExcludedProperty[] {
  return (realEstate?.excluded_properties ?? []).filter(
    (p) => p.classification === "desconhecido",
  );
}

export interface ReportDataQualitySignals {
  /** Presente somente quando share > NAO_IDENTIFICADO_THRESHOLD_PCT. */
  readonly naoIdentificado: NaoIdentificadoShare | null;
  readonly needsReviewDocs: number;
  readonly premissas: PremissasDegrade | null;
  readonly imoveisPendentes: number;
  /** A40.l22 — itens do parecer retidos na conferência (só o desfecho
   *  PARCIAL; o retido inteiro é auto-evidente ao rolar e não ganha linha). */
  readonly parecerRetidos: number;
  /** Quantos sinais ativos (0 = banner colapsa para barra fina). */
  readonly count: number;
}

/** Sinais ativos. Cada linha do banner é condicional num sinal específico, então
 *  o `count` tem de ser a soma EXATA das linhas que vão renderizar — contar algo
 *  sem linha própria produz "1 pendência" com `<ul>` vazia (A40.l18 · ADR-357). */
function countActiveSignals(s: Omit<ReportDataQualitySignals, "count">): number {
  return (
    (s.naoIdentificado ? 1 : 0) +
    (s.needsReviewDocs > 0 ? 1 : 0) +
    (s.premissas ? 1 : 0) +
    (s.imoveisPendentes > 0 ? 1 : 0) +
    (s.parecerRetidos > 0 ? 1 : 0)
  );
}

export function computeDataQualitySignals(
  data: ReportAnalysisData,
  needsReviewDocs: number,
  parecerRetidos = 0,
): ReportDataQualitySignals {
  const share = computeNaoIdentificadoShare(data.fluxo_caixa as FluxoCaixaSummary | undefined);
  const parcial = {
    naoIdentificado:
      share && share.pct > NAO_IDENTIFICADO_THRESHOLD_PCT ? share : null,
    needsReviewDocs,
    premissas: computePremissasDegrade(data.premissas_economicas),
    imoveisPendentes: pendingClassificationProperties(data.real_estate).length,
    parecerRetidos,
  };
  return { ...parcial, count: countActiveSignals(parcial) };
}

/** Chaves de KPI de IF que o bloco de stats da S7 realmente lê. */
const IF_STAT_KEYS = ["if_meta", "if_pct", "ano_if", "if_gap"] as const;

/** Há ao menos um KPI de IF para mostrar?
 *
 * O gate da S7 era a truthiness de `goals`, mas o E5 emite a chave SEMPRE
 * (dict, eventualmente só com `alocacao_alvo`): workspace sem meta de IF
 * caía no ramo verdadeiro e imprimia "—  0,0%  —  —". Hide-when-empty.
 */
export function hasIfStats(
  goals: Record<string, unknown> | undefined,
): goals is Record<string, unknown> {
  return goals != null && IF_STAT_KEYS.some((key) => goals[key] != null);
}

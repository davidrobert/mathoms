/**
 * ADR-196 · Reconciliação dos cards PGBL S7 × S_IRPF_OTIMIZACAO.
 *
 * Quando o workspace tem IRPF Full do ano-base "authoritativo" (≤1 ano
 * de defasagem em relação ao período de análise), o Card B
 * (`IrpfPgblCapacidadeCard`) vira source-of-truth para PGBL e o Card A
 * (`PrevidenciaPgblCard`, S7) degrada para um dos 4 modos informativos
 * — com copy específica por estado do Card B, cross-link e variante
 * `neutral` (G4 hierarquia). Sem IRPF ou IRPF defasado ≥2 anos, Card A
 * mantém modo `default` (ou `default-defasado`) e ganha disclaimer.
 *
 * Regra completa em ADR-196 §D1.
 */

import type { IrpfKpis } from "@/types/irpf";

export type PgblCardMode =
  | "default"
  | "default-defasado"
  | "informative-capacidade"
  | "informative-simplificado"
  | "informative-no-teto"
  | "informative-sem-renda";

export interface PgblCardStrategy {
  mode: PgblCardMode;
  anoBase: number | null;
  defasadoAnos: number | null;
}

export interface IrpfPeriodMatch {
  anoBase: number | null;
  defasadoAnos: number | null;
  authoritative: boolean;
}

const AUTHORITATIVE_MAX_GAP = 1;
const DEFASADO_MIN_GAP = 2;

/** Extrai o ano do último label `YYYY-MM` de
 * `fluxo_caixa.receita_despesa_mensal_detalhado.labels`. Sem labels →
 * `null` (caller deve cair para modo `default`). */
export function derivePrimaryYear(labels: readonly string[] | undefined): number | null {
  if (!labels || labels.length === 0) return null;
  const last = labels[labels.length - 1];
  if (typeof last !== "string" || last.length < 4) return null;
  const year = Number.parseInt(last.slice(0, 4), 10);
  return Number.isFinite(year) ? year : null;
}

/** Seleciona o `ano_base` mais recente elegível e flagga defasagem.
 * Regra G0/ADR-196: IRPF `N` é authoritativo para período `N` ou
 * `N+1`; gap ≥ 2 anos → defasado. */
export function matchIrpfToPeriod(
  anosDisponiveis: readonly number[],
  primaryYear: number,
): IrpfPeriodMatch {
  const elegiveis = anosDisponiveis.filter((a) => a <= primaryYear + 1);
  if (elegiveis.length === 0) {
    return { anoBase: null, defasadoAnos: null, authoritative: false };
  }
  const anoBase = Math.max(...elegiveis);
  const gap = primaryYear - anoBase;
  return {
    anoBase,
    defasadoAnos: gap,
    authoritative: gap <= AUTHORITATIVE_MAX_GAP,
  };
}

const MODE_BY_PGBL_STATUS: Record<IrpfKpis["pgbl_status"], PgblCardMode> = {
  capacidade_disponivel: "informative-capacidade",
  modelo_simplificado: "informative-simplificado",
  no_teto: "informative-no-teto",
  sem_renda_tributavel: "informative-sem-renda",
};

const DEFAULT_STRATEGY: PgblCardStrategy = {
  mode: "default",
  anoBase: null,
  defasadoAnos: null,
};

function resolveFromMatch(
  irpfKpis: IrpfKpis,
  match: IrpfPeriodMatch,
): PgblCardStrategy {
  if (match.anoBase === null) return DEFAULT_STRATEGY;
  if ((match.defasadoAnos ?? 0) >= DEFASADO_MIN_GAP) {
    return { mode: "default-defasado", anoBase: match.anoBase, defasadoAnos: match.defasadoAnos };
  }
  return {
    mode: MODE_BY_PGBL_STATUS[irpfKpis.pgbl_status],
    anoBase: match.anoBase,
    defasadoAnos: match.defasadoAnos,
  };
}

export function getPgblCardStrategy(
  irpfKpis: IrpfKpis | null,
  primaryYear: number | null,
): PgblCardStrategy {
  if (!irpfKpis || primaryYear === null) return DEFAULT_STRATEGY;
  // ADR-305: o backend opina o ano-base fiscal único em `ano_base` (último
  // completo; degradação vem anotada). O match avalia a defasagem DESSE ano —
  // não do IRPF mais recente disponível, que pode ser um ano incompleto cujo
  // pgbl_status não corresponde ao payload.
  return resolveFromMatch(irpfKpis, matchIrpfToPeriod([irpfKpis.ano_base], primaryYear));
}

export function isInformativeMode(mode: PgblCardMode): boolean {
  return mode.startsWith("informative-");
}

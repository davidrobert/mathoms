// ADR-290 F3 — ordering metodológico + caps de display compartilhados pelas
// 3 superfícies de sugestões (/acao InboxTab, SuggestionCalloutInline,
// SuggestionCalloutSummary). Mapeamento de gates validado com
// financial-planner 2026-06-12 (PLAN-suggestion-lifecycle §3 F3).

import type { LayoutSectionId } from "@/generated/report-layout";
import type { Suggestion, SuggestionSeverity } from "@/lib/api";

/** Cap de display do inbox ativo: ≤12 acionáveis (danger+warning); o
 *  excedente vai para disclosure compacta — nunca escondido (KR5). */
export const ACTIONABLE_DISPLAY_CAP = 12;

/** Cards "Promover para ação" inline no relatório: ≤3 por seção. */
export const INLINE_SECTION_CAP = 3;

const SEVERITY_RANK: Record<SuggestionSeverity, number> = {
  danger: 3,
  warning: 2,
  info: 1,
};

// Gates metodológicos: 1 proteção/liquidez · 2 dívida · 3 alocação ·
// 4 renda (reservado — nenhuma seção/category vigente é otimização de
// renda pura; não forçar S7/alvo_if nele) · 5 fiscal · 6 default (fim:
// errar para cima fabrica urgência falsa; severidade precede o gate,
// então risco real nunca fica enterrado).
// Chaveado por `LayoutSectionId` (codegen do report_layout.yaml) para que ID
// inexistente ou queimado — S5/S6 — não entre no mapa: `tsc --noEmit` recusa.
// Só o caminho `origin="llm"` chega aqui; determinística resolve por `category`.
const GATE_BY_SECTION: Partial<Record<LayoutSectionId, number>> = {
  S9: 1,
  S1: 1,
  S2: 1,
  S3: 3,
  S7: 3,
  S8: 5,
  S_IRPF_RENDA: 5,
  S_IRPF_OTIMIZACAO: 5,
};

const GATE_BY_CATEGORY: Record<string, number> = {
  protecao: 1,
  comportamental: 1,
  endividamento: 2,
  carteira: 3,
  alvo_if: 3,
};

const GATE_DEFAULT = 6;

export function methodologicalGate(s: Suggestion): number {
  if (s.origin === "deterministic" && s.category) {
    return GATE_BY_CATEGORY[s.category] ?? GATE_DEFAULT;
  }
  return GATE_BY_SECTION[s.section_id as LayoutSectionId] ?? GATE_DEFAULT;
}

// Comparação apenas — nunca aritmética nem display (ADR-090: money é
// string decimal no wire; <MonetaryValue/> cuida da renderização).
function amountCentsForOrdering(s: Suggestion): number | null {
  if (s.amount_brl == null) return null;
  const parsed = Number(s.amount_brl);
  return Number.isFinite(parsed) ? Math.round(parsed * 100) : null;
}

/** severidade desc (danger sempre topo, não filtrável) → gate metodológico →
 *  sem-valor antes (gap não-quantificado não é rebaixado por R$ alto de
 *  outro item) → impacto desc → created_at desc. Estável e determinístico. */
export function suggestionPriorityComparator(
  a: Suggestion,
  b: Suggestion,
): number {
  const sev =
    (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0);
  if (sev !== 0) return sev;
  const gate = methodologicalGate(a) - methodologicalGate(b);
  if (gate !== 0) return gate;
  const aCents = amountCentsForOrdering(a);
  const bCents = amountCentsForOrdering(b);
  if (aCents === null && bCents !== null) return -1;
  if (aCents !== null && bCents === null) return 1;
  if (aCents !== null && bCents !== null && aCents !== bCents) {
    return bCents - aCents;
  }
  return (b.created_at ?? "").localeCompare(a.created_at ?? "");
}

export function isActionable(s: Suggestion): boolean {
  return s.severity !== "info";
}

/** Corte de foco do inbox: quantas acionáveis abrem em "Decidir agora".
 *  3 porque o dogfood 2026-08-11 mostrou 11 cards de mesmo peso ocupando
 *  ~2,5 viewports — o cap de 12 nunca mordeu e a ordenação, sem grupo,
 *  ficou invisível. Ordenar não é priorizar se nada separa o topo. */
export const FOCUS_GROUP_SIZE = 3;

/** ADR-376 §D4 — "agendada" é afirmação sobre o horizonte, nunca negação de
 *  `execucao`: `horizon: null` (determinística e row legada) é a maioria do
 *  inbox e tem de continuar na fila do agora. Escrever o gate como
 *  `horizon !== "execucao"` mandaria todas elas para "Agendadas" —
 *  a regressão que o teste de polaridade guarda. */
export function isScheduled(s: Suggestion): boolean {
  return s.horizon === "tatica" || s.horizon === "estrategica";
}

export interface SuggestionDisplayPartition {
  /** As FOCUS_GROUP_SIZE primeiras da fila do agora — danger no topo pelo
   *  comparator, então o slice basta para nunca enterrar risco real. */
  focus: Suggestion[];
  /** Resto da fila do agora, até ACTIONABLE_DISPLAY_CAP somado ao focus. */
  rest: Suggestion[];
  /** Acionáveis acima do cap — disclosure compacta, nunca escondidas (KR5). */
  overflow: Suggestion[];
  /** Acionáveis táticas/estratégicas — fora do cap; não competem com o agora. */
  scheduled: Suggestion[];
  /** `info` — colapsadas por default, fora do cap (referência, não fila). */
  informative: Suggestion[];
}

export function partitionForDisplay(
  suggestions: Suggestion[],
): SuggestionDisplayPartition {
  const sorted = [...suggestions].sort(suggestionPriorityComparator);
  const actionable = sorted.filter(isActionable);
  const now = actionable.filter((s) => !isScheduled(s));
  return {
    focus: now.slice(0, FOCUS_GROUP_SIZE),
    rest: now.slice(FOCUS_GROUP_SIZE, ACTIONABLE_DISPLAY_CAP),
    overflow: now.slice(ACTIONABLE_DISPLAY_CAP),
    scheduled: actionable.filter(isScheduled),
    informative: sorted.filter((s) => !isActionable(s)),
  };
}

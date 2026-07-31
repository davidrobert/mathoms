/**
 * ADR-355 (A40.l4) — precedência e normalização do parágrafo de abertura
 * de seção. Único lugar do repo com lógica de "de onde vem esse texto".
 *
 * Três produtores competiam pelo mesmo parágrafo sem precedência declarada:
 * `section_summaries[<ID>]` (LLM, ADR-144 §3, opt-in), `narrativas.summaries`
 * (E5.N, string) e `deriveSectionSummary` (determinístico). O componente lia
 * `narrativas[<ID maiúsculo>]` como objeto — chave e shape que nenhum
 * produtor emite —, então o texto do E5.N não renderizava em seção nenhuma.
 *
 * A normalização vive aqui (e não no boundary HTTP nem em `getReportData`)
 * porque este é o único ponto que TODA superfície de render atravessa:
 * produção, PDF (mesma rota React, ADR-129), E2E e os testes de vitest —
 * que injetam `data` direto no componente.
 */
import { LAYOUT } from "@/generated/report-layout";
import type { ReportAnalysisData } from "@/lib/api";
import { deriveSectionSummary } from "./conclusionUtils";

export type SectionSummarySource = "llm" | "e5n" | "derived";

export interface ResolvedSectionSummary {
  readonly text: string;
  readonly source: SectionSummarySource;
}

function buildSummarySourceMap(): Record<string, string> {
  const entries = [
    ...LAYOUT.estrategico.sections,
    ...(LAYOUT.estrategico.appendices ?? []),
  ];
  const out: Record<string, string> = {};
  for (const entry of entries) {
    if (entry.enabled && entry.summary_source) out[entry.id] = entry.summary_source;
  }
  return out;
}

/**
 * `{sectionId: chave em narrativas.summaries}` — mapa DECLARADO no layout
 * (`config/report_layout.yaml`, codegen ADR-076), nunca `id.toLowerCase()`:
 * `summaries.s2` é o parágrafo de SCORE e a S2 é Fluxo de Caixa.
 */
export const LAYOUT_SUMMARY_SOURCE: Readonly<Record<string, string>> =
  buildSummarySourceMap();

/**
 * Texto utilizável: string não-vazia após `trim()`. Qualquer outro shape
 * (objeto, número, null) conta como ausente — assim um produtor que passe a
 * emitir `{context, conclusion}` sob `summaries.sN` cai para a próxima camada
 * em vez de imprimir `[object Object]`. A divergência é caçada a montante
 * (CV9 §shape + teste Python da fixture), não silenciada aqui.
 */
function usableText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  return text.length > 0 ? text : null;
}

function readLlmSummary(sectionId: string, data: ReportAnalysisData): string | null {
  const bag = data.section_summaries as Record<string, unknown> | undefined;
  return usableText(bag?.[sectionId]);
}

function readE5nSummary(sectionId: string, data: ReportAnalysisData): string | null {
  const key = LAYOUT_SUMMARY_SOURCE[sectionId];
  if (!key) return null;
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const summaries = narrativas?.summaries as Record<string, unknown> | undefined;
  return usableText(summaries?.[key]);
}

/**
 * Resolve o parágrafo de abertura da seção. `null` → não renderiza nada.
 *
 * Precedência: LLM → E5.N → derivado. Fail-soft em todas as camadas (ADR-144
 * §3 — "o relatório nunca falha por causa de LLM"): fonte ausente, vazia,
 * só-whitespace ou de shape inesperado cai para a próxima, sem log e sem
 * throw. Seção sem `summary_source` no layout pula a camada 2 — não é erro.
 */
export function resolveSectionSummary(
  sectionId: string,
  data: ReportAnalysisData,
): ResolvedSectionSummary | null {
  const llm = readLlmSummary(sectionId, data);
  if (llm) return { text: llm, source: "llm" };
  const e5n = readE5nSummary(sectionId, data);
  if (e5n) return { text: e5n, source: "e5n" };
  const derived = usableText(deriveSectionSummary(sectionId, data));
  return derived ? { text: derived, source: "derived" } : null;
}

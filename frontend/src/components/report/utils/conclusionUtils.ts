/**
 * ADR-117/122 · Fase 6 — derivadores determinísticos de texto
 * (chart_conclusions + section_summaries).
 *
 * Templates vivem em config/prompts/chart_conclusions.yaml. Nesta fase,
 * frontend tem versão duplicada inline (mais simples que carregar YAML em
 * runtime + evita dependência extra). Se divergir, pre-commit deve
 * checar — por ora confiamos em revisão.
 *
 * LLM fallback para section_summaries fica fora de escopo da Fase 6 por
 * enquanto; Q11 prevê revisão após Fase 12.
 */
import type { ReportAnalysisData } from "@/lib/api";
import {
  aggregateAlocacao,
  type AlocacaoAlvoV1,
  type ClasseAtivoRow,
} from "./alocacaoBucketMapper";

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

type Formatter = "brl" | "pct" | "int" | "num";

function format(value: unknown, kind: Formatter): string {
  if (typeof value !== "number" || !isFinite(value)) return String(value ?? "");
  switch (kind) {
    case "brl":
      return BRL.format(value);
    case "pct":
      return `${(value <= 1 ? value * 100 : value).toFixed(0)}%`;
    case "int":
      return Math.round(value).toLocaleString("pt-BR");
    case "num":
      return value.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  }
}

/** Lookup case-insensitive via dot-notation ("fluxo_caixa.receita_total"). */
function getPath(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const key of path.split(".")) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[key];
  }
  return cur;
}

function topEntry(
  entries: Record<string, number> | undefined,
): { key: string; value: number; pct: number } | null {
  if (!entries) return null;
  const items = Object.entries(entries).filter(
    ([, v]) => typeof v === "number" && v > 0,
  );
  if (items.length === 0) return null;
  const total = items.reduce((sum, [, v]) => sum + v, 0);
  items.sort(([, a], [, b]) => b - a);
  const [key, value] = items[0];
  return { key, value, pct: total > 0 ? value / total : 0 };
}

/** Formata uma categoria/fonte id ("receita_clt" → "CLT") — heurística. */
function prettyKey(key: string): string {
  if (key === "receita_clt") return "CLT";
  if (key === "receita_pj") return "PJ";
  if (key === "receita_investimento") return "Investimentos";
  if (key === "receita_aluguel") return "Aluguel";
  if (key === "outras_receitas") return "Outras";
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─────────────────────────────────────────────────────────────────────
// Chart conclusions
// ─────────────────────────────────────────────────────────────────────

export interface ChartConclusionContext {
  readonly chartId: string;
  readonly data: ReportAnalysisData;
}

type Builder = (ctx: ChartConclusionContext) => string | null;

/** Retorna null se dados insuficientes (caller usa fallback). */
const BUILDERS: Record<string, Builder> = {
  patrimonio_doughnut: ({ data }) => {
    const composicao = getPath(data, "patrimonio.composicao") as
      | Array<{ categoria: string; valor: number; pct: number }>
      | undefined;
    if (!composicao || composicao.length === 0) return null;
    const top = [...composicao].sort((a, b) => b.valor - a.valor)[0];
    return `${top.categoria} representa ${format(top.pct, "pct")} do patrimônio líquido (${format(top.valor, "brl")}).`;
  },

  score_gauge: ({ data }) => {
    const valor = getPath(data, "score.valor") as number | undefined;
    const max = getPath(data, "score.max") as number | undefined;
    const classe = getPath(data, "score.classificacao") as string | undefined;
    if (typeof valor !== "number" || typeof max !== "number") return null;
    return `Score atual: ${format(valor, "num")} / ${format(max, "int")}${
      classe ? ` (${classe})` : ""
    }.`;
  },

  fluxo_mensal: ({ data }) => {
    const receita = getPath(data, "fluxo_caixa.receita_recorrente_mensal") as
      | number
      | undefined;
    const despesa = getPath(data, "fluxo_caixa.despesa_mensal_media") as
      | number
      | undefined;
    if (typeof receita !== "number" || typeof despesa !== "number") return null;
    const liquido = receita - despesa;
    return `Receita média mensal de ${format(receita, "brl")}, despesa média de ${format(despesa, "brl")}. Fluxo líquido: ${format(liquido, "brl")}.`;
  },

  receita_bar: ({ data }) => {
    const porFonte = getPath(data, "fluxo_caixa.por_fonte") as
      | Record<string, number>
      | undefined;
    const top = topEntry(porFonte);
    if (!top) return null;
    return `${prettyKey(top.key)} lidera as receitas (${format(top.pct, "pct")}).`;
  },

  despesas_doughnut: ({ data }) => {
    const cat = getPath(data, "fluxo_caixa.despesas_por_categoria") as
      | Record<string, number>
      | undefined;
    const top = topEntry(cat);
    if (!top) return null;
    return `${prettyKey(top.key)} concentra ${format(top.pct, "pct")} do gasto recorrente.`;
  },

  impostos_pj: ({ data }) => {
    const aliquota = getPath(data, "ratios.aliquota_efetiva_ir_pct") as
      | number
      | string
      | undefined;
    if (typeof aliquota !== "number") return null;
    return `Carga fiscal efetiva do ano: ${format(aliquota, "pct")}.`;
  },

  alocacao_atual: ({ data }) => buildAlocacaoFooter(data, "subalocada"),
  alocacao_alvo: ({ data }) => buildAlocacaoFooter(data, "aderente"),
};

const PP = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "always",
});

function summarizeAlocacao(
  data: ReportAnalysisData,
): ReturnType<typeof aggregateAlocacao> | null {
  const invest = getPath(data, "investimentos") as
    | { tabela_classes?: ClasseAtivoRow[]; total?: number }
    | undefined;
  const alvo = getPath(data, "goals.alocacao_alvo") as AlocacaoAlvoV1 | undefined;
  if (!invest?.tabela_classes || invest.tabela_classes.length === 0) return null;
  const summary = aggregateAlocacao(invest.tabela_classes, alvo, invest.total ?? 0);
  if (!summary.hasAlvo) return null;
  return summary;
}

function maiorDesvioBucket(
  summary: ReturnType<typeof aggregateAlocacao>,
): { label: string; desvio_pp: number } | null {
  return summary.buckets
    .filter((b) => b.desvio_pp !== null)
    .reduce<{ label: string; desvio_pp: number } | null>(
      (m, c) =>
        m === null || Math.abs(c.desvio_pp ?? 0) > Math.abs(m.desvio_pp)
          ? { label: c.label, desvio_pp: c.desvio_pp as number }
          : m,
      null,
    );
}

function buildAlocacaoFooter(
  data: ReportAnalysisData,
  mode: "subalocada" | "aderente",
): string | null {
  const summary = summarizeAlocacao(data);
  if (summary === null) return null;
  if (mode === "subalocada") {
    const sub = summary.buckets.find((b) => b.id === summary.nextAporteBucket);
    if (sub?.desvio_pp != null) {
      return `Próximo aporte → ${sub.label} (${PP.format(sub.desvio_pp)} pp vs alvo).`;
    }
    return null;
  }
  const top = maiorDesvioBucket(summary);
  return top ? `Maior desvio: ${PP.format(top.desvio_pp)} pp em ${top.label}.` : null;
}

const FALLBACKS: Record<string, string> = {
  patrimonio_doughnut: "Distribuição patrimonial por categoria.",
  waterfall_if: "Progresso acumulado rumo à independência financeira.",
  score_gauge: "Indicador consolidado da saúde financeira.",
  fluxo_mensal: "Receita vs despesa mês a mês.",
  receita_bar: "Composição das receitas por fonte.",
  despesas_doughnut: "Distribuição das despesas por categoria.",
  receita_despesa_mensal: "Receita vs despesa ao longo do tempo.",
  viagens: "Orçamento e gastos de viagem no período.",
  alocacao_atual: "Defina sua alocação-alvo em /plano/alocacao para acompanhar desvio.",
  alocacao_alvo: "Defina sua alocação-alvo em /plano/alocacao para acompanhar desvio.",
  top15_ativos: "Ativos de maior exposição na carteira.",
  cenarios_conjuge: "Cenário de estresse — sem renda do cônjuge.",
  yield_imoveis: "Rendimento dos imóveis comparado ao CDI.",
  projecao_3cenarios: "Projeção patrimonial por cenário.",
  renda_passiva: "Progresso da renda passiva rumo à meta.",
  impostos_pj: "Composição tributária PJ.",
  bubble_riscos: "Matriz de riscos priorizados.",
  top5_decisoes: "Próximas decisões de alto impacto.",
};

/** Gera texto de conclusão determinístico para o chart. Null → oculta box. */
export function deriveChartConclusion(
  chartId: string,
  data: ReportAnalysisData,
): string | null {
  const builder = BUILDERS[chartId];
  if (builder) {
    const result = builder({ chartId, data });
    if (result) return result;
  }
  return FALLBACKS[chartId] ?? null;
}

// ─────────────────────────────────────────────────────────────────────
// Section summaries (templates simples — LLM fica para revisão Q11)
// ─────────────────────────────────────────────────────────────────────

const SECTION_SUMMARIES: Record<
  string,
  (data: ReportAnalysisData) => string
> = {
  S1: (data) => {
    const liquido = getPath(data, "patrimonio.liquido") as number | undefined;
    return liquido
      ? `Patrimônio líquido em ${format(liquido, "brl")}. Composição detalhada abaixo.`
      : "Patrimônio consolidado e estrutura de ativos/passivos.";
  },
  S2: (data) => {
    const receita = getPath(data, "fluxo_caixa.receita_recorrente_mensal") as
      | number
      | undefined;
    return receita
      ? `Receita recorrente de ${format(receita, "brl")}/mês e distribuição de despesas no período.`
      : "Fluxo de caixa e diagnóstico comportamental do período.";
  },
  S3: () => "Carteira de investimentos: alocação atual, alvo e principais ativos.",
  S4: () => "Imóveis e renda passiva — rentabilidade comparada a benchmarks.",
  S7: () => "Independência financeira — projeção de longo prazo em 3 cenários.",
  S8: () => "Estrutura tributária e previdenciária — PGBL, IR e eficiência fiscal.",
  S9: () => "Mapa de riscos e cobertura atual de seguros críticos.",
  S10: (data) => {
    const score = getPath(data, "score.valor") as number | undefined;
    const classe = getPath(data, "score.classificacao") as string | undefined;
    return typeof score === "number"
      ? `Síntese: score ${format(score, "num")} (${classe ?? "—"}). Pontos fortes e urgências consolidados.`
      : "Síntese dos pontos fortes e urgências do ciclo.";
  },
  APP_A: () => "Glossário de termos financeiros e categorias patrimoniais.",
  APP_B: () => "Premissas econômicas e metodologias que fundamentam as projeções.",
  APP_C: () => "Cenários de estresse para validar a margem de segurança do plano.",
  APP_D: () => "Referências metodológicas e lineage dos dados.",
  APP_E: () => "Histórico de ciclos e próximos passos do roadmap.",
};

/**
 * v2.9 · ADR-144 — prefer-snapshot LLM section summaries.
 * v2.8 · ADR-148 — anexa changelog summary quando determinístico.
 *
 * Ordem de precedência (E5 snapshot → fallbacks):
 * 1. `section_summaries[sectionId]` (LLM) tem prioridade absoluta — texto
 *    editorial completo do E5.N.
 * 2. Sem LLM: usa template determinístico + complementa com summary do
 *    `changelog` (ADR-148 builder) se houver para esta seção.
 * 3. Sem nada: fallback do template (ou null).
 */
export function deriveSectionSummary(
  sectionId: string,
  data: ReportAnalysisData,
): string | null {
  const llmText = (data.section_summaries as Record<string, string> | undefined)?.[
    sectionId
  ];
  if (llmText && llmText.trim()) return llmText.trim();
  const base = SECTION_SUMMARIES[sectionId]?.(data) ?? null;
  const changelog = data.changelog ?? null;
  const matched = changelog?.find((entry) => entry.section_id === sectionId);
  if (matched) {
    return base ? `${base} ${matched.summary}.` : `${matched.summary}.`;
  }
  return base;
}

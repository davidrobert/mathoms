/**
 * F9 · ADR-076 · F2.A — Tipos fortes para o E5 JSON por seção.
 *
 * Tipagem progressiva: cada lote (F2.A–F2.H) adiciona tipos fortes
 * para a sua seção. O tipo bruto `ReportAnalysisData` (em api.ts) fica
 * como fallback para chaves ainda não tipadas.
 *
 * Contrato: todas as chaves são opcionais (optional chaining no consumer)
 * pois o E5 JSON pode ter variações entre workspaces e versões.
 */

import type { ChartSeries } from "./chart-series";

// ──────────────────────────────────────────────────────────────────────
// Lote A (S1) — Patrimônio
// ──────────────────────────────────────────────────────────────────────

export interface PatrimonioCaixaDetalhe {
  conta: string;
  moeda: "BRL" | "USD" | "EUR" | string;
  saldo_original: number;
  valor_brl: number;
  tipo: "moeda_nacional" | "moeda_estrangeira" | string;
  /** ADR-238 D5 (A33.l2): "extrato" | "informe_31_12" — informe vence extrato D+1. */
  fonte?: "extrato" | "informe_31_12" | string;
}

/** A33.l2 P4 (co-design product-designer 2026-07-07) — row do card
 * "Posição por instituição e moeda (31/12)" em S1. */
export interface Posicao3112Row {
  instituicao: string;
  moeda: string;
  /** Valor na moeda original — null para contas BRL (sem linha secundária). */
  valor_original: number | null;
  /** Valor convertido a BRL pela PTAX compra 31/12; null quando PTAX ausente. */
  valor_brl: number | null;
  fonte: "informe_31_12" | "extrato" | string;
  /** Data ISO da cotação PTAX usada (footnote). */
  ptax_data: string | null;
  ptax_status: "applied" | "missing" | string | null;
  /** Informe substituiu o saldo do extrato da virada de ano → nudge. */
  informe_venceu_extrato: boolean;
  divergencia_relevante: boolean;
  ano_base: number | null;
  tipo: string;
}

export interface PatrimonioCategoria {
  categoria: string;
  valor: number;
  pct: number;
}

export interface PatrimonioData {
  bruto?: number;
  liquido?: number;
  /** ADR-142 + ADR-215 §6: financeiro puro (cat 3+4+5+6). Sempre presente. */
  investivel_financeiro?: number;
  /** ADR-142 + ADR-215 §6: financeiro + cat_2_efetivo (imóveis geradores líquidos);
   *  igual a investivel_financeiro quando imoveis_no_if=false. */
  investivel_efetivo?: number;
  /** ADR-215 §6: valor bruto de imóveis classificados como locado/comercial. */
  imoveis_geradores?: number;
  /** ADR-215 §6: imóveis classificados como uso pessoal/especulação/desconhecido. */
  imoveis_nao_geradores?: number;
  /** ADR-142: toggle per-workspace para incluir imóveis no cálculo de IF. */
  imoveis_no_if?: boolean;
  dividas?: number;
  residencia?: number;
  imoveis_investimento?: number;
  veiculos?: number;
  investimentos_david?: number;
  investimentos_mariana?: number;
  caixa_moeda_estrangeira?: number;
  fonte_investimentos?: string;
  caixa_detalhes?: PatrimonioCaixaDetalhe[];
  composicao?: PatrimonioCategoria[];
  tabela_categorias?: PatrimonioCategoria[];
  /** A33.l2 P4 — posição por instituição/moeda (informe 31/12 + extrato). */
  posicao_31_12?: Posicao3112Row[];
  /** A33.l2 P5.4 — ativos no exterior ≥ USD 1MM em 31/12 (Res. BCB 279/2022). */
  cbe_obrigatorio?: boolean;
}

// Bloco G — Exposição cambial (plan/RESIDENCIA_E_USO, co-design 2026-05-18).
export interface ExposicaoCambialPorMoeda {
  moeda: string;
  valor_brl: number;
  pct_total_cambial: number;
}

export interface ExposicaoCambialDetalhe {
  fonte?: string;
  nome?: string;
  moeda: string;
  saldo_original?: number;
  valor_brl: number;
  tipo: "caixa" | string;
}

export interface ExposicaoCambialData {
  total_brl: number;
  pct_investivel_financeiro: number;
  por_moeda: ExposicaoCambialPorMoeda[];
  tier: "verde" | "amarelo" | "vermelho" | "empty";
  detalhes: ExposicaoCambialDetalhe[];
}

export interface ReservaEmergenciaData {
  despesas_mensais?: number;
  /** ADR-306 (A28.l4) — rótulo da base de mensalização ("12m" | "full"). */
  janela?: string;
  /** ADR-306 (A28.l4) — meses documentados reais na janela. */
  janela_meses?: number;
  nivel_6_meses?: number;
  nivel_12_meses?: number;
  total_liquida?: number;
  cobertura_meses?: number;
  avaliacao_liquidity?: "Adequada" | "Baixa" | "Excelente" | "Excessiva" | string;
  /** A28.l1 (PR 787) — alvo em meses por perfil de renda (CLT 6 · mista 12 · PJ 18). */
  meses_alvo?: number;
  /** A28.l1 (PR 787) — alvo em R$ (`despesa_essencial × meses_alvo`). */
  alvo_brl?: number;
  /** A28.l1 (PR 787) — gap até o alvo (0 quando reserva ≥ alvo). */
  gap_brl?: number;
  /** A28.l1 (PR 787) — perfil de renda que definiu o alvo (ex.: `pj_dominante`). */
  perfil_renda?: string;
  composicao_liquida?: {
    investimentos_david?: number;
    investimentos_mariana?: number;
    caixa_moeda_estrangeira?: number;
    total_liquido?: number;
    cobertura_meses?: number;
  };
}

export interface EndividamentoData {
  total_dividas?: number;
  percentual_patrimonio?: number;
  dividas?: Array<{
    descricao: string;
    valor: number;
    taxa?: number;
    [key: string]: unknown;
  }>;
  detalhe?: string;
}

/** Track T06 / ADR-191 §D3 — card Rentabilidade aninhado. */
export type RentabilidadeStatus =
  | "ok"
  | "sem_irpf"
  | "gerador_zero"
  | "sem_dados_essencial"
  // A28.l2 — guardrail E5: TRS acima do plausível (> ~8% a.a.); valor
  // presente mas exige "revisar composição" — nunca renderizar sem flag.
  | "suspeito";

// ──────────────────────────────────────────────────────────────────────
// Real Estate (S4 · ADR-216 · Onda 2)
//
// Payload determinístico produzido por
// pipeline/domain/services/real_estate_metrics.py + real_estate_adapter.
// ADR-209: campos *_pct são percentuais absolutos (1.7 = 1,7%).
// ──────────────────────────────────────────────────────────────────────

export type RealEstateOrigemFonte =
  | "informe"
  | "irpf"
  | "e3"
  | "e4"
  | "manual"
  | "pro_rata"
  | "none"
  | "default";

export type RealEstateConfidence = "high" | "medium" | "low";

export type RealEstateStatusContrato =
  | "atualizado"
  | "reajuste_pendente"
  | "sem_renda"
  | "desconhecido";

export type RealEstateAlertaCode =
  | "concentracao_alta"
  | "spread_critico"
  | "aluguel_sem_dado"
  | "contrato_reajuste_pendente";

export interface RealEstateComponenteCalculo {
  readonly valor: number;
  readonly origem: RealEstateOrigemFonte;
  readonly confidence: RealEstateConfidence;
}

export interface RealEstateBenchmarks {
  readonly cdi_liquido_pct: number;
  readonly ntnb_liquido_pct: number;
  readonly ifix_yield_pct: number;
  readonly as_of_date: string;
}

export interface RealEstateImovel {
  readonly property_id: string;
  readonly descricao: string;
  readonly classification: "locado" | "comercial" | "especulacao";
  readonly valor_imovel: number;
  readonly valor_imovel_origem: "irpf" | "mercado";
  readonly aluguel_mensal_bruto: number | null;
  readonly taxa_administracao_mensal: number | null;
  readonly iptu_mensal: number | null;
  readonly condominio_mensal: number | null;
  readonly ir_retido_mensal: number;
  readonly meses_locado_no_ano: number | null;
  readonly vacancia_pct_empirica: number | null;
  readonly cap_rate_bruto_pct: number | null;
  readonly cap_rate_liquido_pct: number | null;
  readonly gap_reajuste_pct: number | null;
  readonly status_contrato: RealEstateStatusContrato;
  readonly indice_reajuste: string | null;
  readonly data_ultimo_reajuste: string | null;
  readonly endereco_canonical: string | null;
  readonly imobiliaria_cnpj: string | null;
  readonly imobiliaria_nome: string | null;
  readonly origem_aluguel: RealEstateOrigemFonte;
}

export interface RealEstateExcludedProperty {
  readonly property_id: string;
  readonly descricao: string;
  readonly classification: string;
  readonly motivo: string;
}

export interface RealEstateAlerta {
  readonly code: RealEstateAlertaCode;
  readonly severity: "info" | "warning" | "critical";
  readonly context: string;
}

export interface RealEstateSpreads {
  readonly vs_cdi: number;
  readonly vs_ntnb: number;
  readonly vs_ifix: number;
}

export interface RealEstateData {
  readonly cap_rate_liquido_pct: number | null;
  readonly cap_rate_bruto_pct: number | null;
  readonly componentes_calculo: Readonly<
    Record<string, RealEstateComponenteCalculo>
  >;
  readonly benchmarks: RealEstateBenchmarks;
  readonly spreads_pp: RealEstateSpreads;
  readonly spread_brl_anual: RealEstateSpreads;
  readonly concentracao_pct: number;
  readonly valor_total_imoveis: number;
  readonly imoveis: readonly RealEstateImovel[];
  readonly excluded_properties: readonly RealEstateExcludedProperty[];
  readonly alertas: readonly RealEstateAlerta[];
}

/** A33.l4 (ADR-238 §L4) — renda de proventos por (ticker, ano_base) do E5
 * `proventos_por_ativo`. `renda_liquida_brl` = total − IR retido (numerador
 * dos dois yields); yields `null` quando o denominador não veio no informe. */
export interface ProventosAtivoData {
  readonly ticker: string;
  readonly ano_base: number;
  readonly total_proventos_brl: number;
  readonly ir_retido_brl: number;
  readonly renda_liquida_brl: number;
  readonly custo_total_brl: number | null;
  readonly valor_mercado_brl: number | null;
  readonly yield_on_cost_pct: number | null;
  readonly yield_on_market_pct: number | null;
}

export interface RentabilidadeRatio {
  valor_pct: number | null;
  ano_base: number | null;
  defasagem_meses: number | null;
  meta_pct: number;
  cobertura_despesa_essencial_pct: number | null;
  status: RentabilidadeStatus;
}

export interface RatiosData {
  taxa_poupanca_recorrente_pct?: number;
  taxa_poupanca_total_pct?: number;
  taxa_endividamento_pct?: number;
  cobertura_despesas_meses?: number;
  rentabilidade_pct?: number | string;
  aliquota_efetiva_ir_pct?: number | string;
  janela_referencia?: string;
  janela_n_meses?: number;
  /** Track T06 — shape aninhado preferido. `null` quando passive_income é omitido (caller). */
  rentabilidade?: RentabilidadeRatio | null;
}

export interface ScoreComponente {
  nome: string;
  valor: number | string;
  peso: number;
  nota: number;
}

export interface ScoreBreakdownEntry {
  dimensao: string;
  valor: number;
  max?: number;
  peso?: number;
  contribuicao?: number;
}

export interface ScoreData {
  valor: number;
  max: number;
  classificacao?: string;
  componentes?: ScoreComponente[];
  /** v2.E.7 — alimenta o ScoreCard premium (dimensão/contribuição). */
  breakdown?: ScoreBreakdownEntry[];
  /** v2.E.7 — fórmula textual exibida no rodapé do ScoreCard. */
  formula?: string;
  /** v2.E.7 — parágrafo `chart-context` (acima do gauge). */
  context?: string;
  /** v2.E.7 — parágrafo `chart-conclusion` (abaixo do breakdown). */
  conclusion?: string;
}

// Receitas (vive em fluxo_caixa, necessário no card de receitas de S1)
export interface FluxoPorFonte {
  outras_receitas?: number;
  receita_investimento?: number;
  receita_pj?: number;
  receita_clt?: number;
  receita_aluguel?: number;
  [key: string]: number | undefined;
}

export interface FluxoCaixaSummary {
  receita_total?: number;
  receita_recorrente?: number;
  receita_one_time?: number;
  receita_recorrente_mensal?: number;
  despesa_total?: number;
  despesa_mensal_media?: number;
  fluxo_liquido?: number;
  por_fonte?: FluxoPorFonte;
  por_fonte_detalhado?: Record<string, number>;
  despesas_por_categoria?: Record<string, number>;
  tabela_receitas?: Array<{ categoria: string; valor: number; pct: number }>;
  receita_despesa_mensal_detalhado?: {
    labels?: string[];
    totais_receita?: number[];
    totais_despesa?: number[];
    /** Onda v2.E.2 — séries por sub-fonte de receita (1 dataset por origem). */
    receita_datasets?: ChartSeries[];
    /** Onda v2.E.2 — séries por sub-categoria de despesa (1 dataset por categoria). */
    despesa_datasets?: ChartSeries[];
  };
}

export type { ChartSeries } from "./chart-series";

// ──────────────────────────────────────────────────────────────────────
// Lote B (S2) — Fluxo de Caixa
// ──────────────────────────────────────────────────────────────────────

export interface OrcamentoProspectivoData {
  categorias?: Record<string, number>;
  total?: number;
  media_mensal?: number;
  legenda?: string;
}

export interface ConsumoConscienteData {
  itens?: Array<{
    descricao: string;
    conta_cartao?: string;
    data?: string;
    mes?: string;
    valor?: number;
    [key: string]: unknown;
  }>;
  total_pontuais?: number;
  equivalente_meses_aporte?: number;
  folga_mensal?: number;
  folga_pct?: number;
  teto_sugerido?: number;
  analise?: string;
}

export interface DiagnosticoComportamental {
  padrao: string;
  evidencia?: string;
  mudanca_sugerida?: string;
}

export interface EquilibrioCerbasiData {
  pct_presente?: number;
  pct_futuro?: number;
  classificacao?: string;
  presente?: string;
  futuro?: string;
}

/** Type guard defensivo. */
export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

// ──────────────────────────────────────────────────────────────────────
// Fase 6 — campos opcionais para alimentar primitives Fase 3.
//
// Os tipos abaixo representam o SHAPE que o E5 produzirá quando estender
// os services. Por ora, consumers (seções migradas em Fase 7-9) usam os
// adapters em frontend/src/components/report/utils/* para derivar
// estes shapes do snapshot atual (determinístico onde possível,
// placeholders onde depende de LLM — ver ADR-122).
// ──────────────────────────────────────────────────────────────────────

/** Score completo (ADR-117/122). `formula` é novo campo Fase 6. */
export interface ScoreFullData extends ScoreData {
  formula?: string;
  /** Breakdown em shape tipado usado pelo ScoreCard primitivo. */
  breakdown?: Array<{
    dimensao: string;
    valor: number;
    max?: number;
    peso?: number;
    contribuicao?: number;
  }>;
}

/** Meta IF (independência financeira) — ADR-117 GAPS Tabela C #5-8. */
export interface MetaIfData {
  progresso_pct?: number;       // 0..100+ (percentual absoluto — ADR-209)
  gap_mensal?: number;          // R$
  ano_alvo?: number;            // 2041
  renda_passiva_alvo?: number;  // R$/mês
}

/** Strip de 5 KPIs na seção de projeção (S7). */
export interface ProjecaoKpiStrip {
  items?: Array<{
    label: string;
    value: string;
    tone?: "default" | "gap" | "meta" | "year";
    progress?: number;
  }>;
}

/** Meta de capa (ADR-117 GAPS Tabela C #17). */
export interface CoverMetaItem {
  readonly label: string;
  readonly value: string | number;
}

/** Dicionários textuais híbridos (ADR-122). Fase 6 entrega versão
 *  derivada frontend-side; LLM fallback fica para revisão Q11. */
export type ChartConclusions = Record<string, string>;
export type SectionSummaries = Record<string, string>;

// ──────────────────────────────────────────────────────────────────────
// Aportes e Investimentos (dashboard)
//
// Shape espelha o `dashboard.aportes` + `dashboard.investimentos_delta`
// produzidos pelo E5. Determinístico; nenhum campo novo no pipeline.
// Originalmente consumido pelo Tático T2 (removido em ADR-149); agora
// vive em `/plano` (seção "Mês corrente", ex-/dashboard absorvido em ADR-155).
// ──────────────────────────────────────────────────────────────────────

/** Item de aporte planejado/executado por destino (CDB, Tesouro, ETF…). */
export interface AporteItem {
  readonly label: string;
  readonly feito: boolean;
  readonly valor_meta: number;
  readonly valor_feito?: number;
}

/** Variação patrimonial por bloco (Investimentos David, Mariana, USD…). */
export interface InvestimentoDeltaItem {
  readonly label: string;
  readonly anterior: number;
  readonly atual: number;
}

/** Subset tipado do `dashboard` (endpoint /v1/dashboard) consumido pelo `/plano` (seção "Mês corrente") e
 * de aportes/investimentos. Mantém-se aberto via `[key: string]: unknown`
 * porque o E5 ainda emite chaves não cobertas (proximos_15d, alertas,
 * tarefas, notas) — Direção E moverá esses para /acao via Onda 4+. */
export interface DashboardData {
  readonly aportes?: Record<string, AporteItem>;
  readonly investimentos_delta?: Record<string, InvestimentoDeltaItem>;
  readonly [key: string]: unknown;
}

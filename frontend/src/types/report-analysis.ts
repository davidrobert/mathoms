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

// ──────────────────────────────────────────────────────────────────────
// Lote A (S1) — Patrimônio
// ──────────────────────────────────────────────────────────────────────

export interface PatrimonioCaixaConversao {
  taxa: string | null;
  taxa_data: string | null;
  taxa_fonte:
    | "ptax_31_12"
    | "market_rate_corrente"
    | "default_hardcoded"
    | "irpf_ja_em_brl"
    | null;
  status: "converted" | "identity" | "missing_rate";
}

export interface PatrimonioCaixaDetalhe {
  conta: string;
  moeda: "BRL" | "USD" | "EUR" | string;
  saldo_original: number;
  valor_brl: number;
  tipo:
    "moeda_nacional" | "moeda_estrangeira" | "moeda_estrangeira_irpf" | string;
  /** ADR-238 D5 (A33.l2): "extrato" | "informe_31_12" — informe vence extrato D+1. */
  fonte?: "extrato" | "informe_31_12" | string;
  /** ADR-390 — carimbo da conversão; ausência = artefato pré-390. */
  conversao?: PatrimonioCaixaConversao;
}

import type { Posicao3112Row } from "./posicao-31-12";

export type { Posicao3112Row };

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
  investimentos_titular?: number; // ADR-338: role-keyed (nome só em valores)
  investimentos_conjuge?: number;
  caixa_total_brl?: number; // CTO-02: caixa TOTAL (BRL+ME); alias legado removido (CTO-08)
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
  avaliacao_liquidity?:
    "Adequada" | "Baixa" | "Excelente" | "Excessiva" | string;
  /** A28.l1 (PR 787) — alvo em meses por perfil de renda (CLT 6 · mista 12 · PJ 18). */
  meses_alvo?: number;
  /** A28.l1 (PR 787) — alvo em R$ (`despesa_essencial × meses_alvo`). */
  alvo_brl?: number;
  /** A28.l1 (PR 787) — gap até o alvo (0 quando reserva ≥ alvo). */
  gap_brl?: number;
  /** A28.l1 (PR 787) — perfil de renda que definiu o alvo (ex.: `pj_dominante`). */
  perfil_renda?: string;
  composicao_liquida?: {
    investimentos_titular?: number; // ADR-338: role-keyed
    investimentos_conjuge?: number;
    caixa?: number;
    caixa_moeda_estrangeira?: number;
    total_liquido?: number;
    cobertura_meses?: number;
  };
  /** A40.l47 PR3 (RV4-18) — qual base o denominador da cobertura usa. */
  base_denominador?: string;
  /** A40.l47 PR3 — despesa essencial mensal, base quando `base_denominador` é essencial. */
  custo_essencial_mensal?: number;
  /** A40.l47 PR3 (RV4-18) — o que a base da reserva deixou de fora. */
  excluido_da_reserva?: {
    investimentos_nao_liquidos?: number;
    caixa_moeda_estrangeira?: number;
    caixa_nao_classificado?: number;
  };
}

export interface EndividamentoData {
  total_dividas?: number;
  percentual_patrimonio?: number;
  /**
   * Espelha `endividamento.properties.dividas.items` de
   * `config/schemas/e5_analysis.schema.json` — nomes do PRODUTOR
   * (`EndividamentoAnalyzer.to_legacy_dict`), não apelidos.
   *
   * RV3-09/RV3-12 (A40.l5): declarava `valor`/`taxa`, que produtor nenhum
   * emite, e o `[key: string]: unknown` fazia o `tsc` aceitar em silêncio —
   * a tabela de dívidas renderizava valor vazio e taxa "—" para todo cliente.
   * **Não reintroduza a index signature aqui**: é ela, não o arquivo ser
   * escrito à mão, que desliga o gate de consumo neste bloco.
   */
  dividas?: Array<{
    divida_id?: string | null;
    descricao: string;
    membro?: string | null;
    tipo?:
      | "financiamento_imobiliario"
      | "financiamento_veiculo"
      | "consignado"
      | "emprestimo_pessoal"
      | "cheque_especial"
      | "cartao_credito"
      | "credito_rotativo"
      | "outros"
      | null;
    saldo_devedor: number;
    saldo_ano_referencia?: number | null;
    parcela_mensal?: number | null;
    /**
     * Percentual absoluto AO ANO (ADR-401). O sufixo `_aa` é load-bearing:
     * 12,5% a.m. e 12,5% a.a. levam a decisões opostas, e o card renderizava
     * `%` nu. Renomeado de `taxa_juros`, que nenhum leitor jamais viu com
     * valor (null em r5/r6/r7).
     */
    taxa_juros_aa?: number | null;
    desembolso_mensal_observado_brl?: number | null;
    /** Origem declarada por campo — presente ⟺ o campo homônimo não é null. */
    fontes: {
      saldo_devedor: "baseline_irpf" | "declarado";
      parcela_mensal?: "declarado";
      taxa_juros_aa?: "declarado";
      desembolso_mensal_observado_brl?: "observado_e4";
    };
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

// Bloco `real_estate` — tipos extraídos para ./report-real-estate (RV6-15,
// gate T2 de tamanho de arquivo). Re-exportados aqui: import site não muda.
export type {
  RealEstateOrigemFonte,
  RealEstateConfidence,
  RealEstateStatusContrato,
  RealEstateAlertaCode,
  RealEstateComponenteCalculo,
  RealEstateBenchmarks,
  RealEstateImovel,
  RealEstateExcludedProperty,
  RealEstateAlerta,
  RealEstateSpreads,
  RealEstateData,
} from "./report-real-estate";

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
  cobertura_despesa_essencial_pct: number | null;
  status: RentabilidadeStatus;
}

export interface RatiosData {
  taxa_poupanca_recorrente_pct?: number;
  taxa_poupanca_total_pct?: number;
  taxa_endividamento_pct?: number;
  /** ADR-335: runway financeiro (sem imóvel ilíquido). `cobertura_despesas_meses` = alias deprecated por 1 ciclo. */
  autonomia_financeira_meses?: number;
  cobertura_despesas_meses?: number;
  rentabilidade_pct?: number | string;
  aliquota_efetiva_ir_pct?: number | string;
  /** ADR-306 D2 — vocabulário fechado da base (`12m` | `full` | `irpf_<ano>`).
   * **Não confundir com `janela_referencia`**, que é string de PERÍODO
   * ("2026-01 a 2026-01", `ratios_calculator.py`): passar `janela_referencia`
   * a um formatador de rótulo funciona na fixture e quebra em produção. */
  janela?: string;
  janela_meses?: number;
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

// Bloco `fluxo_caixa` — tipos extraídos para ./report-fluxo (A40.l3, gate T2
// de tamanho de arquivo). Re-exportados aqui: import site não muda.
export type {
  FluxoPorFonte,
  FluxoJanela12m,
  FluxoPeriodoInterativo,
  FluxoReceitaMensalRow,
  FluxoNaturezaMensalRow,
  FluxoConsumoMensalRow,
  FluxoJanelaInterativa,
  FluxoJanelas,
  FluxoCaixaSummary,
} from "./report-fluxo";

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

/** Um balde da base do gasto pontual. `pct` **não é campo** ([[ADR-425]] §D2) e
 * o card **não o deriva** — imprime absolutos. Quando alguém precisar dele, a
 * razão é `publicado / (publicado + excluidos.nao_identificado)`: `recorrente` e
 * `transferencia_*` não entram no denominador, porque são exclusão deliberada e
 * não falha de medição. */
export interface BaldePontual {
  valor: number;
  contagem: number;
}

/** A40.l98 ([[ADR-425]] §D2) — o que a base do gasto pontual exclui, **por
 * causa**, declarado na superfície que a publica. Existiam três produtores de
 * "gasto pontual" com filtros disjuntos e nenhum declarava o próprio.
 *
 * Invariante: `bruto.valor === publicado.valor + Σ excluidos[].valor`. */
/** Vereditos que EXCLUEM. `incluido` não aparece aqui de propósito: ele é o
 * `publicado`, não um balde de exclusão. */
export type VeredictoExcluido =
  "recorrente" | "transferencia_por_categoria" | "transferencia_detectada";

export interface BasePontuais {
  bruto: BaldePontual;
  publicado: BaldePontual;
  /** Chave = veredito de `GastoPontualPolicy.classify` (enum fechado no Python,
   * espelhado no schema). Balde ausente = nenhum lançamento caiu nessa causa —
   * o leitor omite a causa em vez de imprimir zero. */
  excluidos: Partial<Record<VeredictoExcluido, BaldePontual>>;
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
  /** ADR-306 (A40.l3) — total de pontuais **dentro da janela**. Desde a
   * [[ADR-422]] ele NÃO entra em `folga_mensal` (que é
   * `receita_recorrente_mensal − despesa_consumo_mensal`): é o **numerador** de
   * `equivalente_meses_poupanca`. **Não é renderizado** — o card imprime
   * `total_pontuais` (full) ao lado do equivalente, logo o leitor NÃO consegue
   * reproduzir esse KPI hoje. Exibi-lo é a lane A40.l15. */
  total_pontuais_janela?: number;
  /** A40.l98 — o que a base exclui, por causa. Lido pelo
   * `ConsumoConscienteCard`; ausente em payload anterior à lane. */
  base_pontuais?: BasePontuais;
  /** ADR-306 D2 — rótulo da janela ("12m" | "full"). */
  janela?: string;
  janela_meses?: number;
  /** [[ADR-422]] — `total_pontuais_janela` ÷ folga mensal publicada: numerador
   * e denominador na MESMA janela. **`null` fora do domínio de definição**
   * (folga publicada não-positiva) — ver `motivo_supressao`; `0.0` significa
   * apenas "nenhum gasto pontual relevante" (A40.l101). */
  equivalente_meses_poupanca?: number | null;
  folga_mensal?: number;
  /** A40.l101 — `null` sem receita recorrente na janela; `0.0` afirmava
   * "empatou" para quem queimou caixa. */
  folga_pct?: number | null;
  analise?: string;
  /** A40.l101 — por que `equivalente_meses_poupanca` saiu nulo (`null` = não
   * suprimido). Forma `<causa_slug>: <detalhe>` ([[ADR-394]] §D7). A copy que a
   * família lê vive na prosa `analise`; este campo é de máquina/LLM. */
  motivo_supressao?: string | null;
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
  progresso_pct?: number; // 0..100+ (percentual absoluto — ADR-209)
  gap_mensal?: number; // R$
  ano_alvo?: number; // 2041
  renda_passiva_alvo?: number; // R$/mês
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

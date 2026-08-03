import type { ScoreData } from "@/types/report-analysis";
import { API_BASE, apiFetch } from "./core";

// ─── Report Types ───

export interface ReportResponse {
  id: string;
  workspace_id: string;
  title: string;
  period: string | null;
  score: number | null;
  patrimonio_liquido: number | null;
  created_at: string;
  /** F11.4a — execução do pipeline que gerou o snapshot (se houver). */
  pipeline_run_id: string | null;
  /** F11.4a — documentos prontos no workspace (agregado; IDs truncados no backend). */
  source_document_count: number;
  source_document_ids: string[];
  /** Documentos efetivamente extraídos pela run (DISTINCT document_id em pipeline_artifacts). */
  consumed_document_count: number;
  consumed_document_ids: string[];
  /** F9 · ADR-076 · ADR-131 — true se o relatório tem JSON de análise (FK ao pipeline_artifact) p/ render nativo. */
  has_analysis_data: boolean;
  /** F11.6b — snapshot de premissas (hash goals.json + metas ativas) na geração. */
  premissas_snapshot?: Record<string, unknown> | null;
  /** v2.F.3 — sobrenome da família (do workspace) para badge/cover. Pode vir
   * `null` quando o workspace não definiu sobrenome ou pré v2.F.3a. */
  workspace_family_surname?: string | null;
}

export interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
}

/** v3 (ADR-190 §Emenda 2026-07-09) — unidade de exibição da métrica:
 * `pp`/`meses` formatam Δ absoluto (after−before); `brl` usa MonetaryValue. */
export type ComparisonMetricUnit = "brl" | "pp" | "meses";

/** v2.8 (ADR-148) — Item de comparação seção-a-seção entre relatórios.
 *
 * `direction_positive` (W2 · ADR-190 D3): direção "boa pro usuário" — a cor
 * da célula Δ inverte quando `delta_signal !== direction_positive`. Optional
 * para tolerar payload de backend pré-W2 (default "up" preserva comportamento).
 * `unit` (v3): optional para tolerar payload pré-v3 (default "brl"). */
export interface ComparisonItemRead {
  section_id: string;
  section_label: string;
  before: number;
  after: number;
  delta_pct: number | null;
  delta_signal: "up" | "down" | "stable";
  direction_positive?: "up" | "down";
  unit?: ComparisonMetricUnit;
}

/** v3 (ADR-190 §Emenda) — períodos yyyymm do par comparado; `null` no
 * primeiro relatório (moldura temporal da seção V0). */
export interface ComparisonPeriodsRead {
  current: string;
  previous: string;
}

/** v2.8 (ADR-148) — Entrada do changelog determinístico (uma por seção). */
export interface ChangelogEntryRead {
  section_id: string;
  summary: string;
  delta_signal: "up" | "down" | "stable";
  delta_pct: number | null;
}

/** F9 · ADR-076 — payload do GET /reports/{id}/data.
 *
 * Tipagem progressiva: as 24 chaves top-level do E5 JSON serão tipadas
 * fortemente conforme as seções forem migradas nos lotes 2.A–2.H. Nesta
 * fase (F0.5) expomos shape parcial + fallback `Record<string, unknown>`.
 */
export interface ReportAnalysisData {
  /** v2.8 (ADR-148) — comparativos seção-a-seção. `null` no primeiro relatório. */
  comparisons?: ComparisonItemRead[] | null;
  /** v2.8 (ADR-148) — changelog determinístico. Permanece no wire, mas a UI
   * não o consome desde a V0 (SNAPSHOT_CHANGELOG_V3 W4-T07). */
  changelog?: ChangelogEntryRead[] | null;
  /** v3 (ADR-190 §Emenda) — períodos reais do par comparado. `null` no primeiro relatório. */
  comparison_periods?: ComparisonPeriodsRead | null;
  /** F11.4a — injetado pelo GET /reports/{id}/data (não faz parte do E5 legado). */
  _report_lineage?: {
    pipeline_run_id: string | null;
    source_document_count: number;
    source_document_ids: string[];
    consumed_document_count: number;
    consumed_document_ids: string[];
  };
  /** ADR-279 · A25.l5 — bloco `_lineage` field-level do E5. Tipado de
   * propósito SÓ com o subset que a UI consome (label/edge_type/signals);
   * member_hashes/inputs/rule_ref existem no wire mas são proibidos na UI
   * cliente (lista negra do popover N2). */
  _lineage?: {
    lineage_version: string;
    fields: Record<
      string,
      {
        label?: string;
        edge_type?: string;
        signals?: Record<string, string>;
      }
    >;
  };
  periodo_dados?: string;
  data_analise?: string;
  patrimonio?: Record<string, unknown>;
  goals?: Record<string, unknown>;
  fluxo_caixa?: Record<string, unknown>;
  ratios?: Record<string, unknown>;
  /** v2.E.7 — score top-level tipado (absorve v2.5; elimina o cast inline em S1). */
  score?: ScoreData;
  orcamento_prospectivo?: Record<string, unknown>;
  reserva_emergencia?: Record<string, unknown>;
  endividamento?: Record<string, unknown>;
  previdencia_pgbl?: Record<string, unknown>;
  pontos_fortes?: unknown[];
  pontos_urgentes?: unknown[];
  tarefas?: unknown[];
  diagnostico_comportamental?: unknown[];
  tarefas_status?: Record<string, unknown>;
  investimentos?: Record<string, unknown>;
  equilibrio_cerbasi?: Record<string, unknown>;
  /** ADR-166 (A8.4): chave estável universal. Bloco populado quando o gate
   *  `should_render_conjuge_scenarios` (ADR-167) retorna True. */
  cenarios_conjuge?: Record<string, unknown>;
  programa_milhas?: Record<string, unknown>;
  alertas?: unknown[];
  consumo_consciente?: Record<string, unknown>;
  narrativas?: Record<string, unknown>;
  /** v2.9 · ADR-144 — LLM-driven section summaries (id → texto). */
  section_summaries?: Record<string, string>;
  review_metadata?: Record<string, unknown>;
  /** ADR-157 — KPIs IRPF (renda, alíquota, PGBL, split trabalho×capital, evolução).
   *  Ausente quando o workspace não tem declaração IRPF processada. */
  irpf_kpis?: Record<string, unknown>;
  /** A8.3 — TRS efetiva e carteira de renda. Sempre presente; ``status``
   * controla render (ok = KPIs · sem_irpf | gerador_zero = empty state). */
  passive_income?: PassiveIncomeData;
  /** Onda 2 · ADR-216 — cap rate líquido + tríade benchmarks + tabela por imóvel.
   *  Ausente quando workspace não tem property_identity (UI oculta S4). */
  real_estate?: import("@/types/report-analysis").RealEstateData | null;
  /** A33.l4 (ADR-238 §L4) — renda de proventos por ativo (informes
   *  proventos_acoes). Ausente quando workspace não tem informe (UI oculta o card). */
  proventos_por_ativo?: readonly import("@/types/report-analysis").ProventosAtivoData[];
  /** N3 — Monte Carlo IF com cone P10/P50/P90. Presente quando workspace
   * tem meta IF configurada. ``exibir_cone`` controla se o chart aparece. */
  if_monte_carlo?: IFMonteCarloData;
  /** ADR-219 wave 2 — snapshot das premissas econômicas vigentes na data do
   *  run (auditoria fiduciária). Ausente em runs antigos pré-ADR-219;
   *  UI degrada com empty state. */
  premissas_economicas?: PremissasEconomicasData;
  /** ADR-236 §D5 — bundle tributário PJ (cascata fiscal calculada).
   *  Ausente quando workspace não tem `business_profile_json` ou pipeline
   *  pré-A16 L2 P5. UI renderiza estado "perfil pendente" se ausente. */
  tributario?: TributarioBundle;
  /** ADR-240 D8 (A19 L1) — bloco S_PROTECAO 4º pilar AUVP. Ausente quando
   *  workspace não tem apólices ingeridas (UI oculta seção). */
  protecao_patrimonial?: import("@/types/protecao").ProtecaoPatrimonialData | null;
  // Extensibilidade para chaves ainda não tipadas
  [key: string]: unknown;
}

/** ADR-236 §D6 — Decision trigger T1-T5 com break-even computado. */
export interface CascataTrigger {
  code: "T1" | "T2" | "T3" | "T4" | "T5";
  severity: "oportunidade" | "atencao" | "considere";
  title: string;
  /** Valores monetários como string Decimal (ADR-090). */
  params: Record<string, string>;
}

/** ADR-236 §D3 — Cascata calculada (todos os valores anuais em BRL float). */
export interface CascataPayload {
  regime: "mei" | "simples" | "lucro_presumido" | "lucro_real" | null;
  regime_label: string;
  regime_nao_suportado: boolean;
  motivo_nao_suportado: "lucro_real" | "perfil_incompleto" | "anexo_simples_pendente" | null;
  receita_bruta: number;
  tributos_federais: number;
  iss_total: number;
  lucro_contabil_pj: number;
  pro_labore_bruto: number;
  inss_patronal: number;
  inss_empregado: number;
  irrf_pro_labore: number;
  lucros_distribuidos: number;
  renda_pf_tributavel_total: number;
  /** Fração (0.183 = 18,3%). */
  carga_total_pct: number;
  pgbl_base_anual: number;
  pgbl_limite_anual: number;
  pgbl_aplicavel: boolean;
  pgbl_motivo_inaplicavel: "declaracao_simplificada" | "renda_tributavel_pf_zerada" | null;
  /** Fração (0.32 = 32%). Apenas em regime=simples. */
  fator_r_pct: number | null;
  fator_r_faixa: "anexo_iii" | "anexo_v" | null;
  fator_r_break_even_mensal: number | null;
  triggers: CascataTrigger[];
}

/** ADR-236 §D4 — Bundle exposto no E5 output. */
export interface TributarioBundle {
  regime: "mei" | "simples" | "lucro_presumido" | "lucro_real" | null;
  regime_label: string;
  cascata: CascataPayload;
  contador_nome: string | null;
  holding_prazo_meses: number | null;
  _source?: string;
}

/** ADR-219 — Premissas econômicas auditáveis snapshotadas no payload E5.
 *
 *  Status ``parcial`` quando pelo menos uma classe está ``indisponivel``
 *  (sem premissa vigente). Valores em string (Decimal no wire, ADR-090).
 */
export interface PremissasEconomicasData {
  status: "completo" | "parcial";
  snapshot_at: string;
  classes: PremissasEconomicasClassRow[];
}

export interface PremissasEconomicasClassRow {
  classe_auvp: string;
  status: "emitted" | "indisponivel";
  retorno_real_esperado_pct_anual: string | null;
  sigma_anual_pct: string | null;
  fonte: string | null;
  fonte_origem: "global" | "workspace_override" | null;
  effective_from: string | null;
  justificativa: string | null;
  razao_indisponivel: string | null;
}

/** N3 — Monte Carlo IF: cone de probabilidade P10/P50/P90.
 *
 * ``exibir_cone`` false → mostrar apenas ``motivo_sem_cone`` (se presente).
 * ``caminho_p*`` são séries [ano_absoluto, valor_brl] para o Chart.js. */
export interface IFMonteCarloData {
  /** ADR-361 — quantil da BASE CHEIA, com censura à direita: `null` quando a
   * taxa de sucesso no horizonte não sustenta o percentil. `pXX_censurado`
   * distingue essa censura de "cone não simulado" (`exibir_cone: false`), e só
   * é significativo com `exibir_cone: true`. Atenção: `p10_ano_if` é o ano mais
   * CEDO (cenário favorável), enquanto `caminho_p10` é o patrimônio mais BAIXO
   * (cenário adverso) — o sufixo `p10` aponta para lados opostos nos dois. */
  p10_ano_if: number | null;
  p10_censurado?: boolean;
  p50_ano_if: number | null;
  p50_censurado?: boolean;
  p90_ano_if: number | null;
  p90_censurado?: boolean;
  /** `null` quando a projeção determinística não produziu idade-meta: sem
   * alvo não há "probabilidade até a idade X". O cone independe dos dois. */
  prob_if_ate_idade_meta: number | null;
  /** Taxa de sucesso no horizonte simulado (base cheia) — decide a censura. */
  prob_if_ate_horizonte?: number;
  idade_meta_usada: number | null;
  sigma_usado: number;
  exibir_cone: boolean;
  /** ADR-237 — PMT mensal real assumido na simulação (R$/mês de hoje). */
  aporte_mensal_usado?: number;
  motivo_sem_cone: string | null;
  caminho_p10: [number, number][];
  caminho_p50: [number, number][];
  caminho_p90: [number, number][];
  horizonte_anos?: number;
}

/** A8.3 — TRS efetiva, renda passiva observada e carteira de renda.
 *
 * Renderizado em S7. ``status`` decide o caminho da UI:
 * - ``ok``: 4 KPIs + caption permanente em acumulação + banners condicionais.
 * - ``sem_irpf``: empty state com CTA "Importar IRPF".
 * - ``gerador_zero``: empty state explicando que TRS exige patrimônio investido. */
export interface PassiveIncomeData {
  status: "ok" | "sem_irpf" | "gerador_zero";
  renda_passiva_anual_brl: number;
  renda_passiva_mensal_brl: number;
  /** A37.l7 PR-2 — dict auto-conservativo: Σ(fontes) == renda_passiva_anual_brl.
   * Payloads pré-PR-2 ainda carregam ganho_capital/distribuicao_pj_titular dentro
   * do dict (ignorados pela UI). */
  renda_passiva_por_fonte_brl: {
    dividendos: number;
    jcp: number;
    aplicacoes: number;
    exterior: number;
    alugueis: number;
  };
  /** A28.l2 (ADR-191) — distribuição de lucros da PJ do titular ≈ renda de
   * trabalho: FORA da TRS (não soma em renda_passiva_anual_brl). Ausente em
   * payloads pré-A37.l7 PR-2. */
  renda_ativa_pj_excluida_brl?: number;
  /** ADR-336 — ganho de capital (realização one-time, não yield recorrente):
   * FORA da TRS. Ausente em payloads pré-A37.l7 PR-2. */
  ganho_capital_excluido_brl?: number;
  patrimonio_gerador_brl: number;
  trs_efetiva_pct: number;
  ano_referencia_irpf: number | null;
  defasagem_meses: number | null;
  acumuladores_pct_gerador: number;
}

// ─── Reports ───

export async function listReports(workspaceId: string): Promise<ReportListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports`);
}

export async function getReport(workspaceId: string, reportId: string): Promise<ReportResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}`);
}

/** F9 · F4.2 — URL de download do PDF server-side (Playwright). */
export function getReportDownloadPdfUrl(workspaceId: string, reportId: string): string {
  return `${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/download.pdf`;
}

/** F9 · ADR-076 · ADR-131 — Busca o snapshot E5 JSON para o render nativo.
 *
 * Retorna 404 se o relatório é pré-F9 ou se o artifact foi removido — verifique
 * antes via `ReportResponse.has_analysis_data` para evitar a requisição.
 */
export async function getReportData(workspaceId: string, reportId: string): Promise<ReportAnalysisData> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/data`);
}

// ─── Consumo Pontuais — gastos ≥ R$2k filtrados (transferências internas excluídas no backend) ───

export interface ConsumoPontuaisItem {
  data: string;
  descricao: string;
  valor: number;
  banco: string;
  categoria: string;
  tipo_conta?: string | null;
  titular?: string | null;
  transaction_hash: string;
}

export interface ConsumoPontuaisResponse {
  period: string;
  date_from: string;
  date_to: string;
  items: ConsumoPontuaisItem[];
  total: number;
  total_valor: number;
}

export type ConsumoPontuaisPeriod = "3m" | "6m" | "12m" | "ytd";

export async function getConsumoPontuais(
  workspaceId: string,
  period: ConsumoPontuaisPeriod,
  anchorDate?: string,
): Promise<ConsumoPontuaisResponse> {
  const qs = new URLSearchParams({ period });
  if (anchorDate) qs.set("anchor_date", anchorDate);
  return apiFetch(
    `/workspaces/${workspaceId}/reports/consumo-pontuais?${qs.toString()}`,
  );
}

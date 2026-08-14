import type { E5AnalysisArtifact } from "@/generated/report-analysis";
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
  /** A40.l18 · ADR-357 — desfecho do run, polaridade POSITIVA: só `complete`
   * autoriza o relatório a AFIRMAR que não há pendências. Obrigatório: campo
   * opcional que chegasse `undefined` faria a supressão sumir em silêncio. */
  run_outcome: ReportRunOutcome;
  /** ADR-362 — revisão do executor no stage E5 do run (colofão). `null` =
   * executor não declarou (run pré-ADR-362, purgado) — a UI mostra "—". */
  executor_revision: string | null;
}

/** Desfecho do run sob a ótica do relatório (espelha `ReportRunOutcome` do backend). */
export type ReportRunOutcome = "complete" | "with_gap" | "unknown";

/** O relatório pode afirmar "sem pendências"? Só um run que entregou tudo pode. */
export function mayAssertCleanQuality(outcome: ReportRunOutcome): boolean {
  return outcome === "complete";
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

/** A40.l25 — faceta do bloco de IF que a recalibração moveu.
 *
 * `ano_cone` é comparável (par explícito); `probabilidade_alvo` NÃO é — mudou
 * a pergunta (ADR-369 D2), então o payload não carrega o valor anterior e a
 * copy recusa a comparação em vez de declarar direção.
 */
export type RecalibracaoFaceta =
  | { faceta: "ano_cone"; ano_anterior: number; ano_novo: number }
  | {
      faceta: "probabilidade_alvo";
      prazo_declarado_anos: number | null;
      ano_alvo_declarado: number | null;
    };

/** A40.l25 — nota one-shot de recalibração (ADR-360 §Nota one-shot).
 *
 * Vive no view-model, nunca no artefato E5: a chave de cache do parecer é
 * sha256 sobre o payload E5, e um campo novo lá re-geraria o parecer da frota.
 */
export interface RecalibracaoMcData {
  facetas: RecalibracaoFaceta[];
  periodo_anterior: string | null;
  competencia_mudou: boolean;
}

/** Campos adicionados pelo endpoint depois de carregar o artefato E5. */
export interface ReportEndpointAugmentations {
  /** v2.8 (ADR-148) — comparativos seção-a-seção. `null` no primeiro relatório. */
  comparisons?: ComparisonItemRead[] | null;
  /** v2.8 (ADR-148) — changelog determinístico. Permanece no wire, mas a UI
   * não o consome desde a V0 (SNAPSHOT_CHANGELOG_V3 W4-T07). */
  changelog?: ChangelogEntryRead[] | null;
  /** v3 (ADR-190 §Emenda) — períodos reais do par comparado. `null` no primeiro relatório. */
  comparison_periods?: ComparisonPeriodsRead | null;
  /** A40.l2 §3c2b — os dois lados do par foram consolidados por métodos diferentes; sob
   * `true` a V0 não afirma mérito em nenhuma célula de delta. */
  comparison_base_changed?: boolean | null;
  /** A40.l25 — nota one-shot de recalibração da S7. `null` calа: sem relatório
   * anterior, bloco anterior ilegível, ou nenhuma faceta renderizável. */
  recalibracao_mc?: RecalibracaoMcData | null;
  /** F11.4a — injetado pelo GET /reports/{id}/data (não faz parte do E5 legado). */
  _report_lineage?: {
    pipeline_run_id: string | null;
    source_document_count: number;
    source_document_ids: string[];
    consumed_document_count: number;
    consumed_document_ids: string[];
  };
}

/** ADR-279 — subset de lineage permitido no cliente; hashes e inputs ficam fora. */
export interface ReportLineageData {
  lineage_version: string;
  fields: Record<
    string,
    {
      label?: string;
      edge_type?: string;
      signals?: Record<string, string>;
    }
  >;
}

type E5Goals = NonNullable<E5AnalysisArtifact["goals"]>;
type DeepPartial<T> =
  T extends Array<infer Item>
    ? ReadonlyArray<DeepPartial<Item>>
    : T extends object
      ? { readonly [Key in keyof T]?: DeepPartial<T[Key]> }
      : T;

interface LegacyFluxoFields {
  readonly por_fonte?: Readonly<Record<string, number | undefined>>;
  readonly despesas_por_categoria?: Readonly<Record<string, number>>;
  readonly receita_despesa_mensal_detalhado?: {
    readonly labels?: readonly string[];
    readonly totais_receita?: readonly number[];
    readonly totais_despesa?: readonly number[];
  };
}

type GeneratedReadSnapshot = DeepPartial<
  Omit<E5AnalysisArtifact, "_lineage" | "goals">
>;
type HistoricalE5Snapshot = Omit<GeneratedReadSnapshot, "fluxo_caixa"> & {
  readonly fluxo_caixa?: GeneratedReadSnapshot["fluxo_caixa"] &
    LegacyFluxoFields;
};

/** GET /reports/{id}/data = snapshot E5 (inclusive legado) + enriquecimentos HTTP. */
export type ReportAnalysisData = HistoricalE5Snapshot &
  ReportEndpointAugmentations & {
    readonly _lineage?: ReportLineageData;
    readonly goals?: DeepPartial<E5Goals> & {
      readonly premissas_snapshot?: Readonly<Record<string, unknown>> | null;
    };
    /** Segundo writer E5n; o schema bruto segue aberto no topo para merges. */
    readonly tributario?: TributarioBundle;
  };

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
  motivo_nao_suportado:
    "lucro_real" | "perfil_incompleto" | "anexo_simples_pendente" | null;
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
  pgbl_motivo_inaplicavel:
    | "declaracao_simplificada"
    | "renda_tributavel_pf_zerada"
    /** ADR-375 D4 cond. 1 — modelo de declaração não registrado. */
    | "tipo_declaracao_desconhecido"
    | null;
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

/** N3 — Monte Carlo IF: cone de cenários (favorável / central / adverso).
 *
 * ``exibir_cone`` false → mostrar apenas ``motivo_sem_cone`` (se presente).
 * ``caminho_p*`` são séries [ano_absoluto, valor_brl] para o Chart.js. */
export interface IFMonteCarloData {
  /** ADR-361 — quantil da BASE CHEIA, com censura à direita: `null` quando a
   * taxa de sucesso no horizonte não sustenta o percentil. O irmão
   * `_censurado` distingue essa censura de "cone não simulado"
   * (`exibir_cone: false`), e só é significativo com `exibir_cone: true`.
   *
   * ADR-369 D1 — o cenário é NOMEADO porque o percentil apontava para lados
   * opostos: `ano_if_cenario_favoravel` é o ano mais CEDO, enquanto
   * `caminho_p10` é o patrimônio mais BAIXO (cenário adverso). As séries
   * mantiveram `pXX` de propósito — ali o número já casa com a legenda.
   *
   * Opcionais porque relatório de artefato stale (`mc_version` < 4.0)
   * legitimamente não os traz — o leitor tem de tolerar a ausência. */
  ano_if_cenario_favoravel?: number | null;
  ano_if_cenario_favoravel_censurado?: boolean;
  ano_if_cenario_central?: number | null;
  ano_if_cenario_central_censurado?: boolean;
  ano_if_cenario_adverso?: number | null;
  ano_if_cenario_adverso_censurado?: boolean;
  /** ADR-369 D2 — P(cumprir o PRAZO QUE A FAMÍLIA DECLAROU), não a idade que o
   * projetor determinístico produziu. `null` nos três estados de ausência
   * (prazo não declarado, prazo vencido, artefato de contrato anterior), sempre
   * com `motivo_sem_prazo_declarado`. Publicar 0% seria correto e inútil. */
  prob_if_ate_prazo_declarado?: number | null;
  prazo_declarado_anos?: number | null;
  /** Ano absoluto do alvo — a data da declaração + o prazo declarado. */
  ano_alvo_declarado?: number | null;
  /** ISO date em que a família declarou o prazo (`Goal.effective_from`). */
  declarado_em?: string | null;
  /** Prazo declarado excede a janela simulada: a probabilidade publicada é a da
   * janela, portanto um PISO — truncar só remove sucessos, nunca adiciona. */
  prazo_declarado_truncado?: boolean;
  motivo_sem_prazo_declarado?: string | null;
  /** Taxa de sucesso na janela SIMULADA (base cheia) — decide a censura. */
  prob_if_ate_horizonte_simulado?: number;
  sigma_usado: number;
  /** A40.l25 — procedência de `sigma_usado`, padrão `fonte_origem` da ADR-219.
   *  `fallback_codigo` = constante do modelo, NÃO calibrada à carteira: a
   *  legenda tem de dizer isso, senão publica precisão que o número não tem.
   *  Opcional para tolerar artefato anterior a #1338. */
  sigma_procedencia?: "global" | "workspace_override" | "fallback_codigo";
  exibir_cone: boolean;
  /** ADR-237 — PMT mensal real assumido na simulação (R$/mês de hoje). */
  aporte_mensal_usado?: number;
  motivo_sem_cone: string | null;
  caminho_p10: [number, number][];
  caminho_p50: [number, number][];
  caminho_p90: [number, number][];
  /** Janela da SIMULAÇÃO (40 anos) — não o prazo declarado pela família. */
  horizonte_simulado_anos?: number;
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

export async function listReports(
  workspaceId: string,
): Promise<ReportListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports`);
}

export async function getReport(
  workspaceId: string,
  reportId: string,
): Promise<ReportResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}`);
}

/** F9 · F4.2 — URL de download do PDF server-side (Playwright). */
export function getReportDownloadPdfUrl(
  workspaceId: string,
  reportId: string,
): string {
  return `${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/download.pdf`;
}

/** F9 · ADR-076 · ADR-131 — Busca o snapshot E5 JSON para o render nativo.
 *
 * Retorna 404 se o relatório é pré-F9 ou se o artifact foi removido — verifique
 * antes via `ReportResponse.has_analysis_data` para evitar a requisição.
 */
export async function getReportData(
  workspaceId: string,
  reportId: string,
): Promise<ReportAnalysisData> {
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

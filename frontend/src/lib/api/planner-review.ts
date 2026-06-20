// ADR-199 / ADR-208 — Parecer do Planejador (E6).
//
// Tipos espelham `backend/app/schemas/dto/planner_review/response.py`. UI
// nunca recebe `ancora_metodologica` (sigilo §13 · ADR-207); só
// `tema_canonico` é exibido.

import { apiFetch } from "./core";

export type Severidade = "Crítica" | "Alta" | "Média" | "Baixa";
export type Prioridade = "P0" | "P1" | "P2";
export type Confianca = "alta" | "media" | "baixa";

export const TEMAS_CANONICOS = [
  "Proteção",
  "Alocação",
  "Renda passiva",
  "Liquidez",
  "Custo tributário",
  "Saúde de balanço",
  "Diagnóstico de dados",
  "Equilíbrio presente-futuro",
  "Convergência metodológica",
] as const;
export type TemaCanonico = (typeof TEMAS_CANONICOS)[number];

export type FrequenciaRevisao = "mensal" | "trimestral" | "semestral" | "anual";
export type UnidadeImpacto = "ano" | "mes";
export type PlannerReviewTier = "free" | "premium";

export type PlannerSectionId =
  | "S1"
  | "S2"
  | "S3"
  | "S4"
  | "S7"
  | "S8"
  | "S_IRPF_RENDA"
  | "S_IRPF_OTIMIZACAO"
  | "S9"
  | "S10"
  | "S_parecer"
  | "plano_de_acao";

export interface PontoForte {
  titulo: string;
  descricao: string;
  tema_canonico: TemaCanonico | null;
  section_id: PlannerSectionId | null;
}

/** ADR-296: âncora de citação determinística — chip D2-puro no rodapé do card.
 *  `valor_renderizado` é o R$ resolvido do `path` pelo finalize (snapshot). v1
 *  (sem `ancoras`) usa `evidencia_path`; renderer faz dispatch por `content.version`. */
export interface Ancora {
  path: string | null;
  rotulo: string | null;
  valor_renderizado: string | null;
}

export interface Risco {
  severidade: Severidade;
  titulo: string;
  descricao: string;
  tema_canonico: TemaCanonico;
  evidencia: string | null;
  evidencia_path: string | null;
  ancoras: Ancora[];
  section_id: PlannerSectionId;
  confianca: Confianca | null;
}

/** ADR-220: tipagem semântica do impacto. Evita confundir fluxo anual com
 *  patrimônio-alvo (estoque pela regra 25× IF). */
export type ImpactoTipo =
  | "patrimonio_alvo"
  | "fluxo_anual"
  | "economia_anual_irpf"
  | "gap_protecao"
  | "outro";

export interface ImpactoEstimado {
  /** Decimal string (ex.: "150000.00") — LLM emite só com confianca='alta'.
   *  Frontend converte via `Number()` na renderização via `<MonetaryValue/>`. */
  valor_estimado_brl: string;
  unidade: UnidadeImpacto;
  caveat: string;
  /** ADR-220: tipagem opcional do impacto. Ausente em runs pré-ADR-220 —
   *  renderer trata como "outro" e mantém label legado "Impacto estimado". */
  tipo?: ImpactoTipo | null;
}

export interface Sugestao {
  prioridade: Prioridade;
  acao: string;
  impacto_qualitativo: string;
  tema_canonico: TemaCanonico;
  confianca: Confianca;
  section_id: PlannerSectionId;
  /** sha256 hex (64) — chave usada por `Suggestion` aggregate p/ idempotência. */
  suggestion_dedup_key: string;
  impacto_estimado: ImpactoEstimado | null;
  evidencia_path: string | null;
  ancoras: Ancora[];
  /** ADR-220: categoria editorial da sugestão (natureza do impacto), ortogonal
   *  a tema_canonico (tema = metodologia; categoria = natureza). */
  categoria_sugestao?: ImpactoTipo | null;
}

export interface Metrica {
  nome: string;
  valor_atual: string;
  target: string;
  frequencia_revisao: FrequenciaRevisao;
  section_id: PlannerSectionId;
  tema_canonico: TemaCanonico | null;
}

export interface NotaMetodologica {
  titulo: string;
  conteudo: string;
  temas_canonicos: TemaCanonico[];
}

export interface GatedCounts {
  pontos_fortes: number;
  riscos: number;
  sugestoes_execucao: number;
  sugestoes_taticas: number;
  sugestoes_estrategicas: number;
  metricas: number;
  notas_metodologicas: number;
}

export interface ParecerContentMeta {
  tier_at_generation: PlannerReviewTier;
  persona_hash: string;
  manifest_version: string;
  schema_version: string;
  model_id: string;
  generated_at: string;
  gated_counts: GatedCounts;
}

export interface ParecerPlanejadorContent {
  version: string;
  diagnostico_geral: string;
  pontos_fortes: PontoForte[];
  riscos: Risco[];
  sugestoes_execucao: Sugestao[];
  sugestoes_taticas: Sugestao[];
  sugestoes_estrategicas: Sugestao[];
  metricas: Metrica[];
  notas_metodologicas: NotaMetodologica[];
  meta: ParecerContentMeta;
}

export type PlannerReviewStatus = "Pendente" | "Gerado" | "Publicado" | "Superseded";

export interface PlannerReviewResponse {
  id: string;
  workspace_id: string;
  pipeline_run_id: string;
  status: PlannerReviewStatus;
  persona_hash: string;
  manifest_version: string;
  schema_version: string;
  model_id: string;
  tier_at_generation: PlannerReviewTier;
  items_shown_count: number;
  items_gated_count: number;
  cost_usd_cents: number;
  created_at: string;
  published_at: string | null;
  superseded_at: string | null;
  supersedes_id: string | null;
  superseded_by_id: string | null;
  immutable_hash: string | null;
  content: ParecerPlanejadorContent;
}

/** GET .../planner-review — retorna parecer com tier filter aplicado.
 *
 * `404 not_generated_yet` quando stage `review_finances_holistic` ainda não
 * rodou para o run. Caller renderiza placeholder educativo.
 */
export async function getPlannerReview(
  workspaceId: string,
  reportId: string,
): Promise<PlannerReviewResponse> {
  return apiFetch<PlannerReviewResponse>(
    `/workspaces/${workspaceId}/reports/${reportId}/planner-review`,
  );
}

/** POST .../publish — flippa Gerado → Publicado. Idempotente.
 *
 * Chamada pelo frontend quando usuário publica o relatório (gate
 * editorial). Backend congela `immutable_hash` do content e retorna o
 * mesmo DTO atualizado.
 */
export async function publishPlannerReview(
  workspaceId: string,
  reportId: string,
): Promise<PlannerReviewResponse> {
  return apiFetch<PlannerReviewResponse>(
    `/workspaces/${workspaceId}/reports/${reportId}/planner-review/publish`,
    { method: "POST" },
  );
}

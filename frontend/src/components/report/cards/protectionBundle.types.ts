/** ADR-192 §D2 · S9-T04 — TypeScript types espelhando
 * `pipeline/domain/protection_bundle.py` + DTOs Pydantic
 * em `backend/app/schemas/dto/protection/bundle.py`.
 *
 * Bundle é consumido pelos cards da S9. Backend serializa centavos
 * (`coverage_brl_cents`) como `Decimal` (`coverage_brl`) — frontend
 * recebe como `number` após `JSON.parse` no client de API.
 *
 * T03 popula `gap_analysis`, `recommendations`, `auto_inferred_risks`
 * e `methodology_thresholds`. Até T03 mergear, esses campos vêm
 * vazios — cards renderizam estados degradados coerentes.
 */

export type ProtectionCategory =
  | "vida"
  | "invalidez"
  | "saude"
  | "patrimonial"
  | "rc_profissional"
  | "sucessorio";

export type ProtectionStatus = "Ativa" | "Suspensa" | "Cancelada" | "Vencida";

export type CoverageType = "term" | "whole" | "universal";

export type ProtectionPriority = "alta" | "média" | "baixa";

export type MitigationStatus = "coberto" | "parcial" | "descoberto";

export interface ProtectionItem {
  id: string;
  category: ProtectionCategory | string;
  holder_family_member_id?: string | null;
  insurer?: string | null;
  /** Valor monetário em BRL (já convertido de centavos pelo adapter). */
  coverage_brl: number;
  premium_monthly_brl?: number | null;
  coverage_type?: CoverageType | string | null;
  /** ISO 8601 (YYYY-MM-DD). */
  starts_at: string;
  ends_at?: string | null;
  status: ProtectionStatus | string;
}

export interface ProtectionGapItem {
  ideal_brl?: number | null;
  actual_brl: number;
  gap_brl?: number | null;
  methodology?: string | null;
}

export interface ProtectionRecommendation {
  category: ProtectionCategory | string;
  rationale: string;
  priority: ProtectionPriority | string;
}

export interface RiskInferred {
  category: string;
  name: string;
  rationale: string;
  estimated_impact_brl?: number | null;
  source_calculator: string;
}

export interface ProtectionThresholds {
  life_insurance_multiple_renda_anual?: number | null;
  reserva_meses_clt?: number | null;
  reserva_meses_pj?: number | null;
  reserva_meses_socio_variavel?: number | null;
  fbar_threshold_usd?: number | null;
  estate_tax_threshold_usd?: number | null;
}

export interface ProtectionBundle {
  policies: ProtectionItem[];
  /** Key = `ProtectionCategory`. */
  gap_analysis: Record<string, ProtectionGapItem>;
  recommendations: ProtectionRecommendation[];
  auto_inferred_risks: RiskInferred[];
  methodology_thresholds: ProtectionThresholds;
  has_us_exposure: boolean;
  adapter_version: number;
}

/** Ordem canônica de exibição das categorias na tabela
 * `CoberturaSegurosCard`. Mantém ordem do ADR-192 §D1.
 */
export const CATEGORY_ORDER: ProtectionCategory[] = [
  "vida",
  "invalidez",
  "saude",
  "patrimonial",
  "rc_profissional",
  "sucessorio",
];

export const CATEGORY_LABELS: Record<ProtectionCategory, string> = {
  vida: "Vida",
  invalidez: "Invalidez",
  saude: "Saúde",
  patrimonial: "Patrimonial",
  rc_profissional: "RC Profissional",
  sucessorio: "Sucessório",
};

/** Disclaimer fiduciário canônico (ADR-192 §"Atualizações pós-revisão").
 *
 * COPY_GUIDELINES.md §13 — atribuição direta a fontes metodológicas
 * (Cerbasi/Perini/AUVP) é proibida em superfície user-facing. Usamos
 * substituições canônicas (§13.2): "metodologia consagrada de
 * planejamento patrimonial brasileiro" / "padrão de mercado de wealth
 * management". `methodology` recebe o **contexto** (ex.: "sucessório
 * BR", "wealth management"), nunca nomes próprios.
 *
 * `effectiveDate` vem do bundle de fiscal_parameters (T03 popula).
 */
export function fiduciaryDisclaimer(
  methodology: string,
  effectiveDate?: string | null,
): string {
  const date = effectiveDate ?? "data corrente";
  return `Estimativa baseada em metodologia consagrada de planejamento patrimonial brasileiro (${methodology}); não constitui recomendação fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. Dados fiscais válidos para ${date}.`;
}

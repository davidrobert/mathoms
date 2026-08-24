/** Tipos do bloco `real_estate` do view-model E5 (S4 · ADR-216 · Onda 2).
 *
 * Extraídos de `report-analysis.ts` em RV6-15/ADR-401 para manter aquele
 * arquivo dentro do limite de 500 linhas (CLAUDE.md §Code style · gate
 * `dev/audit_code_style.py` T2) — mesmo movimento que `report-fluxo.ts` fez
 * em A40.l3. `report-analysis.ts` re-exporta tudo: todo import existente
 * continua válido.
 *
 * Payload determinístico produzido por
 * pipeline/domain/services/real_estate_metrics.py + real_estate_adapter.
 * ADR-209: campos *_pct são percentuais absolutos (1.7 = 1,7%).
 */

export type RealEstateOrigemFonte =
  "informe" | "irpf" | "e3" | "e4" | "manual" | "pro_rata" | "none" | "default";

export type RealEstateConfidence = "high" | "medium" | "low";

export type RealEstateStatusContrato =
  "atualizado" | "reajuste_pendente" | "sem_renda" | "desconhecido";

export type RealEstateAlertaCode =
  | "concentracao_alta"
  | "spread_critico"
  | "aluguel_sem_dado"
  | "contrato_reajuste_pendente"
  | "premissa_if_imoveis";

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
  readonly endereco_display: string | null;
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

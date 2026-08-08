/**
 * Tipos do payload `protecao_patrimonial` (ADR-240 D8).
 *
 * Wire string decimal (ADR-090); UI parseia para Number.parseFloat() apenas
 * para display via MonetaryValue. Validação JSON-schema no backend (ADR-212).
 */

export type ProtecaoGapSinal = "ok" | "atencao_branda" | "atencao";

export interface BemGapCobertura {
  veiculo_id: string;
  veiculo_descricao?: string;
  lmi_brl: string;
  fipe_brl: string;
  gap_pct: string;
  sinal: ProtecaoGapSinal;
}

export type GapQualitativoCategoria = "vida" | "saude" | "rc_familiar" | "rd_profissional" | "ap";

export interface GapQualitativo {
  categoria: GapQualitativoCategoria;
  flag: boolean;
  rationale: string;
}

export interface ApoliceResumo {
  apolice_numero: string;
  seguradora: string;
  /** Display name via institution_catalog (A37.l11); ausente em artifacts antigos. */
  seguradora_nome?: string;
  vigencia_inicio: string;
  vigencia_fim: string;
  premio_total_brl: string;
  bens_count: number;
  tipos_bem?: string[];
}

/**
 * Escopo dos agregados monetários (ADR-240 §Emenda 2026-08-08).
 *
 * `premio_total_anual_brl` e `pct_renda_anual` somam só apólice extraída de
 * documento. Com cobertura conhecida fora desse escopo o numerador é
 * sabidamente parcial, e o veredito de faixa não pode ser emitido.
 */
export interface EscopoCobertura {
  premio_inclui_cadastro_manual: boolean;
  categorias_somente_no_cadastro: string[];
  veredito_pct_renda_suprimido: boolean;
}

export interface ProtecaoPatrimonialData {
  premio_total_anual_brl: string;
  premio_decomposicao: Record<string, string>;
  pct_renda_anual: string;
  bens_com_gap_cobertura: BemGapCobertura[];
  gap_qualitativo: GapQualitativo[];
  apolices_vigentes: ApoliceResumo[];
  apolices_vencendo: ApoliceResumo[];
  apolices_vencidas: ApoliceResumo[];
  corretoras_count: number;
  seguradoras_count: number;
  /** Ausente em artifacts gerados antes da emenda de 2026-08-08. */
  escopo_cobertura?: EscopoCobertura;
}

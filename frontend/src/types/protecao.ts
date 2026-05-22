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
  vigencia_inicio: string;
  vigencia_fim: string;
  premio_total_brl: string;
  bens_count: number;
  tipos_bem?: string[];
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
}

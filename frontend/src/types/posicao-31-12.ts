/** A33.l2 P4 (co-design product-designer 2026-07-07) — row do card
 * "Posição por instituição e moeda (31/12)" em S1. Extraído de
 * report-analysis.ts em A40.l39 (arquivo no teto de 500 linhas). */
export interface Posicao3112Row {
  /** Id estável da linha (A40.l39) — key do React + natural key de diff. */
  id?: string;
  /** Fim de período do saldo (YYYY-MM-DD): 31/12 p/ informe; data real do extrato. */
  data_referencia?: string | null;
  data_referencia_precisao?: "dia" | "mes" | "desconhecida" | string;
  instituicao: string;
  moeda: string;
  /** Valor na moeda original — null para contas BRL (sem linha secundária). */
  valor_original: number | null;
  /** BRL da linha. Em `fonte: "informe_31_12"`, convertido pela PTAX compra
   * de 31/12 (`ptax_data`/`ptax_status` preenchidos). Em `fonte: "extrato"`,
   * é o `valor_brl` do E3 copiado cru, com PTAX nula — a linha não é 31/12
   * (posicao_31_12_builder.py::_posicao_from_extrato). */
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

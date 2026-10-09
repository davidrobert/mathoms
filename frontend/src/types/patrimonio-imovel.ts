/** Tipos do patrimônio imobiliário publicado pelo E5 ([[ADR-439]]) — extraídos de
 *  `report-analysis.ts`, que chegou ao teto de 500 linhas (T2). */

export interface PatrimonioCategoria {
  categoria: string;
  valor: number;
  pct: number;
  /** ADR-439 D5: só na linha `Residência` não apurada — o `valor` segue 0 na partição. */
  estado?: "nao_apurado";
  motivo?: MotivoBaldeImovel | null;
}

/** ADR-439 D1: por que um balde de imóvel saiu `null` — cada um pede uma ação diferente. */
export type MotivoBaldeImovel =
  | "nao_localizada"
  | "sem_valor"
  | "nao_classificada"
  | "nao_declarada"
  | "vinculo_perdido"
  | "nao_classificados";

/** ADR-439 D1: vocabulário de `cobertura_investimentos[]` (ADR-394 §Emenda (b) D7). */
export interface VereditoBaldeImovel {
  status: "apurado" | "zero_apurado" | "nao_apurado";
  motivo: MotivoBaldeImovel | null;
  piso: boolean;
}

/** ADR-439 D1 · ADR-433 §D3: partição do valor de imóvel + veredito por balde. */
export interface CoberturaClassificacaoImovel {
  valor_total: number;
  valor_desconhecido: number;
  n_total: number;
  n_desconhecido: number;
  pct_desconhecido: number;
  residencia_identificada: number;
  geradores_identificados: number;
  nao_geradores_identificados: number;
  residencia: VereditoBaldeImovel;
  imoveis_geradores: VereditoBaldeImovel;
  n_desconhecido_em_aberto: number;
  overrides_sem_imovel: { residencia_principal: number; geradores: number };
  residencia_status: "owned" | "rented" | "undeclared";
}

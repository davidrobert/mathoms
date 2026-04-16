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

export interface PatrimonioCaixaDetalhe {
  conta: string;
  moeda: "BRL" | "USD" | "EUR" | string;
  saldo_original: number;
  valor_brl: number;
  tipo: "moeda_nacional" | "moeda_estrangeira" | string;
}

export interface PatrimonioCategoria {
  categoria: string;
  valor: number;
  pct: number;
}

export interface PatrimonioData {
  bruto?: number;
  liquido?: number;
  investivel?: number;
  dividas?: number;
  residencia?: number;
  imoveis_investimento?: number;
  veiculos?: number;
  investimentos_david?: number;
  investimentos_mariana?: number;
  caixa_moeda_estrangeira?: number;
  fonte_investimentos?: string;
  caixa_detalhes?: PatrimonioCaixaDetalhe[];
  composicao?: PatrimonioCategoria[];
  tabela_categorias?: PatrimonioCategoria[];
}

export interface ReservaEmergenciaData {
  despesas_mensais?: number;
  nivel_6_meses?: number;
  nivel_12_meses?: number;
  total_liquida?: number;
  cobertura_meses?: number;
  avaliacao_liquidity?: "Adequada" | "Baixa" | "Excelente" | string;
  composicao_liquida?: {
    investimentos_david?: number;
    investimentos_mariana?: number;
    caixa_moeda_estrangeira?: number;
    total_liquido?: number;
    cobertura_meses?: number;
  };
}

export interface EndividamentoData {
  total_dividas?: number;
  percentual_patrimonio?: number;
  dividas?: Array<{
    descricao: string;
    valor: number;
    taxa?: number;
    [key: string]: unknown;
  }>;
  detalhe?: string;
}

export interface RatiosData {
  taxa_poupanca_recorrente_pct?: number;
  taxa_poupanca_total_pct?: number;
  taxa_endividamento_pct?: number;
  cobertura_despesas_meses?: number;
  rentabilidade_pct?: number | string;
  aliquota_efetiva_ir_pct?: number | string;
  janela_referencia?: string;
  janela_n_meses?: number;
}

export interface ScoreComponente {
  nome: string;
  valor: number | string;
  peso: number;
  nota: number;
}

export interface ScoreData {
  valor: number;
  max: number;
  classificacao?: string;
  componentes?: ScoreComponente[];
}

// Receitas (vive em fluxo_caixa, necessário no card de receitas de S1)
export interface FluxoPorFonte {
  outras_receitas?: number;
  receita_investimento?: number;
  receita_pj?: number;
  receita_clt?: number;
  receita_aluguel?: number;
  [key: string]: number | undefined;
}

export interface FluxoCaixaSummary {
  receita_total?: number;
  receita_recorrente?: number;
  receita_one_time?: number;
  receita_recorrente_mensal?: number;
  despesa_total?: number;
  despesa_mensal_media?: number;
  fluxo_liquido?: number;
  por_fonte?: FluxoPorFonte;
}

/** Type guard defensivo. */
export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

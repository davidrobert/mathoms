/** Tipos do bloco `fluxo_caixa` do view-model E5.
 *
 * Extraídos de `report-analysis.ts` em A40.l3 para manter aquele arquivo
 * dentro do limite de 500 linhas (CLAUDE.md §Code style · gate
 * `dev/audit_code_style.py` T2). `report-analysis.ts` re-exporta tudo — todo
 * import existente continua válido.
 */
import type { ChartSeries } from "./chart-series";

// Receitas (vive em fluxo_caixa, necessário no card de receitas de S1)
export interface FluxoPorFonte {
  outras_receitas?: number;
  receita_investimento?: number;
  receita_pj?: number;
  receita_clt?: number;
  receita_aluguel?: number;
  [key: string]: number | undefined;
}

/** ADR-306 D1 (A40.l3) — bloco de mensalização canônico do fluxo: últimos 12
 * meses **documentados**. Todo campo é opcional porque
 * `config/schemas/e5_analysis.schema.json` não declara o bloco (workspace
 * pré-A28 e `degraded` chegam sem ele).
 *
 * `fluxo_liquido` é `receita_total − despesa_total` **do intervalo de 12
 * meses** — um TOTAL; lê-lo como taxa mensal infla o número em ~20×.
 *
 * E `receita_recorrente_mensal − despesa_mensal_media` **não** é "quanto sobra":
 * `despesa_mensal_media` é BRUTA (inclui `transferencia_patrimonial`/aporte por
 * ADR-333), logo essa diferença não fecha com `taxa_poupanca_recorrente`, que é
 * ex-aporte. Nenhum consumidor deriva sobra daqui — o número de sobra exibido é
 * `consumo_consciente.folga_mensal`, que o E5 calcula. */
export interface FluxoJanela12m {
  janela?: string;
  janela_meses?: number;
  periodo?: string;
  n_meses?: number;
  receita_total?: number;
  receita_recorrente?: number;
  receita_one_time?: number;
  receita_recorrente_mensal?: number;
  despesa_total?: number;
  despesa_mensal_media?: number;
  despesa_mensal_essencial?: number;
  fluxo_liquido?: number;
  /** ADR-333 — numerador ex-aporte (`despesa_total − transferencia_patrimonial`). */
  despesa_consumo?: number;
  transferencia_patrimonial?: number;
  /** Canônica ex-aporte; nunca recompute de `despesa_mensal_media`. */
  taxa_poupanca_recorrente?: number;
  taxa_poupanca_total?: number;
  despesas_por_categoria?: Record<string, number>;
}

export interface FluxoCaixaSummary {
  /** ADR-306 D1 — rótulo da base de mensalização do bloco top-level ("full"). */
  janela?: string;
  /** ADR-306 D1 — meses documentados do bloco top-level. */
  janela_meses?: number;
  /** ADR-306 D1 — bloco canônico de 12 meses (ausente em payload pré-A28). */
  janela_12m?: FluxoJanela12m;
  receita_total?: number;
  receita_recorrente?: number;
  receita_one_time?: number;
  receita_recorrente_mensal?: number;
  despesa_total?: number;
  despesa_mensal_media?: number;
  fluxo_liquido?: number;
  por_fonte?: FluxoPorFonte;
  por_fonte_detalhado?: Record<string, number>;
  despesas_por_categoria?: Record<string, number>;
  tabela_receitas?: Array<{ categoria: string; valor: number; pct: number }>;
  receita_despesa_mensal_detalhado?: {
    labels?: string[];
    totais_receita?: number[];
    totais_despesa?: number[];
    /** Onda v2.E.2 — séries por sub-fonte de receita (1 dataset por origem). */
    receita_datasets?: ChartSeries[];
    /** Onda v2.E.2 — séries por sub-categoria de despesa (1 dataset por categoria). */
    despesa_datasets?: ChartSeries[];
  };
}

/**
 * F11.7a — catálogo mínimo “número ↔ regra” (texto curto; referência ao motor E5).
 * Mantido alinhado a docs/reference/FORMULAS.md.
 */
export interface ReportFormulaEntry {
  id: string;
  title: string;
  summary: string;
  codeRef?: string;
}

export const REPORT_FORMULA_CATALOG: ReportFormulaEntry[] = [
  {
    id: "patrimonio_liquido",
    title: "Patrimônio líquido",
    summary:
      "Ativos reconhecidos menos passivos explícitos no snapshot consolidado (E4/E5).",
    codeRef: "E5 análise · patrimonio",
  },
  {
    id: "score_consolidado",
    title: "Score do relatório",
    summary:
      "Combinação ponderada de componentes de saúde financeira já normalizados no motor; o valor exibido é o mesmo persistido no JSON de análise.",
    codeRef: "E5 · score",
  },
  {
    id: "fv_aporte",
    title: "Projeção de independência (aportes)",
    summary:
      "Para metas tipo IF, o motor usa valor futuro de série de aportes com taxa e horizonte definidos nas metas materializadas em goals.json.",
    codeRef: "Motor de metas / E5 narrativas",
  },
];

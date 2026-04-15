/**
 * GENERATED FILE — do not edit by hand.
 * Source: config/report_layout.yaml
 * Regenerate: python3 dev/codegen_report_layout.py
 *
 * Schema: config/schemas/report_layout.schema.json (ADR-076)
 */


export type CardVariant =
  | 'highlight'
  | 'feature'
  | 'success'
  | 'warn'
  | 'critical'
  | 'primary'
  | 'neutral'
  | 'top-danger'
  | 'top-accent';

export type CardSize = 'full' | 'half';

export type ReportMode = 'estrategico' | 'tatico' | 'usa';

export interface CardSpec {
  id: string;
  enabled: boolean;
  variant?: CardVariant;
  size?: CardSize;
}

export interface ChartSpec {
  id: string;
  enabled: boolean;
  row?: string;
}

export interface SectionSpec {
  id: string;
  title: string;
  enabled: boolean;
  charts?: ChartSpec[];
  cards?: CardSpec[];
  data_source?: string;
}

export interface AppendixSpec {
  id: string;
  title: string;
  enabled: boolean;
}

export interface KpiSpec {
  id: string;
  label: string;
  enabled: boolean;
}

export interface ReportLayout {
  version: string;
  estrategico: {
    sections: SectionSpec[];
    appendices?: AppendixSpec[];
  };
  tatico: {
    kpis?: KpiSpec[];
    sections: SectionSpec[];
  };
  usa: {
    sections: SectionSpec[];
  };
  chart_palette?: string[];
  chart_canvas_map?: Record<string, string>;
  chart_titles?: Record<string, string>;
}

export const LAYOUT: ReportLayout = {
  "version": "1.1",
  "estrategico": {
    "sections": [
      {
        "id": "S1",
        "title": "Patrimônio — Estrutura e Composição",
        "enabled": true,
        "charts": [
          {
            "id": "patrimonio_doughnut",
            "enabled": true
          },
          {
            "id": "waterfall_if",
            "enabled": true
          },
          {
            "id": "score_gauge",
            "enabled": true
          }
        ],
        "cards": [
          {
            "id": "patrimonio_categorias",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "receitas_fonte",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "reserva_emergencia",
            "enabled": true,
            "variant": "warn",
            "size": "half"
          },
          {
            "id": "endividamento",
            "enabled": true,
            "variant": "feature",
            "size": "half"
          }
        ]
      },
      {
        "id": "S2",
        "title": "Fluxo de Caixa — Receitas e Despesas",
        "enabled": true,
        "charts": [
          {
            "id": "fluxo_mensal",
            "enabled": true
          },
          {
            "id": "receita_bar",
            "enabled": true
          },
          {
            "id": "despesas_doughnut",
            "enabled": true
          },
          {
            "id": "receita_despesa_mensal",
            "enabled": true
          },
          {
            "id": "viagens",
            "enabled": true
          }
        ],
        "cards": [
          {
            "id": "orcamento_prospectivo",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "consumo_consciente",
            "enabled": true,
            "variant": "success",
            "size": "full"
          },
          {
            "id": "diagnostico_comportamental",
            "enabled": true,
            "variant": "primary",
            "size": "half"
          },
          {
            "id": "equilibrio_cerbasi",
            "enabled": true,
            "variant": "highlight",
            "size": "half"
          },
          {
            "id": "milhas",
            "enabled": false,
            "variant": "feature",
            "size": "half"
          }
        ]
      },
      {
        "id": "S3",
        "title": "Investimentos — Carteira Financeira",
        "enabled": true,
        "charts": [
          {
            "id": "alocacao_atual",
            "enabled": true,
            "row": "alocacao"
          },
          {
            "id": "alocacao_alvo",
            "enabled": true,
            "row": "alocacao"
          },
          {
            "id": "top15_ativos",
            "enabled": true
          },
          {
            "id": "mariana_cenarios",
            "enabled": true
          }
        ],
        "cards": [
          {
            "id": "investimentos_classe",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "kpi_rentabilidade",
            "enabled": true,
            "variant": "feature",
            "size": "half"
          },
          {
            "id": "estrategia_aporte",
            "enabled": true,
            "variant": "highlight",
            "size": "full"
          },
          {
            "id": "contrafluxo",
            "enabled": true,
            "variant": "primary",
            "size": "half"
          }
        ]
      },
      {
        "id": "S4",
        "title": "Real Estate — Imóveis e Renda Passiva",
        "enabled": true,
        "charts": [
          {
            "id": "yield_imoveis",
            "enabled": true
          }
        ],
        "cards": []
      },
      {
        "id": "S7",
        "title": "Independência Financeira — Projeção de Longo Prazo",
        "enabled": true,
        "charts": [
          {
            "id": "projecao_3cenarios",
            "enabled": true
          },
          {
            "id": "renda_passiva",
            "enabled": true
          }
        ],
        "cards": [
          {
            "id": "previdencia_pgbl",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          }
        ]
      },
      {
        "id": "S8",
        "title": "Previdência — PGBL e Fiscalidade",
        "enabled": true,
        "charts": [
          {
            "id": "impostos_pj",
            "enabled": true
          }
        ],
        "cards": []
      },
      {
        "id": "S9",
        "title": "Riscos e Proteção — Seguros Críticos",
        "enabled": true,
        "charts": [
          {
            "id": "bubble_riscos",
            "enabled": true
          }
        ],
        "cards": []
      },
      {
        "id": "S10",
        "title": "Síntese Estratégica — Tarefas e Score",
        "enabled": true,
        "charts": [
          {
            "id": "top5_decisoes",
            "enabled": true
          }
        ],
        "cards": [
          {
            "id": "pontos_fortes",
            "enabled": true,
            "variant": "success",
            "size": "half"
          },
          {
            "id": "pontos_urgentes",
            "enabled": true,
            "variant": "critical",
            "size": "half"
          },
          {
            "id": "equilibrio_cerbasi_ref",
            "enabled": false,
            "variant": "highlight",
            "size": "full"
          }
        ]
      }
    ],
    "appendices": [
      {
        "id": "APP_A",
        "title": "Definições e Siglas",
        "enabled": true
      },
      {
        "id": "APP_B",
        "title": "Premissas Econômicas",
        "enabled": true
      },
      {
        "id": "APP_C",
        "title": "Cenários de Sensibilidade",
        "enabled": true
      },
      {
        "id": "APP_D",
        "title": "Referências e Recursos",
        "enabled": true
      },
      {
        "id": "APP_E",
        "title": "Próximos Ciclos e Roadmap",
        "enabled": true
      }
    ]
  },
  "tatico": {
    "kpis": [
      {
        "id": "patrimonio_delta",
        "label": "Patrimônio Δ",
        "enabled": true
      },
      {
        "id": "aportes_check",
        "label": "Aportes ✓",
        "enabled": true
      },
      {
        "id": "despesas_alerta",
        "label": "Despesas Alerta",
        "enabled": true
      },
      {
        "id": "tarefas_pct",
        "label": "Tarefas %",
        "enabled": true
      },
      {
        "id": "alerta_1",
        "label": "Alerta Crítico 1",
        "enabled": true
      },
      {
        "id": "alerta_2",
        "label": "Alerta Crítico 2",
        "enabled": true
      }
    ],
    "sections": [
      {
        "id": "T1",
        "title": "Fluxo Operacional — Despesas vs Tetos",
        "enabled": true,
        "data_source": "dashboard.despesas_por_categoria"
      },
      {
        "id": "T2",
        "title": "Aportes e Investimentos",
        "enabled": true,
        "data_source": "dashboard.aportes + dashboard.investimentos_delta"
      },
      {
        "id": "T3",
        "title": "Checklist de Tarefas",
        "enabled": true,
        "data_source": "dashboard.tarefas + dashboard.tarefas_status"
      },
      {
        "id": "T4",
        "title": "Alertas e Pendências",
        "enabled": true,
        "data_source": "dashboard.alertas"
      },
      {
        "id": "T5",
        "title": "Próximos Passos",
        "enabled": true,
        "data_source": "dashboard.proximos_15d"
      },
      {
        "id": "T6",
        "title": "Notas e Observações",
        "enabled": true,
        "data_source": "dashboard.notas"
      }
    ]
  },
  "usa": {
    "sections": [
      {
        "id": "U1",
        "title": "Mudança EUA — Estrutura F1/F2 e Custos",
        "enabled": true,
        "charts": [
          {
            "id": "custos_f1f2",
            "enabled": true
          }
        ],
        "cards": []
      },
      {
        "id": "U2",
        "title": "Green Card — EB2-NIW e Compliance",
        "enabled": true,
        "charts": [
          {
            "id": "cenarios_cambiais",
            "enabled": true
          }
        ],
        "cards": []
      },
      {
        "id": "U3",
        "title": "NCLEX Roadmap — Licenciamento RN",
        "enabled": true,
        "charts": [],
        "cards": [
          {
            "id": "nclex_roadmap",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          }
        ]
      },
      {
        "id": "U4",
        "title": "Simulação — Cônjuge Sem Trabalhar",
        "enabled": true,
        "charts": [
          {
            "id": "mariana_cenarios_usa",
            "enabled": true
          }
        ],
        "cards": [
          {
            "id": "simulacao_mariana",
            "enabled": true,
            "variant": "warn",
            "size": "full"
          }
        ]
      }
    ]
  },
  "chart_palette": [
    "#1A3A5C",
    "#2A9D8F",
    "#15803D",
    "#F4A261",
    "#B91C1C",
    "#457B9D",
    "#8338EC",
    "#A8DADC",
    "#E63946",
    "#1E6E8F",
    "#E76F51",
    "#06B6D4",
    "#FFB703",
    "#7C3AED",
    "#219EBC",
    "#6366F1",
    "#EC4899",
    "#84CC16",
    "#F97316",
    "#8B5CF6"
  ],
  "chart_canvas_map": {
    "patrimonio_doughnut": "chart-patrimonio-doughnut",
    "waterfall_if": "chart-waterfall-if",
    "receita_bar": "chart-receita-bar",
    "despesas_doughnut": "chart-despesas-doughnut",
    "fluxo_mensal": "chart-fluxo-mensal",
    "receita_despesa_mensal": "chart-receita-despesa-mensal",
    "score_gauge": "chart-score-gauge",
    "alocacao_atual": "chart-alocacao-atual",
    "alocacao_alvo": "chart-alocacao-alvo",
    "top15_ativos": "chart-top15-ativos",
    "yield_imoveis": "chart-yield-imoveis",
    "custos_f1f2": "chart-custos-f1f2",
    "cenarios_cambiais": "chart-cenarios-cambiais",
    "projecao_3cenarios": "chart-projecao-3cenarios",
    "renda_passiva": "chart-renda-passiva",
    "impostos_pj": "chart-impostos-pj",
    "bubble_riscos": "chart-bubble-riscos",
    "top5_decisoes": "chart-top5-decisoes",
    "mariana_cenarios": "chart-mariana-cenarios",
    "mariana_cenarios_usa": "chart-mariana-cenarios-usa",
    "viagens": "chart-viagens"
  },
  "chart_titles": {
    "patrimonio_doughnut": "Composição Patrimonial",
    "waterfall_if": "Caminho para Independência Financeira",
    "receita_bar": "Receita por Fonte",
    "despesas_doughnut": "Despesas por Categoria",
    "fluxo_mensal": "Fluxo de Caixa Mensal",
    "receita_despesa_mensal": "Receita vs Despesa — Mês a Mês",
    "score_gauge": "Score Financeiro",
    "alocacao_atual": "Alocação Atual",
    "alocacao_alvo": "Alocação Alvo",
    "top15_ativos": "Top 15 Ativos Financeiros",
    "yield_imoveis": "Rentabilidade dos Imóveis (Yield) vs CDI",
    "custos_f1f2": "Custos Mensais F1/F2",
    "cenarios_cambiais": "Cenários Cambiais",
    "projecao_3cenarios": "Projeção Patrimonial — 3 Cenários",
    "renda_passiva": "Renda Passiva — Progresso até a Meta",
    "impostos_pj": "Tributário PJ — Cascata Fiscal",
    "bubble_riscos": "Mapa de Riscos",
    "top5_decisoes": "Top 5 Decisões de Impacto",
    "mariana_cenarios": "Cenários IF — Cônjuge",
    "mariana_cenarios_usa": "Cenários IF — Cônjuge",
    "viagens": "Orçamento de Viagens"
  },
  "section_charts": {
    "1": [
      "patrimonio_doughnut",
      "waterfall_if"
    ],
    "2": [
      "fluxo_mensal",
      "receita_bar",
      "despesas_doughnut",
      "receita_despesa_mensal",
      "score_gauge"
    ],
    "3": [
      "alocacao_atual",
      "alocacao_alvo",
      "top15_ativos",
      "mariana_cenarios",
      "viagens"
    ],
    "4": [
      "yield_imoveis"
    ],
    "7": [
      "projecao_3cenarios",
      "renda_passiva"
    ],
    "8": [
      "impostos_pj"
    ],
    "9": [
      "bubble_riscos"
    ],
    "10": [
      "top5_decisoes"
    ]
  },
  "usa_section_charts": {
    "1": [
      "custos_f1f2"
    ],
    "2": [
      "cenarios_cambiais"
    ],
    "4": [
      "mariana_cenarios_usa"
    ]
  },
  "dark_mode": {
    "css_vars": {
      "color-bg": "#0F172A",
      "color-surface": "#1E293B",
      "color-text": "#E2E8F0",
      "color-text-muted": "#94A3B8",
      "color-border": "#334155",
      "color-primary": "#2E86AB",
      "color-light": "#1E3A5F"
    },
    "table": {
      "row_even": "#1A2332",
      "row_hover": "#243447",
      "th_bg": "#1E3A5F",
      "th_color": "#E2E8F0",
      "td_total": "#1A2332",
      "td_border": "#334155"
    },
    "alerts": {
      "danger_bg": "#2D1B1B",
      "danger_color": "#FCA5A5",
      "warning_bg": "#2D2410",
      "warning_color": "#FCD34D",
      "success_bg": "#1A2D1A",
      "success_color": "#86EFAC",
      "info_bg": "#1A2440",
      "info_color": "#93C5FD"
    },
    "badges": {
      "green_bg": "#16533480",
      "green_color": "#86EFAC",
      "red_bg": "#991B1B80",
      "red_color": "#FCA5A5",
      "yellow_bg": "#92400E80",
      "yellow_color": "#FCD34D",
      "blue_bg": "#1E40AF80",
      "blue_color": "#93C5FD"
    },
    "kpi": {
      "blue": "#60A5FA",
      "green": "#4ADE80",
      "red": "#F87171"
    },
    "headings_color": "#F1F5F9",
    "strong_color": "#F1F5F9",
    "section_summary_bg": "#1A2440",
    "section_summary_color": "#CBD5E1",
    "chart_conclusion_bg": "#1A2440",
    "chart_conclusion_border": "#2E86AB",
    "chart_context_color": "#94A3B8",
    "export_toolbar_bg": "linear-gradient(135deg, #0B1929, #132337)",
    "progress_bar_bg": "#334155",
    "compare_col2_bg": "#2D1B1B",
    "compare_col3_bg": "#1A2D1A",
    "chart_theme": {
      "dark": {
        "text_color": "#94A3B8",
        "grid_color": "#334155"
      },
      "light": {
        "text_color": "#64748B",
        "grid_color": "#E2E8F0"
      }
    }
  },
  "version_fallback": "v5.3"
} as ReportLayout;

export const ALL_CARD_IDS = ["patrimonio_categorias", "receitas_fonte", "reserva_emergencia", "endividamento", "orcamento_prospectivo", "consumo_consciente", "diagnostico_comportamental", "equilibrio_cerbasi", "milhas", "investimentos_classe", "kpi_rentabilidade", "estrategia_aporte", "contrafluxo", "previdencia_pgbl", "pontos_fortes", "pontos_urgentes", "equilibrio_cerbasi_ref", "nclex_roadmap", "simulacao_mariana"] as const;
export type CardId = (typeof ALL_CARD_IDS)[number];

export const ALL_CHART_IDS = ["patrimonio_doughnut", "waterfall_if", "score_gauge", "fluxo_mensal", "receita_bar", "despesas_doughnut", "receita_despesa_mensal", "viagens", "alocacao_atual", "alocacao_alvo", "top15_ativos", "mariana_cenarios", "yield_imoveis", "projecao_3cenarios", "renda_passiva", "impostos_pj", "bubble_riscos", "top5_decisoes", "custos_f1f2", "cenarios_cambiais", "mariana_cenarios_usa"] as const;
export type ChartId = (typeof ALL_CHART_IDS)[number];

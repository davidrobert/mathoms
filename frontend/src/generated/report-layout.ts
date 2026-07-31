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
  | 'info'
  | 'top-danger'
  | 'top-accent';

export type CardSize = 'full' | 'half';

export type ReportMode = 'estrategico';

export type TopBorder = 'danger' | 'accent';

export type ChartHeight = number | 'auto';

export interface CardSpec {
  id: string;
  enabled: boolean;
  variant?: CardVariant;
  size?: CardSize;
  top_border?: TopBorder;
  comparison_anchor_id?: string;
}

export interface ChartSpec {
  id: string;
  enabled: boolean;
  row?: string;
  conclusion?: boolean;
  context?: boolean;
  period_toggle?: boolean;
  height?: ChartHeight;
}

/** Report Premium UI v2.1 — placeholder de <ComparisonBlock> por seção (deferred_until v2.8). */
export interface ComparisonSpec {
  id: string;
  enabled: boolean;
  deferred_until?: string;
}

/** Report Premium UI v2.1 — placeholder de <ChangelogList> por seção (deferred_until v2.8). */
export interface ChangelogSpec {
  id: string;
  enabled: boolean;
  deferred_until?: string;
}

export interface SectionSpec {
  id: string;
  title: string;
  enabled: boolean;
  charts?: ChartSpec[];
  cards?: CardSpec[];
  comparisons?: ComparisonSpec[];
  changelog?: ChangelogSpec[];
  data_source?: string;
  summary?: boolean;
  summary_source?: string | null;
  divider_before?: boolean;
  collapsible?: boolean;
}

export interface AppendixSpec {
  id: string;
  title: string;
  enabled: boolean;
  optional?: boolean;
  summary?: boolean;
  summary_source?: string | null;
  charts?: ChartSpec[];
  cards?: CardSpec[];
}

export interface KpiSpec {
  id: string;
  label: string;
  enabled: boolean;
}

export interface CoverMetaSpec {
  label_key: string;
  value_key?: string;
  conditional_on?: string;
}

export interface CoverSpec {
  enabled: boolean;
  badge?: string;
  title_key?: string;
  subtitle_key?: string;
  meta?: CoverMetaSpec[];
}

export interface NavLinkSpec {
  section_id: string;
  num?: string;
  is_appendix?: boolean;
}

export interface NavGroupSpec {
  label?: string;
  links: NavLinkSpec[];
}

export interface NavigationSpec {
  estrategico?: NavGroupSpec[];
}

export interface ReportLayout {
  version: string;
  estrategico: {
    sections: SectionSpec[];
    appendices?: AppendixSpec[];
  };
  cover?: CoverSpec;
  navigation?: NavigationSpec;
  footer?: boolean;
  export_toolbar?: boolean;
  chart_palette?: string[];
  chart_canvas_map?: Record<string, string>;
  chart_titles?: Record<string, string>;
}

export const LAYOUT: ReportLayout = {
  "version": "1.2",
  "cover": {
    "enabled": true,
    "badge": "Relatório Premium",
    "meta": [
      {
        "label_key": "Família",
        "conditional_on": "workspace_family_surname"
      },
      {
        "label_key": "Período"
      },
      {
        "label_key": "Gerado em"
      },
      {
        "label_key": "Versão"
      }
    ]
  },
  "navigation": {
    "estrategico": [
      {
        "label": "Visão geral",
        "links": [
          {
            "section_id": "V0"
          },
          {
            "section_id": "S1",
            "num": "1"
          },
          {
            "section_id": "S2",
            "num": "2"
          },
          {
            "section_id": "S_PROTECAO",
            "num": "2.5"
          },
          {
            "section_id": "S3",
            "num": "3"
          }
        ]
      },
      {
        "label": "Detalhes",
        "links": [
          {
            "section_id": "S4",
            "num": "4"
          },
          {
            "section_id": "S7",
            "num": "7"
          },
          {
            "section_id": "S8",
            "num": "8"
          },
          {
            "section_id": "S_IRPF_RENDA",
            "num": "8.1"
          },
          {
            "section_id": "S_IRPF_OTIMIZACAO",
            "num": "8.2"
          },
          {
            "section_id": "S9",
            "num": "9"
          }
        ]
      },
      {
        "label": "Síntese",
        "links": [
          {
            "section_id": "S10",
            "num": "10"
          },
          {
            "section_id": "S_parecer",
            "num": "10.1"
          },
          {
            "section_id": "plano_de_acao",
            "num": "11"
          }
        ]
      },
      {
        "label": "Apêndices",
        "links": [
          {
            "section_id": "APP_A",
            "num": "A",
            "is_appendix": true
          },
          {
            "section_id": "APP_B",
            "num": "B",
            "is_appendix": true
          },
          {
            "section_id": "APP_C",
            "num": "C",
            "is_appendix": true
          },
          {
            "section_id": "APP_D",
            "num": "D",
            "is_appendix": true
          },
          {
            "section_id": "APP_E",
            "num": "E",
            "is_appendix": true
          }
        ]
      }
    ]
  },
  "footer": true,
  "export_toolbar": true,
  "estrategico": {
    "sections": [
      {
        "id": "S1",
        "title": "Patrimônio — Estrutura e Composição",
        "enabled": true,
        "summary": true,
        "summary_source": "s1",
        "charts": [
          {
            "id": "patrimonio_doughnut",
            "enabled": true,
            "conclusion": true,
            "context": true
          },
          {
            "id": "waterfall_if",
            "enabled": true,
            "conclusion": true
          },
          {
            "id": "score_gauge",
            "enabled": true,
            "conclusion": true
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
            "id": "posicao_informe_31_12",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "exposicao_cambial",
            "enabled": true,
            "variant": "feature",
            "size": "half"
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
        "summary": true,
        "summary_source": null,
        "divider_before": true,
        "charts": [
          {
            "id": "fluxo_mensal",
            "enabled": true,
            "conclusion": true,
            "period_toggle": true
          },
          {
            "id": "receita_bar",
            "enabled": true,
            "conclusion": true,
            "period_toggle": true
          },
          {
            "id": "despesas_doughnut",
            "enabled": true,
            "conclusion": true,
            "period_toggle": true
          },
          {
            "id": "receita_despesa_mensal",
            "enabled": true,
            "conclusion": true,
            "period_toggle": true
          },
          {
            "id": "viagens",
            "enabled": true,
            "conclusion": true
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
        "id": "S_PROTECAO",
        "title": "Proteção Patrimonial — Pilar AUVP",
        "enabled": false,
        "summary": true,
        "summary_source": null,
        "divider_before": true,
        "charts": [
          {
            "id": "protecao_premio_decomp",
            "enabled": false,
            "conclusion": true
          }
        ],
        "cards": [
          {
            "id": "protecao_kpi_hero",
            "enabled": false,
            "variant": "highlight",
            "size": "full"
          },
          {
            "id": "protecao_bens",
            "enabled": false,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "protecao_gap_qualitativo",
            "enabled": false,
            "variant": "warn",
            "size": "half"
          },
          {
            "id": "protecao_apolices",
            "enabled": false,
            "variant": "neutral",
            "size": "full"
          }
        ]
      },
      {
        "id": "S3",
        "title": "Investimentos — Carteira Financeira",
        "enabled": true,
        "summary": true,
        "summary_source": "s3",
        "divider_before": true,
        "charts": [
          {
            "id": "top15_ativos",
            "enabled": true,
            "conclusion": true
          },
          {
            "id": "cenarios_conjuge",
            "enabled": true,
            "conclusion": true
          },
          {
            "id": "viagens",
            "enabled": false,
            "conclusion": true
          }
        ],
        "cards": [
          {
            "id": "alocacao_atual_vs_alvo",
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
            "id": "proventos_yield",
            "enabled": true,
            "variant": "feature",
            "size": "full"
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
        "summary": true,
        "summary_source": "s4",
        "divider_before": true,
        "charts": [],
        "cards": [
          {
            "id": "real_estate_yield",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          }
        ]
      },
      {
        "id": "S7",
        "title": "Independência Financeira — Projeção de Longo Prazo",
        "enabled": true,
        "summary": true,
        "summary_source": "s7",
        "divider_before": true,
        "charts": [
          {
            "id": "projecao_3cenarios",
            "enabled": true,
            "conclusion": true
          },
          {
            "id": "renda_passiva",
            "enabled": true,
            "conclusion": true
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
        "summary": true,
        "summary_source": "s8",
        "divider_before": true,
        "charts": [
          {
            "id": "impostos_pj",
            "enabled": true,
            "conclusion": true,
            "period_toggle": true
          }
        ],
        "cards": []
      },
      {
        "id": "S_IRPF_RENDA",
        "title": "Renda Anual e Impostos",
        "enabled": true,
        "summary": true,
        "summary_source": null,
        "divider_before": true,
        "charts": [
          {
            "id": "renda_evolucao_multi_anos",
            "enabled": true,
            "conclusion": true
          },
          {
            "id": "aliquota_efetiva_dual_gauge",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": [
          {
            "id": "renda_anual_familiar",
            "enabled": true,
            "variant": "feature",
            "size": "half"
          },
          {
            "id": "ir_pago_total",
            "enabled": true,
            "variant": "feature",
            "size": "half"
          },
          {
            "id": "split_trabalho_capital",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          }
        ]
      },
      {
        "id": "S_IRPF_OTIMIZACAO",
        "title": "Otimização Tributária",
        "enabled": true,
        "summary": true,
        "summary_source": null,
        "cards": [
          {
            "id": "pgbl_capacidade",
            "enabled": true,
            "variant": "info",
            "size": "half"
          },
          {
            "id": "irpf_dependentes_declarados",
            "enabled": true,
            "variant": "neutral",
            "size": "half"
          },
          {
            "id": "irpf_dedutiveis_aplicados",
            "enabled": true,
            "variant": "info",
            "size": "full"
          }
        ]
      },
      {
        "id": "S9",
        "title": "Riscos e Proteção — Seguros Críticos",
        "enabled": true,
        "summary": true,
        "summary_source": "s9",
        "divider_before": true,
        "charts": [
          {
            "id": "bubble_riscos",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": [
          {
            "id": "hero_gap_protecao",
            "enabled": true,
            "variant": "critical",
            "size": "full"
          },
          {
            "id": "cobertura_seguros",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "sucessao",
            "enabled": true,
            "variant": "warn",
            "size": "half"
          },
          {
            "id": "acoes_mitigacao",
            "enabled": true,
            "variant": "highlight",
            "size": "half"
          }
        ]
      },
      {
        "id": "S10",
        "title": "Síntese Estratégica — Tarefas e Score",
        "enabled": true,
        "summary": true,
        "summary_source": "s10",
        "divider_before": true,
        "charts": [
          {
            "id": "top5_decisoes",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": [
          {
            "id": "pontos_fortes",
            "enabled": true,
            "variant": "success",
            "size": "half",
            "top_border": "accent"
          },
          {
            "id": "pontos_urgentes",
            "enabled": true,
            "variant": "critical",
            "size": "half",
            "top_border": "danger"
          },
          {
            "id": "equilibrio_cerbasi_ref",
            "enabled": false,
            "variant": "highlight",
            "size": "full"
          }
        ]
      },
      {
        "id": "S_parecer",
        "title": "Parecer do Planejador",
        "enabled": true,
        "summary": false,
        "divider_before": true,
        "data_source": "planner_review",
        "charts": [],
        "cards": []
      },
      {
        "id": "plano_de_acao",
        "title": "Plano de Ação — Decisões em Vigor",
        "enabled": true,
        "summary": false,
        "divider_before": true,
        "data_source": "decisions",
        "charts": [],
        "cards": []
      }
    ],
    "appendices": [
      {
        "id": "APP_A",
        "title": "Definições e Siglas",
        "enabled": true,
        "summary": true,
        "summary_source": null
      },
      {
        "id": "APP_B",
        "title": "Premissas Econômicas",
        "enabled": true,
        "summary": true,
        "summary_source": null,
        "cards": [
          {
            "id": "premissas_economicas",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          },
          {
            "id": "metodologias",
            "enabled": true,
            "variant": "neutral",
            "size": "full"
          }
        ]
      },
      {
        "id": "APP_C",
        "title": "Cenários de Estresse",
        "enabled": true,
        "optional": true,
        "summary": true,
        "summary_source": null,
        "charts": [],
        "cards": [
          {
            "id": "sensibilidade_ativos",
            "enabled": true,
            "variant": "feature",
            "size": "full"
          }
        ]
      },
      {
        "id": "APP_D",
        "title": "Referências e Recursos",
        "enabled": true,
        "summary": true,
        "summary_source": null,
        "cards": [
          {
            "id": "fontes_dados",
            "enabled": true,
            "variant": "neutral",
            "size": "half"
          },
          {
            "id": "metodologia_links",
            "enabled": true,
            "variant": "neutral",
            "size": "half"
          }
        ]
      },
      {
        "id": "APP_E",
        "title": "Próximos Ciclos e Roadmap",
        "enabled": true,
        "summary": true,
        "summary_source": null,
        "cards": [
          {
            "id": "proximos_ciclos",
            "enabled": true,
            "variant": "highlight",
            "size": "full"
          },
          {
            "id": "disclaimers",
            "enabled": true,
            "variant": "neutral",
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
    "top15_ativos": "chart-top15-ativos",
    "projecao_3cenarios": "chart-projecao-3cenarios",
    "renda_passiva": "chart-renda-passiva",
    "impostos_pj": "chart-impostos-pj",
    "bubble_riscos": "chart-bubble-riscos",
    "top5_decisoes": "chart-top5-decisoes",
    "cenarios_conjuge": "chart-cenarios-conjuge",
    "viagens": "chart-viagens",
    "renda_evolucao_multi_anos": "chart-renda-evolucao-multi-anos",
    "aliquota_efetiva_dual_gauge": "chart-aliquota-efetiva-dual-gauge"
  },
  "chart_titles": {
    "patrimonio_doughnut": "Composição Patrimonial",
    "waterfall_if": "Caminho para Independência Financeira",
    "receita_bar": "Receita por Fonte",
    "despesas_doughnut": "Despesas por Categoria",
    "fluxo_mensal": "Fluxo de Caixa Mensal",
    "receita_despesa_mensal": "Receita vs Despesa — Mês a Mês",
    "score_gauge": "Score Financeiro",
    "top15_ativos": "Top 15 Ativos Financeiros",
    "projecao_3cenarios": "Projeção Patrimonial — 3 Cenários",
    "renda_passiva": "Renda Passiva — Progresso até a Meta",
    "impostos_pj": "Tributário PJ — Cascata Fiscal",
    "bubble_riscos": "Mapa de Riscos",
    "top5_decisoes": "Decisões de Impacto",
    "cenarios_conjuge": "Cenários de Estresse — Sem renda do cônjuge",
    "viagens": "Orçamento de Viagens",
    "renda_evolucao_multi_anos": "Evolução da Renda — Multi-anos",
    "aliquota_efetiva_dual_gauge": "Alíquota Efetiva — RFB e Renda Total"
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
      "top15_ativos",
      "cenarios_conjuge",
      "viagens"
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

export const ALL_CARD_IDS = ["patrimonio_categorias", "posicao_informe_31_12", "exposicao_cambial", "receitas_fonte", "reserva_emergencia", "endividamento", "orcamento_prospectivo", "consumo_consciente", "diagnostico_comportamental", "equilibrio_cerbasi", "milhas", "protecao_kpi_hero", "protecao_bens", "protecao_gap_qualitativo", "protecao_apolices", "alocacao_atual_vs_alvo", "kpi_rentabilidade", "proventos_yield", "estrategia_aporte", "contrafluxo", "real_estate_yield", "previdencia_pgbl", "renda_anual_familiar", "ir_pago_total", "split_trabalho_capital", "pgbl_capacidade", "irpf_dependentes_declarados", "irpf_dedutiveis_aplicados", "hero_gap_protecao", "cobertura_seguros", "sucessao", "acoes_mitigacao", "pontos_fortes", "pontos_urgentes", "equilibrio_cerbasi_ref"] as const;
export type CardId = (typeof ALL_CARD_IDS)[number];

export const ALL_CHART_IDS = ["patrimonio_doughnut", "waterfall_if", "score_gauge", "fluxo_mensal", "receita_bar", "despesas_doughnut", "receita_despesa_mensal", "viagens", "protecao_premio_decomp", "top15_ativos", "cenarios_conjuge", "projecao_3cenarios", "renda_passiva", "impostos_pj", "renda_evolucao_multi_anos", "aliquota_efetiva_dual_gauge", "bubble_riscos", "top5_decisoes"] as const;
export type ChartId = (typeof ALL_CHART_IDS)[number];

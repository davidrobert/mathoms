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
  divider_before?: boolean;
  collapsible?: boolean;
}

export interface AppendixSpec {
  id: string;
  title: string;
  enabled: boolean;
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
  tatico?: NavGroupSpec[];
  usa?: NavGroupSpec[];
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
        "label_key": "Período analisado"
      },
      {
        "label_key": "Gerado em"
      },
      {
        "label_key": "Documentos"
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
            "section_id": "S1",
            "num": "1"
          },
          {
            "section_id": "S2",
            "num": "2"
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
    ],
    "tatico": [
      {
        "links": [
          {
            "section_id": "T1",
            "num": "T1"
          },
          {
            "section_id": "T2",
            "num": "T2"
          },
          {
            "section_id": "T3",
            "num": "T3"
          },
          {
            "section_id": "T4",
            "num": "T4"
          },
          {
            "section_id": "T5",
            "num": "T5"
          },
          {
            "section_id": "T6",
            "num": "T6"
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
        ],
        "comparisons": [
          {
            "id": "comparisons_s1",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ],
        "changelog": [
          {
            "id": "changelog_s1",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ]
      },
      {
        "id": "S2",
        "title": "Fluxo de Caixa — Receitas e Despesas",
        "enabled": true,
        "summary": true,
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
        ],
        "comparisons": [
          {
            "id": "comparisons_s2",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ],
        "changelog": [
          {
            "id": "changelog_s2",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ]
      },
      {
        "id": "S3",
        "title": "Investimentos — Carteira Financeira",
        "enabled": true,
        "summary": true,
        "divider_before": true,
        "charts": [
          {
            "id": "alocacao_atual",
            "enabled": true,
            "row": "alocacao",
            "conclusion": true
          },
          {
            "id": "alocacao_alvo",
            "enabled": true,
            "row": "alocacao",
            "conclusion": true
          },
          {
            "id": "top15_ativos",
            "enabled": true,
            "conclusion": true
          },
          {
            "id": "mariana_cenarios",
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
        ],
        "comparisons": [
          {
            "id": "comparisons_s3",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ],
        "changelog": [
          {
            "id": "changelog_s3",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ]
      },
      {
        "id": "S4",
        "title": "Real Estate — Imóveis e Renda Passiva",
        "enabled": true,
        "summary": true,
        "divider_before": true,
        "charts": [
          {
            "id": "yield_imoveis",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": []
      },
      {
        "id": "S7",
        "title": "Independência Financeira — Projeção de Longo Prazo",
        "enabled": true,
        "summary": true,
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
        "id": "S9",
        "title": "Riscos e Proteção — Seguros Críticos",
        "enabled": true,
        "summary": true,
        "divider_before": true,
        "charts": [
          {
            "id": "bubble_riscos",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": []
      },
      {
        "id": "S10",
        "title": "Síntese Estratégica — Tarefas e Score",
        "enabled": true,
        "summary": true,
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
        "enabled": true,
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
        "title": "Cenários de Sensibilidade",
        "enabled": true,
        "charts": [
          {
            "id": "cenarios_cambiais",
            "enabled": false,
            "conclusion": true
          }
        ],
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
        "collapsible": true,
        "data_source": "dashboard.despesas_por_categoria",
        "charts": [],
        "cards": []
      },
      {
        "id": "T2",
        "title": "Aportes e Investimentos",
        "enabled": true,
        "collapsible": true,
        "data_source": "dashboard.aportes + dashboard.investimentos_delta",
        "charts": [],
        "cards": [],
        "comparisons": [
          {
            "id": "comparisons_t2",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ],
        "changelog": [
          {
            "id": "changelog_t2",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ]
      },
      {
        "id": "T3",
        "title": "Checklist de Tarefas",
        "enabled": true,
        "collapsible": true,
        "data_source": "dashboard.tarefas + dashboard.tarefas_status",
        "charts": [],
        "cards": [],
        "comparisons": [
          {
            "id": "comparisons_t3",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ],
        "changelog": [
          {
            "id": "changelog_t3",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ]
      },
      {
        "id": "T4",
        "title": "Alertas e Pendências",
        "enabled": true,
        "collapsible": true,
        "data_source": "dashboard.alertas",
        "charts": [],
        "cards": []
      },
      {
        "id": "T5",
        "title": "Próximos Passos",
        "enabled": true,
        "collapsible": true,
        "data_source": "dashboard.proximos_15d",
        "charts": [],
        "cards": [],
        "comparisons": [
          {
            "id": "comparisons_t5",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ],
        "changelog": [
          {
            "id": "changelog_t5",
            "enabled": false,
            "deferred_until": "v2.D.1 SnapshotChangelogBuilder"
          }
        ]
      },
      {
        "id": "T6",
        "title": "Notas e Observações",
        "enabled": true,
        "collapsible": true,
        "data_source": "dashboard.notas",
        "charts": [],
        "cards": []
      },
      {
        "id": "plano_de_acao",
        "title": "Plano de Ação",
        "enabled": true,
        "collapsible": true,
        "data_source": "decisions",
        "charts": [],
        "cards": []
      }
    ]
  },
  "usa": {
    "sections": [
      {
        "id": "U1",
        "title": "Mudança EUA — Estrutura F1/F2 e Custos",
        "enabled": false,
        "summary": true,
        "charts": [
          {
            "id": "custos_f1f2",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": []
      },
      {
        "id": "U2",
        "title": "Green Card — EB2-NIW e Compliance",
        "enabled": false,
        "summary": true,
        "divider_before": true,
        "charts": [
          {
            "id": "cenarios_cambiais",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": []
      },
      {
        "id": "U3",
        "title": "NCLEX Roadmap — Licenciamento RN",
        "enabled": false,
        "summary": true,
        "divider_before": true,
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
        "enabled": false,
        "summary": true,
        "divider_before": true,
        "charts": [
          {
            "id": "mariana_cenarios_usa",
            "enabled": true,
            "conclusion": true
          }
        ],
        "cards": [
          {
            "id": "simulacao_mariana",
            "enabled": true,
            "variant": "warn",
            "size": "full",
            "top_border": "accent"
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

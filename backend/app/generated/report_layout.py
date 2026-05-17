"""GENERATED FILE — do not edit by hand.

Source: config/report_layout.yaml
Regenerate: python3 dev/codegen_report_layout.py
Schema: config/schemas/report_layout.schema.json (ADR-076)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

CardVariant = Literal[
    "highlight",
    "feature",
    "success",
    "warn",
    "critical",
    "primary",
    "neutral",
    "info",
    "top-danger",
    "top-accent",
]

CardSize = Literal["full", "half"]

ReportMode = Literal["estrategico"]

TopBorder = Literal["danger", "accent"]

ChartHeight = int | Literal["auto"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CardSpec(_Base):
    id: str
    enabled: bool
    variant: CardVariant | None = None
    size: CardSize | None = None
    top_border: TopBorder | None = None
    comparison_anchor_id: str | None = None


class ChartSpec(_Base):
    id: str
    enabled: bool
    row: str | None = None
    conclusion: bool | None = None
    context: bool | None = None
    period_toggle: bool | None = None
    height: ChartHeight | None = None


class ComparisonSpec(_Base):
    """Report Premium UI v2.1 — placeholder de <ComparisonBlock> por seção (deferred_until v2.8)."""

    id: str
    enabled: bool
    deferred_until: str | None = None


class ChangelogSpec(_Base):
    """Report Premium UI v2.1 — placeholder de <ChangelogList> por seção (deferred_until v2.8)."""

    id: str
    enabled: bool
    deferred_until: str | None = None


class SectionSpec(_Base):
    id: str
    title: str
    enabled: bool
    charts: list[ChartSpec] = []
    cards: list[CardSpec] = []
    comparisons: list[ComparisonSpec] = []
    changelog: list[ChangelogSpec] = []
    data_source: str | None = None
    summary: bool | None = None
    divider_before: bool | None = None
    collapsible: bool | None = None


class AppendixSpec(_Base):
    id: str
    title: str
    enabled: bool
    charts: list[ChartSpec] = []
    cards: list[CardSpec] = []


class KpiSpec(_Base):
    id: str
    label: str
    enabled: bool


class CoverMetaSpec(_Base):
    label_key: str
    value_key: str | None = None
    conditional_on: str | None = None


class CoverSpec(_Base):
    enabled: bool
    badge: str | None = None
    title_key: str | None = None
    subtitle_key: str | None = None
    meta: list[CoverMetaSpec] = []


class NavLinkSpec(_Base):
    section_id: str
    num: str | None = None
    is_appendix: bool | None = None


class NavGroupSpec(_Base):
    label: str | None = None
    links: list[NavLinkSpec]


class NavigationSpec(_Base):
    estrategico: list[NavGroupSpec] = []


class Estrategico(_Base):
    sections: list[SectionSpec]
    appendices: list[AppendixSpec] = []


class ReportLayout(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str
    estrategico: Estrategico
    cover: CoverSpec | None = None
    navigation: NavigationSpec | None = None
    footer: bool | None = None
    export_toolbar: bool | None = None
    chart_palette: list[str] | None = None
    chart_canvas_map: dict[str, str] | None = None
    chart_titles: dict[str, str] | None = None

LAYOUT_DICT: dict = {   'version': '1.2',
    'cover': {   'enabled': True,
                 'badge': 'Relatório Premium',
                 'meta': [   {'label_key': 'Família', 'conditional_on': 'workspace_family_surname'},
                             {'label_key': 'Período'},
                             {'label_key': 'Gerado em'},
                             {'label_key': 'Versão'}]},
    'navigation': {   'estrategico': [   {   'label': 'Visão geral',
                                             'links': [   {'section_id': 'S1', 'num': '1'},
                                                          {'section_id': 'S2', 'num': '2'},
                                                          {'section_id': 'S3', 'num': '3'}]},
                                         {   'label': 'Detalhes',
                                             'links': [   {'section_id': 'S4', 'num': '4'},
                                                          {'section_id': 'S7', 'num': '7'},
                                                          {'section_id': 'S8', 'num': '8'},
                                                          {   'section_id': 'S_IRPF_RENDA',
                                                              'num': '8.1'},
                                                          {   'section_id': 'S_IRPF_OTIMIZACAO',
                                                              'num': '8.2'},
                                                          {'section_id': 'S9', 'num': '9'}]},
                                         {   'label': 'Síntese',
                                             'links': [   {'section_id': 'S10', 'num': '10'},
                                                          {   'section_id': 'S_parecer',
                                                              'num': '10.1'},
                                                          {   'section_id': 'plano_de_acao',
                                                              'num': '11'}]},
                                         {   'label': 'Apêndices',
                                             'links': [   {   'section_id': 'APP_A',
                                                              'num': 'A',
                                                              'is_appendix': True},
                                                          {   'section_id': 'APP_B',
                                                              'num': 'B',
                                                              'is_appendix': True},
                                                          {   'section_id': 'APP_C',
                                                              'num': 'C',
                                                              'is_appendix': True},
                                                          {   'section_id': 'APP_D',
                                                              'num': 'D',
                                                              'is_appendix': True},
                                                          {   'section_id': 'APP_E',
                                                              'num': 'E',
                                                              'is_appendix': True}]}]},
    'footer': True,
    'export_toolbar': True,
    'estrategico': {   'sections': [   {   'id': 'S1',
                                           'title': 'Patrimônio — Estrutura e Composição',
                                           'enabled': True,
                                           'summary': True,
                                           'charts': [   {   'id': 'patrimonio_doughnut',
                                                             'enabled': True,
                                                             'conclusion': True,
                                                             'context': True},
                                                         {   'id': 'waterfall_if',
                                                             'enabled': True,
                                                             'conclusion': True},
                                                         {   'id': 'score_gauge',
                                                             'enabled': True,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'patrimonio_categorias',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'},
                                                        {   'id': 'receitas_fonte',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'},
                                                        {   'id': 'reserva_emergencia',
                                                            'enabled': True,
                                                            'variant': 'warn',
                                                            'size': 'half'},
                                                        {   'id': 'endividamento',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'half'}],
                                           'comparisons': [   {   'id': 'comparisons_s1',
                                                                  'enabled': True}],
                                           'changelog': [{'id': 'changelog_s1', 'enabled': True}]},
                                       {   'id': 'S2',
                                           'title': 'Fluxo de Caixa — Receitas e Despesas',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'fluxo_mensal',
                                                             'enabled': True,
                                                             'conclusion': True,
                                                             'period_toggle': True},
                                                         {   'id': 'receita_bar',
                                                             'enabled': True,
                                                             'conclusion': True,
                                                             'period_toggle': True},
                                                         {   'id': 'despesas_doughnut',
                                                             'enabled': True,
                                                             'conclusion': True,
                                                             'period_toggle': True},
                                                         {   'id': 'receita_despesa_mensal',
                                                             'enabled': True,
                                                             'conclusion': True,
                                                             'period_toggle': True},
                                                         {   'id': 'viagens',
                                                             'enabled': True,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'orcamento_prospectivo',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'},
                                                        {   'id': 'consumo_consciente',
                                                            'enabled': True,
                                                            'variant': 'success',
                                                            'size': 'full'},
                                                        {   'id': 'diagnostico_comportamental',
                                                            'enabled': True,
                                                            'variant': 'primary',
                                                            'size': 'half'},
                                                        {   'id': 'equilibrio_cerbasi',
                                                            'enabled': True,
                                                            'variant': 'highlight',
                                                            'size': 'half'},
                                                        {   'id': 'milhas',
                                                            'enabled': False,
                                                            'variant': 'feature',
                                                            'size': 'half'}],
                                           'comparisons': [   {   'id': 'comparisons_s2',
                                                                  'enabled': True}],
                                           'changelog': [{'id': 'changelog_s2', 'enabled': True}]},
                                       {   'id': 'S3',
                                           'title': 'Investimentos — Carteira Financeira',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'alocacao_atual',
                                                             'enabled': False,
                                                             'row': 'alocacao',
                                                             'conclusion': True},
                                                         {   'id': 'alocacao_alvo',
                                                             'enabled': False,
                                                             'row': 'alocacao',
                                                             'conclusion': True},
                                                         {   'id': 'top15_ativos',
                                                             'enabled': True,
                                                             'conclusion': True},
                                                         {   'id': 'cenarios_conjuge',
                                                             'enabled': True,
                                                             'conclusion': True},
                                                         {   'id': 'viagens',
                                                             'enabled': False,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'alocacao_atual_vs_alvo',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'},
                                                        {   'id': 'investimentos_classe',
                                                            'enabled': False,
                                                            'variant': 'feature',
                                                            'size': 'full'},
                                                        {   'id': 'kpi_rentabilidade',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'half'},
                                                        {   'id': 'estrategia_aporte',
                                                            'enabled': True,
                                                            'variant': 'highlight',
                                                            'size': 'full'},
                                                        {   'id': 'contrafluxo',
                                                            'enabled': True,
                                                            'variant': 'primary',
                                                            'size': 'half'}],
                                           'comparisons': [   {   'id': 'comparisons_s3',
                                                                  'enabled': True}],
                                           'changelog': [{'id': 'changelog_s3', 'enabled': True}]},
                                       {   'id': 'S4',
                                           'title': 'Real Estate — Imóveis e Renda Passiva',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [],
                                           'cards': [   {   'id': 'real_estate_yield',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'}]},
                                       {   'id': 'S7',
                                           'title': 'Independência Financeira — Projeção de Longo '
                                                    'Prazo',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'projecao_3cenarios',
                                                             'enabled': True,
                                                             'conclusion': True},
                                                         {   'id': 'renda_passiva',
                                                             'enabled': True,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'previdencia_pgbl',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'}]},
                                       {   'id': 'S8',
                                           'title': 'Previdência — PGBL e Fiscalidade',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'impostos_pj',
                                                             'enabled': True,
                                                             'conclusion': True,
                                                             'period_toggle': True}],
                                           'cards': []},
                                       {   'id': 'S_IRPF_RENDA',
                                           'title': 'Renda Anual e Impostos',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'renda_evolucao_multi_anos',
                                                             'enabled': True,
                                                             'conclusion': True},
                                                         {   'id': 'aliquota_efetiva_dual_gauge',
                                                             'enabled': True,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'renda_anual_familiar',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'half'},
                                                        {   'id': 'ir_pago_total',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'half'},
                                                        {   'id': 'split_trabalho_capital',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'}]},
                                       {   'id': 'S_IRPF_OTIMIZACAO',
                                           'title': 'Otimização Tributária',
                                           'enabled': True,
                                           'summary': True,
                                           'cards': [   {   'id': 'pgbl_capacidade',
                                                            'enabled': True,
                                                            'variant': 'info',
                                                            'size': 'half'},
                                                        {   'id': 'irpf_dependentes_declarados',
                                                            'enabled': True,
                                                            'variant': 'neutral',
                                                            'size': 'half'},
                                                        {   'id': 'irpf_dedutiveis_aplicados',
                                                            'enabled': True,
                                                            'variant': 'info',
                                                            'size': 'full'}]},
                                       {   'id': 'S9',
                                           'title': 'Riscos e Proteção — Seguros Críticos',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'bubble_riscos',
                                                             'enabled': True,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'hero_gap_protecao',
                                                            'enabled': True,
                                                            'variant': 'critical',
                                                            'size': 'full'},
                                                        {   'id': 'cobertura_seguros',
                                                            'enabled': True,
                                                            'variant': 'feature',
                                                            'size': 'full'},
                                                        {   'id': 'sucessao',
                                                            'enabled': True,
                                                            'variant': 'warn',
                                                            'size': 'half'},
                                                        {   'id': 'acoes_mitigacao',
                                                            'enabled': True,
                                                            'variant': 'highlight',
                                                            'size': 'half'}]},
                                       {   'id': 'S10',
                                           'title': 'Síntese Estratégica — Tarefas e Score',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'charts': [   {   'id': 'top5_decisoes',
                                                             'enabled': True,
                                                             'conclusion': True}],
                                           'cards': [   {   'id': 'pontos_fortes',
                                                            'enabled': True,
                                                            'variant': 'success',
                                                            'size': 'half',
                                                            'top_border': 'accent'},
                                                        {   'id': 'pontos_urgentes',
                                                            'enabled': True,
                                                            'variant': 'critical',
                                                            'size': 'half',
                                                            'top_border': 'danger'},
                                                        {   'id': 'equilibrio_cerbasi_ref',
                                                            'enabled': False,
                                                            'variant': 'highlight',
                                                            'size': 'full'}]},
                                       {   'id': 'S_parecer',
                                           'title': 'Parecer do Planejador',
                                           'enabled': True,
                                           'summary': False,
                                           'divider_before': True,
                                           'data_source': 'planner_review',
                                           'charts': [],
                                           'cards': []},
                                       {   'id': 'plano_de_acao',
                                           'title': 'Plano de Ação — Decisões em Vigor',
                                           'enabled': True,
                                           'summary': True,
                                           'divider_before': True,
                                           'data_source': 'decisions',
                                           'charts': [],
                                           'cards': []}],
                       'appendices': [   {   'id': 'APP_A',
                                             'title': 'Definições e Siglas',
                                             'enabled': True},
                                         {   'id': 'APP_B',
                                             'title': 'Premissas Econômicas',
                                             'enabled': True,
                                             'cards': [   {   'id': 'premissas_economicas',
                                                              'enabled': True,
                                                              'variant': 'feature',
                                                              'size': 'full'},
                                                          {   'id': 'metodologias',
                                                              'enabled': True,
                                                              'variant': 'neutral',
                                                              'size': 'full'}]},
                                         {   'id': 'APP_C',
                                             'title': 'Cenários de Estresse',
                                             'enabled': True,
                                             'optional': True,
                                             'charts': [],
                                             'cards': [   {   'id': 'sensibilidade_ativos',
                                                              'enabled': True,
                                                              'variant': 'feature',
                                                              'size': 'full'}]},
                                         {   'id': 'APP_D',
                                             'title': 'Referências e Recursos',
                                             'enabled': True,
                                             'cards': [   {   'id': 'fontes_dados',
                                                              'enabled': True,
                                                              'variant': 'neutral',
                                                              'size': 'half'},
                                                          {   'id': 'metodologia_links',
                                                              'enabled': True,
                                                              'variant': 'neutral',
                                                              'size': 'half'}]},
                                         {   'id': 'APP_E',
                                             'title': 'Próximos Ciclos e Roadmap',
                                             'enabled': True,
                                             'cards': [   {   'id': 'proximos_ciclos',
                                                              'enabled': True,
                                                              'variant': 'highlight',
                                                              'size': 'full'},
                                                          {   'id': 'disclaimers',
                                                              'enabled': True,
                                                              'variant': 'neutral',
                                                              'size': 'full'}]}]},
    'chart_palette': [   '#1A3A5C',
                         '#2A9D8F',
                         '#15803D',
                         '#F4A261',
                         '#B91C1C',
                         '#457B9D',
                         '#8338EC',
                         '#A8DADC',
                         '#E63946',
                         '#1E6E8F',
                         '#E76F51',
                         '#06B6D4',
                         '#FFB703',
                         '#7C3AED',
                         '#219EBC',
                         '#6366F1',
                         '#EC4899',
                         '#84CC16',
                         '#F97316',
                         '#8B5CF6'],
    'chart_canvas_map': {   'patrimonio_doughnut': 'chart-patrimonio-doughnut',
                            'waterfall_if': 'chart-waterfall-if',
                            'receita_bar': 'chart-receita-bar',
                            'despesas_doughnut': 'chart-despesas-doughnut',
                            'fluxo_mensal': 'chart-fluxo-mensal',
                            'receita_despesa_mensal': 'chart-receita-despesa-mensal',
                            'score_gauge': 'chart-score-gauge',
                            'alocacao_atual': 'chart-alocacao-atual',
                            'alocacao_alvo': 'chart-alocacao-alvo',
                            'top15_ativos': 'chart-top15-ativos',
                            'projecao_3cenarios': 'chart-projecao-3cenarios',
                            'renda_passiva': 'chart-renda-passiva',
                            'impostos_pj': 'chart-impostos-pj',
                            'bubble_riscos': 'chart-bubble-riscos',
                            'top5_decisoes': 'chart-top5-decisoes',
                            'cenarios_conjuge': 'chart-cenarios-conjuge',
                            'viagens': 'chart-viagens',
                            'renda_evolucao_multi_anos': 'chart-renda-evolucao-multi-anos',
                            'aliquota_efetiva_dual_gauge': 'chart-aliquota-efetiva-dual-gauge'},
    'chart_titles': {   'patrimonio_doughnut': 'Composição Patrimonial',
                        'waterfall_if': 'Caminho para Independência Financeira',
                        'receita_bar': 'Receita por Fonte',
                        'despesas_doughnut': 'Despesas por Categoria',
                        'fluxo_mensal': 'Fluxo de Caixa Mensal',
                        'receita_despesa_mensal': 'Receita vs Despesa — Mês a Mês',
                        'score_gauge': 'Score Financeiro',
                        'alocacao_atual': 'Alocação Atual',
                        'alocacao_alvo': 'Alocação Alvo',
                        'top15_ativos': 'Top 15 Ativos Financeiros',
                        'projecao_3cenarios': 'Projeção Patrimonial — 3 Cenários',
                        'renda_passiva': 'Renda Passiva — Progresso até a Meta',
                        'impostos_pj': 'Tributário PJ — Cascata Fiscal',
                        'bubble_riscos': 'Mapa de Riscos',
                        'top5_decisoes': 'Top 5 Decisões de Impacto',
                        'cenarios_conjuge': 'Cenários de Estresse — Sem renda do cônjuge',
                        'viagens': 'Orçamento de Viagens',
                        'renda_evolucao_multi_anos': 'Evolução da Renda — Multi-anos',
                        'aliquota_efetiva_dual_gauge': 'Alíquota Efetiva — RFB e Renda Total'},
    'section_charts': {   1: ['patrimonio_doughnut', 'waterfall_if'],
                          2: [   'fluxo_mensal',
                                 'receita_bar',
                                 'despesas_doughnut',
                                 'receita_despesa_mensal',
                                 'score_gauge'],
                          3: [   'alocacao_atual',
                                 'alocacao_alvo',
                                 'top15_ativos',
                                 'cenarios_conjuge',
                                 'viagens'],
                          7: ['projecao_3cenarios', 'renda_passiva'],
                          8: ['impostos_pj'],
                          9: ['bubble_riscos'],
                          10: ['top5_decisoes']},
    'dark_mode': {   'css_vars': {   'color-bg': '#0F172A',
                                     'color-surface': '#1E293B',
                                     'color-text': '#E2E8F0',
                                     'color-text-muted': '#94A3B8',
                                     'color-border': '#334155',
                                     'color-primary': '#2E86AB',
                                     'color-light': '#1E3A5F'},
                     'table': {   'row_even': '#1A2332',
                                  'row_hover': '#243447',
                                  'th_bg': '#1E3A5F',
                                  'th_color': '#E2E8F0',
                                  'td_total': '#1A2332',
                                  'td_border': '#334155'},
                     'alerts': {   'danger_bg': '#2D1B1B',
                                   'danger_color': '#FCA5A5',
                                   'warning_bg': '#2D2410',
                                   'warning_color': '#FCD34D',
                                   'success_bg': '#1A2D1A',
                                   'success_color': '#86EFAC',
                                   'info_bg': '#1A2440',
                                   'info_color': '#93C5FD'},
                     'badges': {   'green_bg': '#16533480',
                                   'green_color': '#86EFAC',
                                   'red_bg': '#991B1B80',
                                   'red_color': '#FCA5A5',
                                   'yellow_bg': '#92400E80',
                                   'yellow_color': '#FCD34D',
                                   'blue_bg': '#1E40AF80',
                                   'blue_color': '#93C5FD'},
                     'kpi': {'blue': '#60A5FA', 'green': '#4ADE80', 'red': '#F87171'},
                     'headings_color': '#F1F5F9',
                     'strong_color': '#F1F5F9',
                     'section_summary_bg': '#1A2440',
                     'section_summary_color': '#CBD5E1',
                     'chart_conclusion_bg': '#1A2440',
                     'chart_conclusion_border': '#2E86AB',
                     'chart_context_color': '#94A3B8',
                     'export_toolbar_bg': 'linear-gradient(135deg, #0B1929, #132337)',
                     'progress_bar_bg': '#334155',
                     'compare_col2_bg': '#2D1B1B',
                     'compare_col3_bg': '#1A2D1A',
                     'chart_theme': {   'dark': {'text_color': '#94A3B8', 'grid_color': '#334155'},
                                        'light': {   'text_color': '#64748B',
                                                     'grid_color': '#E2E8F0'}}},
    'version_fallback': 'v5.3'}

LAYOUT: ReportLayout = ReportLayout.model_validate(LAYOUT_DICT)

ALL_CARD_IDS: tuple[str, ...] = ('patrimonio_categorias', 'receitas_fonte', 'reserva_emergencia', 'endividamento', 'orcamento_prospectivo', 'consumo_consciente', 'diagnostico_comportamental', 'equilibrio_cerbasi', 'milhas', 'alocacao_atual_vs_alvo', 'investimentos_classe', 'kpi_rentabilidade', 'estrategia_aporte', 'contrafluxo', 'real_estate_yield', 'previdencia_pgbl', 'renda_anual_familiar', 'ir_pago_total', 'split_trabalho_capital', 'pgbl_capacidade', 'irpf_dependentes_declarados', 'irpf_dedutiveis_aplicados', 'hero_gap_protecao', 'cobertura_seguros', 'sucessao', 'acoes_mitigacao', 'pontos_fortes', 'pontos_urgentes', 'equilibrio_cerbasi_ref')
ALL_CHART_IDS: tuple[str, ...] = ('patrimonio_doughnut', 'waterfall_if', 'score_gauge', 'fluxo_mensal', 'receita_bar', 'despesas_doughnut', 'receita_despesa_mensal', 'viagens', 'alocacao_atual', 'alocacao_alvo', 'top15_ativos', 'cenarios_conjuge', 'projecao_3cenarios', 'renda_passiva', 'impostos_pj', 'renda_evolucao_multi_anos', 'aliquota_efetiva_dual_gauge', 'bubble_riscos', 'top5_decisoes')

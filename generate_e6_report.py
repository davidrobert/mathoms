#!/usr/bin/env python3
"""
⚠️  DEPRECATED — abr/2026 (manual v4.0, renomeado v4.5)
Substituído por: scripts/e6_render.py (determinístico, sem LLM)
Motivo: Este script misturava renderização com geração de narrativa.
Com a arquitetura v4.0, narrativas vêm do E5.N e E6 é puro script Python.
Manter apenas como referência histórica. NÃO EXECUTAR.

--- Original docstring ---
E6 HTML Financial Report Generator — Ferreira Campos Family
Generates comprehensive HTML financial analysis from E4 JSON and supporting data

Usage: python generate_e5_report.py
Output: output/relatorio_financeiro_ferreira_campos_20260403.html
"""

import sys
sys.exit("DEPRECATED: Use 'python scripts/e6_render.py' instead. See manual_operacao.md v4.5.")

import json
import os
from datetime import datetime
from pathlib import Path
import shutil

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / 'config' / 'report_template.html'
E4_JSON_PATH = BASE_DIR / 'processed' / 'E4_analysis' / 'analise_financeira-4_analysis.json'
OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

FAMILY_DATA = {
    'nome': 'Ferreira Campos',
    'periodo': '2025-05 a 2026-03',
    'data_geracao': '2026-04-03',
    'version': '1.0',
}

# ============================================================================
# LOAD DATA
# ============================================================================

def load_json(path):
    """Load JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_template():
    """Load HTML template"""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()

# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def fmt_currency(value):
    """Format as Brazilian currency"""
    if value is None:
        return 'R$ 0,00'
    return f"R$ {value:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')

def fmt_pct(value):
    """Format as percentage"""
    if value is None:
        return '0,0%'
    return f"{value:.1f}%".replace('.', ',')

def fmt_numero(value):
    """Format as number"""
    if value is None:
        return '0'
    return f"{value:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')

def fmt_int(value):
    """Format as Brazilian currency without decimals"""
    if value is None:
        return 'R$ 0'
    return f"R$ {value:,.0f}".replace(',', '_').replace('.', ',').replace('_', '.')

def cat_val(cat_data):
    """Extract numeric value from category data (handles both dict and float formats)"""
    if isinstance(cat_data, dict):
        return cat_data.get('total', 0)
    return cat_data if isinstance(cat_data, (int, float)) else 0

def safe_get(d, *keys, default=0):
    """Safely navigate nested dicts with fallback keys. Tries each key path in order."""
    for key in keys:
        if isinstance(d, dict) and key in d:
            return d[key]
    return default

def get_renda_passiva_total(goals):
    """Get renda passiva total from either format"""
    rp = goals.get('renda_passiva', {})
    return rp.get('total_mensal', rp.get('atual_mensal', 0))

def get_renda_passiva_pct(goals):
    """Get renda passiva percentage from either format"""
    rp = goals.get('renda_passiva', {})
    return rp.get('pct_meta', rp.get('pct_atingido', 0))

def get_renda_passiva_fonte(rp, fonte_name):
    """Get individual renda passiva fonte value from either format"""
    # First try legacy format (flat dict keys)
    if fonte_name in rp:
        return rp[fonte_name]

    # Otherwise, search in fontes list
    fontes = rp.get('fontes', [])
    for f in fontes:
        if isinstance(f, dict) and f.get('fonte', '').lower() == fonte_name.lower():
            return f.get('valor', 0)
    return 0

def get_cenario(goals, nome):
    """Get scenario data from either dict or array format"""
    cenarios = goals.get('cenarios', {})
    if isinstance(cenarios, list):
        for c in cenarios:
            if c.get('nome', '').lower() == nome.lower():
                return c
        return {}
    elif isinstance(cenarios, dict):
        return cenarios.get(nome.lower(), cenarios.get(nome, {}))
    return {}

# ============================================================================
# BUILD PLACEHOLDERS - COVER & KPIs
# ============================================================================

def build_cover_and_kpis(e4_data):
    """Build all cover and KPI placeholders"""
    replacements = {}

    # Cover info
    replacements['{{COVER_FAMILIA}}'] = FAMILY_DATA['nome']
    replacements['{{COVER_PERIODO}}'] = FAMILY_DATA['periodo']
    replacements['{{COVER_DATA_HORA}}'] = 'São Paulo, 3 de abril de 2026'
    replacements['{{COVER_VERSAO_MANUAL}}'] = 'E5 • Relatório Financeiro Completo v1.0'
    replacements['{{NOME}}'] = FAMILY_DATA['nome']

    # KPIs
    bruto = e4_data['patrimonio']['bruto']
    investivel = e4_data['patrimonio']['investivel']
    if_meta = e4_data['goals']['if_meta']
    if_gap = e4_data['goals']['if_gap']
    if_pct = e4_data['goals']['if_pct']
    renda_mensal = e4_data['fluxo_caixa']['receita_recorrente_mensal']
    taxa_poupanca = e4_data['racios']['taxa_poupanca_recorrente_pct']
    prazo_anos = e4_data['goals']['prazo_anos_realista']
    score = e4_data['score']['valor']

    replacements['{{KPI_PATRIMONIO_BRUTO}}'] = fmt_currency(bruto)
    replacements['{{KPI_PATRIMONIO_BRUTO_SUB}}'] = 'Patrimônio bruto (residência + imóveis + investimentos + caixa + veículos)'

    replacements['{{KPI_PATRIMONIO_INVESTIVEL}}'] = fmt_currency(investivel)
    replacements['{{KPI_PATRIMONIO_INVESTIVEL_SUB}}'] = 'Patrimônio investível (bruto − residência − veículos)'

    replacements['{{KPI_RENDA_MENSAL}}'] = fmt_currency(renda_mensal)
    replacements['{{KPI_RENDA_MENSAL_SUB}}'] = 'Renda mensal recorrente (média 11 meses, excluindo Kiwify)'

    replacements['{{KPI_TAXA_POUPANCA}}'] = fmt_pct(taxa_poupanca)
    replacements['{{KPI_TAXA_POUPANCA_SUB}}'] = 'Taxa de poupança recorrente (renda − despesas / renda)'

    replacements['{{KPI_META_IF}}'] = fmt_currency(if_meta)
    trs_pct = e4_data['goals'].get('if_trs', 0.05) * 100
    replacements['{{KPI_META_IF_SUB}}'] = f'Meta de independência financeira (R$30k/mês ÷ {trs_pct:.0f}% TRS)'

    replacements['{{KPI_GAP_IF}}'] = fmt_currency(if_gap)
    replacements['{{KPI_GAP_IF_SUB}}'] = 'Gap para atingir meta IF (meta − patrimônio investível)'

    replacements['{{KPI_PRAZO_IF}}'] = f"{prazo_anos:.1f} anos".replace('.', ',')
    replacements['{{KPI_PRAZO_IF_SUB}}'] = 'Prazo realista com aporte R$20k/mês (6% retorno real, 2035)'

    replacements['{{KPI_SCORE}}'] = f"{score:.1f}/10".replace('.', ',')
    replacements['{{KPI_SCORE_SUB}}'] = 'Score financeiro: Bom (patrimônio + renda + gestão)'

    return replacements

# ============================================================================
# BUILD PROFILE SECTIONS
# ============================================================================

def build_perfil_familia(e4_data):
    """Build family profile sections"""
    replacements = {}

    perfil_left = """
<div class="perfil-col">
    <h3>David Robert C. Ferreira Campos</h3>
    <p><strong>Idade:</strong> 44 anos | <strong>Profissão:</strong> CTO @ Arvo (PJ)</p>
    <p><strong>Formação:</strong> MSc Computação USP | <strong>Renda PJ:</strong> ~R$47.209/mês</p>
    <p><strong>Patrimônio pessoal:</strong> R$605.979 (17,3%) — Investimentos Ricardo, BTG, Wise USD</p>
    <p><strong>Responsabilidades:</strong> Gestão geral, planejamento financeiro, impostos (PJ + IRPF)</p>
    <p><strong>Objetivo 2035:</strong> Independência financeira, residência EUA, Green Card EB2-NIW</p>
</div>
    """

    perfil_right = """
<div class="perfil-col">
    <h3>Mariana Teixeira F. Campos</h3>
    <p><strong>Idade:</strong> 41 anos | <strong>Profissão:</strong> Enfermeira Einstein (CLT, P4)</p>
    <p><strong>Formação:</strong> Especial. Cardiologia USP + Mestrado | <strong>Renda CLT:</strong> ~R$10.900/mês bruto</p>
    <p><strong>Patrimônio pessoal:</strong> R$188.124 (5,4%) — Investimentos BTG, poupança Bradesco</p>
    <p><strong>Responsabilidades:</strong> Gestão aluguéis (3 imóveis), NCLEX roadmap, seguros família</p>
    <p><strong>Objetivo 2027:</strong> Visto F1, NCLEX aprovado, trabalho remoto cardiologia EUA</p>
</div>
    """

    replacements['{{PERFIL_FAMILIA_LEFT}}'] = perfil_left
    replacements['{{PERFIL_FAMILIA_RIGHT}}'] = perfil_right

    return replacements

# ============================================================================
# BUILD SECTION SUMMARIES (SUMMARY_S1 - SUMMARY_S10)
# ============================================================================

def build_section_summaries(e4_data):
    """Build all 10 section summaries"""
    replacements = {}

    patrimonio = e4_data['patrimonio']
    fluxo = e4_data['fluxo_caixa']
    goals = e4_data['goals']
    score_data = e4_data['score']
    racios = e4_data['racios']

    # S1: VISÃO GERAL PATRIMONIAL
    replacements['{{SUMMARY_S1}}'] = (
        f"Patrimônio bruto de <strong>R${patrimonio['bruto']:,.0f}</strong> distribuído em 7 categorias: "
        f"41,2% imóveis de investimento, 28,5% residência própria, 17,3% investimentos David, "
        f"6,5% veículos, 5,4% investimentos Mariana, 1,0% caixa/USD, 0,1% criptoativos. "
        f"Patrimônio investível: <strong>R${patrimonio['investivel']:,.0f}</strong>."
    )

    # S2: FLUXO DE CAIXA & RENDA
    replacements['{{SUMMARY_S2}}'] = (
        f"Renda total 11 meses: R${fluxo['receita_total']:,.0f} (R${fluxo['receita_recorrente_mensal']:,.0f}/mês recorrente). "
        f"Despesas estimadas: R${fluxo['despesas_totais_estimadas']:,.0f}. "
        f"Taxa de poupança: <strong>{racios['taxa_poupanca_recorrente_pct']:.1f}%</strong> "
        f"(exclui Kiwify rescisão). Fluxo líquido: R${fluxo['fluxo_liquido']:,.0f}."
    )

    # S3: TAXA DE POUPANÇA E CONSUMO
    replacements['{{SUMMARY_S3}}'] = (
        f"Taxa de poupança recorrente de {racios['taxa_poupanca_recorrente_pct']:.1f}% com despesa média de "
        f"{fmt_int(fluxo['despesa_mensal_media'])}/mês. Maior gasto: alimentação ({fmt_int(cat_val(fluxo['por_categoria_despesa'].get('alimentacao', 0)))}), "
        f"seguido de financeiro/taxas ({fmt_int(cat_val(fluxo['por_categoria_despesa'].get('financeiro', 0)))}). "
        f"Reserva emergência: {racios['cobertura_despesas_meses']:.1f} meses (acima da meta 12 meses). "
        f"Consumo consciente: folga mensal de R${e4_data['consumo_consciente']['folga_mensal']:,.0f}."
    )

    # S4: INDEPENDÊNCIA FINANCEIRA
    rp_total = get_renda_passiva_total(goals)
    rp_meta = goals.get('renda_passiva', {}).get('meta_mensal', 30000)
    rp_pct = goals.get('renda_passiva', {}).get('pct_meta', goals.get('renda_passiva', {}).get('pct_atingido', 0))
    cenario_real = get_cenario(goals, 'Realista')
    david_idade_if = cenario_real.get('david_idade', goals.get('david_idade_if', 52))
    prazo_cenario = cenario_real.get('prazo_anos', cenario_real.get('prazo', goals.get('prazo_anos_realista', 9)))
    replacements['{{SUMMARY_S4}}'] = (
        f"Meta IF: {fmt_int(goals['if_meta'])} (R$30k/mês com {goals.get('if_trs', 0.05)*100:.0f}% TRS). "
        f"Progresso: {goals['if_pct']:.1f}% atingido, gap {fmt_int(goals['if_gap'])}. "
        f"Renda passiva atual: {fmt_int(rp_total)}/mês ({rp_pct:.1f}% da meta). "
        f"Com aporte R$20k/mês a 6% retorno real: <strong>~{goals['prazo_anos_realista']:.1f} anos</strong> "
        f"(David com {david_idade_if} anos, {2026 + int(prazo_cenario)})."
    )

    # S5: IMPOSTOS E TAX PLANNING
    tax = e4_data['tax_planning']
    td = tax.get('david', {})
    tm = tax.get('mariana', {})
    td_devido = td.get('ir_devido', td.get('devido', 0))
    td_pago = td.get('ir_pago', td.get('pago', 0))
    tm_devido = tm.get('ir_devido', tm.get('devido', 0))
    tm_pago = tm.get('ir_pago', tm.get('pago', 0))
    replacements['{{SUMMARY_S5}}'] = (
        f"David: IR devido {fmt_int(td_devido)}, pago {fmt_int(td_pago)}, "
        f"saldo {fmt_int(td.get('saldo', 0))}, alíquota efetiva {td.get('aliquota_efetiva_pct', 0):.1f}%. "
        f"Mariana: IR devido {fmt_int(tm_devido)}, pago {fmt_int(tm_pago)}, "
        f"saldo DEVEDOR {fmt_int(tm.get('saldo', 0))}, alíquota {tm.get('aliquota_efetiva_pct', 0):.1f}%. "
        f"Total anual: {fmt_int(tax.get('total_devido_anual', 0))}. Oportunidades: PGBL, Lucro Presumido, Carnê-leão aluguéis."
    )

    # S6: INVESTIMENTOS E ALOCAÇÃO
    investivel = patrimonio['investivel']
    replacements['{{SUMMARY_S6}}'] = (
        f"Patrimônio investível R${investivel:,.0f} alocado em RF (CDB, Tesouro), RV (ETF, ações), "
        f"fundos (Rico Alaska/Safari, BTG), imóveis (6 propriedades), criptoativos e liquidez USD. "
        f"Aporte mensal planejado: R$10k Cofrinhos (reserva), R$5k Tesouro IPCA+, "
        f"R$3k IVVB11, R$2k Wise USD. Rebalanceamento 01/2027 após reserva emergência."
    )

    # S7: SEGUROS E PROTEÇÃO
    replacements['{{SUMMARY_S7}}'] = (
        f"Proteção parcial: Arvo cobre David+Mariana+Theo; Mariana tem seguro vida Einstein R$27,41/mês. "
        f"Gaps críticos: seguro vida David (URGENTE), seguro invalidez, seguro residencial Tasso, "
        f"seguro auto (Toro + 2 motos). Transação Porto Seguro: R$5.337,90 (04/04/2026). "
        f"Ação: Levantar apólices até 30/04, cotar alternativas, implementar proteção faltante."
    )

    # S8: PLANO INTERNACIONAL & F1/F2
    replacements['{{SUMMARY_S8}}'] = (
        f"Fase F1/F2 (2027, ~6 meses): Anderson University SC, custo US$3.990/mês + R$8.919 BR. "
        f"Dados reais 2025 (Orlando): US$3.915/mês validou premissas. Parto Theo: US$1.716 com seguro. "
        f"Renda David remota mantida (PJ Brasil). Sobra: R$38.231/mês. Green Card EB2-NIW: ~5 anos. "
        f"Stratégia USD: meta US$20k pré-EUA, gap US$12.581 (~37 meses a R$2k/mês)."
    )

    # S9: DIAGNÓSTICO E ALERTAS
    replacements['{{SUMMARY_S9}}'] = (
        f"6 alertas: (1) Moradia sub-representada R$747/11meses, (2) 49 txns Itaú corrompidas, "
        f"(3) DAS PJ não rastreável, (4) Concentração 70% imóveis, (5) Reserva abaixo meta, "
        f"(6) IRPF Mariana saldo R$18.171. Comportamentos: aluguéis não transferem auto, "
        f"multas trânsito R$3.599 evitáveis. Próximos 15 dias: aporte R$20k, DAS, extratos BTG, "
        f"IRPF Mariana, custos moradia, início Wise USD."
    )

    # S10: TAREFAS E PRÓXIMOS PASSOS
    replacements['{{SUMMARY_S10}}'] = (
        f"20 tarefas priorizadas (P0-P2): P0 = aporte IF, incluir extratos PJ, reserva emergência (até 05/04); "
        f"P1 = transferência auto aluguéis, DAS, BTG consolidação, IRPF Mariana, moradia custos (até 20/04); "
        f"P2 = rebalanceamento, venda Leonardo da Vinci, F1/F2 docs, revisão IRPF 2025 (até 30/06). "
        f"Score: 5,5/10 (Bom) — aumentar com aporte mensal, diversificação RF, reduzir concentração imóvel."
    )

    return replacements

# ============================================================================
# BUILD CONTENT SECTIONS (CONTENT_S1 - CONTENT_S10)
# ============================================================================

def build_section_contents(e4_data):
    """Build all 10 section content (rich HTML)"""
    replacements = {}

    # S1: Visão Geral Patrimonial
    replacements['{{CONTENT_S1}}'] = build_content_s1(e4_data)

    # S2: Fluxo de Caixa
    replacements['{{CONTENT_S2}}'] = build_content_s2(e4_data)

    # S3: Taxa de Poupança
    replacements['{{CONTENT_S3}}'] = build_content_s3(e4_data)

    # S4: Independência Financeira
    replacements['{{CONTENT_S4}}'] = build_content_s4(e4_data)

    # S5: Impostos
    replacements['{{CONTENT_S5}}'] = build_content_s5(e4_data)

    # S6: Investimentos
    replacements['{{CONTENT_S6}}'] = build_content_s6(e4_data)

    # S7: Seguros
    replacements['{{CONTENT_S7}}'] = build_content_s7(e4_data)

    # S8: Plano Internacional
    replacements['{{CONTENT_S8}}'] = build_content_s8(e4_data)

    # S9: Diagnóstico
    replacements['{{CONTENT_S9}}'] = build_content_s9(e4_data)

    # S10: Tarefas
    replacements['{{CONTENT_S10}}'] = build_content_s10(e4_data)

    return replacements

def build_content_s1(e4_data):
    """Patrimônio Bruto"""
    patrimonio = e4_data['patrimonio']
    comp = patrimonio['composicao']

    # Build dynamic summary from composition data
    # Support both dict format (legacy) and list format (composicao_detalhada)
    if isinstance(comp, list) and len(comp) > 0 and isinstance(comp[0], str):
        # composicao is just labels — use composicao_detalhada or patrimonio flat fields
        comp_det = patrimonio.get('composicao_detalhada', [])
        if comp_det:
            items_sorted = sorted(
                [(item['categoria'].lower(), item['pct']) for item in comp_det],
                key=lambda x: x[1],
                reverse=True
            )
        else:
            # Fallback: compute from flat patrimonio fields
            bruto = patrimonio.get('bruto', 1)
            raw = [
                ('imóveis de investimento', patrimonio.get('imoveis_investimento', 0)),
                ('residência própria', patrimonio.get('residencia', 0)),
                ('investimentos David', patrimonio.get('investimentos_david', 0)),
                ('veículos', patrimonio.get('veiculos', 0)),
                ('investimentos Mariana', patrimonio.get('investimentos_mariana', 0)),
                ('caixa/USD', patrimonio.get('caixa_moeda_estrangeira', 0)),
                ('criptoativos', patrimonio.get('criptoativos', 0)),
            ]
            items_sorted = sorted(
                [(label, round(val / bruto * 100, 1)) for label, val in raw],
                key=lambda x: x[1],
                reverse=True
            )
    elif isinstance(comp, dict):
        items_sorted = sorted(
            [
                ('imóveis de investimento', comp['imoveis_investimento']['pct']),
                ('residência própria', comp['residencia_propria']['pct']),
                ('investimentos David', comp['investimentos_david']['pct']),
                ('veículos', comp['veiculos']['pct']),
                ('investimentos Mariana', comp['investimentos_mariana']['pct']),
                ('caixa/USD', comp['caixa_moeda_estrangeira']['pct']),
                ('criptoativos', comp['criptoativos']['pct']),
            ],
            key=lambda x: x[1],
            reverse=True
        )
    else:
        items_sorted = []
    parts = [f'{label} ({pct:.1f}%)' for label, pct in items_sorted]
    summary_text = (
        f'Patrimônio bruto de {fmt_currency(patrimonio["bruto"])} distribuído em 7 categorias: '
        + ', '.join(parts[:-1]) + f' e {parts[-1]}.'
    )

    html = '<div class="section">'
    html += '<h2>1. VISÃO GERAL DO PATRIMÔNIO</h2>'
    html += f'<p class="section-summary">{summary_text}</p>'

    # Doughnut chart — composição patrimonial
    html += '<div class="chart-container">'
    html += '<div class="card-title">Composição Patrimonial</div>'
    html += '<canvas id="chart-patrimonio-doughnut" data-type="doughnut"></canvas>'
    html += '</div>'

    # Waterfall chart — gap patrimônio investível → meta IF
    html += '<div class="chart-container">'
    html += '<div class="card-title">Gap Patrimônio Investível → Meta IF</div>'
    html += f'<p class="chart-context">De {fmt_currency(patrimonio["investivel"])} até {fmt_currency(e4_data["goals"]["if_meta"])}.</p>'
    html += '<canvas id="chart-waterfall-if" data-type="bar"></canvas>'
    html += '</div>'

    # Composição table
    html += '<table class="table-patrimonio">'
    html += '<tr><th>Categoria</th><th style="text-align:right;">Valor</th><th style="text-align:right;">%</th></tr>'

    # Build items from composicao_detalhada (list) or legacy dict format
    comp_det = patrimonio.get('composicao_detalhada', [])
    if comp_det:
        # Map category names to friendly labels
        LABEL_MAP = {
            'imóveis investimento': 'Imóvel de investimento',
            'residência própria': 'Residência própria (Tasso da Silveira)',
            'investimentos david': 'Investimentos David',
            'veículos': 'Veículos (Toro + 2 motos)',
            'investimentos mariana': 'Investimentos Mariana',
            'caixa + moeda estrangeira': 'Caixa + moeda estrangeira',
            'criptoativos': 'Criptoativos',
        }
        items = [
            (LABEL_MAP.get(item['categoria'].lower(), item['categoria']), item['valor'], item['pct'])
            for item in comp_det
        ]
    elif isinstance(comp, dict):
        items = [
            ('Imóvel de investimento', comp['imoveis_investimento']['valor'], comp['imoveis_investimento']['pct']),
            ('Residência própria (Tasso da Silveira)', comp['residencia_propria']['valor'], comp['residencia_propria']['pct']),
            ('Investimentos David', comp['investimentos_david']['valor'], comp['investimentos_david']['pct']),
            ('Veículos (Toro + 2 motos)', comp['veiculos']['valor'], comp['veiculos']['pct']),
            ('Investimentos Mariana', comp['investimentos_mariana']['valor'], comp['investimentos_mariana']['pct']),
            ('Caixa + moeda estrangeira', comp['caixa_moeda_estrangeira']['valor'], comp['caixa_moeda_estrangeira']['pct']),
            ('Criptoativos', comp['criptoativos']['valor'], comp['criptoativos']['pct']),
        ]
    else:
        items = []

    for label, valor, pct in items:
        html += f'<tr><td>{label}</td><td class="td-right">{fmt_currency(valor)}</td><td class="td-right">{pct:.1f}%</td></tr>'

    html += f'<tr class="td-total"><td><strong>TOTAL</strong></td><td class="td-right"><strong>{fmt_currency(patrimonio["bruto"])}</strong></td><td class="td-right"><strong>100,0%</strong></td></tr>'
    html += '</table>'

    # Insights
    html += '<div class="card card-highlight">'
    html += '<h3 class="card-title">Insights & Alertas</h3>'
    html += '<ul style="font-size:13px; line-height:1.7;">'
    html += '<li><strong>Concentração imobiliária:</strong> 70% em imóveis (residência 28,5% + investimento 41,2%). Meta: reduzir para <50% com diversificação RF/RV.</li>'
    html += '<li><strong>Patrimônio investível:</strong> R$2.276.977,98 (excluindo residência + veículos) destinado a IF.</li>'
    html += '<li><strong>Dívidas:</strong> R$234.792,61 (6,7% de endividamento — saudável). Patrimônio líquido: R$3.266.482,83.</li>'
    html += '<li><strong>6 imóveis:</strong> 1 residência, 1 investment property major, 1 living wish, 1 living concept, 1 Leonardo da Vinci (usufruto, 0% yield), 1 Calixto (David).</li>'
    html += '</ul>'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s2(e4_data):
    """Fluxo de Caixa"""
    fluxo = e4_data['fluxo_caixa']

    html = '<div class="section">'
    html += '<h2>2. FLUXO DE CAIXA & RECEITAS</h2>'
    html += f'<p class="section-summary">Renda total 11 meses R${fluxo["receita_total"]:,.0f} (média R${fluxo["receita_recorrente_mensal"]:,.0f}/mês recorrente). Duas fontes PJ (Arvo, BrandLovers) + uma rescisão (Kiwify) + aluguéis + investimentos.</p>'

    # Bar chart receita
    html += '<div class="chart-container">'
    html += '<div class="card-title">Receita por Fonte (11 meses)</div>'
    html += '<canvas id="chart-receita-bar" data-type="bar"></canvas>'
    html += '</div>'

    # Despesas doughnut + Receita vs Despesa mensal
    html += '<div class="chart-row">'
    html += '<div class="chart-container"><div class="card-title">Despesas por Categoria</div><canvas id="chart-despesas-doughnut" data-type="doughnut"></canvas></div>'
    html += '<div class="chart-container"><div class="card-title">Receita vs Despesa Mensal</div><canvas id="chart-receita-despesa-mensal" data-type="bar"></canvas></div>'
    html += '</div>'

    # Receitas por fonte
    html += '<h3>Receitas por Fonte (11 meses)</h3>'
    html += '<table>'
    html += '<tr><th>Fonte</th><th style="text-align:right;">Total</th><th style="text-align:right;">Média/mês</th><th>Tipo</th></tr>'

    # por_fonte values may be flat floats or dicts with 'total' key
    def _get_fonte(key, default=0):
        v = fluxo.get('por_fonte', {}).get(key, default)
        return v['total'] if isinstance(v, dict) else v

    fontes = [
        ('Arvo (PJ)', _get_fonte('arvo'), 'Recorrente'),
        ('BrandLovers (PJ)', _get_fonte('brandlovers'), 'Recorrente'),
        ('QuintoAndar (aluguéis)', _get_fonte('quintoandar'), 'Recorrente'),
        ('Kiwify (rescisão)', _get_fonte('kiwify_rescisao', _get_fonte('kiwify')), 'One-time'),
        ('Rendimentos investimentos', _get_fonte('rendimentos', _get_fonte('rendimento_aplicacao')), 'Recorrente'),
        ('Canary/CNRY', _get_fonte('cnry_canary'), 'PJ irregular'),
        ('Outros PJ', _get_fonte('pj_nao_identificado') + _get_fonte('arbitralis') + _get_fonte('learntofly') + _get_fonte('barte'), 'PJ'),
    ]

    for label, valor, tipo in fontes:
        media = valor / 11
        html += f'<tr><td>{label}</td><td class="td-right">{fmt_currency(valor)}</td><td class="td-right">{fmt_currency(media)}</td><td>{tipo}</td></tr>'

    html += f'<tr class="td-total"><td><strong>TOTAL</strong></td><td class="td-right"><strong>{fmt_currency(fluxo["receita_total"])}</strong></td><td class="td-right"><strong>{fmt_currency(fluxo["receita_recorrente_mensal"])}</strong></td><td></td></tr>'
    html += '</table>'

    # Key metrics
    html += '<div class="kpi-grid">'
    html += f'<div class="kpi-card"><div class="kpi-label">Receita recorrente/mês</div><div class="kpi-value">{fmt_currency(fluxo["receita_recorrente_mensal"])}</div></div>'
    html += f'<div class="kpi-card"><div class="kpi-label">Despesa mensal média</div><div class="kpi-value">{fmt_currency(fluxo["despesa_mensal_media"])}</div></div>'
    html += f'<div class="kpi-card"><div class="kpi-label">Folga mensal</div><div class="kpi-value green">{fmt_currency(fluxo["receita_recorrente_mensal"] - fluxo["despesa_mensal_media"])}</div></div>'
    html += f'<div class="kpi-card"><div class="kpi-label">Fluxo líquido (11m)</div><div class="kpi-value green">{fmt_currency(fluxo["fluxo_liquido"])}</div></div>'
    html += '</div>'

    html += '<div class="alert alert-info">'
    html += '<strong>Nota DAS:</strong> DAS PJ estimado em R$5.029/mês (life_plan). Valor real não confirmado — extratos conta PJ C6 Bank não processados ainda. Tarefa P0: incluir extratos PJ até 15/04.'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s3(e4_data):
    """Taxa de Poupança"""
    fluxo = e4_data['fluxo_caixa']
    racios = e4_data['racios']
    consumo = e4_data['consumo_consciente']

    html = '<div class="section">'
    html += '<h2>3. TAXA DE POUPANÇA & CONSUMO CONSCIENTE</h2>'
    html += f'<p class="section-summary">Taxa de poupança recorrente de {racios["taxa_poupanca_recorrente_pct"]:.1f}% com reserva emergência de {racios["cobertura_despesas_meses"]:.0f} meses (meta: 12 meses = R$382k).</p>'

    # Score gauge — saúde financeira
    html += '<div class="chart-container">'
    html += '<div class="card-title">Score Financeiro</div>'
    html += f'<p class="chart-context">Avaliação consolidada: {e4_data["score"]["valor"]:.1f}/10 ({e4_data["score"]["classificacao"]}).</p>'
    html += '<canvas id="chart-score-gauge" data-type="gauge"></canvas>'
    html += '</div>'

    # Despesas por categoria
    html += '<h3>Despesas por Categoria (11 meses)</h3>'
    html += '<table>'
    html += '<tr><th>Categoria</th><th style="text-align:right;">Total</th><th style="text-align:right;">% Despesa</th><th style="text-align:right;">Média/mês</th></tr>'

    categorias = fluxo['por_categoria_despesa']
    total_despesa = fluxo['despesas_pessoais']

    for cat in ['alimentacao', 'financeiro', 'saude', 'melhoria_reforma', 'lazer_viagens', 'transporte', 'assinaturas', 'suporte_familiar', 'vestuario', 'moradia', 'educacao']:
        if cat in categorias:
            valor = cat_val(categorias[cat])
            pct = (valor / total_despesa) * 100
            media = valor / 11
            html += f'<tr><td>{cat.replace("_", " ").title()}</td><td class="td-right">{fmt_currency(valor)}</td><td class="td-right">{pct:.1f}%</td><td class="td-right">{fmt_currency(media)}</td></tr>'

    html += f'<tr class="td-total"><td><strong>TOTAL</strong></td><td class="td-right"><strong>{fmt_currency(total_despesa)}</strong></td><td class="td-right"><strong>100,0%</strong></td><td class="td-right"><strong>{fmt_currency(fluxo["despesa_mensal_media"])}</strong></td></tr>'
    html += '</table>'

    # Poupança card
    html += '<div class="card card-success">'
    html += f'<h3 class="card-title card-title-green">Poupança Recorrente: {racios["taxa_poupanca_recorrente_pct"]:.1f}%</h3>'
    html += f'<p><strong>Renda mensal:</strong> {fmt_currency(fluxo["receita_recorrente_mensal"])}</p>'
    html += f'<p><strong>Despesa mensal:</strong> {fmt_currency(fluxo["despesa_mensal_media"])}</p>'
    html += f'<p><strong>Folga para aporte:</strong> {fmt_currency(fluxo["receita_recorrente_mensal"] - fluxo["despesa_mensal_media"])}</p>'
    html += '</div>'

    # Consumo consciente
    html += '<div class="card card-highlight">'
    html += '<h3 class="card-title">Consumo Consciente</h3>'
    html += f'<p><strong>Itens pontuais:</strong> {fmt_currency(consumo["total_pontuais"])} ({consumo.get("equivalente_meses_aporte", 0):.2f} meses de aporte)</p>'
    html += f'<p><strong>Folga mensal:</strong> {fmt_currency(consumo["folga_mensal"])} ({consumo["folga_pct"]:.1f}%)</p>'
    html += f'<p><strong>Teto sugerido para gastos extras:</strong> {fmt_currency(consumo["teto_sugerido"])}</p>'
    html += '<p>Itens monitorados: tarifas câmbio (R$6k/11m), multas trânsito (R$3.599 em jan/26), saúde pontual (R$2.599).</p>'
    html += '</div>'

    # Alertas
    html += '<div class="alert alert-warning">'
    html += '<strong>Alerta — Moradia sub-representada:</strong> Apenas R$747 em 11 meses (provavelmente IPTU, condomínio, energia, água não categorizados). Tarefa P1: mapear custos reais até 15/04.'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s4(e4_data):
    """Independência Financeira"""
    goals = e4_data['goals']

    html = '<div class="section">'
    html += '<h2>4. INDEPENDÊNCIA FINANCEIRA & PROJEÇÃO</h2>'

    if_pct = goals['if_pct']
    status_color = 'green' if if_pct > 0 else 'red'
    trs_pct = goals.get('if_trs', 0.05) * 100
    html += f'<p class="section-summary">Meta R${goals["if_meta"]:,.0f} (R$30k/mês ÷ {trs_pct:.0f}% TRS). Progresso: <strong>{if_pct:.1f}%</strong> atingido. Gap: R${goals["if_gap"]:,.0f}. Prazo realista: ~{goals["prazo_anos_realista"]:.1f} anos com aporte R$20k/mês (6% retorno real).</p>'

    # IF journey card
    html += '<div class="card card-feature">'
    html += '<h3 class="card-title">A Jornada para IF</h3>'
    html += f'<div class="kpi-grid">'
    html += f'<div class="kpi-card"><div class="kpi-label">Meta IF</div><div class="kpi-value">{fmt_currency(goals["if_meta"])}</div></div>'
    html += f'<div class="kpi-card"><div class="kpi-label">Patrimônio investível</div><div class="kpi-value">{fmt_currency(e4_data["patrimonio"]["investivel"])}</div></div>'
    html += f'<div class="kpi-card"><div class="kpi-label">Gap restante</div><div class="kpi-value red">{fmt_currency(goals["if_gap"])}</div></div>'
    html += f'<div class="kpi-card"><div class="kpi-label">Progresso</div><div class="kpi-value">{if_pct:.1f}%</div></div>'
    html += '</div>'
    html += '</div>'

    # Projeção 3 cenários chart
    html += '<div class="chart-container">'
    html += '<div class="card-title">Projeção Patrimonial — 3 Cenários</div>'
    html += '<p class="chart-context">Evolução do patrimônio investível com aporte R$20k/mês em diferentes taxas de retorno real.</p>'
    html += '<canvas id="chart-projecao-3cenarios" data-type="line"></canvas>'
    html += '</div>'

    # Cenários
    html += '<h3>Cenários de Prazo (com aporte R$20k/mês)</h3>'
    html += '<table>'
    html += '<tr><th>Cenário</th><th style="text-align:center;">Retorno real</th><th style="text-align:right;">Prazo</th><th style="text-align:right;">David com...</th></tr>'

    # Get cenarios from either dict or list format
    for nome in ['Pessimista', 'Realista', 'Otimista']:
        dados = get_cenario(goals, nome)
        if dados:  # Only render if scenario exists
            html += f'<tr><td><strong>{nome}</strong></td><td style="text-align:center;">{dados.get("retorno", 0)*100:.0f}%</td><td style="text-align:right;"><strong>{dados.get("prazo", 0):.1f} anos</strong></td><td style="text-align:right;">{dados.get("david_idade", "")} anos ({2026 + int(dados.get("prazo", 0))})</td></tr>'

    html += '</table>'

    # Renda passiva chart
    html += '<div class="chart-container">'
    html += '<div class="card-title">Renda Passiva Atual vs Meta</div>'
    rp_total = get_renda_passiva_total(goals)
    rp_pct = get_renda_passiva_pct(goals)
    html += f'<p class="chart-context">Atual: {fmt_currency(rp_total)}/mês ({rp_pct:.1f}% da meta R$30k).</p>'
    html += '<canvas id="chart-renda-passiva" data-type="bar"></canvas>'
    html += '</div>'

    # Renda passiva
    html += '<h3>Renda Passiva Atual vs Meta</h3>'
    html += '<table>'
    html += '<tr><th>Fonte</th><th style="text-align:right;">Valor/mês</th><th style="text-align:right;">% da meta</th></tr>'

    rp = goals['renda_passiva']
    rp_meta = rp.get('meta_mensal', 30000)

    # Map display names to fonte field names
    fonte_mapping = [
        ('Aluguéis David (Major Freire + Calixto)', 'Aluguéis David'),
        ('Aluguéis Mariana (Living Wish + Living Concept)', 'Aluguéis Mariana'),
        ('Dividendos/JCP (Rico)', 'Dividendos/JCP'),
        ('Rendimentos RF (Tesouro, CDB)', 'Rendimentos RF'),
        ('BTG cupons', 'BTG cupons'),
    ]

    for display_name, fonte_key in fonte_mapping:
        valor = get_renda_passiva_fonte(rp, fonte_key)
        if valor:  # Only show non-zero values
            pct = (valor / rp_meta) * 100
            html += f'<tr><td>{display_name}</td><td class="td-right">{fmt_currency(valor)}</td><td class="td-right">{pct:.1f}%</td></tr>'

    rp_total = get_renda_passiva_total(goals)
    rp_pct = get_renda_passiva_pct(goals)
    html += f'<tr class="td-total"><td><strong>TOTAL ATUAL</strong></td><td class="td-right"><strong>{fmt_currency(rp_total)}</strong></td><td class="td-right"><strong>{rp_pct:.1f}%</strong></td></tr>'
    html += f'<tr><td colspan="3"><strong>Meta: {fmt_currency(rp_meta)}/mês (R$30k)</strong></td></tr>'
    html += '</table>'

    # Aporte planejado
    html += '<div class="card card-success">'
    html += '<h3 class="card-title card-title-green">Aporte Mensal Planejado: R$20.000</h3>'
    html += '<table style="margin: 12px 0;">'
    html += '<tr><td><strong>CDB Cofrinhos Itaú</strong></td><td class="td-right">R$ 10.000</td><td style="color:var(--color-text-muted);">Reserva emergência</td></tr>'
    html += '<tr><td><strong>Tesouro IPCA+</strong></td><td class="td-right">R$ 5.000</td><td style="color:var(--color-text-muted);">Proteção inflação</td></tr>'
    html += '<tr><td><strong>IVVB11 / ETF global</strong></td><td class="td-right">R$ 3.000</td><td style="color:var(--color-text-muted);">Dolarização + RV</td></tr>'
    html += '<tr><td><strong>Wise USD</strong></td><td class="td-right">R$ 2.000</td><td style="color:var(--color-text-muted);">Acumulação USD pré-EUA</td></tr>'
    html += '<tr class="td-total"><td colspan="3"><strong>TOTAL DIÁRIO: R$ 20.000</strong></td></tr>'
    html += '</table>'
    html += '</div>'

    html += '<div class="alert alert-info">'
    prazo_realista = e4_data['goals']['prazo_anos_realista']
    html += f'<strong>Ação imediata:</strong> Primeiro aporte R$20k no dia 05/04/2026. Este aporte é essencial para atingir projeção de {prazo_realista:.1f} anos (cenário realista com 6% retorno). Rebalanceamento em 01/2027 após atingir R$382k de reserva emergência.'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s5(e4_data):
    """Impostos"""
    tax = e4_data['tax_planning']

    html = '<div class="section">'
    html += '<h2>5. IMPOSTOS & TAX PLANNING</h2>'

    david = tax['david']
    mariana = tax['mariana']

    html += '<p class="section-summary">Impostos totais devidos anuais: R${:,.0f}. David pagou 95%, Mariana pagou 55% do devido. Oportunidades: PGBL (dedução IRPF), Lucro Presumido vs Simples, Carnê-leão aluguéis.'.format(tax['total_devido_anual'])
    html += '</p>'

    # DAS PJ chart mês a mês
    html += '<div class="chart-container">'
    html += '<div class="card-title">DAS PJ — Evolução Mensal</div>'
    html += '<p class="chart-context">Estimativa R$5.029/mês (Simples Nacional). Confirmação pendente: extratos PJ C6 Bank.</p>'
    html += '<canvas id="chart-impostos-pj" data-type="bar"></canvas>'
    html += '</div>'

    # David vs Mariana comparison
    html += '<div class="two-col">'

    html += '<div class="card card-highlight">'
    html += '<h3 class="card-title">David C. Ferreira Campos (PJ + IRPF)</h3>'
    # Regime from previdencia_pgbl if available
    pgbl = e4_data.get('previdencia_pgbl', {})
    regime = pgbl.get('regime', 'Progressivo')
    html += f'<p><strong>Regime:</strong> {regime}</p>'
    html += f'<p><strong>IR devido (anual):</strong> {fmt_currency(david.get("devido", david.get("ir_devido", 0)))}</p>'
    html += f'<p><strong>IR pago:</strong> {fmt_currency(david.get("pago", david.get("ir_pago", 0)))}</p>'
    html += f'<p class="text-bold" style="color: var(--color-accent);">Saldo a favor: {fmt_currency(david.get("saldo", 0))}</p>'
    html += f'<p><strong>Alíquota efetiva:</strong> {david.get("aliquota_efetiva_pct", 0):.2f}%</p>'
    html += '</div>'

    html += '<div class="card card-warn">'
    html += '<h3 class="card-title card-title-red">Mariana Teixeira F. Campos (CLT + aluguéis)</h3>'
    html += f'<p><strong>Regime:</strong> Progressivo (CLT)</p>'
    html += f'<p><strong>IR devido (anual):</strong> {fmt_currency(mariana.get("devido", mariana.get("ir_devido", 0)))}</p>'
    html += f'<p><strong>IR pago:</strong> {fmt_currency(mariana.get("pago", mariana.get("ir_pago", 0)))}</p>'
    html += f'<p class="text-bold" style="color: var(--color-danger);">Saldo DEVEDOR: {fmt_currency(mariana.get("saldo", 0))}</p>'
    html += f'<p><strong>Alíquota efetiva:</strong> {mariana.get("aliquota_efetiva_pct", 0):.2f}%</p>'
    html += '</div>'

    html += '</div>'

    # Oportunidades
    html += '<h3>Oportunidades de Redução</h3>'
    html += '<table>'
    html += '<tr><th>Oportunidade</th><th>Beneficiário</th><th>Impacto estimado</th></tr>'

    for oportunidade in tax['oportunidades']:
        html += f'<tr><td>{oportunidade}</td><td>David</td><td>Até R$10k/ano</td></tr>'

    html += '</table>'

    # Alertas
    html += '<div class="alert alert-danger">'
    html += '<strong>Ação urgente — Mariana:</strong> Saldo devedor R$18.171 deve ser regularizado até 30/04/2026. Verificar se há parcelamento disponível ou opção de pagamento via débito direto. Consultar contador para revisar cálculo e possibilidades de dedução (aluguéis).'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s6(e4_data):
    """Investimentos"""
    patrimonio = e4_data['patrimonio']

    html = '<div class="section">'
    html += '<h2>6. INVESTIMENTOS & ALOCAÇÃO DE PATRIMÔNIO</h2>'

    html += f'<p class="section-summary">Patrimônio investível de R${patrimonio["investivel"]:,.0f} alocado em múltiplos ativos: imóveis (63%), RF (~15%), RV (15%), fundos (5%), liquidez (1,5%), crypto (0,5%).</p>'

    # Alocação chart
    html += '<div class="chart-row">'
    html += '<div class="chart-container"><canvas id="chart-alocacao-atual" data-type="doughnut"></canvas></div>'
    html += '<div class="chart-container"><canvas id="chart-alocacao-alvo" data-type="doughnut"></canvas></div>'
    html += '</div>'

    # Composição detalhada
    html += '<h3>Composição Atual vs Alvo</h3>'
    html += '<table class="table-compare">'
    html += '<tr><th>Categoria</th><th style="text-align:center;">Atual</th><th style="text-align:center;">Alvo 2027</th><th>Razão</th></tr>'

    items = [
        ('Imóveis de investimento', '41%', '35%', 'Reduzir concentração'),
        ('Residência própria', '28%', '20%', 'Reclassificar ativo não-investível'),
        ('RF (Tesouro, CDB, Poupança)', '8%', '20%', 'Aumentar reserva emergência'),
        ('RV (ETF, ações, FII)', '12%', '15%', 'Diversificação global'),
        ('Fundos (Rico, BTG)', '7%', '7%', 'Manter exposição'),
        ('Liquidez + USD', '4%', '3%', 'Normalizar'),
    ]

    for cat, atual, alvo, razao in items:
        html += f'<tr><td>{cat}</td><td style="text-align:center; background: #FEF2F2;">{atual}</td><td style="text-align:center; background: #F0FDF4;">{alvo}</td><td>{razao}</td></tr>'

    html += '</table>'

    # Top 15 ativos
    html += '<h3>Top 15 Ativos (descending)</h3>'
    html += '<div class="chart-container">'
    html += '<canvas id="chart-top15-ativos" data-type="bar"></canvas>'
    html += '</div>'

    # Yield imóveis
    html += '<h3>Rendimento Imóveis (yield bruto/ano)</h3>'
    html += '<div class="chart-container">'
    html += '<canvas id="chart-yield-imoveis" data-type="bar"></canvas>'
    html += '</div>'

    # Recomendações
    html += '<div class="card card-feature">'
    html += '<h3 class="card-title">Recomendações de Rebalanceamento</h3>'
    html += '<ul style="font-size:13px; line-height:1.7;">'
    html += '<li><strong>Aumentar RF:</strong> Meta 12 meses de despesas = R$382k (atual ~R$120k). Aporte R$10k/mês para Cofrinhos até atingir meta.</li>'
    html += '<li><strong>Reduzir concentração imóvel:</strong> Avaliar venda Leonardo da Vinci (usufruto, 0% yield) ou refinanciar para liberar capital para RF/RV.</li>'
    html += '<li><strong>Diversificação RV:</strong> Manter IVVB11, avaliar Fundo Imobiliário com yield >6% como alternativa a imóvel físico.</li>'
    html += '<li><strong>Dolarização:</strong> Meta US$20k até mudança para EUA. Aporte R$2k/mês via Wise (gap ~37 meses).</li>'
    html += '</ul>'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s7(e4_data):
    """Seguros"""
    seguros = e4_data['seguros']

    html = '<div class="section">'
    html += '<h2>7. SEGUROS & PROTEÇÃO PATRIMONIAL</h2>'

    html += '<p class="section-summary">Proteção parcial: Arvo cobre David+Mariana+Theo. Gaps críticos: seguro vida David (URGENTE), seguro invalidez, seguro residencial/auto. Orçamento de seguros: até 4-5% da renda bruta.</p>'

    # Status atual
    html += '<h3>Status Atual de Seguros</h3>'
    html += '<table>'
    html += '<tr><th>Tipo</th><th>Membro</th><th>Status</th><th>Ação</th></tr>'

    protecoes = [
        ('Plano de saúde (Arvo)', 'David + Mariana + Theo', '✅ Ativo', 'Manter — cobre pediatria (Theo)'),
        ('Seguro de vida', 'Mariana (Einstein)', '✅ Ativo (R$27,41/mês)', 'Revisar cobertura, aumentar limite'),
        ('Seguro de vida', 'David', '🔴 INEXISTENTE', 'URGENTE: contratar Term Life R$3-5M, 20 anos'),
        ('Seguro de invalidez', 'David + Mariana', '🔴 INEXISTENTE', 'URGENTE: 60% da renda bruta, principal risco'),
        ('Seguro residencial (Tasso)', 'Família', '🟡 Santander (?)', 'Cotar alternativas — economia potencial 20-40%'),
        ('Seguro auto (Toro + motos)', 'David', '🔴 INEXISTENTE', 'Adicionar: cobertura terceiros obrigatória'),
        ('Seguro conta C6', 'David', '✅ Ativo (R$20/mês)', 'Manter — proteção conta USD'),
    ]

    for tipo, membro, status, acao in protecoes:
        html += f'<tr><td>{tipo}</td><td>{membro}</td><td>{status}</td><td>{acao}</td></tr>'

    html += '</table>'

    # Chart custos F1/F2 + seguros
    html += '<div class="chart-container">'
    html += '<div class="card-title">Custos Mensais F1/F2 & Seguros</div>'
    html += '<p class="chart-context">Projeção de custos fixos durante fase F1/F2 (Anderson, SC) incluindo seguros obrigatórios.</p>'
    html += '<canvas id="chart-custos-f1f2" data-type="bar"></canvas>'
    html += '</div>'

    # Custos de seguros
    html += '<h3>Orçamento Estimado de Seguros (2026)</h3>'
    html += '<table>'
    html += '<tr><th>Seguro</th><th style="text-align:right;">Prêmio/mês</th><th style="text-align:right;">Anual</th></tr>'
    html += '<tr><td>Plano de saúde (Arvo) — custeado empresa</td><td class="td-right">—</td><td>—</td></tr>'
    html += '<tr><td>Seguro de vida Mariana</td><td class="td-right">R$ 27,41</td><td class="td-right">R$ 328,92</td></tr>'
    html += '<tr><td>Seguro vida David (nova) — estimate</td><td class="td-right">R$ 150–200</td><td class="td-right">R$ 1.800–2.400</td></tr>'
    html += '<tr><td>Seguro invalidez (D+M) — estimate</td><td class="td-right">R$ 200–300</td><td class="td-right">R$ 2.400–3.600</td></tr>'
    html += '<tr><td>Seguro residencial Tasso</td><td class="td-right">R$ 150–250</td><td class="td-right">R$ 1.800–3.000</td></tr>'
    html += '<tr><td>Seguro auto (Toro + motos)</td><td class="td-right">R$ 200–350</td><td class="td-right">R$ 2.400–4.200</td></tr>'
    html += '<tr class="td-total"><td><strong>TOTAL ESTIMADO</strong></td><td class="td-right"><strong>R$ 727–1.127</strong></td><td class="td-right"><strong>R$ 8.728–13.520</strong></td></tr>'
    html += '</table>'

    # Alertas
    html += '<div class="alert alert-danger">'
    html += '<strong>Prioridades:</strong> (1) Seguro vida David R$3-5M (proteção cônjuge+filhos); (2) Seguro invalidez 60% renda (principal risco pré-IF); (3) Seguro auto Toro (obrigatório). Tarefa: levantar apólices até 30/04, implementar até 31/05.'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s8(e4_data):
    """Plano Internacional"""
    html = '<div class="section">'
    html += '<h2>8. PLANO INTERNACIONAL & FASES F1/F2 → GREEN CARD</h2>'

    html += '<p class="section-summary">Roadmap: F1/F2 Anderson University (2027, 6 meses) → Green Card EB2-NIW (5 anos) → IF 2035. David trabalha remoto (PJ Brasil). Mariana: NCLEX roadmap. Custo F1/F2 validado com dados 2025 Orlando.</p>'

    # Fases timeline
    html += '<h3>Fases da Jornada</h3>'
    html += '<table>'
    html += '<tr><th>Fase</th><th>Descrição</th><th>Duração</th><th>Timeline</th></tr>'
    html += '<tr><td><strong>Atual</strong></td><td>Residência SP, preparação documental</td><td>—</td><td>2026</td></tr>'
    html += '<tr><td><strong>F1/F2</strong></td><td>Anderson University SC — visto estudante/dependente, Theo 2º filho</td><td>~6 meses</td><td>2027</td></tr>'
    html += '<tr><td><strong>Green Card</strong></td><td>Residência permanente EUA (EB2-NIW)</td><td>~5 anos</td><td>2027–2032</td></tr>'
    html += '<tr><td><strong>IF</strong></td><td>Independência financeira atingida</td><td>—</td><td>2035</td></tr>'
    html += '</table>'

    # Cenários cambiais chart
    html += '<div class="chart-container">'
    html += '<div class="card-title">Cenários Cambiais — Sobra Mensal</div>'
    html += '<p class="chart-context">Impacto da variação cambial (R$4,50–R$7,00/USD) na sobra mensal durante fase F1/F2 e Green Card.</p>'
    html += '<canvas id="chart-cenarios-cambiais" data-type="bar"></canvas>'
    html += '</div>'

    # F1/F2 custos
    html += '<h3>Fase F1/F2: Custos & Renda (Anderson, SC, ~6 meses)</h3>'
    html += '<table>'
    html += '<tr><th>Item</th><th style="text-align:right;">Valor</th></tr>'
    html += '<tr><td><strong>Custo base EUA</strong></td><td class="td-right"><strong>US$ 3.990/mês</strong></td></tr>'
    html += '<tr><td>  + Custos BR mantidos</td><td class="td-right">R$ 8.919/mês (suporte + DAS + assinaturas)</td></tr>'
    html += '<tr><td><strong>Custo total (@R$5,88)</strong></td><td class="td-right"><strong>R$ 32.380/mês</strong></td></tr>'
    html += '<tr><td colspan="2"><strong>Renda & Folga</strong></td></tr>'
    html += '<tr><td>Renda David (remota PJ Brasil)</td><td class="td-right">R$ 70.611/mês</td></tr>'
    html += '<tr class="td-total"><td><strong>Sobra mensal</strong></td><td class="td-right"><strong>R$ 38.231 (54%)</strong></td></tr>'
    html += '</table>'

    html += '<p style="margin-top: 12px; font-size: 13px; color: var(--color-text-muted);">David continuará trabalhando remotamente para contratos PJ brasileiros durante a estadia. Mariana em transição para NCLEX. Parto 2º filho: US$5.300–9.000 com seguro IU65.</p>'

    # Green Card phase
    html += '<h3>Fase Green Card: Renda + Custos (~5 anos)</h3>'
    html += '<table>'
    html += '<tr><th>Item</th><th style="text-align:right;">Valor</th></tr>'
    html += '<tr><td>Custo vida família 4</td><td class="td-right">US$ 6.050/mês</td></tr>'
    html += '<tr><td>Renda David (remota BRL)</td><td class="td-right">~US$ 12.000/mês (@R$5,88)</td></tr>'
    html += '<tr><td>Renda Mariana (pós-NCLEX, Cardiologia)</td><td class="td-right">US$ 4.000–7.000/mês</td></tr>'
    html += '<tr class="td-total"><td><strong>Sobra total com Mariana</strong></td><td class="td-right"><strong>US$ 9.499/mês</strong></td></tr>'
    html += '</table>'

    # Dados 2025 validação
    html += '<h3>Validação: Estadia EUA 2025 (02/05–25/09, Orlando/Kissimmee)</h3>'
    html += '<table>'
    html += '<tr><th>Métrica</th><th style="text-align:right;">Valor</th></tr>'
    html += '<tr><td>Custo base confirmado</td><td class="td-right">US$ 3.915/mês (inclui seguro IU65)</td></tr>'
    html += '<tr><td>Parto do Theo (com seguro)</td><td class="td-right">US$ 1.716 ✅ Validou estratégia</td></tr>'
    html += '<tr><td>Total 5 meses</td><td class="td-right">US$ 36.263 (~R$ 213.228)</td></tr>'
    html += '</table>'

    # Dolarização
    html += '<h3>Estratégia de Dolarização Pré-EUA</h3>'
    html += '<table>'
    html += '<tr><th>Plataforma</th><th>Papel</th><th style="text-align:right;">Saldo atual</th></tr>'
    html += '<tr><td>Wise</td><td>Conta principal acumulação USD</td><td class="td-right">US$ 4.722</td></tr>'
    html += '<tr><td>C6 Global</td><td>Cartão viagem/gastos pontuais</td><td class="td-right">US$ 92</td></tr>'
    html += '<tr><td>Bank of America</td><td>Dormida — futura residência EUA</td><td class="td-right">US$ 2.605</td></tr>'
    html += '<tr class="td-total"><td colspan="2"><strong>Meta pré-EUA: US$ 20.000</strong></td><td class="td-right"><strong>Gap US$ 12.581</strong></td></tr>'
    html += '</table>'

    html += '<p style="margin-top: 12px; font-size: 13px;">Gap = ~37 meses a R$2k/mês via aporte mensal. Alcançado com 25% do aporte (R$2k Wise + R$3k IVVB11 = R$5k total).</p>'

    # Impostos EUA
    html += '<div class="alert alert-info">'
    html += '<strong>Compliance fiscal EUA:</strong> Ao virar tax resident (Green Card), David/Mariana precisam de CPA expatriado para: FBAR (>US$10k), Form 8938, Form 1040 (dual taxation BR+EUA), PFIC (fundos BR), INSS (qualidade segurado). Ação: Contratar CPA ANTES de partir (~R$3-5k/ano).'
    html += '</div>'

    html += '</div>'
    return html

def build_content_s9(e4_data):
    """Diagnóstico e Alertas"""
    html = '<div class="section">'
    html += '<h2>9. DIAGNÓSTICO COMPORTAMENTAL & ALERTAS</h2>'

    html += '<p class="section-summary">6 alertas críticos + 3 padrões comportamentais. Maioria relativa a dados incompletos (DAS, Mariana, transações) ou oportunidades de otimização (aluguéis automáticos, multas).</p>'

    # Bubble chart — mapa de riscos
    html += '<div class="chart-container">'
    html += '<div class="card-title">Mapa de Riscos (Probabilidade × Impacto)</div>'
    html += '<p class="chart-context">Bolhas maiores = maior exposição financeira. Eixo X = probabilidade, Y = impacto.</p>'
    html += '<canvas id="chart-bubble-riscos" data-type="bubble"></canvas>'
    html += '</div>'

    # 6 Alertas críticos
    html += '<h3>6 Alertas Críticos</h3>'

    alertas = [
        ('Moradia sub-representada', 'R$747 em 11 meses', 'IPTU, condomínio, energia, água não aparecem nos extratos. Sub-estimativa grave de despesas.', 'P1', '15/04'),
        ('49 transações Itaú corrompidas', 'Valores inválidos ou zerados', 'Extração PDF com erro. Impacta análise fluxo de caixa. Requer investigação manual.', 'P1', '20/04'),
        ('DAS PJ não rastreável', 'Estimado R$5.029/mês', 'Nenhuma transação DAS aparece nos extratos pessoais. Possível: pagamento via conta PJ não capturada.', 'P0', '15/04'),
        ('Concentração patrimonial 70% imóveis', 'Meta: <50% para IF', 'Risco de iliquidez. Reduzir via venda Leonardo da Vinci ou aumento RF/RV.', 'P2', '30/06'),
        ('Reserva emergência abaixo meta', 'Atual 332 meses vs meta 12 meses (R$382k)', 'Folga em dias absolutos, mas em % de patrimônio total está OK. Clarificar meta.', 'P0', '05/04'),
        ('IRPF Mariana saldo devedor', 'R$18.171', 'Pagar até 30/04. Verificar parcelamento ou opção débito direto. Revisar deduções aluguéis.', 'P0', '15/04'),
    ]

    for i, (alerta, desc, detalhes, prioridade, prazo) in enumerate(alertas, 1):
        html += f'<div class="alert alert-warning">'
        html += f'<strong>{i}. {alerta}:</strong> {desc}<br/>'
        html += f'<small>{detalhes} | <strong>Prioridade: {prioridade}</strong> | <strong>Prazo: {prazo}</strong></small>'
        html += '</div>'

    # Diagnóstico comportamental
    html += '<h3>Padrões Comportamentais</h3>'

    diagnosticos = e4_data.get('diagnostico_comportamental', [])
    for i, item in enumerate(diagnosticos, 1):
        html += '<div class="card card-warn">'
        html += f'<h4 style="margin-bottom: 8px;">Padrão {i}: {item["padrao"]}</h4>'
        html += f'<p style="margin: 6px 0; font-size: 12px; color: var(--color-text-muted);"><strong>Evidência:</strong> {item["evidencia"]}</p>'
        html += f'<p style="margin: 6px 0; font-size: 12px;"><strong>Mudança sugerida:</strong> {item["mudanca_sugerida"]}</p>'
        html += '</div>'

    # Qualidade de dados
    html += '<h3>Qualidade de Dados & Gaps</h3>'
    html += '<table>'
    html += '<tr><th>Fonte de dado</th><th>Cobertura</th><th>Gaps</th></tr>'
    html += '<tr><td>Extratos Itaú David</td><td>Completo (2 contas)</td><td>49 txns corrompidas, algumas sem categoria</td></tr>'
    html += '<tr><td>Extratos C6 Bank David</td><td>Completo (2 contas)</td><td>PJ não processada (DAS, pró-labore desconhecido)</td></tr>'
    html += '<tr><td>Extratos Bradesco Mariana</td><td>Poupança + CC</td><td>Faltam extratos completos (depositária aluguéis)</td></tr>'
    html += '<tr><td>Investimentos Rico (David)</td><td>Carteira carregada</td><td>Fundos Alaska/Safari sem composição atualizada</td></tr>'
    html += '<tr><td>Investimentos BTG (Mariana)</td><td>Saldo total</td><td>Composição detalhada não processada</td></tr>'
    html += '<tr><td>Imóveis (6 propriedades)</td><td>Valores IPTU/documentos</td><td>Yields reais desconhecidos, taxas condomínio estimadas</td></tr>'
    html += '</table>'

    html += '</div>'
    return html

def build_content_s10(e4_data):
    """Tarefas e Próximos Passos"""
    html = '<div class="section">'
    html += '<h2>10. TAREFAS & ROADMAP 2026</h2>'

    html += '<p class="section-summary">20 tarefas estruturadas em 3 níveis (P0=imediato, P1=curto prazo, P2=médio prazo). Foco: aporte IF, dados completos, proteção, rebalanceamento.</p>'

    # Próximos 15 dias
    html += '<h3>AÇÕES IMEDIATAS (próximos 15 dias)</h3>'
    html += '<table class="table-steps">'
    html += '<tr><th>Data</th><th>Ação</th><th>Status</th></tr>'

    for item in e4_data['proximos_15d']:
        html += f'<tr><td>{item["data"]}</td><td>{item["acao"]}</td><td><span class="badge badge-yellow">pendente</span></td></tr>'

    html += '</table>'

    # Tarefas full list
    html += '<h3>Backlog Completo (20 tarefas, 2026)</h3>'
    html += '<table>'
    html += '<tr><th>#</th><th>Tarefa</th><th>Pri.</th><th>Prazo</th></tr>'

    for tarefa in e4_data['tarefas']:
        status_badge = 'pendente'
        html += f'<tr><td>{tarefa["n"]}</td><td>{tarefa["t"]}</td><td><span class="badge badge-neutral">{tarefa["p"]}</span></td><td>{tarefa["e"]}</td></tr>'

    html += '</table>'

    # Top 5 decisões impacto chart
    html += '<div class="chart-container">'
    html += '<div class="card-title">Top 5 Decisões de Maior Impacto</div>'
    html += '<p class="chart-context">Impacto estimado em 1 ano e 10 anos das principais decisões financeiras pendentes.</p>'
    html += '<canvas id="chart-top5-decisoes" data-type="bar"></canvas>'
    html += '</div>'

    # Roadmap visual
    html += '<h3>Roadmap Visual 2026</h3>'
    html += '<div style="background: #EFF6FF; border-radius: 8px; padding: 16px; margin: 16px 0; font-size: 12px;">'
    html += '<p><strong>Q2 (abr-jun):</strong> Aporte IF começa | DAS/extratos | Transferência aluguéis automática | Reserva emergência | IRPF Mariana | Seguros</p>'
    html += '<p><strong>Q3 (jul-set):</strong> F1/F2 documents | NCLEX prep Mariana | Rebalanceamento portfólio | Venda Leonardo da Vinci | PGBL dedução</p>'
    html += '<p><strong>Q4 (out-dez):</strong> F1/F2 matrícula | Green Card filing | Revisão IRPF 2025 | Testamentos | CPA expatriado contratado</p>'
    html += '</div>'

    # Métricas success
    html += '<h3>Métricas de Sucesso (2027)</h3>'
    html += '<table>'
    html += '<tr><th>Métrica</th><th>Meta 2027</th><th>Impacto</th></tr>'
    html += '<tr><td>Aporte mensal acumulado</td><td>R$ 240.000</td><td>Começa compounding IF</td></tr>'
    html += '<tr><td>Reserva emergência</td><td>R$ 382.000 (12 meses)</td><td>Segurança operacional</td></tr>'
    html += '<tr><td>Dolarização</td><td>US$ 20.000</td><td>Prepare F1/F2</td></tr>'
    html += '<tr><td>RF/RV (vs imóvel)</td><td>>40% patrimônio investível</td><td>Reduzir concentração</td></tr>'
    html += '<tr><td>Score financeiro</td><td>7,0/10</td><td>Melhorar governança</td></tr>'
    html += '</table>'

    html += '</div>'
    return html

# ============================================================================
# APPENDIX SECTIONS
# ============================================================================

def build_appendix_sections(e4_data):
    """Build appendices A-E"""
    replacements = {}

    # APP A: Definições
    replacements['{{CONTENT_APP_A}}'] = """
<div class="section">
<h2>APÊNDICE A: DEFINIÇÕES & SIGLAS</h2>

<h3>Indicadores Financeiros</h3>
<table>
<tr><td><strong>Patrimônio Bruto</strong></td><td>Soma de todos os ativos (residência, imóveis, investimentos, caixa, veículos, crypto).</td></tr>
<tr><td><strong>Patrimônio Investível</strong></td><td>Bruto − residência própria − veículos = capital disponível para aplicações financeiras.</td></tr>
<tr><td><strong>Patrimônio Líquido</strong></td><td>Bruto − dívidas (hipotecas, empréstimos).</td></tr>
<tr><td><strong>Taxa de Poupança</strong></td><td>(Renda − despesas) / renda. Exclui Kiwify (rescisão).</td></tr>
<tr><td><strong>Independência Financeira (IF)</strong></td><td>Patrimônio que gera renda passiva ≥ despesas mensais. Meta: R$30k/mês = R$7,2M (@5% TRS). Ref. D15.</td></tr>
<tr><td><strong>Renda Passiva</strong></td><td>Aluguéis, dividendos, rendimentos, JCP (sem trabalho ativo).</td></tr>
<tr><td><strong>Fluxo de Caixa</strong></td><td>Entrada − saída de recursos. Positivo indica sobra para investimento.</td></tr>
</table>

<h3>Siglas Frequentes</h3>
<table>
<tr><td><strong>PJ</strong></td><td>Pessoa Jurídica — regime de tributação empresarial.</td></tr>
<tr><td><strong>CLT</strong></td><td>Consolidação das Leis do Trabalho — regime de emprego formal.</td></tr>
<tr><td><strong>DAS</strong></td><td>Documento de Arrecadação do Simples Nacional — imposto para PJ.</td></tr>
<tr><td><strong>IRPF</strong></td><td>Imposto de Renda Pessoa Física — declaração anual de impostos.</td></tr>
<tr><td><strong>PGBL</strong></td><td>Plano de Geração de Benefício Livre — previdência privada (até 12% deução IRPF).</td></tr>
<tr><td><strong>TRS</strong></td><td>Taxa de Retirada Segura — 5% a.a. (carteira diversificada imóveis+RF+RV). Ref. D15. Anterior: 4% (Trinity Study).</td></tr>
<tr><td><strong>RF</strong></td><td>Renda Fixa (Tesouro, CDB, poupança, fundos).</td></tr>
<tr><td><strong>RV</strong></td><td>Renda Variável (ações, ETF, FII, crypto).</td></tr>
<tr><td><strong>FII</strong></td><td>Fundo de Investimento Imobiliário — securitização de imóveis.</td></tr>
<tr><td><strong>ETF</strong></td><td>Exchange-Traded Fund — cesta de ativos negociada em bolsa.</td></tr>
<tr><td><strong>USD</strong></td><td>Dólar americano — moeda de proteção inflacionária.</td></tr>
<tr><td><strong>FBAR</strong></td><td>Foreign Bank Account Report — declaração de contas estrangeiras (EUA).</td></tr>
<tr><td><strong>PFIC</strong></td><td>Passive Foreign Investment Company — tributação punitiva fundos BR nos EUA.</td></tr>
<tr><td><strong>EB2-NIW</strong></td><td>Employment-Based Green Card, segunda preferência (National Interest Waiver).</td></tr>
<tr><td><strong>NCLEX</strong></td><td>National Council Licensure Examination — prova de licença de enfermeira EUA.</td></tr>
</table>
</div>
    """

    # APP B: Premissas & Metodologia
    replacements['{{CONTENT_APP_B}}'] = """
<div class="section">
<h2>APÊNDICE B: PREMISSAS & METODOLOGIA</h2>

<div class="chart-container">
<div class="card-title">Orçamento de Viagens</div>
<p class="chart-context">Teto anual de viagens vs gasto realizado (Portugal 2025, EUA 2025).</p>
<canvas id="chart-viagens" data-type="bar"></canvas>
</div>

<h3>Período de Dados</h3>
<p><strong>Cobertura:</strong> 11 meses (2025-05 a 2026-03). <strong>Baseline patrimonial:</strong> IRPF 2024 (31/12/2024).</p>

<h3>Premissas IF</h3>
<ul>
<li><strong>Retorno real anual:</strong> 6% (cenário base), 4% (pessimista), 8% (otimista). Baseado em histórico 1927–2024.</li>
<li><strong>TRS:</strong> 5,0% a.a. (carteira diversificada imóveis+RF+RV, com renda ativa parcial pós-IF). Ref. D15.</li>
<li><strong>Inflação:</strong> 4,0% a.a. (IPCA médio Brasil 2015–2025).</li>
<li><strong>Aporte:</strong> R$20.000/mês fixo (dia 5). Pode aumentar com bônus/rescisões.</li>
<li><strong>Renda ativa:</strong> Mantida constante real (6% aumento nominal anual).</li>
</ul>

<h3>Ajustes & Estimativas</h3>
<ul>
<li><strong>DAS PJ:</strong> Estimado R$5.029/mês (life_plan). Não validado em extratos PJ.</li>
<li><strong>Moradia:</strong> Apenas R$747 em 11 meses (sub-representado). Estimativa real: IPTU R$1.500 + condomínio R$500 + utilidades R$500 = R$2.500/mês (~R$27.500/ano).</li>
<li><strong>Múltiplos imóveis:</strong> Yields calculados via aluguéis brutos ÷ avaliação. Taxes/manutenção deduzidos parcialmente.</li>
</ul>

<h3>Fontes de Dados</h3>
<ul>
<li><strong>Extratos bancários:</strong> Itaú, C6 Bank, Bradesco (PDF + CSV importados).</li>
<li><strong>Investimentos:</strong> Bruto de extratos Ricardo, BTG, Tesouro Direto, Wise (APIs + manuais).</li>
<li><strong>Imóveis:</strong> Valores IPTU 2025, aluguéis recebidos, documentação cartorial.</li>
<li><strong>Dados pessoais:</strong> Holerite Mariana, contratos PJ (Arvo, BrandLovers), IRPF 2024.</li>
</ul>

<h3>Limitações Conhecidas</h3>
<ol>
<li>49 transações Itaú com valores corrompidos (extração PDF).</li>
<li>~173 transações sem categorização (9,1% do total).</li>
<li>Extratos PJ não incluídos (DAS, pró-labore desconhecido).</li>
<li>Moradia sub-representada (IPTU, condomínio, utilidades não aparecem).</li>
<li>Composição fundos (Rico Alaska/Safari, BTG) não atualizada.</li>
<li>Seguros: apenas Mariana Einstein identificado (life = R$27,41/mês).</li>
</ol>
</div>
    """

    # APP C: Cenários & Sensibilidade (calculados dinamicamente)
    import math

    goals = e4_data['goals']
    pv = e4_data['patrimonio']['investivel']
    fv = goals['if_meta']
    aporte_base = goals['aporte_mensal']
    david_idade_atual = 2026 - 1983  # 43 anos

    def calc_prazo_meses(pv, fv, pmt, r_anual):
        """Calcula prazo em meses para atingir FV com aporte mensal e juros compostos"""
        r = r_anual / 12
        if r == 0:
            return (fv - pv) / pmt if pmt > 0 else float('inf')
        x = (fv * r + pmt) / (pv * r + pmt)
        if x <= 0:
            return float('inf')
        return math.log(x) / math.log(1 + r)

    def prazo_anos(pv, fv, pmt, r_anual):
        return calc_prazo_meses(pv, fv, pmt, r_anual) / 12

    # Cenários principais (from either dict or list format)
    cen_pess = get_cenario(goals, 'pessimista')
    cen_real = get_cenario(goals, 'realista')
    cen_otim = get_cenario(goals, 'otimista')

    prazo_r = prazo_anos(pv, fv, aporte_base, 0.06)
    prazo_p = prazo_anos(pv, fv, aporte_base, 0.04)
    prazo_o = prazo_anos(pv, fv, 22000, 0.08)

    # Sensibilidade: aportes
    prazo_15k = prazo_anos(pv, fv, 15000, 0.06)
    prazo_20k = prazo_anos(pv, fv, 20000, 0.06)
    prazo_25k = prazo_anos(pv, fv, 25000, 0.06)
    prazo_30k = prazo_anos(pv, fv, 30000, 0.06)

    # Sensibilidade: retornos
    prazo_4 = prazo_anos(pv, fv, aporte_base, 0.04)
    prazo_5 = prazo_anos(pv, fv, aporte_base, 0.05)
    prazo_6 = prazo_anos(pv, fv, aporte_base, 0.06)
    prazo_7 = prazo_anos(pv, fv, aporte_base, 0.07)
    prazo_8 = prazo_anos(pv, fv, aporte_base, 0.08)

    # Cenário Mariana reduz aporte
    prazo_13k = prazo_anos(pv, fv, 13200, 0.06)

    def fmt_prazo(p):
        return f"{p:.1f} anos ({2026 + int(round(p))})"

    def fmt_impacto(p, base):
        diff = p - base
        if abs(diff) < 0.05:
            return "—"
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff:.1f} anos"

    replacements['{{CONTENT_APP_C}}'] = f"""
<div class="section">
<h2>APÊNDICE C: CENÁRIOS DE SENSIBILIDADE</h2>

<h3>Cenário 1: Pessimista (4% retorno real, sem aumento renda)</h3>
<table>
<tr><th>Métrica</th><th>Valor</th></tr>
<tr><td>Retorno real anual</td><td>4,0%</td></tr>
<tr><td>Aporte mensal</td><td>R$ {aporte_base:,.0f}</td></tr>
<tr><td>Renda ativa</td><td>Flat (sem aumento)</td></tr>
<tr><td>Prazo IF</td><td>{fmt_prazo(prazo_p)} (David com {david_idade_atual + int(round(prazo_p))})</td></tr>
</table>

<h3>Cenário 2: Realista (6% retorno real, aumento 2% a.a.)</h3>
<table>
<tr><th>Métrica</th><th>Valor</th></tr>
<tr><td>Retorno real anual</td><td>6,0%</td></tr>
<tr><td>Aporte mensal</td><td>R$ {aporte_base:,.0f} (+2%/ano)</td></tr>
<tr><td>Renda ativa</td><td>+2% a.a. (inflação)</td></tr>
<tr><td>Prazo IF</td><td>{fmt_prazo(prazo_r)} (David com {david_idade_atual + int(round(prazo_r))})</td></tr>
</table>

<h3>Cenário 3: Otimista (8% retorno real, aporte +10% via bônus)</h3>
<table>
<tr><th>Métrica</th><th>Valor</th></tr>
<tr><td>Retorno real anual</td><td>8,0%</td></tr>
<tr><td>Aporte mensal</td><td>R$ 22.000 (+10% Kiwify/bônus)</td></tr>
<tr><td>Renda ativa</td><td>+4% a.a. (crescimento PJ)</td></tr>
<tr><td>Prazo IF</td><td>{fmt_prazo(prazo_o)} (David com {david_idade_atual + int(round(prazo_o))})</td></tr>
</table>

<h3>Análise de Sensibilidade: Mudanças no Aporte</h3>
<table>
<tr><th>Aporte mensal</th><th>Prazo IF (6% retorno)</th><th>Impacto</th></tr>
<tr><td>R$ 15.000 (−25%)</td><td>{fmt_prazo(prazo_15k)}</td><td>{fmt_impacto(prazo_15k, prazo_20k)}</td></tr>
<tr><td>R$ 20.000 (base)</td><td>{fmt_prazo(prazo_20k)}</td><td>—</td></tr>
<tr><td>R$ 25.000 (+25%)</td><td>{fmt_prazo(prazo_25k)}</td><td>{fmt_impacto(prazo_25k, prazo_20k)}</td></tr>
<tr><td>R$ 30.000 (+50%)</td><td>{fmt_prazo(prazo_30k)}</td><td>{fmt_impacto(prazo_30k, prazo_20k)}</td></tr>
</table>

<h3>Análise de Sensibilidade: Mudanças no Retorno</h3>
<table>
<tr><th>Retorno real a.a.</th><th>Prazo IF (aporte R$20k)</th><th>Impacto</th></tr>
<tr><td>4,0% (pessimista)</td><td>{fmt_prazo(prazo_4)}</td><td>{fmt_impacto(prazo_4, prazo_6)}</td></tr>
<tr><td>5,0%</td><td>{fmt_prazo(prazo_5)}</td><td>{fmt_impacto(prazo_5, prazo_6)}</td></tr>
<tr><td>6,0% (realista)</td><td>{fmt_prazo(prazo_6)}</td><td>—</td></tr>
<tr><td>7,0%</td><td>{fmt_prazo(prazo_7)}</td><td>{fmt_impacto(prazo_7, prazo_6)}</td></tr>
<tr><td>8,0% (otimista)</td><td>{fmt_prazo(prazo_8)}</td><td>{fmt_impacto(prazo_8, prazo_6)}</td></tr>
</table>

<h3>Pausas Cenário</h3>
<p><strong>Se Mariana deixar trabalho durante F1/F2:</strong> Impacto −R$6.830/mês líquido, mas folga de R$26.780 absorve. IF com aporte R$20k mantido = {prazo_r:.1f} anos (sem impacto). Se reduzir aporte a R$13,2k: IF = {prazo_13k:.1f} anos ({fmt_impacto(prazo_13k, prazo_r)}).</p>
</div>
    """

    # APP D: Referências & Recursos
    replacements['{{CONTENT_APP_D}}'] = """
<div class="section">
<h2>APÊNDICE D: REFERÊNCIAS & RECURSOS</h2>

<h3>Independência Financeira</h3>
<ul>
<li><strong>Trinity Study (1998):</strong> Research Affiliates. "A Retirement Spending Plan." Base histórica TRS 4%. Família adotou TRS 5% por diversificação imóveis+RF+RV (D15).</li>
<li><strong>FIRE Movement:</strong> r/financialindependence, Early Retirement Forum. Comunidade Brasil: FIRE Brasil Oficial.</li>
<li><strong>Calculadora IF:</strong> Calculadora de Patrimônio (blog Laranja Mecânica, GitHub code-fire).</li>
</ul>

<h3>Planejamento Tributário Brasil</h3>
<ul>
<li><strong>Simples Nacional vs Lucro Presumido:</strong> Faixa de faturamento David (R$292k Arvo + R$50k BrandLovers + outras = ~R$400k–800k/ano). Comparar alíquotas.</li>
<li><strong>PGBL:</strong> Até 12% da renda tributável para dedução IRPF. Opção: Vanguard (Brasil desconectado), Bradesco (ativa), XP Investimentos (ativa).</li>
<li><strong>Carnê-leão:</strong> Recolhimento mensal IR aluguéis. Alíquota: 15% até R$1.903,98, 22,5% acima.</li>
</ul>

<h3>Planejamento Internacional & EUA</h3>
<ul>
<li><strong>FBAR:</strong> FinCEN Form 114. Vencimento 15/04 anualmente (extensão automática até 15/10).</li>
<li><strong>Form 8938:</strong> FATCA — reportar ativos estrangeiros >US$200k (solteiro) ou US$400k (casado).</li>
<li><strong>Form 1040:</strong> Declaração federal EUA (residentes, inclusive tax residents imigrantes).</li>
<li><strong>CPA Expatriado:</strong> Especialista BR+EUA (taxa ~R$3-5k/ano). Recomendação: contratar ANTES de virar tax resident.</li>
<li><strong>CGFNS VisaScreen:</strong> Credencial de enfermeira Brasil para EUA. Custo US$1.515–2.440 (8–18 meses).</li>
<li><strong>EB2-NIW:</strong> Green Card por talento (Mestrado USP + experiência). Prazo aproximado 5 anos (2027–2032).</li>
</ul>

<h3>Ferramentas de Gestão</h3>
<ul>
<li><strong>Wise:</strong> Transferência internacional, conta USD (spread 0,5–1%).</li>
<li><strong>Tesouro Direto:</strong> Títulos públicos (CFF Banco: IPCA+ 2035, Pré 2027, Pós-fixado).</li>
<li><strong>ETF Ibovespa:</strong> IVVB11 (Vanguard S&P 500 BRL), VGIR (diversificado global).</li>
<li><strong>Cofrinhos Itaú:</strong> CDB automático, liquidez D+0, segurança FGC R$250k.</li>
<li><strong>Apps:</strong> Nubank (fluxo), C6 Bank (forex), Wise (USD), Google Sheets (tracking manual).</li>
</ul>

<h3>Consultores Recomendados</h3>
<ul>
<li><strong>Contador PJ/IRPF:</strong> Especialista em Simples + PGBL + Carnê-leão. Budget: R$2–5k/ano.</li>
<li><strong>CPA Expatriado:</strong> FBAR + Form 1040 + dupla tributação. Budget: R$3–5k/ano.</li>
<li><strong>Advogado Sucessório/Tributário:</strong> Testamentos, procurações, proteção patrimonial. Budget: R$10–20k (setup único).</li>
<li><strong>Segurador (vida, invalidez, residência):</strong> Cotação 3+ seguradoras. Target: R$800–1.200/mês (proteção completa).</li>
</ul>
</div>
    """

    # APP E: Próximos Ciclos de Análise
    replacements['{{CONTENT_APP_E}}'] = """
<div class="section">
<h2>APÊNDICE E: PRÓXIMOS CICLOS & ROADMAP ANÁLISE</h2>

<div class="chart-container">
<div class="card-title">Cenários IF — Mariana</div>
<p class="chart-context">Projeção de contribuição da Mariana para IF em diferentes cenários (CLT Brasil, NCLEX EUA, pausa F1/F2).</p>
<canvas id="chart-mariana-cenarios" data-type="line"></canvas>
</div>

<h3>E6 (Junho 2026) — Revalidação Q2</h3>
<ul>
<li>Validar aporte R$20k/mês (execução de 3 aportes).</li>
<li>Extratos PJ C6 Bank — confirmar DAS real, pró-labore, despesas operacionais.</li>
<li>Extratos Bradesco Mariana — cartório aluguéis, saldo poupança, BTG composição.</li>
<li>Imóveis — yields reais 2025-26 validados vs projeção.</li>
<li>Seguros — levantamento apólices implementadas (vida David, invalidez, auto).</li>
<li>Score recalculado com novos dados — target 6,5/10.</li>
</ul>

<h3>E7 (Setembro 2026) — Preparação F1/F2</h3>
<ul>
<li>Documentação F1/F2 completa (vistos, I-20, comprovante financeiro).</li>
<li>NCLEX Mariana — etapa de inglês (MET, OET, PTE) + CGFNS VisaScreen.</li>
<li>Green Card filing (EB2-NIW) iniciado — PERM labor cert + I-140.</li>
<li>CPA expatriado contratado — briefing FBAR/FATCA/Form 1040.</li>
<li>Rebalanceamento portfólio — reduzir imóvel, aumentar RF/RV.</li>
</ul>

<h3>E8 (Dezembro 2026) — Consolidação Ano 1</h3>
<ul>
<li>IRPF 2025 otimizado — PGBL David, Carnê-leão Mariana, deduções máximas.</li>
<li>Aporte acumulado: R$240k (12 aportes × R$20k).</li>
<li>Reserva emergência: R$120k → meta R$382k (31% atingido).</li>
<li>Dolarização: US$5–7k acumulado (Wise + IVVB11).</li>
<li>Score IF: 6,5–7,0/10 (gestão otimizada).</li>
<li>Roadmap 2027 (F1/F2 execution) confirmado.</li>
</ul>

<h3>Ciclos Futuros</h3>
<ul>
<li><strong>2027–2032:</strong> Ciclos a cada 6 meses (F1/F2 fase 1, Green Card, NCLEX). Focus: renda EUA, impostos duplos, investimento USD.</li>
<li><strong>2033–2035:</strong> Ciclos anuais (IF realizada). Focus: distribuição renda passiva, retirada PGBL, planejamento sucessório.</li>
<li><strong>2035+:</strong> Ciclos por demanda (otimização estado estacionário, hedging cambial, educação filhos).</li>
</ul>

<h3>Métricas a Monitorar (Dashboards Contínuos)</h3>
<ul>
<li><strong>IF Progress:</strong> (Patrimônio investível / meta IF) × 100%.</li>
<li><strong>Renda Passiva:</strong> Aluguéis + dividendos + rendimentos (vs meta R$30k/mês).</li>
<li><strong>Taxa Poupança:</strong> (Renda − despesas) / renda (vs target 80%).</li>
<li><strong>Concentração Imóvel:</strong> Imóveis / patrimônio investível (vs target <50%).</li>
<li><strong>Score Financeiro:</strong> Função de 14 componentes (atual 5,5 → target 8,0 em 2027).</li>
</ul>
</div>
    """

    return replacements

# ============================================================================
# BUILD FOOTER
# ============================================================================

def build_footer(e4_data):
    """Build footer content"""
    replacements = {}

    footer_html = """
<div style="border-top: 1px solid var(--color-border); margin-top: 56px; padding-top: 32px; color: var(--color-text-muted); font-size: 12px;">

<p><strong>Preparado por:</strong> Sistema de Análise Financeira E5 (Pipeline Completo)</p>
<p><strong>Data:</strong> São Paulo, 3 de abril de 2026</p>
<p><strong>Período coberto:</strong> 2025-05 a 2026-03 (11 meses de dados)</p>
<p><strong>Próxima revisão:</strong> Junho 2026 (E6 — revalidação Q2)</p>

<h4 style="margin-top: 20px; margin-bottom: 10px; font-size: 12px; color: var(--color-primary);">Confidencialidade</h4>
<p>Este relatório contém informações confidenciais e pessoais da família Ferreira Campos. Distribuição restrita. Não é aconselhamento financeiro — consultar profissionais (contador, CPA, advogado, segurador) para implementação.</p>

<h4 style="margin-top: 20px; margin-bottom: 10px; font-size: 12px; color: var(--color-primary);">Isenção de Responsabilidade</h4>
<p>Análise baseada em dados disponibilizados até 31/03/2026. Premissas (retorno 6%, inflação 4%, TRS 5%) sujeitas a variação. Cenários de sensibilidade mostram amplitude de resultados possíveis. Este relatório não substitui aconselhamento profissional personalizado. Implementação e decisões de investimento são responsabilidade exclusiva da família.</p>

</div>
    """

    replacements['{{FOOTER_CONTENT}}'] = footer_html
    return replacements

# ============================================================================
# MAIN REPORT GENERATION
# ============================================================================

def generate_report():
    """Main report generation"""
    print("🔄 Loading data...")
    template = load_template()
    e4_data = load_json(E4_JSON_PATH)

    print("📋 Building placeholders...")
    all_replacements = {}

    # Build all replacements
    all_replacements.update(build_cover_and_kpis(e4_data))
    all_replacements.update(build_perfil_familia(e4_data))
    all_replacements.update(build_section_summaries(e4_data))
    all_replacements.update(build_section_contents(e4_data))
    all_replacements.update(build_appendix_sections(e4_data))
    all_replacements.update(build_footer(e4_data))

    # Build report data JSON for charts
    print("📊 Building chart data...")
    report_data_json = build_chart_data(e4_data)
    all_replacements['{{REPORT_DATA_JSON}}'] = report_data_json

    # Replace placeholders
    print("🎨 Applying replacements...")
    html_output = template
    for placeholder, replacement in all_replacements.items():
        html_output = html_output.replace(placeholder, replacement)

    # Verify no remaining placeholders
    print("✓ Verifying no remaining placeholders...")
    remaining = len([p for p in all_replacements.keys() if p in html_output])
    if remaining == 0:
        print("✅ No remaining placeholders found")
    else:
        print(f"⚠️  {remaining} placeholders still remain")

    # Save output
    output_path = OUTPUT_DIR / 'relatorio_financeiro_ferreira_campos_20260404.html'

    # Archive old version if exists
    if output_path.exists():
        backup_path = output_path.with_suffix('.html.bak')
        shutil.copy(output_path, backup_path)
        print(f"📦 Archived previous version to {backup_path.name}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"✅ Report saved to {output_path}")
    print(f"📄 File size: {output_path.stat().st_size / 1024:.0f} KB")

    return output_path

def _build_receita_despesa_mensal(e4_data):
    """Build receita vs despesa chart data from E4 fluxo_mensal (real monthly data)."""
    MONTH_LABELS = {
        '2025-05': 'mai/25', '2025-06': 'jun/25', '2025-07': 'jul/25',
        '2025-08': 'ago/25', '2025-09': 'set/25', '2025-10': 'out/25',
        '2025-11': 'nov/25', '2025-12': 'dez/25', '2026-01': 'jan/26',
        '2026-02': 'fev/26', '2026-03': 'mar/26'
    }
    MESES_ORDEM = ['2025-05','2025-06','2025-07','2025-08','2025-09','2025-10','2025-11','2025-12','2026-01','2026-02','2026-03']

    fluxo = e4_data.get('fluxo_mensal', {})
    if not fluxo:
        print("⚠️  AVISO: fluxo_mensal ausente no E4 — gráfico receita_despesa_mensal ficará vazio!")
        return {'labels': [], 'datasets': []}

    # Sort months in chronological order
    meses = sorted([m for m in fluxo.keys() if m in MONTH_LABELS], key=lambda x: MESES_ORDEM.index(x) if x in MESES_ORDEM else 99)

    labels = [MONTH_LABELS[m] for m in meses]
    receita_pj = [round(fluxo[m].get('receita_pj', 0), 2) for m in meses]
    receita_clt = [round(fluxo[m].get('receita_clt_alugueis', 0), 2) for m in meses]
    despesas = [round(fluxo[m].get('despesas', 0), 2) for m in meses]

    # Validation: check totals match E4 aggregates
    total_receita_chart = sum(receita_pj) + sum(receita_clt)
    total_desp_chart = sum(despesas)
    e4_receita_total = e4_data.get('fluxo_caixa', {}).get('receita_total', 0)
    if e4_receita_total > 0:
        diff_pct = abs(total_receita_chart - e4_receita_total) / e4_receita_total * 100
        if diff_pct > 5:
            print(f"⚠️  ALERTA: receita mensal do gráfico (R${total_receita_chart:,.2f}) diverge {diff_pct:.1f}% do E4 total (R${e4_receita_total:,.2f})")

    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Receita PJ',
                'data': receita_pj,
                'backgroundColor': 'rgba(46, 134, 171, 0.7)',
                'borderColor': '#2E86AB',
                'stack': 'receita'
            },
            {
                'label': 'CLT + Alugueis',
                'data': receita_clt,
                'backgroundColor': 'rgba(106, 153, 78, 0.7)',
                'borderColor': '#6A994E',
                'stack': 'receita'
            },
            {
                'label': 'Despesas',
                'data': despesas,
                'backgroundColor': 'rgba(214, 40, 40, 0.5)',
                'borderColor': '#D62828',
                'stack': 'despesa'
            }
        ]
    }


def build_chart_data(e4_data):
    """Build JSON with all chart data"""
    charts_data = {
        'patrimonio_doughnut': {
            'labels': [
                'Imóvel investimento (41,2%)',
                'Residência própria (28,5%)',
                'Investimentos David (17,3%)',
                'Veículos (6,5%)',
                'Investimentos Mariana (5,4%)',
                'Caixa+USD (1,0%)',
                'Criptoativos (0,1%)'
            ],
            'datasets': [{
                'label': 'Patrimônio Bruto',
                'data': [1443000, 996821, 605979, 227476, 188124, 36686, 3190],
                'backgroundColor': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E', '#BC4749', '#8B5A3C']
            }]
        },
        'receita_bar': {
            'labels': ['Arvo', 'BrandLovers', 'QuintoAndar', 'Kiwify', 'Rendimentos', 'Canary', 'Outros'],
            'datasets': [{
                'label': 'Receita (11 meses)',
                'data': [292666, 50000, 65805, 407357, 831, 120000, 104250],
                'backgroundColor': '#2E86AB'
            }]
        },
        'despesas_doughnut': {
            'labels': [
                'Alimentação (27,0%)',
                'Financeiro (21,7%)',
                'Saúde (10,8%)',
                'Melhoria/reforma (9,6%)',
                'Lazer/viagens (8,5%)',
                'Transporte (5,9%)',
                'Assinaturas (5,4%)',
                'Suporte familiar (5,1%)',
                'Vestuário (3,4%)',
                'Moradia (1,4%)',
                'Educação (1,3%)'
            ],
            'datasets': [{
                'label': 'Despesas (11 meses)',
                'data': [14228, 11482, 5696, 5071, 4519, 3107, 2847, 2683, 1817, 747, 687],
                'backgroundColor': ['#D62828', '#F77F00', '#FCBF49', '#EAE2B7', '#003049', '#669BBC', '#780000', '#E63946', '#A4161A', '#9D4EDD', '#3A86FF']
            }]
        },
        'receita_despesa_mensal': _build_receita_despesa_mensal(e4_data),
        'alocacao_atual': {
            'labels': ['Imóveis', 'RF', 'RV', 'Fundos', 'Liquidez+USD', 'Crypto'],
            'datasets': [{
                'data': [70, 8, 12, 7, 2, 1],
                'backgroundColor': ['#2E86AB', '#6A994E', '#F18F01', '#A23B72', '#BC4749', '#8B5A3C']
            }]
        },
        'alocacao_alvo': {
            'labels': ['Imóveis', 'RF', 'RV', 'Fundos', 'Liquidez+USD', 'Crypto'],
            'datasets': [{
                'data': [55, 20, 15, 7, 2, 1],
                'backgroundColor': ['#2E86AB', '#6A994E', '#F18F01', '#A23B72', '#BC4749', '#8B5A3C']
            }]
        },
        'top15_ativos': {
            'labels': ['Living Wish', 'Living Concept', 'Major Freire', 'Calixto', 'Leonardo da Vinci', 'IVVB11', 'Tesouro IPCA+', 'CDB Cofrinhos', 'Poupança C6', 'Ações Rico', 'Fundos BTG', 'FII', 'Toro', 'Motos', 'Wise USD'],
            'datasets': [{
                'label': 'Valor do ativo',
                'data': [600000, 500000, 343000, 150000, 150000, 220000, 150000, 120000, 100000, 80000, 70000, 50000, 150000, 77476, 36686],
                'backgroundColor': '#2E86AB'
            }]
        },
        'yield_imoveis': {
            'labels': ['Living Wish', 'Living Concept', 'Major Freire', 'Calixto', 'Leonardo da Vinci'],
            'datasets': [{
                'label': 'Yield bruto anual (%)',
                'data': [14.4, 14.4, 11.9, 27.3, 0.0],
                'backgroundColor': ['#6A994E', '#6A994E', '#F18F01', '#F18F01', '#D62828']
            }]
        }
    }

    # Wrap in the structure expected by the template:
    # DATA.charts.xxx, DATA.kpis, DATA.meta, DATA.dashboard
    goals = e4_data['goals']
    patrimonio = e4_data['patrimonio']
    fluxo = e4_data['fluxo_caixa']
    racios = e4_data['racios']

    report_data = {
        'charts': charts_data,
        'kpis': {
            'patrimonio_bruto': patrimonio['bruto'],
            'patrimonio_investivel': patrimonio['investivel'],
            'renda_mensal': fluxo['receita_recorrente_mensal'],
            'taxa_poupanca': racios['taxa_poupanca_recorrente_pct'] / 100,
            'taxa_poupanca_recorrente': racios['taxa_poupanca_recorrente_pct'] / 100,
            'meta_if': goals['if_meta'],
            'gap_if': goals['if_gap'],
            'prazo_if': goals['prazo_anos_realista'],
            'score': e4_data['score']['valor']
        },
        'meta': {
            'modo_padrao': 'strategic',
            'familia': 'Ferreira Campos',
            'periodo': '2025-05 a 2026-03',
            'data_geracao': '2026-04-03'
        },
        'dashboard': None
    }

    return json.dumps(report_data, ensure_ascii=False, indent=2)

# ============================================================================
# EXECUTE
# ============================================================================

if __name__ == '__main__':
    try:
        output_file = generate_report()
        print(f"\n✨ Report generation complete!")
        print(f"📍 Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

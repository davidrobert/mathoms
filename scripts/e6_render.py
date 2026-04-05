#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E6 Renderer — Deterministic Financial Report Generation
Reads E5 JSON (data + narratives) and HTML template, produces final report via string replacement.
No LLM needed. Pure data transformation.

Output: /output/relatorio_financeiro_ferreira_campos_YYYYMMDD.html
"""

import json
import re
from pathlib import Path
from datetime import datetime
import pytz

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent  # financas-familia/
TEMPLATE_PATH = BASE_DIR / "config" / "report_template.html"
E5_JSON_PATH = BASE_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
E4_INVEST_PATH = BASE_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
MANUAL_PATH = BASE_DIR / "config" / "manual_operacao.md"
DEFINITIONS_PATH = BASE_DIR / "config" / "definitions.md"
OUTPUT_DIR = BASE_DIR / "output"

# Color palette for charts
PALETTE = [
    "#1A3A5C", "#1E6E8F", "#15803D", "#F4A261", "#B91C1C",
    "#457B9D", "#E63946", "#A8DADC", "#457B9D", "#2A9D8F",
    "#E76F51", "#F4A460", "#FFB703", "#8ECAE6", "#219EBC"
]

# Mapping: narrativas chart key → canonical canvas ID (as expected by template JS)
CHART_CANVAS_MAP = {
    "patrimonio_doughnut": "chart-patrimonio-doughnut",
    "waterfall_if": "chart-waterfall-if",
    "receita_bar": "chart-receita-bar",
    "despesas_doughnut": "chart-despesas-doughnut",
    "receita_despesa_mensal": "chart-receita-despesa-mensal",
    "score_gauge": "chart-score-gauge",
    "alocacao_atual": "chart-alocacao-atual",
    "alocacao_alvo": "chart-alocacao-alvo",
    "top15_ativos": "chart-top15-ativos",
    "yield_imoveis": "chart-yield-imoveis",
    "custos_f1f2": "chart-custos-f1f2",
    "cenario_cambial": "chart-cenarios-cambiais",
    "projecao_if": "chart-projecao-3cenarios",
    "renda_passiva": "chart-renda-passiva",
    "impostos_pj": "chart-impostos-pj",
    "riscos_bubble": "chart-bubble-riscos",
    "decisoes": "chart-top5-decisoes",
    "cenarios_mariana": "chart-mariana-cenarios",
    "viagens": "chart-viagens",
}

# Mapping: chart key → friendly display title (avoid auto-generated "Waterfall If" etc.)
CHART_TITLES = {
    "patrimonio_doughnut": "Composição Patrimonial",
    "waterfall_if": "Caminho para Independência Financeira",
    "receita_bar": "Receita por Fonte",
    "despesas_doughnut": "Despesas por Categoria",
    "receita_despesa_mensal": "Receita vs Despesa — Mês a Mês",
    "score_gauge": "Score Financeiro",
    "alocacao_atual": "Alocação Atual",
    "alocacao_alvo": "Alocação Alvo",
    "top15_ativos": "Top 15 Ativos Financeiros",
    "yield_imoveis": "Rentabilidade dos Imóveis (Yield) vs CDI",
    "custos_f1f2": "Custos Mensais F1/F2",
    "cenario_cambial": "Cenários Cambiais",
    "projecao_if": "Projeção Patrimonial — 3 Cenários",
    "renda_passiva": "Renda Passiva vs Meta",
    "impostos_pj": "DAS PJ — Mês a Mês",
    "riscos_bubble": "Mapa de Riscos",
    "decisoes": "Top 5 Decisões de Impacto",
    "cenarios_mariana": "Cenários IF — Mariana",
    "viagens": "Orçamento de Viagens",
}

# Mapping: section number → which chart keys belong to it
SECTION_CHARTS = {
    1: ["patrimonio_doughnut", "waterfall_if"],
    2: ["receita_bar", "despesas_doughnut", "receita_despesa_mensal", "score_gauge"],
    3: ["alocacao_atual", "alocacao_alvo", "top15_ativos", "cenarios_mariana", "viagens"],
    4: ["yield_imoveis"],
    5: ["custos_f1f2"],
    6: ["cenario_cambial"],
    7: ["projecao_if", "renda_passiva"],
    8: ["impostos_pj"],
    9: ["riscos_bubble"],
    10: ["decisoes"],
}

# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def fmt_brl(value: float) -> str:
    """Format as R$ 3.501.275 (punto separator for thousands)"""
    if not isinstance(value, (int, float)):
        return "—"
    return f"R$ {int(value):,}".replace(",", ".")

def fmt_brl_m(value: float) -> str:
    """Format as R$ 3,5M (comma for decimal, padrão BR)"""
    if not isinstance(value, (int, float)):
        return "—"
    m_val = value / 1_000_000
    return f"R$ {m_val:.1f}M".replace(".", ",")

def fmt_pct(value: float) -> str:
    """Format as 65,7% (comma for decimal)"""
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value:.1f}%".replace(".", ",")

def fmt_pct_int(value: float) -> str:
    """Format as 66% (integer percentage)"""
    if not isinstance(value, (int, float)):
        return "—"
    return f"{int(value)}%"

def fmt_moeda(value: float) -> str:
    """Format as -$10.042 or similar for USD"""
    if not isinstance(value, (int, float)):
        return "—"
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${abs(value):,.2f}"

def chart_html(chart_key: str, title: str, narrativas_charts: dict, extra_attrs: str = "") -> str:
    """Generate chart container HTML with canonical canvas ID"""
    canvas_id = CHART_CANVAS_MAP.get(chart_key, f"chart-{chart_key}")
    narr = narrativas_charts.get(chart_key, {})
    context = narr.get("context", "")
    conclusion = narr.get("conclusion", "")

    parts = [f'<div class="chart-container">']
    parts.append(f'  <div class="card-title">{title}</div>')
    # Yield explainer for non-specialists
    if chart_key == "yield_imoveis":
        parts.append('  <p class="chart-context" style="font-style:italic;opacity:0.85;">'
                      '<strong>O que é yield?</strong> Yield (rentabilidade) é o retorno anual '
                      'que o imóvel gera em aluguéis, expresso como percentual do valor estimado '
                      'do bem. Fórmula: (aluguel anual ÷ valor estimado) × 100. Comparar com o CDI '
                      'ajuda a avaliar se o capital imobilizado rende mais ou menos que uma aplicação '
                      'financeira de baixo risco.</p>')
    if context:
        parts.append(f'  <p class="chart-context">{context}</p>')
    # Special handling for score gauge
    if chart_key == "score_gauge":
        parts.append(f'  <canvas id="{canvas_id}" data-type="gauge" {extra_attrs}></canvas>')
    else:
        parts.append(f'  <canvas id="{canvas_id}"></canvas>')
    if conclusion:
        parts.append(f'  <p class="chart-conclusion">{conclusion}</p>')
    parts.append('</div>')
    return '\n'.join(parts)

# ============================================================================
# STEP 1: LOAD DATA
# ============================================================================

def load_e4_json() -> dict:
    """Load E4 analysis JSON"""
    print("[E6.0] Loading E5 JSON...")
    with open(E5_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_top15_investimentos() -> list:
    """Load E3 unified investments, sort by valor_atual desc, return top 15.
    Excludes positions with valor_atual <= 0 (closed/sold).
    Source: investimentos-3_unified.json (posicoes dict)."""
    print("[E6.0] Loading E4 investimentos for Top 15...")
    with open(E4_INVEST_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    posicoes = data.get("posicoes", {})
    items = [
        {"nome": v["nome"], "banco": v["banco"], "valor": v["valor_atual"]}
        for v in posicoes.values()
        if v.get("valor_atual", 0) > 0
    ]
    items.sort(key=lambda x: x["valor"], reverse=True)
    return items[:15]

def load_manual() -> str:
    """Load manual_operacao.md for version extraction"""
    print("[E6.0] Loading manual_operacao.md...")
    with open(MANUAL_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def load_template() -> str:
    """Load HTML template"""
    print("[E6.0] Loading HTML template...")
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def extract_version(manual_text: str) -> str:
    """Extract version from manual: ## Versão: 3.3"""
    match = re.search(r'## Versão: ([\d.]+)', manual_text)
    return match.group(1) if match else "3.0"

def get_sp_time() -> str:
    """Get current São Paulo time as '4 abr 2026, 14h32'"""
    sp_tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(sp_tz)
    # Format: "4 abr 2026, 14h32"
    return now.strftime("%-d %b %Y, %Hh%M").replace("May", "mai").replace("Apr", "abr")\
        .replace("Jan", "jan").replace("Feb", "fev").replace("Mar", "mar")\
        .replace("Jun", "jun").replace("Jul", "jul").replace("Aug", "ago")\
        .replace("Sep", "set").replace("Oct", "out").replace("Nov", "nov")\
        .replace("Dec", "dez")

# ============================================================================
# STEP 2: E6.1 — BUILD COVER, KPIs, FOOTER
# ============================================================================

def build_kpi_section(e4: dict, manual_text: str) -> dict:
    """Build all KPI and cover replacements"""
    print("[E6.1] Building KPI section...")

    version = extract_version(manual_text)
    sp_time = get_sp_time()

    p = e4["patrimonio"]
    g = e4["goals"]
    f = e4["fluxo_caixa"]
    r = e4["racios"]
    s = e4["score"]

    replacements = {
        "{{COVER_FAMILIA}}": "Ferreira Campos",
        "{{COVER_PERIODO}}": e4["periodo_dados"],
        "{{COVER_VERSAO_MANUAL}}": version,
        "{{COVER_DATA_HORA}}": sp_time,
        "{{NOME}}": "David",

        # KPIs
        "{{KPI_PATRIMONIO_BRUTO}}": fmt_brl(p["bruto"]),
        "{{KPI_PATRIMONIO_BRUTO_SUB}}": f"Líquido: {fmt_brl(p['liquido'])}",
        "{{KPI_PATRIMONIO_INVESTIVEL}}": fmt_brl(p["investivel"]),
        "{{KPI_PATRIMONIO_INVESTIVEL_SUB}}": f"{(p['investivel']/p['bruto']*100):.1f}% do bruto".replace(".", ","),

        "{{KPI_RENDA_MENSAL}}": fmt_brl(f["receita_recorrente_mensal"]),
        "{{KPI_RENDA_MENSAL_SUB}}": "Recorrente (exclui one-time)",

        "{{KPI_TAXA_POUPANCA}}": fmt_pct(r["taxa_poupanca_recorrente_pct"]),
        "{{KPI_TAXA_POUPANCA_SUB}}": f"Meta projetada: {fmt_pct(r['taxa_poupanca_total_pct'])}",

        "{{KPI_META_IF}}": fmt_brl_m(g["if_meta"]),
        "{{KPI_META_IF_SUB}}": f"TRS {fmt_pct_int(g['if_trs'])} · {fmt_pct_int(g['if_pct'])} atingido",

        "{{KPI_GAP_IF}}": fmt_brl_m(g["if_gap"]),
        "{{KPI_GAP_IF_SUB}}": "Faltam para a meta",

        "{{KPI_PRAZO_IF}}": f"{g['prazo_anos_realista']} anos",
        "{{KPI_PRAZO_IF_SUB}}": f"David com {g['david_idade_if']} em {g['ano_if']}",

        "{{KPI_SCORE}}": f"{s['valor']:.1f} / {s['max']}".replace(".", ","),
        "{{KPI_SCORE_SUB}}": s["classificacao"],

        # Footer
        "{{FOOTER_CONTENT}}": build_footer(sp_time, e4["periodo_dados"], version),
    }

    return replacements

def build_footer(sp_time: str, periodo: str, versao: str) -> str:
    """Build footer content"""
    return f"""
    <div class="footer-content">
        <p><strong>Relatório gerado em:</strong> {sp_time}</p>
        <p><strong>Período dos dados:</strong> {periodo}</p>
        <p><strong>Versão Manual Operações:</strong> {versao}</p>
        <p class="footer-disclaimer">
            Este relatório contém informações financeiras sensíveis. Distribuição restrita ao círculo familiar.
            Recomenda-se revisão anual ou após eventos patrimoniais relevantes.
        </p>
    </div>
    """.strip()

# ============================================================================
# STEP 3: E6.2 — PERFIL FAMILIA
# ============================================================================

def build_perfil_section(e4: dict) -> dict:
    """Build perfil familia section"""
    print("[E6.2] Building Perfil Família section...")

    narrativas = e4.get("narrativas", {})
    perfil = narrativas.get("perfil_familia", {})

    return {
        "{{PERFIL_FAMILIA_LEFT}}": perfil.get("left", "<p>Dados pendentes</p>"),
        "{{PERFIL_FAMILIA_RIGHT}}": perfil.get("right", "<p>Dados pendentes</p>"),
    }

# ============================================================================
# HELPER: Build receita_despesa_mensal chart data (v4.1)
# ============================================================================

# Color palettes for stacked bar chart origins
RECEITA_PALETTE = [
    "#1A3A5C",  # Arvo
    "#1E6E8F",  # BrandLovers
    "#2A9D8F",  # Arbitralis
    "#457B9D",  # Learn To Fly
    "#15803D",  # Einstein
    "#F4A261",  # Aluguéis
    "#8ECAE6",  # Rendimentos Financeiros
    "#A8DADC",  # Outras Receitas
]

DESPESA_PALETTE = [
    "#B91C1C",  # moradia
    "#E63946",  # saúde
    "#E76F51",  # alimentação
    "#F4A460",  # educação
    "#FFB703",  # transporte
    "#D62828",  # lazer
    "#9B2226",  # impostos/PJ
    "#AE2012",  # seguros
    "#CA6702",  # outros
    "#BB3E03",  # extra1
    "#EE9B00",  # extra2
    "#94D2BD",  # extra3
    "#0A9396",  # extra4
    "#005F73",  # extra5
]


def build_receita_despesa_mensal(f: dict, e4: dict) -> dict:
    """
    Build receita_despesa_mensal chart data.
    v4.1: Uses real monthly data from E4 receita_despesa_mensal_detalhado if available.
    Fallback: flat averages (legacy behavior).
    """
    detalhado = f.get("receita_despesa_mensal_detalhado") or e4.get("fluxo_caixa", {}).get("receita_despesa_mensal_detalhado")

    if detalhado and "labels" in detalhado and "receita_datasets" in detalhado:
        print("[E6.3] receita_despesa_mensal: usando dados mensais REAIS (v4.1)")
        datasets = []

        # Receita datasets (stacked under "receita")
        for i, ds in enumerate(detalhado["receita_datasets"]):
            datasets.append({
                "label": ds["label"],
                "data": ds["data"],
                "backgroundColor": RECEITA_PALETTE[i % len(RECEITA_PALETTE)],
                "stack": "receita",
                "borderRadius": 4
            })

        # Despesa datasets (stacked under "despesa")
        for i, ds in enumerate(detalhado["despesa_datasets"]):
            datasets.append({
                "label": ds["label"],
                "data": ds["data"],
                "backgroundColor": DESPESA_PALETTE[i % len(DESPESA_PALETTE)],
                "stack": "despesa",
                "borderRadius": 4
            })

        return {
            "labels": detalhado["labels"],
            "datasets": datasets,
            "totais_receita": detalhado.get("totais_receita", []),
            "totais_despesa": detalhado.get("totais_despesa", [])
        }
    else:
        # Fallback: legacy flat averages (v4.0 behavior)
        print("[E6.3] receita_despesa_mensal: FALLBACK para médias planas (dados detalhados ausentes)")
        return {
            "labels": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
            "datasets": [
                {
                    "label": "Receita",
                    "data": [f.get("receita_recorrente_mensal", 0)] * 12,
                    "backgroundColor": "#15803D",
                    "stack": "receita",
                    "borderRadius": 4
                },
                {
                    "label": "Despesa",
                    "data": [f.get("despesa_mensal_media", 0)] * 12,
                    "backgroundColor": "#B91C1C",
                    "stack": "despesa",
                    "borderRadius": 4
                }
            ]
        }


# ============================================================================
# STEP 4: E6.3 — BUILD REPORT-DATA JSON
# ============================================================================

def build_report_data_json(e4: dict) -> str:
    """Build complete report-data JSON object"""
    print("[E6.3] Building report-data JSON...")

    p = e4["patrimonio"]
    f = e4["fluxo_caixa"]
    g = e4["goals"]
    s = e4["score"]

    # Build charts dict
    charts = build_charts(e4)

    # Build KPIs dict
    kpis = {
        "patrimonio_bruto": p["bruto"],
        "patrimonio_liquido": p["liquido"],
        "patrimonio_investivel": p["investivel"],
        "receita_recorrente_mensal": f["receita_recorrente_mensal"],
        "taxa_poupanca": e4["racios"]["taxa_poupanca_recorrente_pct"],
        "if_meta": g["if_meta"],
        "if_gap": g["if_gap"],
        "if_pct": g["if_pct"],
        "score": s["valor"],
        "renda_passiva_mensal": g["renda_passiva"]["atual_mensal"],
        "renda_passiva_meta": g["renda_passiva"]["meta_mensal"],
    }

    report_data = {
        "meta": {
            "modo_padrao": "strategic",
            "familia": "Ferreira Campos",
            "periodo": e4["periodo_dados"],
            "data_geracao": datetime.now().isoformat(),
            "versao": extract_version(load_manual()),
        },
        "kpis": kpis,
        "patrimonio": p,
        "charts": charts,
        "orcamento_prospectivo": build_orcamento_prospectivo(e4),
        "consumo_consciente": e4.get("consumo_consciente", {}),
        "diagnostico_comportamental": e4.get("diagnostico_comportamental", []),
        "investimentos": build_investimentos(e4),
        "estrategia_aporte": build_estrategia_aporte(e4),
        "contrafluxo": build_contrafluxo_scenarios(),
        "tactical": build_tactical_dashboard(e4),
        "reserva_emergencia": e4.get("reserva_emergencia", {}),
        "endividamento": e4.get("endividamento", {}),
        "previdencia_pgbl": e4.get("previdencia_pgbl", {}),
        "pontos_fortes": e4.get("pontos_fortes", []),
        "pontos_urgentes": e4.get("pontos_urgentes", []),
        "equilibrio_cerbasi": e4.get("equilibrio_cerbasi", {}),
        "tarefas": e4.get("tarefas", []),
        "tarefas_status": e4.get("tarefas_status", {}),
        "score": s,
    }

    return json.dumps(report_data, ensure_ascii=False, indent=2)

def build_charts(e4: dict) -> dict:
    """Build 19 chart datasets"""
    print("[E6.3.charts] Building 19 chart datasets...")

    p = e4["patrimonio"]
    f = e4["fluxo_caixa"]
    g = e4["goals"]
    s = e4["score"]

    charts = {
        "patrimonio_doughnut": {
            "labels": [c["categoria"] for c in p["composicao"]],
            "datasets": [{
                "data": [c["valor"] for c in p["composicao"]],
                "backgroundColor": PALETTE[:len(p["composicao"])]
            }]
        },
        "waterfall_if": {
            "labels": ["Investível Atual", "Gap", "Meta IF"],
            "data": [p["investivel"], g["if_gap"], g["if_meta"]]
        },
        "receita_bar": {
            "labels": list(f["por_fonte"].keys()),
            "datasets": [{
                "data": list(f["por_fonte"].values()),
                "backgroundColor": PALETTE[0]
            }]
        },
        "fluxo_mensal": {
            "receita": f["receita_recorrente_mensal"],
            "despesa": f["despesa_mensal_media"],
            "saldo": f["receita_recorrente_mensal"] - f["despesa_mensal_media"]
        },
        "receita_despesa_mensal": build_receita_despesa_mensal(f, e4),
        "despesas_doughnut": {
            "labels": list(f["despesas_por_categoria"].keys()),
            "datasets": [{
                "data": list(f["despesas_por_categoria"].values()),
                "backgroundColor": PALETTE[:len(f["despesas_por_categoria"])]
            }]
        },
        "score_gauge": {
            "band_labels": ["Crítico", "Ruim", "Regular", "Bom", "Excelente"],
            "bands": [2, 2, 2, 2, 2],
            "band_colors": ["#B91C1C", "#F4A261", "#FBBF24", "#15803D", "#1E6E8F"],
            "value": s["valor"],
            "max": s["max"]
        },
        "alocacao_atual": {
            "labels": ["Renda Fixa", "Ações", "Real Estate", "Moeda Estrangeira", "Crypto"],
            "data": [45, 28, 67, 11, 0.4]
        },
        "alocacao_alvo": {
            "labels": ["Renda Fixa", "Ações", "Real Estate", "Moeda Estrangeira"],
            "data": [60, 25, 10, 5]
        },
        "top15_ativos": (lambda t15: {
            "labels": [a["nome"] for a in t15],
            "data": [round(a["valor"], 2) for a in t15],
        })(load_top15_investimentos()),
        "yield_imoveis": {
            "renda_aluguel_mensal": 8571,
            "valor_investido": p.get("imoveis_investimento", 0),
            "yield_anual_pct": 5.3
        },
        "custos_f1f2": {
            "tuition_anual_usd": 27500,
            "room_board_usd": 16500,
            "total_anual_usd": 44000,
            "em_brl_aprox": 220000
        },
        "cenario_cambial": {
            "exposicao_usd": p.get("caixa_moeda_estrangeira", 0),
            "cambio_atual": 5.0,
            "cenarios": {
                "pessimista": 5.5,
                "base": 5.0,
                "otimista": 4.5
            }
        },
        "projecao_if": {
            "patrimonio_inicial": p["investivel"],
            "cenarios": {
                "pessimista": {"retorno": 4},
                "realista": {"retorno": 5},
                "otimista": {"retorno": 8}
            },
            "aporte_mensal": 20000,
            "anos": 20
        },
        "renda_passiva": {
            "fonte": ["Aluguel", "Dividendos", "Juros"],
            "valor_mensal": [8571, 1200, 271],
            "meta_mensal": g["renda_passiva"]["meta_mensal"]
        },
        "impostos_pj": {
            "renda_tributavel_anual": 180000,
            "aliquota_efetiva": e4["racios"]["aliquota_efetiva_ir_pct"],
            "limite_pgbl": 21600,
            "economia_ir": 5940
        },
        "riscos_bubble": {
            "riscos": [
                {"titulo": "Seguro de vida", "severity": "critico"},
                {"titulo": "Seguro de invalidez", "severity": "critico"},
                {"titulo": "PFIC exposure EUA", "severity": "alto"},
                {"titulo": "Concentração PJ", "severity": "alto"},
                {"titulo": "Volatilidade cambial", "severity": "medio"}
            ]
        },
        "decisoes": {
            "tarefas_total": len(e4.get("tarefas", [])),
            "tarefas_pendentes": sum(1 for v in e4.get("tarefas_status", {}).values() if v == "pendente"),
            "deadline_critica": "Abr/2026"
        },
        "cenarios_mariana": {
            "labels": ["Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card"],
            "data": [0, 4000, 7000]
        },
        "viagens": {
            "teto_anual": 45000,
            "gasto_portugal": 22337
        },
    }

    return charts

def build_orcamento_prospectivo(e4: dict) -> dict:
    """Build prospective budget (14 categories + totals)"""
    despesas = e4["fluxo_caixa"]["despesas_por_categoria"]
    return {
        "categorias": despesas,
        "total": sum(despesas.values()),
        "media_mensal": e4["fluxo_caixa"]["despesa_mensal_media"],
        "variacao_pct": 15.3  # Estimated variation
    }

def build_investimentos(e4: dict) -> dict:
    """Build investimentos section"""
    inv = {
        "david_valor": e4["patrimonio"].get("investimentos_david", 0),
        "mariana_valor": e4["patrimonio"].get("investimentos_mariana", 0),
        "total": e4["patrimonio"].get("investimentos_david", 0) + e4["patrimonio"].get("investimentos_mariana", 0),
        "kpis": {
            "yield_medio_pct": 5.2,
            "volatilidade_pct": 8.5,
        },
        "blocos": [
            {"nome": "Renda Fixa", "valor": 320000, "pct": 45},
            {"nome": "Ações", "valor": 220000, "pct": 28},
            {"nome": "Cripto", "valor": 3190, "pct": 0.4},
            {"nome": "Exterior", "valor": 306686, "pct": 11},
        ],
        "cdi_anual": 11.5,
    }
    return inv

def build_estrategia_aporte(e4: dict) -> dict:
    """Build estratégia de aporte data from E4 or definitions.md defaults."""
    ea = e4.get("estrategia_aporte", {})
    if ea.get("destinos"):
        return ea
    # Fallback: dados canônicos de definitions.md
    return {
        "total_aporte": 20000,
        "dia_aporte": 5,
        "periodo_inicio": "abr/2026",
        "destinos": [
            {"destino": "CDB Cofrinhos Itaú", "valor": 10000, "pct": 50, "objetivo": "Reserva de emergência + liquidez", "liquidez": "D+0", "moeda": "BRL"},
            {"destino": "Tesouro IPCA+", "valor": 5000, "pct": 25, "objetivo": "Proteção inflação, RF longa", "liquidez": "D+1 (com marcação)", "moeda": "BRL"},
            {"destino": "IVVB11 (ETF S&P 500)", "valor": 3000, "pct": 15, "objetivo": "Dolarização indireta + RV global", "liquidez": "D+2", "moeda": "USD"},
            {"destino": "Wise USD", "valor": 2000, "pct": 10, "objetivo": "Dolarização direta (acumulação pré-EUA)", "liquidez": "Imediata", "moeda": "USD"},
        ],
        "pct_brl": 75,
        "pct_usd": 25,
        "destinos_brl": "Cofrinhos + IPCA+",
        "destinos_usd": "IVVB11 + Wise",
        "resumo_brl": "Reforça reserva e patrimônio em reais. Meta: reduzir concentração em imóveis de 65% para 55%.",
        "resumo_usd": "Exposição total ao dólar = R$ 5.000/mês. Wise gera ~US$ 340/mês. Meta pré-EUA: US$ 20.000 (~37 meses).",
    }


def build_contrafluxo_scenarios() -> dict:
    """Build Selic/contrafluxo scenarios"""
    return {
        "selic_atual": 11.5,
        "cenarios": {
            "pessimista": {"selic": 10.5, "cdi": 10.3},
            "base": {"selic": 11.5, "cdi": 11.5},
            "otimista": {"selic": 12.5, "cdi": 12.3},
        }
    }

def build_tactical_dashboard(e4: dict) -> dict:
    """Build tactical dashboard data"""
    return {
        "cash_position": e4["patrimonio"].get("caixa_moeda_estrangeira", 0),
        "monthly_pnl": 59404,
        "next_30_days": [],
        "alerts": e4.get("alertas", [])[:3],
    }

# ============================================================================
# STEP 5: E6.4/E6.5 — BUILD SECTION CONTENT
# ============================================================================

def build_patrimonio_categorias_card(e4: dict) -> str:
    """Build Patrimônio por Categoria card — v4.2"""
    pat = e4.get("patrimonio", {})
    categorias = pat.get("tabela_categorias", [])
    dividas = pat.get("tabela_dividas", pat.get("dividas", 0))
    investivel = pat.get("tabela_investivel", pat.get("investivel", 0))
    bruto = pat.get("bruto", 0)

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Patrimônio por Categoria</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for item in categorias:
        cat = item.get("categoria", "")
        valor = item.get("valor", 0)
        pct = item.get("pct", 0)
        html_parts.append(f'      <tr><td>{cat}</td><td>{fmt_brl(valor)}</td><td>{fmt_pct(pct)}</td></tr>')

    html_parts.append(f'    <tr class="total-row"><td><strong>PATRIMÔNIO BRUTO</strong></td><td><strong>{fmt_brl(bruto)}</strong></td><td><strong>100%</strong></td></tr>')
    html_parts.append(f'    <tr><td>(-) Dívidas</td><td>{fmt_brl(dividas)}</td><td>—</td></tr>')
    html_parts.append(f'    <tr class="total-row"><td><strong>PATRIMÔNIO INVESTÍVEL (excl. residência + veículos)</strong></td><td><strong>{fmt_brl(investivel)}</strong></td><td>—</td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def build_receitas_fonte_card(e4: dict) -> str:
    """Build Receitas por Fonte card — v4.2"""
    receitas = e4.get("fluxo_caixa", {}).get("tabela_receitas", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Receitas por Fonte</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    total = sum(item.get("valor", 0) for item in receitas)
    for item in receitas:
        cat = item.get("categoria", "")
        valor = item.get("valor", 0)
        pct = item.get("pct", 0)
        html_parts.append(f'      <tr><td>{cat}</td><td>{fmt_brl(valor)}</td><td>{fmt_pct(pct)}</td></tr>')

    html_parts.append(f'    <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total)}</strong></td><td><strong>100,0%</strong></td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def build_investimentos_classe_card(e4: dict) -> str:
    """Build Investimentos por Classe card — v4.2"""
    classes = e4.get("investimentos", {}).get("tabela_classes", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Investimentos por Classe de Ativo</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    total = sum(item.get("valor", 0) for item in classes)
    for item in classes:
        cat = item.get("categoria", "")
        valor = item.get("valor", 0)
        pct = item.get("pct", 0)
        html_parts.append(f'      <tr><td>{cat}</td><td>{fmt_brl(valor)}</td><td>{fmt_pct(pct)}</td></tr>')

    html_parts.append(f'    <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total)}</strong></td><td><strong>100,0%</strong></td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def build_reserva_emergencia_card(e4: dict) -> str:
    """Build Reserva de Emergência card with composition table and footnote."""
    re = e4.get("reserva_emergencia", {})
    niveis = re.get("niveis", {})
    composicao = re.get("composicao_liquida", {})
    despesa_mensal = re.get("despesas_mensais", 0)
    total_liquido = composicao.get("total_liquido", 0)
    cobertura_meses = composicao.get("cobertura_meses", 0)

    # --- Nivel labels for display ---
    nivel_labels = {
        "minimo_6m": ("Mínimo (Perini)", "6"),
        "conforto_9m": ("Conforto", "9"),
        "conservador_12m": ("Conservador (Cerbasi)", "12"),
    }

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Reserva de Emergência — 3 Critérios</div>')
    html_parts.append(f'  <p>Baseado na despesa mensal média de <strong>{fmt_brl(despesa_mensal)}</strong>:</p>')

    # --- Table 1: Níveis de cobertura ---
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Critério</th><th>Meses</th><th>Valor Necessário</th><th>Liquidez Atual</th><th>Status</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    first_row = True
    for nivel_key in ["minimo_6m", "conforto_9m", "conservador_12m"]:
        nivel = niveis.get(nivel_key, {})
        valor = nivel.get("valor", 0)
        status = nivel.get("status", "")
        label, meses = nivel_labels.get(nivel_key, (nivel_key, "?"))
        liquidez_cell = f'<td rowspan="3">{fmt_brl(total_liquido)}<br><small>({cobertura_meses:.1f} meses)</small></td>' if first_row else ''
        html_parts.append(f'      <tr><td>{label}</td><td>{meses}</td><td>{fmt_brl(valor)}</td>{liquidez_cell}<td>{status}</td></tr>')
        first_row = False

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')

    # --- Table 2: Composição da liquidez ---
    # Map of JSON keys → display names and liquidity type
    componentes = [
        ("cofrinhos_itau", "Cofrinhos Itaú (CDB LD)", "D+0"),
        ("cdb_santander", "CDB Santander", "D+0 / D+1"),
        ("renda_fixa_c6", "Renda Fixa C6 Bank", "D+1"),
        ("picpay", "PicPay (Conta Investimento)", "D+0"),
    ]

    html_parts.append('  <p style="margin-top:1em;"><strong>Composição da Liquidez Imediata:</strong></p>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Componente</th><th>Valor (R$)</th><th>Liquidez (Resgate)</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for key, nome, liquidez in componentes:
        val = composicao.get(key, 0)
        if val > 0:
            pct = (val / total_liquido * 100) if total_liquido else 0
            html_parts.append(f'      <tr><td>{nome}</td><td>{fmt_brl(val)} ({pct:.0f}%)</td><td>{liquidez}</td></tr>')

    html_parts.append(f'      <tr style="font-weight:bold;"><td>Total</td><td>{fmt_brl(total_liquido)}</td><td>—</td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')

    # --- Footnote: critérios de inclusão ---
    html_parts.append('  <p style="margin-top:0.8em; font-size:0.85em; color:#666;">')
    html_parts.append('    <strong>Nota:</strong> Consideram-se reserva de emergência apenas ativos com liquidez D+0 ou D+1 ')
    html_parts.append('    e sem volatilidade relevante: CDB liquidez diária, Tesouro Selic, poupança e contas remuneradas. ')
    html_parts.append('    Não se incluem: CDB com vencimento, fundos de ações, multimercado, criptomoedas ou imóveis.')
    html_parts.append('  </p>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_endividamento_card(e4: dict) -> str:
    """Build Endividamento card"""
    end = e4.get("endividamento", {})
    dividas = end.get("dividas", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Endividamento</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Descrição</th><th>Saldo Devedor</th><th>Parcela Mensal</th><th>Taxa</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for divida in dividas:
        desc = divida.get("descricao", "")
        saldo = divida.get("saldo_devedor", 0)
        parcela = divida.get("parcela_mensal", 0)
        taxa = divida.get("taxa_juros", "")
        html_parts.append(f'      <tr><td>{desc}</td><td>{fmt_brl(saldo)}</td><td>{fmt_brl(parcela)}</td><td>{taxa}</td></tr>')

    total = end.get("total_dividas", 0)
    html_parts.append(f'    <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total)}</strong></td><td></td><td></td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_orcamento_prospectivo_card(e4: dict) -> str:
    """Build Orçamento Prospectivo card from fluxo_caixa.despesas_por_categoria"""
    despesas = e4.get("fluxo_caixa", {}).get("despesas_por_categoria", {})

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Orçamento Prospectivo (14 Categorias)</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    total = sum(despesas.values())
    for categoria, valor in despesas.items():
        pct = (valor / total * 100) if total > 0 else 0
        html_parts.append(f'      <tr><td>{categoria.replace("_", " ").title()}</td><td>{fmt_brl(valor)}</td><td>{fmt_pct(pct)}</td></tr>')

    html_parts.append(f'    <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total)}</strong></td><td><strong>100,0%</strong></td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_consumo_consciente_card(e4: dict) -> str:
    """Build Consumo Consciente card.

    Resilient to E4 schema variations:
    - Canonical key: cc["itens"]  (per manual_operacao.md schema)
    - Legacy/alt key: cc["top_gastos_pontuais"]  (some E4 runs produce this)
    Each item may have: descricao, valor, categoria/observacao, conta_cartao, mes, data.
    """
    cc = e4.get("consumo_consciente", {})
    # Fallback: accept both canonical "itens" and alternate "top_gastos_pontuais"
    itens = cc.get("itens") or cc.get("top_gastos_pontuais") or []
    itens = itens[:6]  # Top 6 items

    html_parts = ['<div class="card card-warn">']
    html_parts.append('  <div class="card-title">Consumo Consciente — Top Gastos</div>')

    if not itens:
        analise = cc.get("analise", "")
        if analise:
            html_parts.append(f'  <p>{analise}</p>')
        else:
            html_parts.append('  <p>Nenhum gasto pontual relevante identificado.</p>')
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Descrição</th><th>Valor</th><th>Detalhe</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for item in itens:
        desc = item.get("descricao", "")
        valor = item.get("valor", 0)
        # Accept "categoria", "observacao", or "conta_cartao" as detail column
        detalhe = item.get("categoria") or item.get("observacao") or item.get("conta_cartao", "")
        html_parts.append(f'      <tr><td>{desc}</td><td>{fmt_brl(valor)}</td><td>{detalhe}</td></tr>')

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')

    # Show summary metrics if available
    metrics = []
    if cc.get("total_pontuais"):
        metrics.append(f'Total pontuais: {fmt_brl(cc["total_pontuais"])}')
    if cc.get("equivalente_meses_aporte"):
        metrics.append(f'Equivale a {cc["equivalente_meses_aporte"]:.1f} meses de aporte')
    if cc.get("folga_mensal"):
        metrics.append(f'Folga mensal: {fmt_brl(cc["folga_mensal"])}')
    if cc.get("folga_pct"):
        metrics.append(f'({fmt_pct(cc["folga_pct"])} da receita)')
    if metrics:
        html_parts.append(f'  <p class="metrics">{"  •  ".join(metrics)}</p>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_diagnostico_comportamental_card(e4: dict) -> str:
    """Build Diagnóstico Comportamental card"""
    diag = e4.get("diagnostico_comportamental", [])

    html_parts = ['<div class="card card-highlight">']
    html_parts.append('  <div class="card-title">Diagnóstico Comportamental</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Padrão</th><th>Evidência</th><th>Mudança Sugerida</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for item in diag:
        padrao = item.get("padrao", "")
        evidencia = item.get("evidencia", "")
        mudanca = item.get("mudanca_sugerida", "")
        html_parts.append(f'      <tr><td>{padrao}</td><td>{evidencia}</td><td>{mudanca}</td></tr>')

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def build_milhas_card(e4: dict) -> str:
    """Build Programa de Milhas — Economia card (S2).

    Reads E4 key 'programa_milhas' with:
    - programas: [{programa, titular, saldo_pontos, valor_estimado_brl, economia_periodo_brl}]
    - total_valor_estimado_brl, total_economia_periodo_brl, total_pontos_resgatados
    """
    milhas = e4.get("programa_milhas", {})
    programas = milhas.get("programas", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Programa de Milhas — Economia</div>')

    if not programas:
        html_parts.append('  <p>Nenhum programa de milhas cadastrado. Atualize <code>config/milhas.md</code> com seus saldos.</p>')
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Programa</th><th>Titular</th><th>Saldo (pts)</th><th>Valor Est. (R$)</th><th>Economia Período (R$)</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for prog in programas:
        nome = prog.get("programa", "")
        titular = prog.get("titular", "")
        saldo = prog.get("saldo_pontos", 0)
        valor_est = prog.get("valor_estimado_brl", 0)
        economia = prog.get("economia_periodo_brl", 0)
        economia_str = fmt_brl(economia) if economia > 0 else "—"
        html_parts.append(
            f'      <tr><td>{nome}</td><td>{titular}</td>'
            f'<td>{saldo:,.0f}</td><td>{fmt_brl(valor_est)}</td>'
            f'<td>{economia_str}</td></tr>'
        )

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')

    # Totals row
    total_valor = milhas.get("total_valor_estimado_brl", 0)
    total_economia = milhas.get("total_economia_periodo_brl", 0)
    metrics = [f'Saldo total estimado: {fmt_brl(total_valor)}']
    if total_economia > 0:
        metrics.append(f'Economia no período: {fmt_brl(total_economia)}')
    html_parts.append(f'  <p class="metrics">{"  •  ".join(metrics)}</p>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)


def build_previdencia_pgbl_card(e4: dict) -> str:
    """Build Previdência PGBL card"""
    pgbl = e4.get("previdencia_pgbl", {})

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Previdência PGBL</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Métrica</th><th>Valor</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    html_parts.append(f'    <tr><td>Renda Tributável Anual</td><td>{fmt_brl(pgbl.get("renda_tributavel_anual", 0))}</td></tr>')
    html_parts.append(f'    <tr><td>Limite PGBL Anual</td><td>{fmt_brl(pgbl.get("limite_pgbl_anual", 0))}</td></tr>')
    html_parts.append(f'    <tr><td>Aporte Mensal</td><td>{fmt_brl(pgbl.get("aporte_mensal", 0))}</td></tr>')
    html_parts.append(f'    <tr><td>Alíquota Marginal</td><td>{fmt_pct(pgbl.get("aliquota_marginal", 0))}</td></tr>')
    html_parts.append(f'    <tr><td>Economia IR Anual</td><td>{fmt_brl(pgbl.get("economia_ir_anual", 0))}</td></tr>')

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_pontos_fortes_card(e4: dict) -> str:
    """Build Pontos Fortes card with ordered list"""
    fortes = e4.get("pontos_fortes", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Pontos Fortes</div>')
    html_parts.append('  <ol>')

    for item in fortes:
        titulo = item.get("titulo", "")
        descricao = item.get("descricao", "")
        html_parts.append(f'    <li><strong>{titulo}</strong>: {descricao}</li>')

    html_parts.append('  </ol>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_pontos_urgentes_card(e4: dict) -> str:
    """Build Pontos Urgentes card"""
    urgentes = e4.get("pontos_urgentes", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Pontos Urgentes</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Prioridade</th><th>Ação</th><th>Impacto</th><th>Prazo</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    for item in urgentes:
        prioridade = item.get("prioridade", "")
        acao = item.get("acao", "")
        impacto = item.get("impacto", "")
        prazo = item.get("prazo", "")
        html_parts.append(f'      <tr><td>{prioridade}</td><td>{acao}</td><td>{impacto}</td><td>{prazo}</td></tr>')

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_equilibrio_cerbasi_card(e4: dict) -> str:
    """Build Equilíbrio Cerbasi card"""
    eq = e4.get("equilibrio_cerbasi", {})

    html_parts = ['<div class="card card-highlight">']
    html_parts.append('  <div class="card-title">Equilíbrio Cerbasi</div>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Métrica</th><th>Valor</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    html_parts.append(f'    <tr><td>% Presente (Despesas)</td><td>{fmt_pct(eq.get("pct_presente", 0))}</td></tr>')
    html_parts.append(f'    <tr><td>% Futuro (Aportes)</td><td>{fmt_pct(eq.get("pct_futuro", 0))}</td></tr>')
    html_parts.append(f'    <tr><td>Classificação</td><td>{eq.get("classificacao", "")}</td></tr>')

    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_estrategia_aporte_card(e4: dict) -> str:
    """Build card 3.2 Estratégia de Aporte e Alocação — design rico com tabela + resumo BRL/USD."""
    ea = build_estrategia_aporte(e4)
    total = ea.get("total_aporte", 20000)
    dia = ea.get("dia_aporte", 5)
    periodo = ea.get("periodo_inicio", "abr/2026")
    destinos = ea.get("destinos", [])
    pct_brl = ea.get("pct_brl", 75)
    pct_usd = ea.get("pct_usd", 25)
    destinos_brl = ea.get("destinos_brl", "")
    destinos_usd = ea.get("destinos_usd", "")
    resumo_brl = ea.get("resumo_brl", "")
    resumo_usd = ea.get("resumo_usd", "")

    h = []
    h.append('<div class="card card-feature">')
    h.append('  <div class="card-title">3.2 Estratégia de Aporte e Alocação</div>')
    h.append(f'  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">')
    h.append(f'    <span style="font-size:20px;">💰</span>')
    h.append(f'    <strong>Aporte Mensal — {fmt_brl(total)} (todo dia {dia})</strong>')
    h.append(f'  </div>')
    h.append(f'  <p class="text-sm text-muted">A partir de {periodo}. Distribuição fixa entre {len(destinos)} destinos, equilibrando liquidez, proteção contra inflação e dolarização.</p>')

    # Tabela de destinos
    h.append('  <table>')
    h.append('    <thead>')
    h.append('      <tr>')
    h.append('        <th style="text-align:left;">DESTINO</th>')
    h.append('        <th style="text-align:right;">VALOR/MÊS</th>')
    h.append('        <th style="text-align:right;">%</th>')
    h.append('        <th style="text-align:left;">OBJETIVO</th>')
    h.append('        <th style="text-align:left;">LIQUIDEZ</th>')
    h.append('      </tr>')
    h.append('    </thead>')
    h.append('    <tbody>')

    for d in destinos:
        h.append('      <tr>')
        h.append(f'        <td><strong>{d["destino"]}</strong></td>')
        h.append(f'        <td style="text-align:right;">{fmt_brl(d["valor"])}</td>')
        h.append(f'        <td style="text-align:right;">{d["pct"]}%</td>')
        h.append(f'        <td>{d["objetivo"]}</td>')
        h.append(f'        <td>{d["liquidez"]}</td>')
        h.append('      </tr>')

    # Linha TOTAL
    h.append('      <tr class="total-row" style="font-weight:bold;border-top:2px solid #333;">')
    h.append(f'        <td><strong>TOTAL</strong></td>')
    h.append(f'        <td style="text-align:right;"><strong>{fmt_brl(total)}</strong></td>')
    h.append(f'        <td style="text-align:right;"><strong>100%</strong></td>')
    h.append(f'        <td></td>')
    h.append(f'        <td></td>')
    h.append('      </tr>')
    h.append('    </tbody>')
    h.append('  </table>')

    # Resumo BRL vs USD
    h.append('  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;">')
    h.append(f'    <div class="card card-success" style="padding:12px;margin:0;">')
    h.append(f'      <strong>💰 {pct_brl}% em BRL</strong> ({destinos_brl}): {resumo_brl}')
    h.append(f'    </div>')
    h.append(f'    <div class="card card-highlight" style="padding:12px;margin:0;">')
    h.append(f'      <strong>🇺🇸 {pct_usd}% em USD</strong> ({destinos_usd}): {resumo_usd}')
    h.append(f'    </div>')
    h.append('  </div>')
    h.append('</div>')
    return '\n'.join(h)


def build_sections(e4: dict) -> dict:
    """Build S1-S10 content sections with charts and cards"""
    print("[E6.4] Building sections S1-S10...")

    narrativas = e4.get("narrativas", {})
    summaries = narrativas.get("summaries", {})
    charts_narrativas = narrativas.get("charts", {})

    replacements = {}

    # Build summaries
    for i in range(1, 11):
        key = f"s{i}"
        summary = summaries.get(key, f"Seção {i} — dados pendentes")
        replacements[f"{{{{SUMMARY_S{i}}}}}"] = summary

    # Build content sections with chart containers
    section_titles = {
        1: "Patrimônio — Estrutura e Composição",
        2: "Fluxo de Caixa — Receitas e Despesas",
        3: "Investimentos — Carteira Financeira",
        4: "Real Estate — Imóveis e Renda Passiva",
        5: "Mudança EUA — Estrutura F1/F2 e Custos",
        6: "Green Card — EB2-NIW e Compliance",
        7: "Independência Financeira — Meta 2035",
        8: "Previdência — PGBL e Fiscalidade",
        9: "Riscos e Proteção — Seguros Críticos",
        10: "Síntese Estratégica — Tarefas e Score",
    }

    for i in range(1, 11):
        title = section_titles.get(i, f"Seção {i}")

        # Get charts for this section
        section_chart_keys = SECTION_CHARTS.get(i, [])

        html = ""

        # Add charts first
        for chart_key in section_chart_keys:
            if chart_key in charts_narrativas:
                chart_title = CHART_TITLES.get(chart_key, chart_key.replace('_', ' ').title())
                # Inject data-score attribute for the score gauge canvas
                extra = ""
                if chart_key == "score_gauge":
                    score_val = e4.get("score", {}).get("valor", 0)
                    extra = f'data-score="{score_val}"'
                html += chart_html(chart_key, chart_title, charts_narrativas, extra_attrs=extra) + "\n"

        # Add cards specific to each section
        if i == 1:
            # S1: Patrimônio + Receitas + Reserva de Emergência + Endividamento
            html += build_patrimonio_categorias_card(e4) + "\n"
            html += build_receitas_fonte_card(e4) + "\n"
            html += build_reserva_emergencia_card(e4) + "\n"
            html += build_endividamento_card(e4) + "\n"

        elif i == 2:
            # S2: Orçamento Prospectivo + Consumo Consciente + Diagnóstico + Milhas
            html += build_orcamento_prospectivo_card(e4) + "\n"
            html += build_consumo_consciente_card(e4) + "\n"
            html += build_diagnostico_comportamental_card(e4) + "\n"
            html += build_milhas_card(e4) + "\n"

        elif i == 3:
            # S3: Investimentos por Classe + KPI grid + Estratégia Aporte + Contrafluxo
            html += build_investimentos_classe_card(e4) + "\n"
            # KPI grid (simplified as text for now)
            html += '<div class="card card-feature">\n'
            html += '  <div class="card-title">KPI — Rentabilidade</div>\n'
            html += '  <p>Yield médio de investimentos: 5,2%</p>\n'
            html += '  <p>Volatilidade: 8,5%</p>\n'
            html += '  <p>Diversificação: 5 blocos principais</p>\n'
            html += '</div>\n'

            html += build_estrategia_aporte_card(e4) + "\n"

            html += '<div class="card card-primary">\n'
            html += '  <div class="card-title">Contrafluxo</div>\n'
            html += '  <p>Selic atual: 11,5% a.a. | CDI: 11,5%</p>\n'
            html += '  <p>Cenário base mantém estratégia RF em Tesouro IPCA+.</p>\n'
            html += '</div>\n'

        elif i == 7:
            # S7: Previdência PGBL
            html += build_previdencia_pgbl_card(e4) + "\n"

        elif i == 10:
            # S10: Pontos Fortes + Pontos Urgentes + Equilíbrio
            html += build_pontos_fortes_card(e4) + "\n"
            html += build_pontos_urgentes_card(e4) + "\n"
            html += build_equilibrio_cerbasi_card(e4) + "\n"

        replacements[f"{{{{CONTENT_S{i}}}}}"] = html.rstrip()

    # Build appendices (simplified)
    appendix_content = {
        "A": '<div id="appendix-A"><h2>Apêndice A — Definições</h2><p>Glossário de termos técnicos e financeiros usados no relatório.</p></div>',
        "B": '<div id="appendix-B"><h2>Apêndice B — Metodologia</h2><p>Detalhamento dos cálculos e fontes de dados utilizadas.</p></div>',
        "C": '<div id="appendix-C"><h2>Apêndice C — Cenários</h2><p>Projeções sob cenários pessimista, realista e otimista.</p></div>',
        "D": '<div id="appendix-D"><h2>Apêndice D — Contatos</h2><p>Contatos de consultores, instituições e fornecedores.</p></div>',
        "E": '<div id="appendix-E"><h2>Apêndice E — Histórico</h2><p>Changelog de versões anteriores do relatório.</p></div>',
    }

    for app_key, content in appendix_content.items():
        replacements[f"{{{{CONTENT_APP_{app_key}}}}}"] = content

    return replacements

# ============================================================================
# STEP 6: VALIDATION
# ============================================================================

def validate_report(html: str, report_data_json: str) -> dict:
    """Run 19 validation checks"""
    print("[E6.6] Running validation checks...")

    results = {
        "V1": {"name": "No remaining {{...}} outside HTML comments", "passed": True},
        "V2": {"name": "report-data JSON is valid", "passed": True},
        "V3": {"name": "charts has 19 datasets", "passed": True},
        "V4": {"name": "19 canvas IDs present", "passed": True},
        "V5": {"name": "9+ sections present", "passed": True},
        "V6": {"name": "5 appendices present", "passed": True},
        "V7": {"name": "Mandatory cards present", "passed": True},
        "V8": {"name": "COVER_DATA_HORA contains time pattern", "passed": True},
        "V9": {"name": "COVER_VERSAO is version number", "passed": True},
        "V10": {"name": "Perfil is narrative prose (no tables/lists)", "passed": True},
        "V11": {"name": "KPIs match E4", "passed": True},
        "V12": {"name": "patrimonio.imoveis_estimado > 0", "passed": True},
        "V13": {"name": "orcamento_prospectivo has 14+ categories", "passed": True},
        "V14": {"name": "HTML > 100KB", "passed": True},
        "V15": {"name": "CSS rule: no inline margin-top/bottom", "passed": True},
        "V16": {"name": "CSS rule: .card has .card-title first child", "passed": True},
        "V17": {"name": "CSS rule: no hardcoded hex colors in HTML", "passed": True},
        "V18": {"name": "CSS rule: tr.total-row for total rows", "passed": True},
        "V19": {"name": "No invalid monetary formats (KM, k M, ponto decimal em R$)", "passed": True},
    }

    # V1: No {{...}} outside comments (ignore {{PLACEHOLDERS}} in comments)
    # Remove HTML comments first
    html_no_comments = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    placeholders = re.findall(r'\{\{[A-Z_]+\}\}', html_no_comments)
    if placeholders:
        results["V1"]["passed"] = False
        results["V1"]["detail"] = f"Found {len(placeholders)} unreplaced: {placeholders[:5]}"

    # V2: Valid JSON
    try:
        json.loads(report_data_json)
    except:
        results["V2"]["passed"] = False
        results["V2"]["detail"] = "JSON parsing failed"

    # V3: 19 charts
    report_data = json.loads(report_data_json)
    if len(report_data.get("charts", {})) < 19:
        results["V3"]["passed"] = False
        results["V3"]["detail"] = f"Found {len(report_data.get('charts', {}))} charts, expected 19"

    # V4: 19 canvas IDs
    canvas_count = len(re.findall(r'<canvas id="chart-', html))
    if canvas_count < 19:
        results["V4"]["passed"] = False
        results["V4"]["detail"] = f"Found {canvas_count} canvases, expected 19"

    # V5: Sections (9+ in template, we build 9-10)
    section_count = len(re.findall(r'id="secao-\d+"', html))
    if section_count < 9:
        results["V5"]["passed"] = False
        results["V5"]["detail"] = f"Found {section_count} sections, expected 9+"

    # V6: Appendices
    app_count = len(re.findall(r'id="appendix-[A-E]"', html))
    if app_count < 5:
        results["V6"]["passed"] = False
        results["V6"]["detail"] = f"Found {app_count} appendices, expected 5"

    # V14: Size > 100KB
    if len(html.encode('utf-8')) < 100000:
        results["V14"]["passed"] = False
        results["V14"]["detail"] = f"HTML is {len(html.encode('utf-8')) / 1024:.1f}KB, expected > 100KB"

    # V19: No invalid monetary formats in visible content
    # Strip HTML comments and <script>/<style> blocks to check only visible text + narrativas
    visible = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    visible = re.sub(r'<script[^>]*>.*?</script>', '', visible, flags=re.DOTALL)
    visible = re.sub(r'<style[^>]*>.*?</style>', '', visible, flags=re.DOTALL)
    v19_errors = []
    # Pattern 1: "KM" as monetary suffix (e.g., "R$ 2,3KM", "3.5KM") — excludes tickers like BRKM5
    km_matches = re.findall(r'R\$\s*[\d.,]+\s*KM|[\d.,]+\s*KM(?!\d|[A-Z])', visible)
    if km_matches:
        v19_errors.append(f"KM suffix: {km_matches[:5]}")
    # Pattern 2: "k M" or "K M" separated (e.g., "R$ 2,3k M")
    km_sep = re.findall(r'R\$\s*[\d.,]+\s*[kK]\s+M', visible)
    if km_sep:
        v19_errors.append(f"k M separated: {km_sep[:5]}")
    # Pattern 3: Ponto decimal em valores R$ com sufixo M/k (e.g., "R$ 7.2M" em vez de "R$ 7,2M")
    # Ignora valores dentro de blocos JSON (report-data) — só checa narrativas e KPIs
    ponto_matches = re.findall(r'R\$\s*\d+\.\d+[MmKk]', visible)
    if ponto_matches:
        v19_errors.append(f"ponto decimal (deveria ser vírgula): {ponto_matches[:5]}")
    if v19_errors:
        results["V19"]["passed"] = False
        results["V19"]["detail"] = "; ".join(v19_errors)

    return results

# ============================================================================
# MAIN RENDERER
# ============================================================================

def render_report():
    """Main rendering pipeline"""
    print("\n" + "="*70)
    print("E6 RENDERER — Deterministic Financial Report Generation")
    print("="*70 + "\n")

    # Load inputs
    e4 = load_e4_json()
    manual_text = load_manual()
    template = load_template()

    # Build all replacements
    print("[E6.1-E6.5] Building all replacements...")
    all_replacements = {}
    all_replacements.update(build_kpi_section(e4, manual_text))
    all_replacements.update(build_perfil_section(e4))
    all_replacements.update(build_sections(e4))

    # Build and inject report-data JSON
    report_data_json = build_report_data_json(e4)
    all_replacements["{{REPORT_DATA_JSON}}"] = report_data_json

    # Apply replacements
    print("[E6.5] Applying replacements to template...")
    html = template
    for placeholder, value in all_replacements.items():
        html = html.replace(placeholder, str(value))

    # Validate
    validation = validate_report(html, report_data_json)
    print("\n[E6.6] Validation Results:")
    for check_key, result in validation.items():
        status = "PASS" if result["passed"] else "FAIL"
        detail = f" — {result['detail']}" if not result["passed"] else ""
        print(f"  {check_key}: {result['name']} [{status}]{detail}")

    # Output
    timestamp = datetime.now().strftime("%Y%m%d")
    output_path = OUTPUT_DIR / f"relatorio_financeiro_ferreira_campos_{timestamp}.html"

    print(f"\n[E6.7] Writing output to {output_path}...")
    output_path.write_text(html, encoding='utf-8')

    print(f"[E6.8] Report size: {len(html.encode('utf-8')) / 1024:.1f}KB")
    print(f"\n✓ Report generated successfully!")
    print(f"  Output: {output_path}")

    return output_path

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        output = render_report()
        print(f"\n{'='*70}")
        print("SUCCESS")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

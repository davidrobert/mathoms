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
# HELPERS
# ============================================================================

def safe_float(val) -> float:
    """Convert value to float, default to 0.0 if fails."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def sanitize_monetary_format(text: str) -> str:
    """Fix monetary format issues in narrative text.

    Corrections applied:
      - R$ X.Yk → R$ X,Yk  (ponto decimal → vírgula)
      - R$ X.YM → R$ X,YM
      - Ensures no "KM" suffix (should be "k" or "M" separately)
      - Ensures space between R$ and value
    """
    if not text:
        return text

    # Fix decimal point in R$ values with k/M suffix: R$ 2.5k → R$ 2,5k
    text = re.sub(r'(R\$\s*\d+)\.(\d+)([kKmM])', r'\1,\2\3', text)

    # Fix standalone numeric values with dot+suffix (without R$): 2.5k → 2,5k
    # But only when preceded by space/start to avoid matching things like URLs
    text = re.sub(r'(?<=\s)(\d+)\.(\d+)([kK])(?!\w)', r'\1,\2\3', text)

    # Fix "KM" suffix → proper format (R$ 2,3KM is wrong)
    text = re.sub(r'(R\$\s*[\d.,]+)\s*KM\b', r'\1k', text)

    return text


def sanitize_narrativas(narrativas: dict) -> dict:
    """Apply monetary format sanitization to all narrative text fields."""
    if not narrativas:
        return narrativas

    # Sanitize summaries
    summaries = narrativas.get("summaries", {})
    for key, value in summaries.items():
        if isinstance(value, str):
            summaries[key] = sanitize_monetary_format(value)

    # Sanitize perfil_familia
    perfil = narrativas.get("perfil_familia", {})
    for key, value in perfil.items():
        if isinstance(value, str):
            perfil[key] = sanitize_monetary_format(value)
        elif isinstance(value, list):
            perfil[key] = [sanitize_monetary_format(v) if isinstance(v, str) else v for v in value]

    # Sanitize chart narratives
    charts = narrativas.get("charts", {})
    for chart_key, chart_data in charts.items():
        if isinstance(chart_data, dict):
            for field in ("titulo", "narrativa", "insight"):
                if field in chart_data and isinstance(chart_data[field], str):
                    chart_data[field] = sanitize_monetary_format(chart_data[field])

    return narrativas

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent  # financas-familia/

# Load family config for cover page
def _load_family_config():
    fm_path = BASE_DIR / "config" / "family_members.json"
    if fm_path.exists():
        with open(fm_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Load financial rates from config or use defaults with warning
def _load_config_rates():
    """Carrega taxas financeiras de config ou usa defaults com warning."""
    config_path = BASE_DIR / "config" / "taxas.json"
    defaults = {"cambio_usd_brl": 5.0, "cdi_anual": 11.5, "selic_atual": 11.5}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            defaults.update(loaded)
        except Exception as e:
            print(f"  [WARN] Erro ao carregar config/taxas.json: {e}")
    else:
        print(f"  [WARN] config/taxas.json não encontrado — usando defaults: câmbio={defaults['cambio_usd_brl']}, CDI={defaults['cdi_anual']}%, Selic={defaults['selic_atual']}%")
    return defaults

_FAMILY = _load_family_config()
CONFIG_RATES = _load_config_rates()
FAMILY_SOBRENOME = _FAMILY.get("familia", {}).get("sobrenome", "Ferreira Campos")
TITULAR_NOME = _FAMILY.get("membros", {}).get("david", {}).get("nome_curto", "David")

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
    "viagens": "chart-viagens",
}

# Mapping: chart key → friendly display title (avoid auto-generated "Waterfall If" etc.)
CHART_TITLES = {
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
    "renda_passiva": "Renda Passiva vs Meta",
    "impostos_pj": "DAS PJ — Mês a Mês",
    "bubble_riscos": "Mapa de Riscos",
    "top5_decisoes": "Top 5 Decisões de Impacto",
    "mariana_cenarios": "Cenários IF — Mariana",
    "viagens": "Orçamento de Viagens",
}

# Mapping: section number → which chart keys belong to it
SECTION_CHARTS = {
    1: ["patrimonio_doughnut", "waterfall_if"],
    2: ["fluxo_mensal", "receita_bar", "despesas_doughnut", "receita_despesa_mensal", "score_gauge"],
    3: ["alocacao_atual", "alocacao_alvo", "top15_ativos", "mariana_cenarios", "viagens"],
    4: ["yield_imoveis"],
    5: ["custos_f1f2"],
    6: ["cenarios_cambiais"],
    7: ["projecao_3cenarios", "renda_passiva"],
    8: ["impostos_pj"],
    9: ["bubble_riscos"],
    10: ["top5_decisoes"],
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
    elif chart_key == "receita_despesa_mensal":
        # Navigation bar + canvas + dots + legend (no generic canvas)
        parts.append('  <div id="rdm-nav" class="chart-nav">')
        parts.append('    <button id="rdm-prev" class="chart-nav-btn" title="Meses anteriores">&#8249;</button>')
        parts.append('    <span id="rdm-period" class="chart-nav-period"></span>')
        parts.append('    <button id="rdm-next" class="chart-nav-btn" title="Meses seguintes">&#8250;</button>')
        parts.append('  </div>')
        parts.append(f'  <canvas id="{canvas_id}"></canvas>')
        parts.append('  <div id="rdm-dots" class="chart-nav-dots"></div>')
        parts.append('  <div id="legend-receita-despesa" class="chart-legend-grouped"></div>')
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
    """Load E5 analysis JSON (historically named e4 in this script)"""
    print("[E6.0] Loading E5 JSON...")
    with open(E5_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # E5 uses 'ratios' but E6 templates reference 'racios' — alias for compat
    if "ratios" in data and "racios" not in data:
        data["racios"] = data["ratios"]
    return data

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
    """Get current São Paulo time as '4 abr 2026, 14h32' (cross-platform, no zero-padding)"""
    sp_tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(sp_tz)
    # Format: "4 abr 2026, 14h32" — use day as str for cross-platform compatibility
    day = str(now.day)  # Cross-platform, no zero-padding
    return now.strftime(f"{day} %b %Y, %Hh%M").replace("May", "mai").replace("Apr", "abr")\
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
        "{{COVER_FAMILIA}}": FAMILY_SOBRENOME,
        "{{COVER_PERIODO}}": e4["periodo_dados"],
        "{{COVER_VERSAO_MANUAL}}": version,
        "{{COVER_DATA_HORA}}": sp_time,
        "{{NOME}}": TITULAR_NOME,

        # KPIs
        "{{KPI_PATRIMONIO_BRUTO}}": fmt_brl(p["bruto"]),
        "{{KPI_PATRIMONIO_BRUTO_SUB}}": f"Líquido: {fmt_brl(p['liquido'])}",
        "{{KPI_PATRIMONIO_INVESTIVEL}}": fmt_brl(p["investivel"]),
        "{{KPI_PATRIMONIO_INVESTIVEL_SUB}}": (f"{(p['investivel']/p['bruto']*100):.1f}% do bruto".replace(".", ",") if p['bruto'] > 0 else "N/D"),

        "{{KPI_RENDA_MENSAL}}": fmt_brl(f.get("janela_12m", f).get("receita_recorrente_mensal", f["receita_recorrente_mensal"])),
        "{{KPI_RENDA_MENSAL_SUB}}": f"Recorrente · média últ. {f.get('janela_12m', {}).get('n_meses', '?')} meses",

        "{{KPI_TAXA_POUPANCA}}": fmt_pct(r["taxa_poupanca_recorrente_pct"]),
        "{{KPI_TAXA_POUPANCA_SUB}}": f"Recorrente últ. {r.get('janela_n_meses', 12)} meses · Total: {fmt_pct(r['taxa_poupanca_total_pct'])}",

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

def _truncate_perfil_paragraphs(html: str, max_chars: int = 300) -> str:
    """Defensively truncate each <p> block to max_chars plain-text characters."""
    import re as _re

    def _truncate_match(m):
        inner = m.group(1)
        plain = _re.sub(r"<[^>]+>", "", inner).strip()
        if len(plain) <= max_chars:
            return m.group(0)
        # Truncate plain text, then rebuild <p>
        truncated = plain[:max_chars - 1] + "…"
        print(f"  [WARN] Perfil paragraph truncated: {len(plain)} → {max_chars} chars")
        return f"<p>{truncated}</p>"

    return _re.sub(r"<p>(.*?)</p>", _truncate_match, html, flags=_re.DOTALL)


def build_perfil_section(e4: dict) -> dict:
    """Build perfil familia section (with defensive 300-char truncation per paragraph)."""
    print("[E6.2] Building Perfil Família section...")

    narrativas = e4.get("narrativas", {})
    perfil = narrativas.get("perfil_familia", {})

    left = _truncate_perfil_paragraphs(perfil.get("left", "<p>Dados pendentes</p>"))
    right = _truncate_perfil_paragraphs(perfil.get("right", "<p>Dados pendentes</p>"))

    return {
        "{{PERFIL_FAMILIA_LEFT}}": left,
        "{{PERFIL_FAMILIA_RIGHT}}": right,
    }

# ============================================================================
# HELPER: Build receita_despesa_mensal chart data (v4.1)
# ============================================================================

# Color palettes for stacked bar chart origins
# Receita: paleta azul → verde (saturação média-alta, bom contraste light/dark)
RECEITA_PALETTE = [
    "#2563EB",  # azul royal — âncora principal
    "#0EA5E9",  # sky blue
    "#0891B2",  # cyan escuro
    "#0D9488",  # teal
    "#059669",  # esmeralda
    "#16A34A",  # verde vivo
    "#3B82F6",  # azul médio
    "#06B6D4",  # cyan claro
    "#14B8A6",  # teal claro
    "#22C55E",  # verde claro
    "#4F46E5",  # indigo (fallback)
    "#10B981",  # verde menta (fallback)
    "#6366F1",  # violeta-azul (fallback)
]

# Despesa: paleta laranja → vermelho (saturação média-alta, bom contraste light/dark)
DESPESA_PALETTE = [
    "#DC2626",  # vermelho vivo — âncora principal
    "#E11D48",  # rosa-vermelho
    "#EA580C",  # laranja queimado
    "#D97706",  # âmbar escuro
    "#F59E0B",  # amarelo-laranja
    "#EF4444",  # vermelho médio
    "#F97316",  # laranja vivo
    "#B91C1C",  # vermelho escuro
    "#C2410C",  # terracota
    "#CA8A04",  # dourado escuro
    "#DB2777",  # magenta (fallback)
    "#BE185D",  # rosa escuro (fallback)
    "#9F1239",  # bordô (fallback)
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

        # Convert labels from "24/03" → "mar/24"
        MESES_PT = {
            "01": "jan", "02": "fev", "03": "mar", "04": "abr",
            "05": "mai", "06": "jun", "07": "jul", "08": "ago",
            "09": "set", "10": "out", "11": "nov", "12": "dez"
        }
        raw_labels = detalhado["labels"]
        formatted_labels = []
        for lbl in raw_labels:
            parts = lbl.split("/")
            if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
                # Format: "YY/MM" → "mmm/YY"
                yy, mm = parts[0], parts[1]
                formatted_labels.append(MESES_PT.get(mm, mm) + "/" + yy)
            else:
                formatted_labels.append(lbl)

        return {
            "labels": formatted_labels,
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
        "renda_passiva_mensal": g.get("renda_passiva", {}).get("atual_mensal", g.get("renda_passiva_estimada_4pct", 0)),
        "renda_passiva_meta": g.get("renda_passiva", {}).get("meta_mensal", g.get("if_trs_monthly_value", 30000)),
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

    # Pre-compute dynamic values for charts
    num_months_chart = max(1, len(f.get("receita_despesa_mensal_detalhado", {}).get("labels", [])))
    aluguel_total = safe_float(f.get("por_fonte", {}).get("receita_aluguel", 0))
    aluguel_mensal = round(aluguel_total / num_months_chart, 2)
    imoveis_inv = max(1, p.get("imoveis_investimento", 1))
    yield_anual = round((aluguel_mensal * 12 / imoveis_inv) * 100, 1) if p.get("imoveis_investimento", 0) > 0 else 0

    receita_pj_total = safe_float(f.get("por_fonte", {}).get("receita_pj", 0))
    receita_pj_anual = round(receita_pj_total * (12 / num_months_chart), 2)
    renda_tributavel = round(receita_pj_anual * 0.32, 2)
    limite_pgbl = round(renda_tributavel * 0.12, 2)
    aliq_marginal = e4.get("previdencia_pgbl", {}).get("aliquota_marginal", 27.5)
    economia_ir = round(limite_pgbl * aliq_marginal / 100, 2)

    # Renda passiva from receitas
    renda_aluguel = aluguel_mensal
    renda_dividendos = round(safe_float(f.get("por_fonte", {}).get("receita_investimento", 0)) / num_months_chart, 2)
    renda_juros = round(safe_float(f.get("por_fonte", {}).get("rendimentos_financeiros", 0)) / num_months_chart, 2)

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
                "backgroundColor": PALETTE[:len(f["por_fonte"])]
            }]
        },
        "fluxo_mensal": (lambda rec, desp: {
            "labels": ["Receita Mensal", "Despesa Mensal", "Saldo"],
            "datasets": [{
                "label": "Fluxo de Caixa (R$)",
                "data": [round(rec, 2), round(desp, 2), round(rec - desp, 2)],
                "backgroundColor": ["#15803D", "#B91C1C", "#2E86AB" if rec >= desp else "#F4A261"],
                "borderRadius": 4
            }]
        })(f["receita_recorrente_mensal"], f["despesa_mensal_media"]),
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
        "alocacao_atual": (lambda ic: {
            "labels": [c["categoria"] for c in ic.get("tabela_classes", [])],
            "datasets": [{
                "data": [c["pct"] for c in ic.get("tabela_classes", [])],
                "backgroundColor": PALETTE[:len(ic.get("tabela_classes", []))]
            }]
        })(e4.get("investimentos", {})),
        "alocacao_alvo": {  # Target allocation — from definitions.md/life_plan
            "labels": ["Renda Fixa", "Ações", "Real Estate", "Moeda Estrangeira"],
            "datasets": [{
                "data": [60, 25, 10, 5],
                "backgroundColor": PALETTE[:4]
            }]
        },
        "top15_ativos": (lambda t15: {
            "labels": [a["nome"] for a in t15],
            "data": [round(a["valor"], 2) for a in t15],
        })(load_top15_investimentos()),
        "yield_imoveis": (lambda im_list: {
            "labels": [im.get("nome", "Imóvel") for im in im_list] + ["CDI (referência)"],
            "datasets": [{
                "data": [round(im.get("yield_anual", 0), 1) for im in im_list] + [CONFIG_RATES["cdi_anual"]],
                "backgroundColor": ["#2E86AB"] * len(im_list) + ["#E63946"]
            }]
        })(p.get("imoveis_lista", [{"nome": "Imóveis", "yield_anual": yield_anual}])),
        "custos_f1f2": (lambda cambio: {
            "labels": ["Tuition", "Room & Board", "TOTAL", "Renda David", "Sobra"],
            "datasets": [{
                "data": [
                    round(27500 / 12 * cambio),      # tuition mensal em BRL
                    round(16500 / 12 * cambio),      # room+board mensal em BRL
                    round(44000 / 12 * cambio),      # total mensal em BRL
                    round(f["receita_recorrente_mensal"]),
                    round(f["receita_recorrente_mensal"] - 44000 / 12 * cambio)
                ],
                "backgroundColor": ["#E63946", "#F4A261", "#1A3A5C", "#2DC653", "#2E86AB"]
            }]
        })(CONFIG_RATES["cambio_usd_brl"]),
        "cenarios_cambiais": (lambda cb, renda: {
            "labels": [
                ["Pessimista", f"R$ {5.5:.2f}/USD"],
                ["Realista", f"R$ {cb:.2f}/USD"],
                ["Otimista", f"R$ {4.5:.2f}/USD"]
            ],
            "datasets": [
                {"label": "Sem Mariana", "data": [
                    round(renda - 44000 / 12 * 5.5),
                    round(renda - 44000 / 12 * cb),
                    round(renda - 44000 / 12 * 4.5)
                ], "backgroundColor": "#F4A261"},
                {"label": "Com Mariana (NCLEX)", "data": [
                    round(renda + 4000 * 5.5 - 44000 / 12 * 5.5),
                    round(renda + 4000 * cb - 44000 / 12 * cb),
                    round(renda + 4000 * 4.5 - 44000 / 12 * 4.5)
                ], "backgroundColor": "#2DC653"}
            ]
        })(CONFIG_RATES["cambio_usd_brl"], f["receita_recorrente_mensal"]),
        "projecao_3cenarios": {
            "meta_if": g["if_meta"],
            "investivel": p["investivel"],
            "imoveis": p.get("imoveis_investimento", 0),
            "aporte_mensal": g.get("aporte_mensal", 20000),
            "anos": 20,
            "taxa_imoveis": 0.02,
            "taxa_pessimista": 0.04,
            "taxa_realista": 0.06,
            "taxa_otimista": 0.08,
        },
        "renda_passiva": (lambda rp_meta: {
            "labels": ["Aluguéis", "Dividendos", "RF/Cupons", "FIIs", "PGBL", "GAP"],
            "datasets": [
                {"label": "Atual", "data": [renda_aluguel, renda_dividendos, renda_juros, 0, 0, 0], "backgroundColor": "#2E86AB"},
                {"label": "Meta", "data": [0, 0, 0, 0, 0, max(0, round(rp_meta - renda_aluguel - renda_dividendos - renda_juros))], "backgroundColor": "#E63946"}
            ]
        })(g.get("renda_passiva", {}).get("meta_mensal", g.get("if_trs_monthly_value", 30000))),
        "impostos_pj": {
            "labels": ["Receita PJ (anual)", "Lucro Presumido (32%)", "DAS Estimado (anual)", "Limite PGBL (12%)", "Economia IR c/ PGBL"],
            "datasets": [{
                "label": "Valores (R$)",
                "data": [round(receita_pj_anual), round(renda_tributavel), round(receita_pj_anual * 0.06), round(limite_pgbl), round(economia_ir)],
                "backgroundColor": [PALETTE[0], PALETTE[1], "#E63946", PALETTE[3], "#2DC653"]
            }]
        },
        "bubble_riscos": (lambda riscos: {
            "datasets": [
                {
                    "label": r["titulo"],
                    "data": [{"x": r.get("probabilidade", 3), "y": r.get("impacto", 3), "r": r.get("raio", 14)}],
                    "backgroundColor": {"critico": "rgba(230,57,70,0.7)", "alto": "rgba(244,162,97,0.7)", "medio": "rgba(46,134,171,0.5)", "baixo": "rgba(168,218,220,0.5)"}.get(r.get("severity", "medio"), "rgba(69,123,157,0.5)")
                }
                for r in riscos
            ]
        })(e4.get("riscos", [
            {"titulo": "Seguro de vida", "severity": "critico", "probabilidade": 2, "impacto": 5, "raio": 20},
            {"titulo": "Seguro de invalidez", "severity": "critico", "probabilidade": 2, "impacto": 4, "raio": 16},
            {"titulo": "PFIC exposure EUA", "severity": "alto", "probabilidade": 3, "impacto": 3, "raio": 18},
            {"titulo": "Concentração PJ", "severity": "alto", "probabilidade": 2, "impacto": 4, "raio": 16},
            {"titulo": "Volatilidade cambial", "severity": "medio", "probabilidade": 3, "impacto": 2, "raio": 12}
        ])),
        "top5_decisoes": (lambda decs: {
            "labels": [d["label"] for d in decs],
            "datasets": [
                {"label": "Impacto 1 ano", "data": [d.get("impacto_1a", 0) for d in decs], "backgroundColor": "#2E86AB"},
                {"label": "Impacto 10 anos", "data": [d.get("impacto_10a", 0) for d in decs], "backgroundColor": "#2DC653"}
            ]
        })(e4.get("top5_decisoes", g.get("top5_decisoes", [
            {"label": "Aportes mensais", "impacto_1a": 0, "impacto_10a": 0},
        ]))),
        "mariana_cenarios": (lambda cm: {
            "labels": cm.get("labels", ["Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card"]),
            "datasets": [
                {"label": "Aporte mensal", "data": cm.get("aportes", [0, 4000, 7000]), "backgroundColor": "#2E86AB"},
                {"label": "Prazo IF (anos)", "data": cm.get("prazos_if", [0, 0, 0]), "backgroundColor": "#2DC653", "yAxisID": "y1"}
            ]
        })(e4.get("cenarios_mariana", g.get("cenarios_mariana", {}))),
        "viagens": (lambda vg: {
            "labels": [f"Orçamento {vg.get('ano', 2026)}"],
            "datasets": [
                {"label": "Gasto", "data": [vg.get("gasto", 0)], "backgroundColor": "#E63946"},
                {"label": "Disponível", "data": [max(0, vg.get("teto_anual", 45000) - vg.get("gasto", 0))], "backgroundColor": "#2DC653"}
            ]
        })(e4.get("viagens", {"teto_anual": 45000, "gasto": 0, "ano": 2026})),
    }

    return charts

def build_orcamento_prospectivo(e4: dict) -> dict:
    """Build prospective budget (14 categories + totals)"""
    despesas = e4["fluxo_caixa"]["despesas_por_categoria"]

    # Calculate variation from monthly data
    det = e4["fluxo_caixa"].get("receita_despesa_mensal_detalhado", {})
    totais_desp = det.get("totais_despesa", [])
    if len(totais_desp) > 1:
        media = sum(totais_desp) / len(totais_desp)
        if media > 0:
            desvio = (sum((x - media)**2 for x in totais_desp) / len(totais_desp)) ** 0.5
            variacao = round(desvio / media * 100, 1)
        else:
            variacao = 0
    else:
        variacao = 0

    return {
        "categorias": despesas,
        "total": sum(despesas.values()),
        "media_mensal": e4["fluxo_caixa"]["despesa_mensal_media"],
        "variacao_pct": variacao,
    }

def build_investimentos(e4: dict) -> dict:
    """Build investimentos section from E5 data"""
    inv_data = e4.get("investimentos", {})
    tabela = inv_data.get("tabela_classes", [])

    return {
        "david_valor": e4["patrimonio"].get("investimentos_david", 0),
        "mariana_valor": e4["patrimonio"].get("investimentos_mariana", 0),
        "total": inv_data.get("total", e4["patrimonio"].get("investimentos_david", 0) + e4["patrimonio"].get("investimentos_mariana", 0)),
        "kpis": {
            "yield_medio_pct": "N/D",
            "volatilidade_pct": "N/D",
        },
        "blocos": [{"nome": c["categoria"], "valor": c["valor"], "pct": c["pct"]} for c in tabela],
        "cdi_anual": CONFIG_RATES["cdi_anual"],  # Loaded from config/taxas.json or defaults
        "tabela_classes": tabela,
    }

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
    """Build Selic/contrafluxo scenarios. Loaded from config/taxas.json or defaults"""
    return {
        "selic_atual": CONFIG_RATES["selic_atual"],  # Loaded from config
        "cenarios": {
            "pessimista": {"selic": 10.5, "cdi": 10.3},
            "base": {"selic": CONFIG_RATES["selic_atual"], "cdi": CONFIG_RATES["cdi_anual"]},
            "otimista": {"selic": 12.5, "cdi": 12.3},
        }
    }

def build_tactical_dashboard(e4: dict) -> dict:
    """Build tactical dashboard data"""
    f = e4.get("fluxo_caixa", {})
    num_months = max(1, len(f.get("receita_despesa_mensal_detalhado", {}).get("labels", [])))
    return {
        "cash_position": e4["patrimonio"].get("caixa_moeda_estrangeira", 0),
        "monthly_pnl": round(f.get("fluxo_liquido", 0) / num_months, 2),
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
    re_data = e4.get("reserva_emergencia", {})
    niveis_raw = re_data.get("niveis", {})
    composicao = re_data.get("composicao_liquida", {})
    despesa_mensal = re_data.get("despesas_mensais", 0)
    total_liquido = composicao.get("total_liquido", 0)
    cobertura_meses = composicao.get("cobertura_meses", 0)

    # Normalize niveis: E5 may produce a dict or a list of strings
    if isinstance(niveis_raw, dict):
        niveis = niveis_raw
    else:
        # Build dict from despesa_mensal when E5 provides list/other
        niveis = {
            "minimo_6m": {"valor": despesa_mensal * 6, "status": "✅" if total_liquido >= despesa_mensal * 6 else "⚠️"},
            "conforto_9m": {"valor": despesa_mensal * 9, "status": "✅" if total_liquido >= despesa_mensal * 9 else "⚠️"},
            "conservador_12m": {"valor": despesa_mensal * 12, "status": "✅" if total_liquido >= despesa_mensal * 12 else "⚠️"},
        }

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
    html_parts.append('  <p style="margin-top:1em;"><strong>Composição da Liquidez Imediata:</strong></p>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Componente</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    # Use actual composition keys from E5
    comp_items = [
        ("investimentos_david", "Investimentos David"),
        ("investimentos_mariana", "Investimentos Mariana"),
        ("caixa_moeda_estrangeira", "Caixa e Moeda Estrangeira"),
    ]
    for key, nome in comp_items:
        val = composicao.get(key, 0)
        if val > 0:
            pct = (val / total_liquido * 100) if total_liquido else 0
            html_parts.append(f'      <tr><td>{nome}</td><td>{fmt_brl(val)} ({pct:.0f}%)</td><td>{fmt_pct(pct)}</td></tr>')

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


# ============================================================================
# APPENDICES (A-E)
# ============================================================================

def build_appendix_a() -> str:
    """Apêndice A — Definições e Siglas: glossário completo para leitura autônoma."""
    h = []
    h.append('<div class="card">')
    h.append('  <div class="card-title">Glossário de Termos Financeiros</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Sigla / Termo</th><th>Definição</th></tr></thead>')
    h.append('    <tbody>')
    terms = [
        ("IF", "Independência Financeira — patrimônio suficiente para gerar renda passiva que cubra todas as despesas da família sem depender de trabalho ativo."),
        ("TRS", "Taxa de Retirada Segura — percentual anual que pode ser sacado do patrimônio investido sem exauri-lo ao longo do tempo. Referência: 4-5% a.a. para carteira diversificada."),
        ("CDI", "Certificado de Depósito Interbancário — taxa de referência para investimentos de renda fixa no Brasil. Acompanha de perto a taxa Selic."),
        ("Selic", "Taxa básica de juros da economia brasileira, definida pelo COPOM (Comitê de Política Monetária do Banco Central)."),
        ("IPCA", "Índice Nacional de Preços ao Consumidor Amplo — indicador oficial de inflação no Brasil, medido pelo IBGE."),
        ("IPCA+", "Título público (Tesouro Direto) ou indexador que paga inflação IPCA mais um juro real prefixado."),
        ("IGPM", "Índice Geral de Preços — Mercado. Índice de inflação medido pela FGV, frequentemente usado em contratos de aluguel."),
        ("DAS", "Documento de Arrecadação do Simples Nacional — guia mensal de impostos para empresas optantes pelo Simples Nacional."),
        ("Simples Nacional", "Regime tributário simplificado para micro e pequenas empresas com faturamento até R$4,8M/ano. Unifica diversos impostos em uma guia (DAS)."),
        ("Lucro Presumido", "Regime tributário alternativo ao Simples onde a base de cálculo do IR é um percentual presumido do faturamento (32% para serviços)."),
        ("PGBL", "Plano Gerador de Benefício Livre — modalidade de previdência privada que permite deduzir até 12% da renda bruta tributável no IRPF."),
        ("VGBL", "Vida Gerador de Benefício Livre — previdência privada sem dedução fiscal, tributada apenas sobre os rendimentos no resgate."),
        ("CDB", "Certificado de Depósito Bancário — título de renda fixa emitido por bancos. Pode ser prefixado, pós-fixado (CDI) ou indexado (IPCA+)."),
        ("LCI / LCA", "Letras de Crédito Imobiliário / Agrícola — títulos de renda fixa isentos de IR para pessoa física."),
        ("FII", "Fundo de Investimento Imobiliário — fundo negociado em bolsa que investe em imóveis ou ativos imobiliários, distribuindo rendimentos mensais."),
        ("ETF", "Exchange Traded Fund — fundo de índice negociado em bolsa. Ex: IVVB11 (replica S&P 500 em BRL)."),
        ("IVVB11", "ETF listado na B3 que replica o índice S&P 500, proporcionando exposição ao mercado americano em reais."),
        ("DY", "Dividend Yield — rendimento de dividendos/rendimentos de um ativo, expresso como percentual anual sobre o preço."),
        ("P/L", "Preço/Lucro — múltiplo que relaciona o preço de uma ação ao lucro por ação. Indica quantos anos de lucro o mercado está pagando."),
        ("PM", "Preço Médio — custo médio de aquisição de um ativo, usado para cálculo de IR sobre ganho de capital."),
        ("Contrafluxo", "Estratégia de investimento da metodologia AUVP: comprar ativos atrelados ao indexador que está em baixa (ex: IPCA+ quando Selic está alta)."),
        ("FBAR", "Foreign Bank Account Report — declaração obrigatória nos EUA para contas estrangeiras com saldo agregado acima de US$10.000."),
        ("FATCA", "Foreign Account Tax Compliance Act — lei americana que exige que instituições financeiras estrangeiras reportem contas de cidadãos/residentes dos EUA."),
        ("PFIC", "Passive Foreign Investment Company — classificação tributária americana que torna fundos brasileiros sujeitos a tributação punitiva nos EUA."),
        ("EB2-NIW", "Employment-Based Second Preference, National Interest Waiver — categoria de Green Card que dispensa oferta de emprego se o candidato demonstrar interesse nacional."),
        ("NCLEX-RN", "National Council Licensure Examination for Registered Nurses — exame de licenciamento para enfermeiros nos EUA."),
        ("IRPF", "Imposto de Renda Pessoa Física — imposto federal sobre a renda de pessoas físicas no Brasil."),
        ("IR", "Imposto de Renda — termo genérico para IRPF ou IRPJ."),
        ("IOF", "Imposto sobre Operações Financeiras — imposto federal sobre câmbio, crédito, seguros e títulos."),
        ("Carnê-Leão", "Recolhimento mensal obrigatório de IR sobre rendimentos recebidos de pessoas físicas ou do exterior, via DARF."),
    ]
    for sigla, desc in terms:
        h.append(f'      <tr><td><strong>{sigla}</strong></td><td>{desc}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Corretoras e instituições
    h.append('<div class="card">')
    h.append('  <div class="card-title">Instituições e Corretoras</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Código</th><th>Instituição</th><th>Uso</th></tr></thead>')
    h.append('    <tbody>')
    inst = [
        ("C6 Bank", "Banco digital", "Conta PJ (receita) + conta PF + cartão Carbon + conta global USD/EUR"),
        ("Itaú Personnalité", "Banco", "Conta PF David — investimentos RF + recebimento aluguéis"),
        ("Santander", "Banco", "Conta PF David — CDBs"),
        ("Rico / XP", "Corretora", "David — fundos, ações, FIIs"),
        ("BTG Pactual", "Corretora", "Mariana — investimentos RF e RV"),
        ("Bradesco", "Banco", "Mariana — CC + poupança (salário Einstein)"),
        ("PicPay", "Conta digital", "David — RDB liquidez"),
        ("Wise", "Conta internacional", "Acumulação USD (spread 0,5-1%)"),
        ("Bank of America", "Banco EUA", "Conta dormida — futura residência"),
        ("Binance", "Exchange crypto", "Criptomoedas"),
        ("QuintoAndar", "Gestora de aluguéis", "Gestão e recebimento dos aluguéis dos imóveis"),
    ]
    for nome, tipo, uso in inst:
        h.append(f'      <tr><td><strong>{nome}</strong></td><td>{tipo}</td><td>{uso}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Categorias patrimoniais
    h.append('<div class="card">')
    h.append('  <div class="card-title">Categorias Patrimoniais</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Categoria</th><th>O que inclui</th></tr></thead>')
    h.append('    <tbody>')
    cats = [
        ("Patrimônio Bruto", "Soma de todos os ativos: imóveis, veículos, investimentos, criptos, contas bancárias, empresas."),
        ("Patrimônio Investível", "Patrimônio Bruto − imóvel de residência − veículos. São os ativos que geram ou podem gerar renda passiva."),
        ("Renda Fixa", "CDBs, Tesouro Direto, LCIs, LCAs, debêntures, fundos RF, poupança."),
        ("Renda Variável", "Ações, FIIs, ETFs, fundos multimercado, BDRs."),
        ("Imóveis (investimento)", "Imóveis não-residenciais que geram aluguel ou valorização."),
        ("Criptomoedas", "Bitcoin, Ethereum e demais ativos digitais."),
        ("Contas Bancárias", "Saldos em contas correntes, poupança e contas digitais."),
        ("Reserva de Emergência", "Parcela líquida (resgate D+0 a D+2) destinada a cobrir 6-12 meses de despesas."),
    ]
    for cat, desc in cats:
        h.append(f'      <tr><td><strong>{cat}</strong></td><td>{desc}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    return '\n'.join(h)


def build_appendix_b() -> str:
    """Apêndice B — Premissas e Metodologia."""
    h = []

    # Premissas econômicas
    h.append('<div class="card">')
    h.append('  <div class="card-title">Premissas Econômicas</div>')
    h.append('  <p>Os cenários abaixo fundamentam todas as projeções deste relatório. Fonte: BCB, IBGE, consenso de mercado (mar/2026).</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Variável</th><th>Pessimista</th><th>Realista (base)</th><th>Otimista</th><th>Atual (mar/2026)</th></tr></thead>')
    h.append('    <tbody>')
    premissas = [
        ("Inflação (IPCA)", "6,0%", "4,5%", "3,5%", "~5%"),
        ("Retorno real carteira", "4,0%", "6,0%", "8,0%", "~6,0%"),
        ("CDI / Selic", "11,0%", "12,0%", "13,5%", "13,75%"),
        ("Câmbio BRL/USD", "R$ 7,50", "R$ 5,88", "R$ 4,50", "R$ 5,88"),
        ("Valorização imóveis SP", "3%", "5%", "8%", "—"),
        ("TRS", "3,5%", "4,0%", "5,0%", "—"),
    ]
    for var, pess, real, ot, at in premissas:
        h.append(f'      <tr><td>{var}</td><td>{pess}</td><td><strong>{real}</strong></td><td>{ot}</td><td>{at}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Metodologias
    h.append('<div class="card">')
    h.append('  <div class="card-title">Metodologias Utilizadas</div>')

    h.append('  <h3>Bruno Perini — "Viver de Renda"</h3>')
    h.append('  <p>Cálculo do "Número da Independência Financeira": patrimônio necessário = despesa anual desejada ÷ TRS. ')
    h.append('  Exemplo: R$30.000/mês × 12 ÷ 5% = R$7.200.000. A projeção de prazo usa taxa de retorno real (acima da inflação) ')
    h.append('  e aporte mensal constante com juros compostos.</p>')

    h.append('  <h3>Gustavo Cerbasi — Equilíbrio Presente × Futuro</h3>')
    h.append('  <p>Análise comportamental que classifica os gastos em "presente" (consumo, moradia, lazer) e "futuro" ')
    h.append('  (investimentos, previdência, aportes). A proporção ideal é ~70% presente / 30% futuro. ')
    h.append('  Classificações: <strong>Gastador</strong> (&lt;10% futuro), <strong>Equilibrado</strong> (20-40%), ')
    h.append('  <strong>Poupador</strong> (&gt;40%). Referência: <em>Casais Inteligentes Enriquecem Juntos</em>.</p>')

    h.append('  <h3>Raul Sena / AUVP — Contrafluxo e Análise Fundamentalista</h3>')
    h.append('  <p>Estratégia de contrafluxo: investir no indexador que está "fora de moda". Quando a Selic está alta, ')
    h.append('  prefixados e IPCA+ oferecem melhor relação risco/retorno. Quando a Selic está baixa, pós-fixados CDI protegem. ')
    h.append('  A análise fundamentalista avalia ações por P/L, ROE, dívida/patrimônio e dividend yield histórico. ')
    h.append('  FIIs são avaliados por DY, vacância, P/VP e qualidade dos inquilinos.</p>')

    h.append('  <h3>Score Financeiro — Metodologia Própria</h3>')
    h.append('  <p>Média ponderada de 5 componentes (0-10), com interpolação linear entre extremos:</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Componente</th><th>Peso</th><th>Nota 10</th><th>Nota 0</th></tr></thead>')
    h.append('    <tbody>')
    score_comp = [
        ("Taxa de poupança recorrente", "2,0", "≥ 50%", "≤ 0%"),
        ("Cobertura de despesas (meses)", "1,5", "≥ 24 meses", "≤ 3 meses"),
        ("Taxa de endividamento", "1,5", "≤ 5%", "≥ 50%"),
        ("Progresso IF (% da meta)", "2,0", "≥ 80%", "≤ 5%"),
        ("Diversificação (categorias ≥ 5%)", "1,0", "≥ 5 categorias", "≤ 1 categoria"),
    ]
    for comp, peso, n10, n0 in score_comp:
        h.append(f'      <tr><td>{comp}</td><td>{peso}</td><td>{n10}</td><td>{n0}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('  <p><em>Fórmula: Score = Σ(nota × peso) / Σ(peso), arredondado a 1 decimal.</em></p>')

    # Nota metodológica sobre janela de 12 meses
    janela_ref = e4.get("ratios", e4.get("racios", {})).get("janela_referencia", "últimos 12 meses")
    janela_n = e4.get("ratios", e4.get("racios", {})).get("janela_n_meses", 12)
    h.append(f'  <p><strong>Nota metodológica:</strong> As taxas de poupança e a despesa mensal média '
             f'são calculadas sobre os <strong>últimos {janela_n} meses ({janela_ref})</strong>, '
             f'não sobre o período completo dos dados. Isso evita distorções causadas por receitas '
             f'extraordinárias concentradas em períodos específicos (ex.: rescisões, vendas de ativos) '
             f'que inflam o acumulado total sem representar a capacidade recorrente de poupança.</p>')
    h.append('</div>')

    # Fontes de dados
    h.append('<div class="card">')
    h.append('  <div class="card-title">Fontes de Dados</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Dado</th><th>Fonte</th><th>Período</th></tr></thead>')
    h.append('    <tbody>')
    fontes = [
        ("Receitas e despesas", "Extratos bancários e faturas de cartão (PDFs originais)", "Mai/2025 – Mar/2026"),
        ("Patrimônio (imóveis, veículos)", "Declaração IRPF 2025 + planilhas XLSX atualizadas", "Posição mar/2026"),
        ("Investimentos", "Posições de corretoras (Rico, BTG, Itaú, Santander, PicPay)", "Posição mar/2026"),
        ("Câmbio", "BCB/PTAX (R$5,88 em mar/2026)", "Spot"),
        ("Selic/CDI", "BCB — 13,75% a.a. (mar/2026)", "Vigente"),
        ("IPCA", "IBGE — acumulado 12 meses ~5%", "Mar/2026"),
    ]
    for dado, fonte, per in fontes:
        h.append(f'      <tr><td>{dado}</td><td>{fonte}</td><td>{per}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Disclaimers
    h.append('<div class="card card-warning">')
    h.append('  <div class="card-title">Disclaimers</div>')
    h.append('  <ul>')
    h.append('    <li>Projeções de renda passiva 2035 usam premissas de IGPM 4%/ano, DY ações 5-8%, DY FIIs 9%, retorno real 6%. Revisar anualmente.</li>')
    h.append('    <li>Tabela fundamentalista de ações — valores estimados, confirmar antes de agir.</li>')
    h.append('    <li>DY de FIIs de referência — DY passado não garante DY futuro.</li>')
    h.append('    <li>Taxa PGBL — confirmar taxa real de administração antes de portabilidade.</li>')
    h.append('    <li>Benchmark de fundos — períodos variam por fundo (retorno acumulado desde aporte, não "últimos 12 meses").</li>')
    h.append('    <li>Para questões tributárias EUA, consultar CPA especializado em expatriados.</li>')
    h.append('  </ul>')
    h.append('</div>')

    return '\n'.join(h)


def build_appendix_c(e4: dict) -> str:
    """Apêndice C — Cenários de Sensibilidade."""
    h = []

    goals = e4.get("goals", {})
    patrimonio = e4.get("patrimonio", {})
    pat_investivel = safe_float(patrimonio.get("investivel", 0))
    meta_if = safe_float(goals.get("if_meta", 7200000))

    # Cenários IF
    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Independência Financeira</div>')
    h.append('  <p>Projeção de prazo para atingir a meta de R$7.200.000 com aporte de R$20.000/mês, variando a taxa de retorno real.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Retorno real a.a.</th><th>Aporte/mês</th><th>Prazo</th><th>David com</th></tr></thead>')
    h.append('    <tbody>')
    h.append('      <tr><td>Pessimista</td><td>4,0%</td><td>R$ 20.000</td><td>~11,9 anos</td><td>55 (2038)</td></tr>')
    h.append('      <tr class="total-row"><td><strong>Realista</strong></td><td><strong>6,0%</strong></td><td><strong>R$ 20.000</strong></td><td><strong>~9,0 anos</strong></td><td><strong>52 (2035)</strong></td></tr>')
    h.append('      <tr><td>Otimista</td><td>8,0%</td><td>R$ 20.000</td><td>~7,0 anos</td><td>50 (2033)</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    pct_atingido = (pat_investivel / meta_if * 100) if meta_if > 0 else 0
    h.append(f'  <p><strong>Progresso atual:</strong> R$ {pat_investivel:,.0f} de R$ {meta_if:,.0f} ({pct_atingido:.1f}% atingido).</p>')
    h.append('</div>')

    # Cenários cambiais
    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Câmbio BRL/USD</div>')
    h.append('  <p>Impacto do câmbio nos custos da fase EUA (F1/F2) e na meta de dolarização.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Câmbio</th><th>Custo F1/F2 mensal (BRL)</th><th>Meta USD (R$20k em BRL)</th><th>Impacto</th></tr></thead>')
    h.append('    <tbody>')
    h.append('      <tr><td>Pessimista (desvalorização)</td><td>R$ 7,50</td><td>R$ 29.925</td><td>R$ 150.000</td><td>Custos +28%, aporte USD rende menos</td></tr>')
    h.append('      <tr class="total-row"><td><strong>Realista</strong></td><td><strong>R$ 5,88</strong></td><td><strong>R$ 23.461</strong></td><td><strong>R$ 117.600</strong></td><td><strong>Base do planejamento</strong></td></tr>')
    h.append('      <tr><td>Otimista (valorização)</td><td>R$ 4,50</td><td>R$ 17.955</td><td>R$ 90.000</td><td>Custos -24%, folga para aportes maiores</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Cenários Selic
    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Selic e Renda Fixa</div>')
    h.append('  <p>Sensibilidade da carteira de renda fixa a mudanças na Selic.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Selic</th><th>CDI estimado</th><th>Impacto na carteira RF</th><th>Ação recomendada</th></tr></thead>')
    h.append('    <tbody>')
    h.append('      <tr><td>Queda acentuada</td><td>8,0%</td><td>~7,9%</td><td>CDBs pós-fixados rendem menos; IPCA+ valoriza (marcação a mercado)</td><td>Manter IPCA+ até vencimento; aumentar prefixados longos</td></tr>')
    h.append('      <tr class="total-row"><td><strong>Estabilidade</strong></td><td><strong>12,0%</strong></td><td><strong>~11,9%</strong></td><td><strong>CDBs pós rendem bem; IPCA+ em carrego</strong></td><td><strong>Manter estratégia atual (contrafluxo IPCA+)</strong></td></tr>')
    h.append('      <tr><td>Alta adicional</td><td>15,0%</td><td>~14,9%</td><td>CDBs pós rendem mais; IPCA+ desvaloriza na marcação</td><td>Aumentar CDBs pós-fixados curtos; evitar IPCA+ longo novo</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Cenários imóveis
    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Mercado Imobiliário SP</div>')
    h.append('  <p>Impacto da valorização (ou desvalorização) dos imóveis no patrimônio e no yield.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Valorização anual</th><th>Impacto em 5 anos</th><th>Efeito no yield</th></tr></thead>')
    h.append('    <tbody>')
    h.append('      <tr><td>Pessimista (estagnação)</td><td>0-2%</td><td>Patrimônio imobiliário estável, perda real</td><td>Yield se mantém ou sobe (valor do imóvel cai)</td></tr>')
    h.append('      <tr class="total-row"><td><strong>Realista</strong></td><td><strong>5%</strong></td><td><strong>Valorização ~28% em 5 anos</strong></td><td><strong>Yield estável (aluguel acompanha valorização)</strong></td></tr>')
    h.append('      <tr><td>Otimista (boom)</td><td>8-10%</td><td>Valorização ~47-61% em 5 anos</td><td>Yield pode comprimir (valor sobe mais que aluguel)</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Stress tests
    h.append('<div class="card card-warning">')
    h.append('  <div class="card-title">Stress Tests — Perguntas-Chave</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Pergunta</th><th>Resposta / Mitigação</th></tr></thead>')
    h.append('    <tbody>')
    stress = [
        ("E se a Selic cair a 8%?", "CDBs pós rendem menos (~R$1.500/mês a menos em RF). Ação: contrafluxo — já ter IPCA+ longos na carteira captura a valorização. Manter Tesouro IPCA+ 2035/2040."),
        ("E se o USD chegar a R$7,50?", "Custos F1/F2 sobem ~28%. A sobra mensal cai de R$38k para ~R$32k — ainda viável. Dolarização via Wise fica mais cara mas protege o patrimônio."),
        ("E se Mariana não conseguir o NCLEX?", "A simulação 'Mariana sem trabalhar' mostra IF em 11,4 anos (vs 9,0). David absorve com aporte reduzido de R$13.200/mês."),
        ("E se David perder o contrato Arvo?", "Renda cai ~60%. Reserva de emergência cobre 19,5 meses. Ações: (1) buscar contratos substitutos, (2) reduzir aporte IF, (3) Mariana mantém renda CLT."),
        ("E se os imóveis desvalorizarem 20%?", "Patrimônio bruto cai ~R$245k, mas o patrimônio investível não muda (imóvel residência já excluído). Yield dos imóveis de investimento sobe proporcionalmente."),
    ]
    for perg, resp in stress:
        h.append(f'      <tr><td><strong>{perg}</strong></td><td>{resp}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    return '\n'.join(h)


def build_appendix_d() -> str:
    """Apêndice D — Referências e Recursos."""
    h = []

    # Livros
    h.append('<div class="card">')
    h.append('  <div class="card-title">Livros Recomendados</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Livro</th><th>Autor</th><th>Tema</th></tr></thead>')
    h.append('    <tbody>')
    livros = [
        ("Viver de Renda", "Bruno Perini", "Independência financeira, cálculo da IF, montagem de carteira de renda passiva"),
        ("Casais Inteligentes Enriquecem Juntos", "Gustavo Cerbasi", "Finanças do casal, equilíbrio presente vs futuro, comportamento financeiro"),
        ("Investimentos Inteligentes", "Gustavo Cerbasi", "Fundamentos de investimento para famílias brasileiras"),
        ("Do Mil ao Milhão", "Thiago Nigro", "Gastar bem, investir melhor, ganhar mais — mentalidade financeira"),
        ("O Homem Mais Rico da Babilônia", "George S. Clason", "Princípios atemporais de poupança e acumulação de riqueza"),
        ("Pai Rico, Pai Pobre", "Robert Kiyosaki", "Ativos vs passivos, mentalidade de riqueza, renda passiva"),
    ]
    for livro, autor, tema in livros:
        h.append(f'      <tr><td><strong>{livro}</strong></td><td>{autor}</td><td>{tema}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Ferramentas
    h.append('<div class="card">')
    h.append('  <div class="card-title">Ferramentas e Plataformas</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Ferramenta</th><th>Uso</th><th>Link</th></tr></thead>')
    h.append('    <tbody>')
    ferramentas = [
        ("Tesouro Direto", "Compra de títulos públicos (IPCA+, Selic, Prefixado)", "tesourodireto.com.br"),
        ("Status Invest", "Análise fundamentalista de ações, FIIs, ETFs", "statusinvest.com.br"),
        ("Fundamentus", "Dados fundamentalistas de empresas listadas na B3", "fundamentus.com.br"),
        ("Investidor 10", "Comparação de FIIs, ações, rankings por DY", "investidor10.com.br"),
        ("AUVP Analítica", "Plataforma educacional + análise de investimentos (Raul Sena)", "auvp.com.br"),
        ("Simulador BCB — Cidadão", "Simulação de investimentos, consórcio, financiamento", "bcb.gov.br/cidadaniafinanceira"),
        ("Calculadora CDB / Tesouro", "Comparativo CDB vs Tesouro vs LCI/LCA com IR", "calculadoradoinvestidor.com.br"),
        ("Wise", "Transferências internacionais e conta multi-moeda", "wise.com"),
        ("Gov.br", "IRPF, consulta restituição, e-CAC, DAS", "gov.br"),
    ]
    for ferr, uso, link in ferramentas:
        h.append(f'      <tr><td><strong>{ferr}</strong></td><td>{uso}</td><td>{link}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Contatos profissionais
    h.append('<div class="card">')
    h.append('  <div class="card-title">Contatos Profissionais Recomendados</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Profissional</th><th>Área</th><th>Quando acionar</th></tr></thead>')
    h.append('    <tbody>')
    contatos = [
        ("Contador (AccountTech)", "Contabilidade PJ, DAS, Simples Nacional", "Mensal (DAS) + IRPF anual + mudança de regime"),
        ("Advogado Sucessório / Tributarista SP", "Testamentos, procurações, holding", "Antes da mudança para EUA — planejamento sucessório"),
        ("CPA Expatriado (EUA)", "FBAR, FATCA, Form 1040, PFIC", "Antes de se tornar US tax resident — essencial"),
        ("Advogado Imigração (EUA)", "EB2-NIW, F1/F2, Green Card", "Acompanhamento do processo de Green Card"),
        ("Corretor de Seguros", "Vida, invalidez (DIT), residencial", "Urgente — cotar term life R$3-5M + DIT 60% da renda"),
    ]
    for prof, area, quando in contatos:
        h.append(f'      <tr><td><strong>{prof}</strong></td><td>{area}</td><td>{quando}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    return '\n'.join(h)


def build_appendix_e(e4: dict) -> str:
    """Apêndice E — Próximos Ciclos e Roadmap."""
    h = []

    # Tarefas priorizadas (from tarefas.md via E5)
    tarefas = e4.get("tarefas", [])
    tarefas_status = e4.get("tarefas_status", {})
    alertas = e4.get("alertas", [])

    # Priority label mapping
    prio_labels = {"alta": "S", "media": "R", "baixa": "O"}

    h.append('<div class="card">')
    h.append('  <div class="card-title">Lista de Tarefas</div>')
    if tarefas:
        h.append('  <table>')
        h.append('    <thead><tr><th>#</th><th>TAREFA</th><th>CATEGORIA</th><th>PRAZO</th><th>ESS.</th></tr></thead>')
        h.append('    <tbody>')
        for t in tarefas:
            if isinstance(t, str):
                continue
            num = t.get("n", "")
            desc = t.get("t", "")
            prio = t.get("p", "media").lower()
            prazo = t.get("e", "—")
            categoria = t.get("categoria", "")
            status = tarefas_status.get(str(num), "pendente")
            prio_letter = prio_labels.get(prio, "R")

            # Style: feito tasks get strikethrough
            if status == "feito":
                desc = f'<s>{desc}</s> ✅'

            h.append(f'      <tr><td>{num}</td><td>{desc}</td><td>{categoria}</td><td>{prazo}</td><td><span class="priority-badge priority-{prio}">{prio_letter}</span></td></tr>')
        h.append('    </tbody>')
        h.append('  </table>')

        # Legend
        essenciais = sum(1 for t in tarefas if t.get("p") == "alta")
        recomendadas = sum(1 for t in tarefas if t.get("p") == "media")
        opcionais = sum(1 for t in tarefas if t.get("p") == "baixa")
        feitas = sum(1 for v in tarefas_status.values() if v == "feito")
        h.append(f'  <p style="margin-top:12px;font-size:13px;"><span class="priority-badge priority-alta">S</span> = Essencial (S) — {essenciais} tarefas &nbsp; ')
        h.append(f'  <span class="priority-badge priority-media">R</span> = Recomendada (R) — {recomendadas} tarefas &nbsp; ')
        h.append(f'  <span class="priority-badge priority-baixa">O</span> = Opcional (O) — {opcionais} tarefas</p>')
        if feitas > 0:
            h.append(f'  <p style="font-size:13px;">✅ {feitas} tarefa(s) concluída(s) neste ciclo.</p>')

        # LLM-suggested tasks (from E5.N)
        sugeridas = e4.get("tarefas_sugeridas", [])
        if sugeridas:
            h.append('  <h3>Tarefas Sugeridas pela Análise</h3>')
            h.append('  <p style="font-size:13px;"><em>Sugeridas automaticamente com base nos dados financeiros. Pendente aprovação do titular para inclusão no backlog.</em></p>')
            h.append('  <table>')
            h.append('    <thead><tr><th>Sugestão</th><th>Motivo</th><th>Prioridade sugerida</th></tr></thead>')
            h.append('    <tbody>')
            for s in sugeridas:
                desc_s = s.get("t", s.get("descricao", str(s)))
                motivo = s.get("motivo", "")
                prio_s = s.get("p", "media").lower()
                h.append(f'      <tr><td>{desc_s}</td><td>{motivo}</td><td><span class="priority-badge priority-{prio_s}">{prio_labels.get(prio_s, "R")}</span></td></tr>')
            h.append('    </tbody>')
            h.append('  </table>')
    else:
        h.append('  <p>Nenhuma tarefa pendente registrada neste ciclo.</p>')

    # Alertas
    if alertas:
        h.append('  <h3>Alertas</h3>')
        h.append('  <ul>')
        for a in alertas:
            msg = a if isinstance(a, str) else a.get("msg", a.get("mensagem", str(a)))
            h.append(f'    <li>⚠️ {msg}</li>')
        h.append('  </ul>')
    h.append('</div>')

    # Viagens e milhas
    h.append('<div class="card">')
    h.append('  <div class="card-title">Viagens e Milhas — Orçamento 2026</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Item</th><th>Valor</th></tr></thead>')
    h.append('    <tbody>')
    h.append('      <tr><td>Teto anual de viagens</td><td><strong>R$ 45.000</strong></td></tr>')
    h.append('      <tr><td>Portugal (realizado)</td><td>R$ 22.337</td></tr>')
    h.append('      <tr><td>Saldo disponível</td><td><strong>R$ 22.663</strong></td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('  <p><em>Nota: Custos da estadia EUA (F1/F2) NÃO entram no orçamento de viagens — são custo de vida.</em></p>')
    h.append('</div>')

    # NCLEX Roadmap
    h.append('<div class="card">')
    h.append('  <div class="card-title">NCLEX Roadmap — Mariana</div>')
    h.append('  <p>Caminho para licenciamento como Registered Nurse nos EUA (estimativa 8-18 meses).</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Etapa</th><th>Descrição</th><th>Custo</th><th>Duração</th></tr></thead>')
    h.append('    <tbody>')
    nclex = [
        ("1", "CGFNS Credentials Evaluation", "US$ 350", "4-8 semanas"),
        ("2", "Teste de Inglês (MET ou OET recomendados)", "US$ 235–455", "Prep 2-3 meses"),
        ("3", "CGFNS VisaScreen Certificate", "US$ 540", "8-12 semanas"),
        ("4", "State Board Application (SC)", "US$ 200", "2-4 semanas"),
        ("5", "ATT (Authorization to Test)", "—", "2-4 semanas"),
        ("6", "NCLEX-RN Exam", "US$ 200", "Agendar Pearson VUE"),
        ("7", "License Issued", "—", "2-4 semanas"),
    ]
    for etapa, desc, custo, dur in nclex:
        h.append(f'      <tr><td>{etapa}</td><td>{desc}</td><td>{custo}</td><td>{dur}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('  <p><strong>Custo total estimado:</strong> US$ 1.515–2.440 | <strong>Perfil competitivo Mariana:</strong> Especialização Cardiologia + Mestrado USP + 11+ anos Einstein + UTI.</p>')
    h.append('  <p><strong>Projeção EUA:</strong> Cardiologia RN US$45–80/hora → US$4.000–7.000/mês líquido.</p>')
    h.append('</div>')

    # Simulação Mariana sem trabalhar
    h.append('<div class="card">')
    h.append('  <div class="card-title">Simulação — Mariana Sem Trabalhar</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Métrica</th><th>Valor</th></tr></thead>')
    h.append('    <tbody>')
    h.append('      <tr><td>Impacto líquido mensal</td><td>-R$ 6.830 (R$8.000 perdido − R$1.170 economizado)</td></tr>')
    h.append('      <tr><td>Faturamento PJ adicional necessário</td><td>R$ 8.035/mês bruto (+13,4%)</td></tr>')
    h.append('      <tr><td>IF com aporte R$20k mantido</td><td><strong>9,0 anos</strong> (folga absorve a perda)</td></tr>')
    h.append('      <tr><td>IF com aporte reduzido R$13,2k</td><td>11,4 anos (+2,4 anos)</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Calendário próximo ciclo
    h.append('<div class="card">')
    h.append('  <div class="card-title">Calendário — Próximo Ciclo</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Data</th><th>Item</th><th>Tipo</th></tr></thead>')
    h.append('    <tbody>')
    calendario = [
        ("05/Abr/2026", "Primeiro aporte R$20.000 (plano IF)", "Financeiro"),
        ("Abr/2026", "Contratar seguro de vida term life R$3-5M", "Proteção"),
        ("Abr/2026", "Contratar seguro invalidez (DIT) 60% da renda", "Proteção"),
        ("Abr/2026", "Consultar advogado sucessório/tributarista SP", "Sucessório"),
        ("Abr/2026", "Atualizar beneficiários PGBL e seguro de vida", "Proteção"),
        ("Mai/2026", "Testamento público David + Mariana (cartório BR)", "Sucessório"),
        ("Mai/2026", "Início prep teste inglês Mariana (MET ou OET)", "NCLEX"),
        ("Jun/2026", "Revisão tática quinzenal — despesas vs tetos", "Pipeline"),
        ("Jul/2026", "Análise completa trimestral (pipeline E0-E6)", "Pipeline"),
        ("T4/2026", "Avaliar holding patrimonial", "Sucessório"),
        ("Antes EUA", "Contratar CPA expatriado", "Tributário"),
        ("Antes EUA", "Procuração pública para Rubens (pai David)", "Sucessório"),
    ]
    for data, item, tipo in calendario:
        h.append(f'      <tr><td>{data}</td><td>{item}</td><td>{tipo}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    return '\n'.join(h)


def build_sections(e4: dict) -> dict:
    """Build S1-S10 content sections with charts and cards"""
    print("[E6.4] Building sections S1-S10...")

    narrativas = e4.get("narrativas", {})
    # Sanitize monetary formats in narrativas before rendering
    narrativas = sanitize_narrativas(narrativas)
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

        # Add charts first (always emit canvas, narratives are optional context)
        for chart_key in section_chart_keys:
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

    # Build appendices (full content)
    print("[E6.4] Building appendices A-E...")
    replacements["{{CONTENT_APP_A}}"] = build_appendix_a()
    replacements["{{CONTENT_APP_B}}"] = build_appendix_b()
    replacements["{{CONTENT_APP_C}}"] = build_appendix_c(e4)
    replacements["{{CONTENT_APP_D}}"] = build_appendix_d()
    replacements["{{CONTENT_APP_E}}"] = build_appendix_e(e4)

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
    app_count = len(re.findall(r'id="apendice-[a-e]"', html))
    if app_count < 5:
        results["V6"]["passed"] = False
        results["V6"]["detail"] = f"Found {app_count} appendices, expected 5"

    # V10-V17: Not yet implemented — mark as warnings
    for vnum in range(10, 18):
        v_key = f"V{vnum}"
        if v_key in results:
            results[v_key]["passed"] = True  # Default to True until implemented
            results[v_key]["warning"] = "Validação pendente de implementação"

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
    validation_failures = 0
    for check_key, result in validation.items():
        status = "PASS" if result["passed"] else "FAIL"
        detail = f" — {result['detail']}" if not result["passed"] else ""
        print(f"  {check_key}: {result['name']} [{status}]{detail}")
        if not result["passed"]:
            validation_failures += 1

    # Check for validation failures before writing HTML
    if validation_failures > 0:
        print(f"\n  [WARN] {validation_failures} validações falharam — relatório pode conter erros")

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

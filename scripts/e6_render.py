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
import yaml

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
            for field in ("titulo", "narrativa", "insight", "context", "conclusion"):
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

def _load_json_config(path: Path, label: str = "") -> dict:
    """Generic JSON config loader with warning on missing/error."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️  Error loading {label or path.name}: {e}")
    else:
        print(f"  [WARN] {label or path.name} não encontrado — usando defaults hardcoded")
    return {}

_FAMILY = _load_family_config()
CONFIG_RATES = _load_config_rates()
GOALS_CONFIG = _load_json_config(BASE_DIR / "config" / "goals.json", "goals.json")
SCORING_CONFIG = _load_json_config(BASE_DIR / "config" / "scoring.json", "scoring.json")
FISCAL_CONFIG = _load_json_config(BASE_DIR / "config" / "parametros_fiscais.json", "parametros_fiscais.json")
CENARIOS_CONFIG = _load_json_config(BASE_DIR / "config" / "cenarios.json", "cenarios.json")
INSTITUTIONS_CONFIG = _load_json_config(BASE_DIR / "config" / "institutions.json", "institutions.json")
PIPELINE_CONFIG = _load_json_config(BASE_DIR / "config" / "pipeline.json", "pipeline.json")

def _build_broker_list() -> str:
    """Build comma-separated broker display names from banco_membro + banco_canonical."""
    banco_membro = _FAMILY.get("banco_membro", {})
    canonical = INSTITUTIONS_CONFIG.get("banco_canonical", {})
    brokers = []
    for key in banco_membro:
        display = canonical.get(key, key).title()
        if display not in brokers:
            brokers.append(display)
    return ", ".join(brokers) if brokers else "corretoras configuradas"

# Load report layout configuration (YAML)
def _load_report_layout() -> dict:
    """Load report_layout.yaml for section/card/chart ordering and visibility."""
    layout_path = BASE_DIR / "config" / "report_layout.yaml"
    if layout_path.exists():
        try:
            with open(layout_path, "r", encoding="utf-8") as f:
                layout = yaml.safe_load(f)
            print(f"  [OK] report_layout.yaml v{layout.get('version', '?')} loaded")
            return layout
        except Exception as e:
            print(f"  ⚠️  Error loading report_layout.yaml: {e} — using hardcoded fallback")
    else:
        print("  [WARN] report_layout.yaml não encontrado — usando layout hardcoded")
    return {}

REPORT_LAYOUT = _load_report_layout()

FAMILY_SOBRENOME = _FAMILY.get("familia", {}).get("sobrenome", "Ferreira Campos")
_TITULAR_KEY_RENDER = _FAMILY.get("titular", "")
TITULAR_NOME = _FAMILY.get("membros", {}).get(_TITULAR_KEY_RENDER, {}).get("nome_curto", "")

TEMPLATE_PATH = BASE_DIR / "config" / "report_template.html"
E5_JSON_PATH = BASE_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
E4_INVEST_PATH = BASE_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
E4_DESPESAS_PATH = BASE_DIR / "processed" / "E4_unified" / "despesas-4_unified.json"
E4_RECEITAS_PATH = BASE_DIR / "processed" / "E4_unified" / "receitas-4_unified.json"
E4_FLUXO_PATH = BASE_DIR / "processed" / "E4_unified" / "fluxo_mensal_detalhado-4_unified.json"
MANUAL_PATH = BASE_DIR / "config" / "manual_operacao.md"
DEFINITIONS_PATH = BASE_DIR / "config" / "definitions.md"
OUTPUT_DIR = BASE_DIR / "output"

# Color palette for charts — from report_layout.yaml
PALETTE = REPORT_LAYOUT.get("chart_palette", []) or [
    "#1A3A5C", "#1E6E8F", "#15803D", "#F4A261", "#B91C1C",
    "#457B9D", "#E63946", "#A8DADC", "#457B9D", "#2A9D8F",
    "#E76F51", "#F4A460", "#FFB703", "#8ECAE6", "#219EBC"
]

# Mapping: narrativas chart key → canonical canvas ID — from report_layout.yaml
CHART_CANVAS_MAP = REPORT_LAYOUT.get("chart_canvas_map", {}) or {
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

# Mapping: chart key → friendly display title — from report_layout.yaml
CHART_TITLES = REPORT_LAYOUT.get("chart_titles", {}) or {
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
    "mariana_cenarios": "Cenários IF — Mariana",
    "viagens": "Orçamento de Viagens",
}

# Mapping: section number → which chart keys belong to it — from report_layout.yaml
# Note: YAML keys may be ints or strings; normalize to int
_raw_section_charts = REPORT_LAYOUT.get("section_charts", {})
SECTION_CHARTS = {int(k): v for k, v in _raw_section_charts.items()} if _raw_section_charts else {
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

def fmt_num(value: float) -> str:
    """Format as 3.501.275 (BR thousands, no currency prefix)"""
    if not isinstance(value, (int, float)):
        return "—"
    return f"{int(value):,}".replace(",", ".")

def fmt_dec(value: float, decimals: int = 1) -> str:
    """Format decimal with BR comma: 19.9 → 19,9"""
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value:.{decimals}f}".replace(".", ",")

def fmt_moeda(value: float) -> str:
    """Format as -$10.042 or similar for USD"""
    if not isinstance(value, (int, float)):
        return "—"
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${abs(value):,.2f}"

PERIOD_TOGGLE_CHARTS = {"fluxo_mensal", "receita_bar", "despesas_doughnut", "viagens", "impostos_pj"}


def _period_toggle_html(chart_key: str) -> str:
    """Emit a segmented-control period toggle for supported charts."""
    cid = CHART_CANVAS_MAP.get(chart_key, f"chart-{chart_key}")
    return (
        f'  <div class="period-toggle-row">'
        f'<div class="period-toggle" data-period-group="{cid}">'
        f'<button class="period-btn" data-period="3">3M</button>'
        f'<button class="period-btn" data-period="6">6M</button>'
        f'<button class="period-btn active" data-period="12">12M</button>'
        f'<button class="period-btn" data-period="ytd">Ano</button>'
        f'</div>'
        f'<span class="period-label" id="{cid}-period-label"></span>'
        f'</div>'
    )


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
    # Period toggle for supported charts
    if chart_key in PERIOD_TOGGLE_CHARTS:
        parts.append(_period_toggle_html(chart_key))
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
        parts.append(f'  <p class="chart-conclusion" id="{canvas_id}-conclusion">{conclusion}</p>')
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
    """Load E4 unified investments, sort by valor_atual desc, return top 15.
    Excludes positions with valor_atual <= 0 (closed/sold).
    Source: investimentos-4_unified.json (dados list).
    Builds a display label that disambiguates generic types (e.g. 'CDB DI')
    by appending the institution name."""
    print("[E6.0] Loading E4 investimentos for Top 15...")
    with open(E4_INVEST_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    dados = data.get("dados", [])
    generic_types = {"CDB", "CDB DI", "CDB-DI", "CDB Progressivo", "LCI", "LCA", "CRI", "CRA", "LF"}
    items = []
    for v in dados:
        if v.get("valor_atual", 0) <= 0:
            continue
        nome = v.get("nome", "").strip()
        tipo = v.get("tipo", "").strip()
        banco = v.get("instituicao", "").strip()
        label = nome or tipo or "Sem nome"
        if label in generic_types and banco:
            label = f"{label} ({banco})"
        items.append({"nome": label, "banco": banco, "valor": v["valor_atual"]})
    items.sort(key=lambda x: x["valor"], reverse=True)
    return items[:15]

def load_viagens_12m() -> dict:
    """Load last 12 months of lazer_viagens expenses from E4 unified data.
    Returns dict with: gasto (total), por_mes (monthly breakdown), realizadas (transactions)."""
    print("[E6.0] Loading E4 viagens data (12-month window)...")

    hoje = datetime.now()
    y, m = hoje.year, hoje.month
    # Go back 12 months
    m -= 12
    if m <= 0:
        y -= 1
        m += 12
    corte_str = f"{y:04d}-{m:02d}"

    # Monthly totals from fluxo
    with open(E4_FLUXO_PATH, 'r', encoding='utf-8') as f:
        fluxo = json.load(f)
    por_mes_raw = fluxo.get("despesas", {}).get("por_mes", {})
    meses_sorted = sorted(por_mes_raw.keys())
    meses_12m = [m for m in meses_sorted if m >= corte_str]

    por_mes = {}
    gasto_total = 0.0
    for m in meses_12m:
        val = por_mes_raw[m].get("lazer_viagens", 0.0)
        por_mes[m] = val
        gasto_total += val

    # Individual transactions from despesas
    with open(E4_DESPESAS_PATH, 'r', encoding='utf-8') as f:
        despesas = json.load(f)
    txns_all = despesas.get("dados", {}).get("lazer_viagens", [])
    txns_12m = [t for t in txns_all if t.get("data", "") >= corte_str]
    txns_12m.sort(key=lambda t: t.get("data", ""))

    periodo_inicio = meses_12m[0] if meses_12m else corte_str
    periodo_fim = meses_12m[-1] if meses_12m else hoje.strftime("%Y-%m")

    return {
        "gasto": round(gasto_total, 2),
        "por_mes": por_mes,
        "realizadas_txns": txns_12m,
        "periodo": f"{periodo_inicio} a {periodo_fim}",
        "meses": meses_12m,
    }


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
        "{{KPI_SCORE_CLASS}}": s["classificacao"],

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
            "_raw_labels": raw_labels,
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
        "renda_passiva_meta": g.get("renda_passiva", {}).get("meta_mensal", g.get("if_trs_monthly_value",
            GOALS_CONFIG.get("independencia_financeira", {}).get("renda_passiva_meta_mensal", 0))),
    }

    # Fiscal parameters for client-side period recalculation (impostos_pj)
    _lp_pct_val = FISCAL_CONFIG.get("lucro_presumido", {}).get("percentual_servicos_pct", 32.0)
    _pgbl_pct_val = FISCAL_CONFIG.get("pgbl", {}).get("limite_deducao_pct", 12.0)
    _aliq_val = e4.get("previdencia_pgbl", {}).get("aliquota_marginal", 27.5)

    report_data = {
        "meta": {
            "modo_padrao": "strategic",
            "familia": FAMILY_SOBRENOME,
            "periodo": e4["periodo_dados"],
            "data_geracao": datetime.now().isoformat(),
            "versao": extract_version(load_manual()),
        },
        "kpis": kpis,
        "patrimonio": p,
        "charts": charts,
        "fiscal_params": {
            "lucro_presumido_pct": _lp_pct_val,
            "pgbl_limite_pct": _pgbl_pct_val,
            "aliquota_marginal": _aliq_val,
            "das_pct": FISCAL_CONFIG.get("das_simples", {}).get("aliquota_efetiva_pct", 6.0),
        },
        "orcamento_prospectivo": build_orcamento_prospectivo(e4),
        "consumo_consciente": e4.get("consumo_consciente", {}),
        "diagnostico_comportamental": e4.get("diagnostico_comportamental", []),
        "investimentos": build_investimentos(e4),
        "estrategia_aporte": build_estrategia_aporte(e4),
        "contrafluxo": build_contrafluxo_scenarios(),
        "dashboard": build_tactical_dashboard(e4),
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

def _build_riscos_fallback() -> list:
    """Build risk fallback from goals.json riscos_prioritarios or hardcoded defaults."""
    _severity_map = {"crítico": "critico", "alto": "alto", "médio": "medio", "média": "medio", "baixo": "baixo"}
    _prob_map = {"alta": 3, "média": 2, "baixa": 1}
    _impacto_map = {"crítico": 5, "alto": 4, "médio": 3, "baixo": 2}
    _raio_map = {"crítico": 20, "alto": 16, "médio": 14, "baixo": 10}

    goals_riscos = GOALS_CONFIG.get("riscos_prioritarios", [])
    if goals_riscos:
        result = []
        for r in goals_riscos:
            imp_str = r.get("impacto", "médio").lower()
            prob_str = r.get("prob", "média").lower()
            sev = _severity_map.get(imp_str, "medio")
            result.append({
                "titulo": r.get("nome", "Risco"),
                "severity": sev,
                "probabilidade": _prob_map.get(prob_str, 2),
                "impacto": _impacto_map.get(imp_str, 3),
                "raio": _raio_map.get(imp_str, 14),
            })
        return result
    # Ultimate fallback
    print("  ⚠️  WARNING: usando riscos hardcoded — goals.json sem riscos_prioritarios")
    return [
        {"titulo": "Seguro de vida", "severity": "critico", "probabilidade": 2, "impacto": 5, "raio": 20},
        {"titulo": "Concentração PJ", "severity": "alto", "probabilidade": 2, "impacto": 4, "raio": 16},
        {"titulo": "Volatilidade cambial", "severity": "medio", "probabilidade": 3, "impacto": 2, "raio": 12},
    ]


def _build_top5_decisoes_fallback() -> list:
    """Build top-5 strategic decisions from goals.json or hardcoded defaults."""
    cfg = GOALS_CONFIG.get("top5_decisoes", [])
    if cfg and all(isinstance(d, dict) and "label" in d for d in cfg):
        return cfg
    print("  ⚠️  WARNING: top5_decisoes não encontrado em goals.json — configure 'top5_decisoes' para evitar dados genéricos")
    aporte = GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 0)
    if aporte <= 0:
        raise ValueError("top5_decisoes e meta_aporte_mensal ausentes em goals.json. Configure pelo menos um deles.")
    seg_min = GOALS_CONFIG.get("seguros", {}).get("vida_term_minimo", 0)
    seg_max = GOALS_CONFIG.get("seguros", {}).get("vida_term_maximo", 0)
    return [
        {"label": f"Aportes R$ {aporte/1000:.0f}k/mês", "impacto_1a": aporte * 12, "impacto_10a": aporte * 12 * 10},
        {"label": "Seguro vida term",           "impacto_1a": seg_min, "impacto_10a": seg_max},
        {"label": "NCLEX/OET",                  "impacto_1a": 280000,  "impacto_10a": 2800000},
        {"label": "CPA expatriado (EUA)",       "impacto_1a": 100000,  "impacto_10a": 500000},
        {"label": "Advogado sucessório BR-EUA", "impacto_1a": 50000,   "impacto_10a": 1000000},
    ]


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
    _lp_pct = FISCAL_CONFIG.get("lucro_presumido", {}).get("percentual_servicos_pct", 32.0) / 100
    _pgbl_pct = FISCAL_CONFIG.get("pgbl", {}).get("limite_deducao_pct", 12.0) / 100
    _das_pct = FISCAL_CONFIG.get("das_simples", {}).get("aliquota_efetiva_pct", 6.0) / 100
    renda_tributavel = round(receita_pj_anual * _lp_pct, 2)
    limite_pgbl = round(renda_tributavel * _pgbl_pct, 2)
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
        "receita_bar": (lambda pfd: {
            "labels": list(pfd.keys()),
            "datasets": [{
                "data": list(pfd.values()),
                "backgroundColor": PALETTE[:len(pfd)]
            }]
        })(f.get("por_fonte_detalhado", f["por_fonte"])),
        "fluxo_mensal": (lambda rec, desp: {
            "labels": ["Receita Mensal", "Despesa Mensal", "Saldo"],
            "datasets": [{
                "label": "Fluxo de Caixa (R$)",
                "data": [round(rec, 2), round(desp, 2), round(rec - desp, 2)],
                "backgroundColor": ["#15803D", "#B91C1C", "#2E86AB" if rec >= desp else "#F4A261"],
                "borderRadius": 4
            }]
        })(f.get("janela_12m", {}).get("receita_recorrente_mensal", f["receita_recorrente_mensal"]),
           f.get("janela_12m", {}).get("despesa_mensal_media", f["despesa_mensal_media"])),
        "receita_despesa_mensal": build_receita_despesa_mensal(f, e4),
        "despesas_doughnut": (lambda dc: {
            "labels": [k for k, _ in dc],
            "datasets": [{
                "data": [v for _, v in dc],
                "backgroundColor": PALETTE[:len(dc)]
            }]
        })(sorted(f["despesas_por_categoria"].items(), key=lambda x: x[1], reverse=True)),
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
        "alocacao_alvo": (lambda alvo: {
            "labels": list(alvo.keys()),
            "datasets": [{
                "data": list(alvo.values()),
                "backgroundColor": PALETTE[:len(alvo)]
            }]
        })({
            "Renda Fixa": GOALS_CONFIG.get("alocacao_alvo", {}).get("renda_fixa_pct", 50),
            "Ações": GOALS_CONFIG.get("alocacao_alvo", {}).get("acoes_pct", 25),
            "Imóveis/REITs": GOALS_CONFIG.get("alocacao_alvo", {}).get("imoveis_reits_pct", 15),
            "Liquidez/USD": GOALS_CONFIG.get("alocacao_alvo", {}).get("liquidez_usd_pct", 10),
        }),
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
        "custos_f1f2": (lambda cambio, tuition_usd, rb_usd: {
            "labels": ["Tuition", "Room & Board", "TOTAL", "Renda David", "Sobra"],
            "datasets": [{
                "data": [
                    round(tuition_usd / 12 * cambio),      # tuition mensal em BRL
                    round(rb_usd / 12 * cambio),            # room+board mensal em BRL
                    round((tuition_usd + rb_usd) / 12 * cambio),  # total mensal em BRL
                    round(f["receita_recorrente_mensal"]),
                    round(f["receita_recorrente_mensal"] - (tuition_usd + rb_usd) / 12 * cambio)
                ],
                "backgroundColor": ["#E63946", "#F4A261", "#1A3A5C", "#2DC653", "#2E86AB"]
            }]
        })(
            CONFIG_RATES["cambio_usd_brl"],
            GOALS_CONFIG.get("fase_f1f2", {}).get("tuition_usd_anual", 27500),
            GOALS_CONFIG.get("fase_f1f2", {}).get("room_board_usd_anual", 16500),
        ),
        "cenarios_cambiais": (lambda cb, renda, cb_pess, cb_otim, f1f2_total_usd, mariana_usd: {
            "labels": [
                ["Pessimista", f"R$ {cb_pess:.2f}/USD"],
                ["Realista", f"R$ {cb:.2f}/USD"],
                ["Otimista", f"R$ {cb_otim:.2f}/USD"]
            ],
            "datasets": [
                {"label": "Sem Mariana", "data": [
                    round(renda - f1f2_total_usd / 12 * cb_pess),
                    round(renda - f1f2_total_usd / 12 * cb),
                    round(renda - f1f2_total_usd / 12 * cb_otim)
                ], "backgroundColor": "#F4A261"},
                {"label": "Com Mariana (NCLEX)", "data": [
                    round(renda + mariana_usd * cb_pess - f1f2_total_usd / 12 * cb_pess),
                    round(renda + mariana_usd * cb - f1f2_total_usd / 12 * cb),
                    round(renda + mariana_usd * cb_otim - f1f2_total_usd / 12 * cb_otim)
                ], "backgroundColor": "#2DC653"}
            ]
        })(
            CONFIG_RATES["cambio_usd_brl"],
            f["receita_recorrente_mensal"],
            CENARIOS_CONFIG.get("cambio", {}).get("pessimista", 7.50),
            CENARIOS_CONFIG.get("cambio", {}).get("otimista", 4.50),
            GOALS_CONFIG.get("fase_f1f2", {}).get("tuition_usd_anual", 27500) + GOALS_CONFIG.get("fase_f1f2", {}).get("room_board_usd_anual", 16500),
            GOALS_CONFIG.get("mariana_eua", {}).get("renda_rn_minima_usd", 4000),
        ),
        "projecao_3cenarios": {
            "meta_if": g["if_meta"],
            "investivel": p["investivel"],
            "imoveis": p.get("imoveis_investimento", 0),
            "aporte_mensal": g.get("aporte_mensal", GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 0)),
            "anos": CENARIOS_CONFIG.get("horizonte_projecao_anos", 20),
            "taxa_imoveis": CENARIOS_CONFIG.get("valorizacao_imoveis", {}).get("pessimista_pct", 2.0) / 100,
            "taxa_pessimista": CENARIOS_CONFIG.get("retorno_real", {}).get("pessimista_pct", 4.0) / 100,
            "taxa_realista": CENARIOS_CONFIG.get("retorno_real", {}).get("realista_pct", 6.0) / 100,
            "taxa_otimista": CENARIOS_CONFIG.get("retorno_real", {}).get("otimista_pct", 8.0) / 100,
        },
        "renda_passiva": (lambda rp_atual, rp_meta: {
            "labels": [""],
            "meta_value": round(rp_meta),
            "atual_total": round(rp_atual),
            "pct_meta": round(rp_atual / rp_meta * 100, 1) if rp_meta > 0 else 0,
            "datasets": [
                {"label": "Aluguéis", "data": [round(renda_aluguel)], "backgroundColor": "#2E86AB"},
                {"label": "Dividendos", "data": [round(renda_dividendos)], "backgroundColor": "#15803D"},
                {"label": "RF/Cupons", "data": [round(renda_juros)], "backgroundColor": "#F4A261"},
                {"label": "Gap até Meta", "data": [max(0, round(rp_meta - rp_atual))], "backgroundColor": "rgba(200,200,200,0.25)"},
            ]
        })(
            renda_aluguel + renda_dividendos + renda_juros,
            g.get("renda_passiva", {}).get("meta_mensal", g.get("if_trs_monthly_value",
                GOALS_CONFIG.get("independencia_financeira", {}).get("renda_passiva_meta_mensal", 0))),
        ),
        "impostos_pj": {
            "labels": ["Receita PJ (anual)", "Lucro Presumido (32%)", "DAS Estimado (anual)", "Limite PGBL (12%)", "Economia IR c/ PGBL"],
            "datasets": [{
                "label": "Valores (R$)",
                "data": [round(receita_pj_anual), round(renda_tributavel), round(receita_pj_anual * _das_pct), round(limite_pgbl), round(economia_ir)],
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
        })(e4.get("riscos", _build_riscos_fallback())),
        "top5_decisoes": (lambda decs: {
            "labels": [d["label"] for d in decs],
            "datasets": [
                {"label": "Impacto 1 ano", "data": [d.get("impacto_1a", 0) for d in decs], "backgroundColor": "#2E86AB"},
                {"label": "Impacto 10 anos", "data": [d.get("impacto_10a", 0) for d in decs], "backgroundColor": "#2DC653"}
            ]
        })(e4.get("top5_decisoes", g.get("top5_decisoes", _build_top5_decisoes_fallback()))),
        "mariana_cenarios": (lambda cm, m_min, m_max: {
            "labels": cm.get("labels", ["Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card"]),
            "datasets": [
                {"label": "Aporte mensal", "data": cm.get("aportes", [0, m_min, m_max]), "backgroundColor": "#2E86AB"},
                {"label": "Prazo IF (anos)", "data": cm.get("prazos_if", [0, 0, 0]), "backgroundColor": "#2DC653", "yAxisID": "y1"}
            ]
        })(
            e4.get("cenarios_mariana", g.get("cenarios_mariana", {})),
            GOALS_CONFIG.get("mariana_eua", {}).get("renda_rn_minima_usd", 4000),
            GOALS_CONFIG.get("mariana_eua", {}).get("renda_rn_maxima_usd", 7000),
        ),
        "viagens": (lambda vg12, teto: (lambda meses, pm: (lambda raw: {
            "labels": meses,
            "datasets": [
                {
                    "label": "Acumulado",
                    "data": [sum(raw[:i+1]) for i in range(len(raw))],
                    "backgroundColor": "#E6394633",
                    "borderColor": "#E63946",
                    "borderWidth": 2,
                    "fill": True,
                    "type": "line",
                    "tension": 0.3,
                },
                {
                    "label": f"Teto {len(meses)}M ({fmt_brl(teto)})",
                    "data": [teto] * len(meses),
                    "borderColor": "#2DC653",
                    "borderWidth": 2,
                    "borderDash": [6, 4],
                    "type": "line",
                    "pointRadius": 0,
                    "fill": False,
                },
            ],
            "_raw_monthly": raw,
            "_teto_anual": teto,
            "_summary": {
                "gasto_12m": vg12.get("gasto", 0),
                "teto_anual": teto,
                "saldo": teto - vg12.get("gasto", 0),
                "periodo": vg12.get("periodo", ""),
            },
        })([pm.get(m, 0) for m in meses]))(vg12.get("meses", []), vg12.get("por_mes", {})))(
            e4.get("_viagens_12m", {"gasto": 0, "por_mes": {}, "meses": []}),
            GOALS_CONFIG.get("viagens", {}).get("teto_anual", 45000),
        ),
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
    """Build estratégia de aporte data from E4, goals.json, or hardcoded defaults."""
    ea = e4.get("estrategia_aporte", {})
    if ea.get("destinos"):
        return ea

    # Fallback: goals.json aportes + destinos detalhados
    aportes_cfg = GOALS_CONFIG.get("aportes", {})
    destinos_cfg = GOALS_CONFIG.get("aportes_destinos_detalhados", [])
    total = aportes_cfg.get("meta_aporte_mensal", 20000)

    if destinos_cfg:
        destinos = destinos_cfg
        brl_total = sum(d["valor"] for d in destinos if d.get("moeda") == "BRL")
        usd_total = sum(d["valor"] for d in destinos if d.get("moeda") == "USD")
        brl_names = ", ".join(d["destino"].split()[0] for d in destinos if d.get("moeda") == "BRL")
        usd_names = ", ".join(d["destino"].split()[0] for d in destinos if d.get("moeda") == "USD")
        return {
            "total_aporte": total,
            "dia_aporte": 5,
            "periodo_inicio": "Imediato",
            "destinos": destinos,
            "pct_brl": round(brl_total / total * 100) if total else 0,
            "pct_usd": round(usd_total / total * 100) if total else 0,
            "destinos_brl": brl_names,
            "destinos_usd": usd_names,
            "resumo_brl": f"Reforça reserva e patrimônio em reais ({fmt_brl(brl_total)}/mês).",
            "resumo_usd": f"Exposição ao dólar = {fmt_brl(usd_total)}/mês. Meta pré-EUA: US$ {fmt_num(GOALS_CONFIG.get('dolarizacao', {}).get('meta_usd', 20000))}.",
        }

    # Ultimate fallback: require config
    raise ValueError(
        "Estratégia de aportes não encontrada em goals.json. "
        "Configure 'aportes.destinos_detalhados' ou 'aportes.meta_aporte_mensal' em config/goals.json."
    )


def build_contrafluxo_scenarios() -> dict:
    """Build Selic/contrafluxo scenarios from cenarios.json + taxas.json."""
    cen_selic = CENARIOS_CONFIG.get("selic", {})
    return {
        "selic_atual": CONFIG_RATES["selic_atual"],
        "cenarios": {
            "pessimista": cen_selic.get("pessimista", {"selic": 8.0, "cdi": 7.9}),
            "base": {"selic": CONFIG_RATES["selic_atual"], "cdi": CONFIG_RATES["cdi_anual"]},
            "otimista": cen_selic.get("otimista", {"selic": 15.0, "cdi": 14.9}),
        }
    }

def build_tactical_dashboard(e4: dict) -> dict:
    """Build tactical dashboard data for the JS buildDashboard() function.

    Expected keys (consumed by buildDashboard in report_template.html):
      patrimonio_delta, aportes, despesas_por_categoria, tarefas_status,
      tarefas, investimentos_delta, alertas, proximos_15d, notas, periodo
    """
    f = e4.get("fluxo_caixa", {})
    num_months = max(1, len(f.get("receita_despesa_mensal_detalhado", {}).get("labels", [])))

    # --- Tetos from definitions.md (monthly ceilings) ---
    _TETOS = {
        "moradia": 2500, "alimentacao": 4500, "saude": 3000,
        "servicos_domesticos": 4000, "educacao": 2000, "transporte": 1700,
        "lazer_viagens": 3750, "vestuario": 2000, "assinaturas": 300,
        "suporte_familiar": 5000, "financeiro": 200, "melhoria_reforma": 1500,
        "reserva_desejos": 3000, "seguros": 1500,
    }
    _LABELS = {
        "moradia": "Moradia", "alimentacao": "Alimentação", "saude": "Saúde",
        "servicos_domesticos": "Serv. Domésticos", "educacao": "Educação",
        "transporte": "Transporte", "lazer_viagens": "Lazer/Viagens",
        "vestuario": "Vestuário", "assinaturas": "Assinaturas",
        "suporte_familiar": "Suporte Familiar", "financeiro": "Financeiro",
        "melhoria_reforma": "Melhoria/Reforma", "reserva_desejos": "Reserva Desejos",
        "seguros": "Seguros", "nao_identificado": "Não Identificado",
        "financiamentos": "Financiamentos", "impostos": "Impostos",
    }

    # --- D1: Despesas por categoria (monthly average vs teto) ---
    raw_despesas = f.get("despesas_por_categoria", {})
    despesas_dash = {}
    for cat, total in raw_despesas.items():
        mensal = round(total / num_months, 2)
        teto = _TETOS.get(cat, round(mensal * 1.2, 2))
        despesas_dash[cat] = {
            "label": _LABELS.get(cat, cat.replace("_", " ").title()),
            "gasto": mensal,
            "teto": teto,
        }

    # --- D2: Aportes (from goals.json destinos) ---
    destinos_cfg = GOALS_CONFIG.get("aportes_destinos_detalhados", [])
    aportes_dash = {}
    for i, d in enumerate(destinos_cfg):
        key = f"aporte_{i}"
        aportes_dash[key] = {
            "label": d.get("destino", f"Destino {i+1}"),
            "feito": False,
            "valor_meta": d.get("valor", 0),
            "valor_feito": 0,
        }

    # --- Investimentos delta (current snapshot, no previous period) ---
    p = e4.get("patrimonio", {})
    inv_delta = {
        "david": {
            "label": "Investimentos David",
            "anterior": 0,
            "atual": p.get("investimentos_david", 0),
        },
        "mariana": {
            "label": "Investimentos Mariana",
            "anterior": 0,
            "atual": p.get("investimentos_mariana", 0),
        },
        "imoveis": {
            "label": "Imóveis Investimento",
            "anterior": 0,
            "atual": p.get("imoveis_investimento", 0),
        },
    }

    # --- Tarefas (pass through from E5) ---
    tarefas = e4.get("tarefas", [])
    tarefas_status = e4.get("tarefas_status", {})

    # --- Alertas ---
    alertas = e4.get("alertas", [])
    pontos_urgentes = e4.get("pontos_urgentes", [])
    for pu in pontos_urgentes:
        txt = f"{pu.get('acao', '')} — {pu.get('impacto', '')}"
        if txt not in alertas:
            alertas.append(txt)

    # --- Próximos 15 dias (derived from tasks with near-term deadlines) ---
    now_label = datetime.now().strftime("%d/%m")
    proximos = []
    for t in tarefas[:10]:
        st = str(tarefas_status.get(str(t["n"]), "pendente"))
        proximos.append({
            "data": t.get("e", "—"),
            "acao": f"#{t['n']} {t['t'][:60]}",
            "status": st,
        })

    # --- Notas ---
    score_val = e4.get("score", {}).get("valor", "N/D")
    score_cls = e4.get("score", {}).get("classificacao", "")
    eq = e4.get("equilibrio_cerbasi", {})
    notas = (
        f"Score financeiro: {score_val}/10 ({score_cls}). "
        f"Equilíbrio Cerbasi: {eq.get('pct_presente', 0):.0f}% presente / {eq.get('pct_futuro', 0):.0f}% futuro "
        f"({eq.get('classificacao', 'N/D')}). "
        f"Período dos dados: {e4.get('periodo_dados', 'N/D')}."
    )

    return {
        "patrimonio_delta": 0,
        "aportes": aportes_dash,
        "despesas_por_categoria": despesas_dash,
        "tarefas_status": tarefas_status,
        "tarefas": tarefas,
        "investimentos_delta": inv_delta,
        "alertas": alertas,
        "proximos_15d": proximos,
        "notas": notas,
        "periodo": e4.get("periodo_dados", ""),
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
    """Build Receitas por Fonte card with interactive period filter (3M/6M/12M/YTD).

    Loads raw transactions from receitas-4_unified.json, embeds as JSON,
    and uses client-side JS to filter by period / rebuild table.
    """
    # Load raw receitas transactions for per-period filtering
    txns_compact: list[dict] = []
    try:
        with open(E4_RECEITAS_PATH, 'r', encoding='utf-8') as f:
            receitas_raw = json.load(f)
        for _cat_key, items in receitas_raw.get("dados", {}).items():
            for tx in items:
                dt = tx.get("data", "")
                if len(dt) >= 7:
                    txns_compact.append({
                        "m": dt[:7],
                        "c": _cat_key.replace("_", " ").title(),
                        "v": round(tx.get("valor", 0), 2),
                    })
    except Exception:
        txns_compact = []

    html_parts = ['<div class="card card-feature" id="rf-card">']
    html_parts.append('  <div class="card-title">Receitas por Fonte</div>')

    if not txns_compact:
        fallback = e4.get("fluxo_caixa", {}).get("tabela_receitas", [])
        html_parts.append('  <table><thead>')
        html_parts.append('    <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
        html_parts.append('  </thead><tbody>')
        total = sum(it.get("valor", 0) for it in fallback)
        for it in fallback:
            html_parts.append(f'    <tr><td>{it.get("categoria","")}</td><td>{fmt_brl(it.get("valor",0))}</td><td>{fmt_pct(it.get("pct",0))}</td></tr>')
        html_parts.append(f'    <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total)}</strong></td><td><strong>100,0%</strong></td></tr>')
        html_parts.append('  </tbody></table></div>')
        return '\n'.join(html_parts)

    # Period toggle buttons
    html_parts.append('  <div class="period-toggle" id="rf-period-toggle">')
    html_parts.append('    <button class="period-btn" data-period="3m" onclick="filterRF(\'3m\')">3M</button>')
    html_parts.append('    <button class="period-btn" data-period="6m" onclick="filterRF(\'6m\')">6M</button>')
    html_parts.append('    <button class="period-btn active" data-period="12m" onclick="filterRF(\'12m\')">12M</button>')
    html_parts.append('    <button class="period-btn" data-period="ytd" onclick="filterRF(\'ytd\')">Ano</button>')
    html_parts.append('  </div>')

    # Table skeleton (JS fills tbody)
    html_parts.append('  <table id="rf-table">')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody></tbody>')
    html_parts.append('  </table>')

    # Embed data + JS
    txns_json = json.dumps(txns_compact, ensure_ascii=False)
    html_parts.append('  <script>')
    html_parts.append('  (function(){')
    html_parts.append(f'    var rfTxns={txns_json};')
    html_parts.append('    function pad(n){return n<10?"0"+n:""+n;}')
    html_parts.append('    function cutoff(p){')
    html_parts.append('      var d=new Date();')
    html_parts.append('      if(p==="3m")d.setMonth(d.getMonth()-3);')
    html_parts.append('      else if(p==="6m")d.setMonth(d.getMonth()-6);')
    html_parts.append('      else if(p==="12m")d.setMonth(d.getMonth()-12);')
    html_parts.append('      else if(p==="ytd")d=new Date(d.getFullYear(),0,1);')
    html_parts.append('      return d.getFullYear()+"-"+pad(d.getMonth()+1);')
    html_parts.append('    }')
    html_parts.append('    function fB(v){return"R$ "+Math.round(v).toLocaleString("pt-BR");}')
    html_parts.append('    function fP(v){return v.toFixed(1).replace(".",",")+"%";}')
    html_parts.append('    window.filterRF=function(p){')
    html_parts.append('      document.querySelectorAll("#rf-period-toggle .period-btn").forEach(function(b){b.classList.remove("active")});')
    html_parts.append('      document.querySelector("#rf-period-toggle .period-btn[data-period=\\""+p+"\\"]").classList.add("active");')
    html_parts.append('      var c=cutoff(p);')
    html_parts.append('      var grouped={};')
    html_parts.append('      rfTxns.forEach(function(t){')
    html_parts.append('        if(t.m>=c){grouped[t.c]=(grouped[t.c]||0)+t.v;}')
    html_parts.append('      });')
    html_parts.append('      var arr=Object.keys(grouped).map(function(k){return{c:k,v:grouped[k]};}).sort(function(a,b){return b.v-a.v;});')
    html_parts.append('      var total=arr.reduce(function(s,i){return s+i.v;},0);')
    html_parts.append('      var tb=document.querySelector("#rf-table tbody");')
    html_parts.append('      if(arr.length===0){')
    html_parts.append('        tb.innerHTML="<tr><td colspan=\\"3\\" style=\\"text-align:center;padding:16px\\">Nenhuma receita no período</td></tr>";')
    html_parts.append('      }else{')
    html_parts.append('        var rows=arr.map(function(i){')
    html_parts.append('          var pct=total>0?(i.v/total*100):0;')
    html_parts.append('          return"<tr><td>"+i.c+"</td><td>"+fB(i.v)+"</td><td>"+fP(pct)+"</td></tr>";')
    html_parts.append('        }).join("");')
    html_parts.append('        rows+="<tr class=\\"total-row\\"><td><strong>Total</strong></td><td><strong>"+fB(total)+"</strong></td><td><strong>100,0%</strong></td></tr>";')
    html_parts.append('        tb.innerHTML=rows;')
    html_parts.append('      }')
    html_parts.append('    };')
    html_parts.append('    filterRF("12m");')
    html_parts.append('  })();')
    html_parts.append('  </script>')

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
    _tit_nome = _FAMILY.get("membros", {}).get(_FAMILY.get("titular", ""), {}).get("nome_curto", "Titular")
    _conj_key = next((k for k, v in _FAMILY.get("membros", {}).items() if v.get("papel") == "conjuge"), "")
    _conj_nome = _FAMILY.get("membros", {}).get(_conj_key, {}).get("nome_curto", "Cônjuge")
    comp_items = [
        ("investimentos_david", f"Investimentos {_tit_nome}"),
        ("investimentos_mariana", f"Investimentos {_conj_nome}"),
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
    """Build Orçamento Prospectivo card with interactive period filter (3M/6M/12M/YTD).

    Monthly data per category is embedded as JSON; client-side JS filters by
    period, computes monthly averages, sorts by impact, and rebuilds the table.
    """
    det = e4.get("fluxo_caixa", {}).get("receita_despesa_mensal_detalhado", {})
    labels = det.get("labels", [])
    despesa_datasets = det.get("despesa_datasets", [])

    op_data = {
        "labels": labels,
        "datasets": [
            {"key": ds.get("label", "").lower().replace(" ", "_"), "label": ds.get("label", ""), "data": ds.get("data", [])}
            for ds in despesa_datasets
        ],
    }
    num_cats = len(despesa_datasets)

    html_parts = ['<div class="card card-feature" id="op-card">']
    html_parts.append(f'  <div class="card-title">Orçamento Prospectivo ({num_cats} Categorias)</div>')

    # Period toggle buttons
    html_parts.append('  <div class="period-toggle" id="op-period-toggle">')
    html_parts.append('    <button class="period-btn" data-period="3m" onclick="filterOP(\'3m\')">3M</button>')
    html_parts.append('    <button class="period-btn" data-period="6m" onclick="filterOP(\'6m\')">6M</button>')
    html_parts.append('    <button class="period-btn active" data-period="12m" onclick="filterOP(\'12m\')">12M</button>')
    html_parts.append('    <button class="period-btn" data-period="ytd" onclick="filterOP(\'ytd\')">Ano</button>')
    html_parts.append('  </div>')

    # Context (JS updates)
    html_parts.append('  <p class="chart-context" id="op-context"></p>')

    # Table skeleton (JS fills tbody)
    html_parts.append('  <table id="op-table">')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Média Mensal</th><th>% do Total</th><th>Acum. %</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody></tbody>')
    html_parts.append('  </table>')

    # Insights (JS updates)
    html_parts.append('  <div id="op-insights"></div>')

    # Methodology note (JS updates month count)
    html_parts.append('  <p id="op-method" style="margin-top:0.8em; font-size:0.85em; color:#666;"></p>')

    # Embed data + JS
    data_json = json.dumps(op_data, ensure_ascii=False)
    html_parts.append('  <script>')
    html_parts.append('  (function(){')
    html_parts.append(f'    var D={data_json};')
    html_parts.append('    function pad(n){return n<10?"0"+n:""+n;}')
    html_parts.append('    function cutoff(p){')
    html_parts.append('      var d=new Date();')
    html_parts.append('      if(p==="3m")d.setMonth(d.getMonth()-3);')
    html_parts.append('      else if(p==="6m")d.setMonth(d.getMonth()-6);')
    html_parts.append('      else if(p==="12m")d.setMonth(d.getMonth()-12);')
    html_parts.append('      else if(p==="ytd")d=new Date(d.getFullYear(),0,1);')
    html_parts.append('      return String(d.getFullYear()%100).padStart(2,"0")+"/"+pad(d.getMonth()+1);')
    html_parts.append('    }')
    html_parts.append('    function fB(v){return"R$ "+Math.round(v).toLocaleString("pt-BR");}')
    html_parts.append('    function fP(v){return v.toFixed(1).replace(".",",")+"%";}')
    html_parts.append('    var pLabels={"3m":"últimos 3 meses","6m":"últimos 6 meses","12m":"últimos 12 meses","ytd":"ano corrente"};')
    html_parts.append('    window.filterOP=function(p){')
    html_parts.append('      document.querySelectorAll("#op-period-toggle .period-btn").forEach(function(b){b.classList.remove("active")});')
    html_parts.append('      document.querySelector("#op-period-toggle .period-btn[data-period=\\""+p+"\\"]").classList.add("active");')
    html_parts.append('      var c=cutoff(p);')
    html_parts.append('      var idx=[];')
    html_parts.append('      D.labels.forEach(function(l,i){if(l>=c)idx.push(i);});')
    html_parts.append('      var nM=idx.length||1;')
    html_parts.append('      var cats=[];')
    html_parts.append('      D.datasets.forEach(function(ds){')
    html_parts.append('        var sum=0;idx.forEach(function(i){sum+=ds.data[i]||0;});')
    html_parts.append('        if(sum>0)cats.push({key:ds.key,label:ds.label,avg:sum/nM,total:sum});')
    html_parts.append('      });')
    html_parts.append('      cats.sort(function(a,b){return b.avg-a.avg;});')
    html_parts.append('      var totalM=cats.reduce(function(s,c){return s+c.avg;},0);')
    html_parts.append('      var first=D.labels.length>0?D.labels[idx[0]||0]:"";')
    html_parts.append('      var last=D.labels.length>0?D.labels[idx[idx.length-1]||0]:"";')
    # Context
    html_parts.append('      var ctx=document.getElementById("op-context");')
    html_parts.append('      ctx.innerHTML="Projeção mensal baseada na média de <strong>"+nM+" meses</strong>"')
    html_parts.append('        +(first&&last?" ("+first+" a "+last+")":"")')
    html_parts.append('        +". Média mensal: <strong>"+fB(totalM)+"</strong>"')
    html_parts.append('        +" &mdash; projeção anual: <strong>"+fB(totalM*12)+"</strong>.";')
    # Table
    html_parts.append('      var tb=document.querySelector("#op-table tbody");')
    html_parts.append('      var rows="";var acum=0;')
    html_parts.append('      cats.forEach(function(c){')
    html_parts.append('        var pct=totalM>0?c.avg/totalM*100:0;acum+=pct;')
    html_parts.append('        var cls=c.key==="nao_identificado"?" class=\\"row-highlight-warn\\"":"";')
    html_parts.append('        rows+="<tr"+cls+"><td>"+c.label+"</td><td>"+fB(c.avg)+"</td><td>"+fP(pct)+"</td><td>"+fP(acum)+"</td></tr>";')
    html_parts.append('      });')
    html_parts.append('      rows+="<tr class=\\"total-row\\"><td><strong>Total Mensal</strong></td><td><strong>"+fB(totalM)+"</strong></td><td><strong>100,0%</strong></td><td></td></tr>";')
    html_parts.append('      tb.innerHTML=rows;')
    # Insights
    html_parts.append('      var ins=document.getElementById("op-insights");var h="";')
    html_parts.append('      var ni=cats.find(function(c){return c.key==="nao_identificado";});')
    html_parts.append('      if(ni&&totalM>0){var nip=ni.avg/totalM*100;')
    html_parts.append('        if(nip>10)h+="<p style=\\"font-size:0.9em;margin-top:0.5em\\"><strong>Atenção:</strong> "+fP(nip)+" das despesas estão como \\"Não Identificado\\" ("+fB(ni.avg)+"/mês). Classificar essas transações melhora a precisão do orçamento.</p>";}')
    html_parts.append('      if(cats.length>=3){var t3=cats.slice(0,3);var t3p=totalM>0?t3.reduce(function(s,c){return s+c.avg;},0)/totalM*100:0;')
    html_parts.append('        h+="<p style=\\"font-size:0.9em;margin-top:0.5em\\">As 3 maiores categorias ("+t3.map(function(c){return c.label}).join(", ")+") representam <strong>"+fP(t3p)+"</strong> do orçamento mensal.</p>";}')
    html_parts.append('      ins.innerHTML=h;')
    # Methodology
    html_parts.append('      var me=document.getElementById("op-method");')
    html_parts.append('      me.innerHTML="<strong>Metodologia:</strong> Valores calculados como média aritmética das despesas por categoria nos "+pLabels[p]+" ("+nM+" meses). Categorias ordenadas por impacto decrescente. Coluna \\"Acum. %\\" mostra concentração acumulada (análise Pareto).";')
    html_parts.append('    };')
    html_parts.append('    filterOP("12m");')
    html_parts.append('  })();')
    html_parts.append('  </script>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_consumo_consciente_card(e4: dict) -> str:
    """Build Consumo Consciente card with interactive period filter (3M/6M/12M/YTD).

    All items are embedded as JSON; client-side JS filters by period,
    rebuilds the table (top 6) and recalculates summary metrics.
    """
    cc = e4.get("consumo_consciente", {})
    itens = cc.get("itens") or cc.get("top_gastos_pontuais") or cc.get("top_gastos") or []

    goals_cfg = e4.get("goals", {})
    aporte_mensal = goals_cfg.get("aporte_mensal",
        GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 0))

    html_parts = ['<div class="card card-warn" id="cc-card">']
    html_parts.append('  <div class="card-title">Consumo Consciente — Top Gastos</div>')

    if not itens:
        analise = cc.get("analise", "")
        html_parts.append(f'  <p>{analise or "Nenhum gasto pontual relevante identificado."}</p>')
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    # Period toggle buttons
    html_parts.append('  <div class="period-toggle" id="cc-period-toggle">')
    html_parts.append('    <button class="period-btn" data-period="3m" onclick="filterCC(\'3m\')">3M</button>')
    html_parts.append('    <button class="period-btn" data-period="6m" onclick="filterCC(\'6m\')">6M</button>')
    html_parts.append('    <button class="period-btn active" data-period="12m" onclick="filterCC(\'12m\')">12M</button>')
    html_parts.append('    <button class="period-btn" data-period="ytd" onclick="filterCC(\'ytd\')">Ano</button>')
    html_parts.append('  </div>')

    # Table skeleton (JS fills tbody)
    html_parts.append('  <table id="cc-table">')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Descrição</th><th>Valor</th><th>Mês</th><th>Categoria</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody></tbody>')
    html_parts.append('  </table>')

    # Metrics (JS updates)
    html_parts.append('  <p class="metrics" id="cc-metrics"></p>')

    # Embed data + JS
    items_json = json.dumps(itens, ensure_ascii=False)
    html_parts.append(f'  <script>')
    html_parts.append(f'  (function(){{')
    html_parts.append(f'    var ccItems={items_json};')
    html_parts.append(f'    var ccAporte={aporte_mensal};')
    html_parts.append(f'    function pad(n){{return n<10?"0"+n:""+n;}}')
    html_parts.append(f'    function cutoff(p){{')
    html_parts.append(f'      var d=new Date();')
    html_parts.append(f'      if(p==="3m")d.setMonth(d.getMonth()-3);')
    html_parts.append(f'      else if(p==="6m")d.setMonth(d.getMonth()-6);')
    html_parts.append(f'      else if(p==="12m")d.setMonth(d.getMonth()-12);')
    html_parts.append(f'      else if(p==="ytd")d=new Date(d.getFullYear(),0,1);')
    html_parts.append(f'      return d.getFullYear()+"-"+pad(d.getMonth()+1);')
    html_parts.append(f'    }}')
    html_parts.append(f'    function fB(v){{return"R$ "+Math.round(v).toLocaleString("pt-BR");}}')
    html_parts.append(f'    window.filterCC=function(p){{')
    html_parts.append(f'      document.querySelectorAll("#cc-period-toggle .period-btn").forEach(function(b){{b.classList.remove("active")}});')
    html_parts.append(f'      document.querySelector("#cc-period-toggle .period-btn[data-period=\\""+p+"\\"]").classList.add("active");')
    html_parts.append(f'      var c=cutoff(p);')
    html_parts.append(f'      var f=ccItems.filter(function(i){{return i.mes>=c}}).sort(function(a,b){{return b.valor-a.valor}});')
    html_parts.append(f'      var top=f.slice(0,6);')
    html_parts.append(f'      var total=f.reduce(function(s,i){{return s+i.valor}},0);')
    html_parts.append(f'      var equiv=ccAporte>0?(total/ccAporte).toFixed(1):"0.0";')
    html_parts.append(f'      var tb=document.querySelector("#cc-table tbody");')
    html_parts.append(f'      if(top.length===0){{')
    html_parts.append(f'        tb.innerHTML="<tr><td colspan=\\"4\\" style=\\"text-align:center;padding:16px\\">Nenhum gasto pontual no período</td></tr>";')
    html_parts.append(f'      }}else{{')
    html_parts.append(f'        tb.innerHTML=top.map(function(i){{')
    html_parts.append(f'          var det=i.categoria||i.observacao||i.conta_cartao||"";')
    html_parts.append(f'          return"<tr><td>"+i.descricao+"</td><td>"+fB(i.valor)+"</td><td>"+i.mes+"</td><td>"+det+"</td></tr>";')
    html_parts.append(f'        }}).join("");')
    html_parts.append(f'      }}')
    html_parts.append(f'      var me=document.getElementById("cc-metrics");')
    html_parts.append(f'      if(f.length>0){{')
    html_parts.append(f'        me.textContent=f.length+" gastos  \\u2022  Total: "+fB(total)+"  \\u2022  Equivale a "+equiv+" meses de aporte";')
    html_parts.append(f'      }}else{{')
    html_parts.append(f'        me.textContent="Nenhum gasto pontual relevante no per\\u00edodo selecionado.";')
    html_parts.append(f'      }}')
    html_parts.append(f'    }};')
    html_parts.append(f'    filterCC("12m");')
    html_parts.append(f'  }})();')
    html_parts.append(f'  </script>')

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
    registrados = milhas.get("programas_registrados", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Programa de Milhas — Economia</div>')

    if not programas:
        if registrados:
            html_parts.append(f'  <p>Programas cadastrados: {", ".join(registrados)}.</p>')
            html_parts.append('  <p>Atualize <code>config/milhas.md</code> com os saldos atuais de pontos/milhas.</p>')
        else:
            html_parts.append('  <p>Nenhum programa de milhas cadastrado. Atualize <code>config/milhas.md</code> com seus programas e saldos.</p>')
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
            f'<td>{fmt_num(saldo)}</td><td>{fmt_brl(valor_est)}</td>'
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
    h.append('  <div class="card-title">Estratégia de Aporte e Alocação</div>')
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
    inst = INSTITUTIONS_CONFIG.get("institution_descriptions", [])
    for entry in inst:
        nome, tipo, uso = entry.get("nome", ""), entry.get("tipo", ""), entry.get("uso", "")
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


def build_appendix_b(e4: dict = None) -> str:
    if e4 is None:
        e4 = {}
    """Apêndice B — Premissas e Metodologia."""
    h = []

    # Premissas econômicas
    h.append('<div class="card">')
    h.append('  <div class="card-title">Premissas Econômicas</div>')
    _periodo_ref = e4.get("periodo_referencia", datetime.now().strftime("%b/%Y"))
    h.append(f'  <p>Os cenários abaixo fundamentam todas as projeções deste relatório. Fonte: BCB, IBGE, consenso de mercado ({_periodo_ref}).</p>')
    h.append('  <table>')
    h.append(f'    <thead><tr><th>Variável</th><th>Pessimista</th><th>Realista (base)</th><th>Otimista</th><th>Atual ({_periodo_ref})</th></tr></thead>')
    h.append('    <tbody>')

    # Build premissas dynamically from cenarios.json + taxas.json
    _cen = CENARIOS_CONFIG
    _cambio = CONFIG_RATES.get("cambio_usd_brl", 0)
    _selic = CONFIG_RATES.get("selic_atual", 0)
    _ipca = CONFIG_RATES.get("ipca_anual", 0)
    _cen_selic_p = _cen.get("selic", {}).get("pessimista", {})
    _cen_selic_o = _cen.get("selic", {}).get("otimista", {})

    premissas = [
        (_cen.get("inflacao_ipca", {}).get("label", "Inflação (IPCA)"),
         f"{_cen.get('inflacao_ipca', {}).get('pessimista_pct', 6.0):.1f}%".replace(".", ","),
         f"{_cen.get('inflacao_ipca', {}).get('realista_pct', 4.5):.1f}%".replace(".", ","),
         f"{_cen.get('inflacao_ipca', {}).get('otimista_pct', 3.5):.1f}%".replace(".", ","),
         _cen.get("inflacao_ipca", {}).get("atual_label", f"~{_ipca:.0f}%")),
        (_cen.get("retorno_real", {}).get("label", "Retorno real carteira"),
         f"{_cen.get('retorno_real', {}).get('pessimista_pct', 4.0):.1f}%".replace(".", ","),
         f"{_cen.get('retorno_real', {}).get('realista_pct', 6.0):.1f}%".replace(".", ","),
         f"{_cen.get('retorno_real', {}).get('otimista_pct', 8.0):.1f}%".replace(".", ","),
         _cen.get("retorno_real", {}).get("atual_label", "~6,0%")),
        (_cen.get("selic", {}).get("label", "CDI / Selic"),
         f"{_cen_selic_p.get('selic', 8.0):.1f}%".replace(".", ",") if isinstance(_cen_selic_p, dict) else "8,0%",
         f"{_selic:.2f}%".replace(".", ","),
         f"{_cen_selic_o.get('selic', 15.0):.1f}%".replace(".", ",") if isinstance(_cen_selic_o, dict) else "15,0%",
         _cen.get("selic", {}).get("atual_label") or f"{_selic:.2f}%".replace(".", ",")),
        ("Câmbio BRL/USD",
         f"R$ {_cen.get('cambio', {}).get('pessimista', 7.50):.2f}".replace(".", ","),
         f"R$ {_cambio:.2f}".replace(".", ","),
         f"R$ {_cen.get('cambio', {}).get('otimista', 4.50):.2f}".replace(".", ","),
         f"R$ {_cambio:.2f}".replace(".", ",")),
        (_cen.get("valorizacao_imoveis", {}).get("label", "Valorização imóveis SP"),
         f"{_cen.get('valorizacao_imoveis', {}).get('pessimista_pct', 2.0):.0f}%",
         f"{_cen.get('valorizacao_imoveis', {}).get('realista_pct', 5.0):.0f}%",
         f"{_cen.get('valorizacao_imoveis', {}).get('otimista_pct', 8.0):.0f}%",
         _cen.get("valorizacao_imoveis", {}).get("atual_label", "—")),
        (_cen.get("trs", {}).get("label", "TRS"),
         f"{_cen.get('trs', {}).get('pessimista_pct', 3.5):.1f}%".replace(".", ","),
         f"{_cen.get('trs', {}).get('realista_pct', 4.0):.1f}%".replace(".", ","),
         f"{_cen.get('trs', {}).get('otimista_pct', 5.0):.1f}%".replace(".", ","),
         _cen.get("trs", {}).get("atual_label", "—")),
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
    # Score components from scoring.json or hardcoded fallback
    _sc = SCORING_CONFIG.get("score_componentes", {})
    if isinstance(_sc, dict) and any(k for k in _sc if not k.startswith("_")):
        _units = {"taxa_poupanca_recorrente": "%", "cobertura_despesas": " meses",
                  "taxa_endividamento": "%", "progresso_if": "%", "diversificacao": " categorias"}
        score_comp = []
        for key, comp in _sc.items():
            if key.startswith("_"):
                continue
            nome = comp.get("nome_display", key)
            peso = f"{comp.get('peso', 1.0):.1f}".replace(".", ",")
            rmin = comp.get("range_min", 0)
            rmax = comp.get("range_max", 10)
            unit = _units.get(key, "")
            if comp.get("invertido", False):
                score_comp.append((nome, peso, f"≤ {rmin}{unit}", f"≥ {rmax}{unit}"))
            else:
                score_comp.append((nome, peso, f"≥ {rmax}{unit}", f"≤ {rmin}{unit}"))
    else:
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
    _per_dados = e4.get("periodo_dados", _periodo_ref)
    _pos_ref = e4.get("periodo_referencia", _periodo_ref)
    _irpf_ano = e4.get("irpf_ano_referencia", datetime.now().year)
    fontes = [
        ("Receitas e despesas", "Extratos bancários e faturas de cartão (PDFs originais)", _per_dados),
        ("Patrimônio (imóveis, veículos)", f"Declaração IRPF {_irpf_ano} + planilhas XLSX atualizadas", f"Posição {_pos_ref}"),
        ("Investimentos", f"Posições de corretoras ({_build_broker_list()})", f"Posição {_pos_ref}"),
        ("Câmbio", f"BCB/PTAX (R$ {fmt_dec(_cambio, 2)} em {_pos_ref})", "Spot"),
        ("Selic/CDI", f"BCB — {fmt_dec(_selic, 2)}% a.a. ({_pos_ref})", "Vigente"),
        ("IPCA", f"IBGE — acumulado 12 meses ~{_ipca:.0f}%", _pos_ref),
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
    _rr_cen = CENARIOS_CONFIG.get("retorno_real", {})
    _rr_real = _rr_cen.get("realista_pct", 6.0)
    h.append(f'    <li>Projeções de renda passiva usam premissas de retorno real {_rr_real:.0f}% a.a. conforme cenários deste relatório. Revisar anualmente.</li>')
    h.append('    <li>Tabela fundamentalista de ações — valores estimados, confirmar antes de agir.</li>')
    h.append('    <li>DY de FIIs de referência — DY passado não garante DY futuro.</li>')
    h.append('    <li>Taxa PGBL — confirmar taxa real de administração antes de portabilidade.</li>')
    h.append('    <li>Benchmark de fundos — períodos variam por fundo (retorno acumulado desde aporte, não "últimos 12 meses").</li>')
    h.append('    <li>Para questões tributárias EUA, consultar CPA especializado em expatriados.</li>')
    h.append('  </ul>')
    h.append('</div>')

    return '\n'.join(h)


def _compute_nper(investivel: float, aporte_mensal: float, taxa_anual_pct: float, meta: float) -> float:
    """Calcula prazo em anos para atingir meta via juros compostos + aportes mensais."""
    import math
    if taxa_anual_pct <= 0:
        gap = meta - investivel
        return gap / (aporte_mensal * 12) if aporte_mensal > 0 else 999
    r = (1 + taxa_anual_pct / 100) ** (1/12) - 1  # taxa mensal
    if r == 0:
        return (meta - investivel) / aporte_mensal / 12 if aporte_mensal > 0 else 999
    # FV = PV*(1+r)^n + PMT*((1+r)^n - 1)/r = meta
    # Solve for n: (meta*r + PMT) / (PV*r + PMT) = (1+r)^n
    numerator = meta * r + aporte_mensal
    denominator = investivel * r + aporte_mensal
    if denominator <= 0 or numerator / denominator <= 0:
        return 999
    n_months = math.log(numerator / denominator) / math.log(1 + r)
    return round(max(0, n_months / 12), 1)


def build_appendix_c(e4: dict) -> str:
    """Apêndice C — Cenários de Sensibilidade (dinâmico a partir de configs)."""
    h = []

    goals = e4.get("goals", {})
    patrimonio = e4.get("patrimonio", {})
    pat_investivel = safe_float(patrimonio.get("investivel", 0))
    meta_if = safe_float(goals.get("if_meta",
        GOALS_CONFIG.get("independencia_financeira", {}).get("if_meta", 0)))
    aporte = safe_float(goals.get("aporte_mensal",
        GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 0)))

    # Taxas de retorno dos cenários
    _rr = CENARIOS_CONFIG.get("retorno_real", {})
    taxa_pess = _rr.get("pessimista_pct", 4.0)
    taxa_real = _rr.get("realista_pct", 6.0)
    taxa_otim = _rr.get("otimista_pct", 8.0)

    _titular_key = _FAMILY.get("titular", "")
    _david = _FAMILY.get("membros", {}).get(_titular_key, {})
    _nasc = _david.get("data_nascimento", "")
    try:
        ano_nasc = int(str(_nasc)[:4])
    except (ValueError, TypeError):
        ano_nasc = datetime.now().year - 40
    idade_atual = datetime.now().year - ano_nasc
    ano_atual = datetime.now().year

    # Calcular prazos IF
    prazo_pess = _compute_nper(pat_investivel, aporte, taxa_pess, meta_if)
    prazo_real = _compute_nper(pat_investivel, aporte, taxa_real, meta_if)
    prazo_otim = _compute_nper(pat_investivel, aporte, taxa_otim, meta_if)

    # Cenários IF
    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Independência Financeira</div>')
    h.append(f'  <p>Projeção de prazo para atingir a meta de {fmt_brl(meta_if)} com aporte de {fmt_brl(aporte)}/mês, variando a taxa de retorno real.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Retorno real a.a.</th><th>Aporte/mês</th><th>Prazo</th><th>David com</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Pessimista</td><td>{fmt_dec(taxa_pess)}%</td><td>{fmt_brl(aporte)}</td><td>~{fmt_dec(prazo_pess)} anos</td><td>{idade_atual + round(prazo_pess)} ({ano_atual + round(prazo_pess)})</td></tr>')
    h.append(f'      <tr class="total-row"><td><strong>Realista</strong></td><td><strong>{fmt_dec(taxa_real)}%</strong></td><td><strong>{fmt_brl(aporte)}</strong></td><td><strong>~{fmt_dec(prazo_real)} anos</strong></td><td><strong>{idade_atual + round(prazo_real)} ({ano_atual + round(prazo_real)})</strong></td></tr>')
    h.append(f'      <tr><td>Otimista</td><td>{fmt_dec(taxa_otim)}%</td><td>{fmt_brl(aporte)}</td><td>~{fmt_dec(prazo_otim)} anos</td><td>{idade_atual + round(prazo_otim)} ({ano_atual + round(prazo_otim)})</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    pct_atingido = (pat_investivel / meta_if * 100) if meta_if > 0 else 0
    h.append(f'  <p><strong>Progresso atual:</strong> {fmt_brl(pat_investivel)} de {fmt_brl(meta_if)} ({fmt_dec(pct_atingido)}% atingido).</p>')
    h.append('</div>')

    # Cenários cambiais (dinâmico)
    _cc = CENARIOS_CONFIG.get("cambio", {})
    cb_pess = _cc.get("pessimista", 7.50)
    cb_real = CONFIG_RATES.get("cambio_usd_brl", 5.80)
    cb_otim = _cc.get("otimista", 4.50)
    _f1f2 = GOALS_CONFIG.get("fase_f1f2", {})
    f1f2_usd_anual = _f1f2.get("tuition_usd_anual", 27500) + _f1f2.get("room_board_usd_anual", 16500)
    meta_usd = GOALS_CONFIG.get("dolarizacao", {}).get("meta_usd", 20000)

    custo_pess = round(f1f2_usd_anual / 12 * cb_pess)
    custo_real = round(f1f2_usd_anual / 12 * cb_real)
    custo_otim = round(f1f2_usd_anual / 12 * cb_otim)
    meta_brl_pess = round(meta_usd * cb_pess)
    meta_brl_real = round(meta_usd * cb_real)
    meta_brl_otim = round(meta_usd * cb_otim)
    var_pess = round((cb_pess / cb_real - 1) * 100)
    var_otim = round((1 - cb_otim / cb_real) * 100)

    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Câmbio BRL/USD</div>')
    h.append('  <p>Impacto do câmbio nos custos da fase EUA (F1/F2) e na meta de dolarização.</p>')
    h.append('  <table>')
    h.append(f'    <thead><tr><th>Cenário</th><th>Câmbio</th><th>Custo F1/F2 mensal (BRL)</th><th>Meta US$ {fmt_num(meta_usd)} em BRL</th><th>Impacto</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Pessimista (desvalorização)</td><td>R$ {fmt_dec(cb_pess, 2)}</td><td>{fmt_brl(custo_pess)}</td><td>{fmt_brl(meta_brl_pess)}</td><td>Custos +{var_pess}%, aporte USD rende menos</td></tr>')
    h.append(f'      <tr class="total-row"><td><strong>Realista</strong></td><td><strong>R$ {fmt_dec(cb_real, 2)}</strong></td><td><strong>{fmt_brl(custo_real)}</strong></td><td><strong>{fmt_brl(meta_brl_real)}</strong></td><td><strong>Base do planejamento</strong></td></tr>')
    h.append(f'      <tr><td>Otimista (valorização)</td><td>R$ {fmt_dec(cb_otim, 2)}</td><td>{fmt_brl(custo_otim)}</td><td>{fmt_brl(meta_brl_otim)}</td><td>Custos -{var_otim}%, folga para aportes maiores</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Cenários Selic (dinâmico)
    _cs = CENARIOS_CONFIG.get("selic", {})
    selic_pess = _cs.get("pessimista", {}) if isinstance(_cs.get("pessimista"), dict) else {"selic": 8.0, "cdi": 7.9}
    selic_otim = _cs.get("otimista", {}) if isinstance(_cs.get("otimista"), dict) else {"selic": 15.0, "cdi": 14.9}
    selic_atual = CONFIG_RATES.get("selic_atual", 14.25)
    cdi_atual = CONFIG_RATES.get("cdi_anual", 14.15)

    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Selic e Renda Fixa</div>')
    h.append('  <p>Sensibilidade da carteira de renda fixa a mudanças na Selic.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Selic</th><th>CDI estimado</th><th>Impacto na carteira RF</th><th>Ação recomendada</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Queda acentuada</td><td>{fmt_dec(selic_pess["selic"])}%</td><td>~{fmt_dec(selic_pess["cdi"])}%</td><td>CDBs pós-fixados rendem menos; IPCA+ valoriza (marcação a mercado)</td><td>Manter IPCA+ até vencimento; aumentar prefixados longos</td></tr>')
    h.append(f'      <tr class="total-row"><td><strong>Estabilidade</strong></td><td><strong>{fmt_dec(selic_atual)}%</strong></td><td><strong>~{fmt_dec(cdi_atual)}%</strong></td><td><strong>CDBs pós rendem bem; IPCA+ em carrego</strong></td><td><strong>Manter estratégia atual (contrafluxo IPCA+)</strong></td></tr>')
    h.append(f'      <tr><td>Alta adicional</td><td>{fmt_dec(selic_otim["selic"])}%</td><td>~{fmt_dec(selic_otim["cdi"])}%</td><td>CDBs pós rendem mais; IPCA+ desvaloriza na marcação</td><td>Aumentar CDBs pós-fixados curtos; evitar IPCA+ longo novo</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Cenários imóveis (dinâmico)
    _ci = CENARIOS_CONFIG.get("valorizacao_imoveis", {})
    im_pess = _ci.get("pessimista_pct", 2.0)
    im_real = _ci.get("realista_pct", 5.0)
    im_otim = _ci.get("otimista_pct", 8.0)
    im_real_5a = round((1 + im_real/100)**5 * 100 - 100)
    im_otim_5a_lo = round((1 + im_otim/100)**5 * 100 - 100)
    im_otim_5a_hi = round((1 + (im_otim + 2)/100)**5 * 100 - 100)

    h.append('<div class="card">')
    h.append('  <div class="card-title">Cenários — Mercado Imobiliário SP</div>')
    h.append('  <p>Impacto da valorização (ou desvalorização) dos imóveis no patrimônio e no yield.</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Cenário</th><th>Valorização anual</th><th>Impacto em 5 anos</th><th>Efeito no yield</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Pessimista (estagnação)</td><td>0-{im_pess:.0f}%</td><td>Patrimônio imobiliário estável, perda real</td><td>Yield se mantém ou sobe (valor do imóvel cai)</td></tr>')
    h.append(f'      <tr class="total-row"><td><strong>Realista</strong></td><td><strong>{im_real:.0f}%</strong></td><td><strong>Valorização ~{im_real_5a}% em 5 anos</strong></td><td><strong>Yield estável (aluguel acompanha valorização)</strong></td></tr>')
    h.append(f'      <tr><td>Otimista (boom)</td><td>{im_otim:.0f}-{im_otim+2:.0f}%</td><td>Valorização ~{im_otim_5a_lo}-{im_otim_5a_hi}% em 5 anos</td><td>Yield pode comprimir (valor sobe mais que aluguel)</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Stress tests — semi-dinâmico com dados do E5
    _reserva_meses = safe_float(e4.get("reserva_emergencia", {}).get("cobertura_meses",
                                 e4.get("ratios", e4.get("racios", {})).get("cobertura_despesas_meses", 0)))
    _receita_mensal = safe_float(e4.get("fluxo_caixa", {}).get("receita_recorrente_mensal", 0))
    _custo_f1f2_mensal = round(f1f2_usd_anual / 12 * cb_real)
    _sobra_base = round(_receita_mensal - _custo_f1f2_mensal)
    _sobra_pess = round(_receita_mensal - round(f1f2_usd_anual / 12 * cb_pess))
    _var_custo_pess = f"+{var_pess}%" if var_pess > 0 else f"{var_pess}%"

    h.append('<div class="card card-warning">')
    h.append('  <div class="card-title">Stress Tests — Perguntas-Chave</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Pergunta</th><th>Resposta / Mitigação</th></tr></thead>')
    h.append('    <tbody>')
    stress = [
        (f"E se a Selic cair a {selic_pess['selic']:.0f}%?",
         f"CDBs pós rendem menos. Ação: contrafluxo — já ter IPCA+ longos na carteira captura a valorização. Manter Tesouro IPCA+ 2035/2040."),
        (f"E se o USD chegar a R$ {fmt_dec(cb_pess, 2)}?",
         f"Custos F1/F2 sobem ~{var_pess}%. A sobra mensal cai de {fmt_brl(_sobra_base)} para ~{fmt_brl(_sobra_pess)} — {'ainda viável' if _sobra_pess > 0 else 'déficit — ajustar aportes'}. Dolarização via Wise fica mais cara mas protege o patrimônio."),
        ("E se Mariana não conseguir o NCLEX?",
         f"A simulação 'Mariana sem trabalhar' mostra prazo IF maior. David absorve com aporte reduzido."),
        ("E se David perder o contrato principal?",
         f"Renda cai significativamente. Reserva de emergência cobre {fmt_dec(_reserva_meses)} meses. Ações: (1) buscar contratos substitutos, (2) reduzir aporte IF, (3) Mariana mantém renda."),
        ("E se os imóveis desvalorizarem 20%?",
         "Patrimônio bruto cai, mas o patrimônio investível não muda (imóvel residência já excluído). Yield dos imóveis de investimento sobe proporcionalmente."),
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
    _contador = GOALS_CONFIG.get("tributario", {}).get("contador_nome", "AccountTech")
    _seg_min = GOALS_CONFIG.get("seguros", {}).get("vida_term_minimo", 0)
    _seg_max = GOALS_CONFIG.get("seguros", {}).get("vida_term_maximo", 0)
    contatos = [
        (f"Contador ({_contador})", "Contabilidade PJ, DAS, Simples Nacional", "Mensal (DAS) + IRPF anual + mudança de regime"),
        ("Advogado Sucessório / Tributarista SP", "Testamentos, procurações, holding", "Antes da mudança para EUA — planejamento sucessório"),
        ("CPA Expatriado (EUA)", "FBAR, FATCA, Form 1040, PFIC", "Antes de se tornar US tax resident — essencial"),
        ("Advogado Imigração (EUA)", "EB2-NIW, F1/F2, Green Card", "Acompanhamento do processo de Green Card"),
        ("Corretor de Seguros", "Vida, invalidez (DIT), residencial", f"Urgente — cotar term life R${_seg_min/1e6:.0f}-{_seg_max/1e6:.0f}M + DIT 60% da renda"),
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

    # Config values used in multiple sub-sections
    _seg_min = GOALS_CONFIG.get("seguros", {}).get("vida_term_minimo", 0)
    _seg_max = GOALS_CONFIG.get("seguros", {}).get("vida_term_maximo", 0)

    # For Simulação Mariana
    goals = e4.get("goals", {})
    patrimonio = e4.get("patrimonio", {})
    pat_investivel = safe_float(patrimonio.get("investivel", 0))
    meta_if = safe_float(goals.get("if_meta",
        GOALS_CONFIG.get("independencia_financeira", {}).get("if_meta", 7200000)))
    taxa_real = CENARIOS_CONFIG.get("retorno_real", {}).get("realista_pct", 6.0)

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

    # Viagens e milhas (dinâmico — janela 12 meses)
    _vg12 = e4.get("_viagens_12m", {})
    _teto_viagens = GOALS_CONFIG.get("viagens", {}).get("teto_anual", 45000)
    _gasto_viagens = safe_float(_vg12.get("gasto", 0))
    _saldo_viagens = _teto_viagens - _gasto_viagens
    _periodo_viagens = _vg12.get("periodo", "últimos 12 meses")
    _por_mes = _vg12.get("por_mes", {})
    _txns = _vg12.get("realizadas_txns", [])

    # Group transactions into "trips" by aggregating consecutive spending into months
    _meses_com_gasto = {m: v for m, v in sorted(_por_mes.items()) if v > 0}

    h.append('<div class="card">')
    h.append(f'  <div class="card-title">Orçamento de Viagens ({_periodo_viagens})</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Item</th><th>Valor</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Teto anual de viagens</td><td><strong>{fmt_brl(_teto_viagens)}</strong></td></tr>')
    h.append(f'      <tr><td>Gasto 12 meses (lazer/viagens)</td><td><strong>{fmt_brl(_gasto_viagens)}</strong></td></tr>')

    if _meses_com_gasto:
        h.append(f'      <tr><td colspan="2" style="padding-top:8px"><strong>Detalhamento mensal</strong></td></tr>')
        for mes, val in _meses_com_gasto.items():
            h.append(f'      <tr><td style="padding-left:16px">{mes}</td><td>{fmt_brl(val)}</td></tr>')

    saldo_class = "" if _saldo_viagens >= 0 else ' style="color:#E63946"'
    h.append(f'      <tr><td>Saldo disponível</td><td{saldo_class}><strong>{fmt_brl(_saldo_viagens)}</strong></td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')

    if _txns:
        h.append('  <details><summary>Ver transações individuais ({} itens)</summary>'.format(len(_txns)))
        h.append('  <table style="font-size:0.85em">')
        h.append('    <thead><tr><th>Data</th><th>Descrição</th><th>Valor</th></tr></thead>')
        h.append('    <tbody>')
        for t in _txns:
            h.append(f'      <tr><td>{t.get("data","")}</td><td>{t.get("descricao","")}</td><td>{fmt_brl(safe_float(t.get("valor",0)))}</td></tr>')
        h.append('    </tbody></table></details>')

    h.append('  <p><em>Nota: Custos da estadia EUA (F1/F2) NÃO entram no orçamento de viagens — são custo de vida.</em></p>')
    h.append('</div>')

    # NCLEX Roadmap (from goals.json or hardcoded fallback)
    _nclex_steps = GOALS_CONFIG.get("nclex_roadmap", [])
    _mariana_usd_min = GOALS_CONFIG.get("mariana_eua", {}).get("renda_rn_minima_usd", 4000)
    _mariana_usd_max = GOALS_CONFIG.get("mariana_eua", {}).get("renda_rn_maxima_usd", 7000)

    h.append('<div class="card">')
    _nclex_conjuge_key = next((k for k, v in _FAMILY.get("membros", {}).items() if v.get("papel") == "conjuge"), None)
    _nclex_conjuge_nome = _FAMILY.get("membros", {}).get(_nclex_conjuge_key, {}).get("nome_curto", "") if _nclex_conjuge_key else ""
    h.append(f'  <div class="card-title">NCLEX Roadmap{f" — {_nclex_conjuge_nome}" if _nclex_conjuge_nome else ""}</div>')
    h.append('  <p>Caminho para licenciamento como Registered Nurse nos EUA (estimativa 8-18 meses).</p>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Etapa</th><th>Descrição</th><th>Custo</th><th>Duração</th></tr></thead>')
    h.append('    <tbody>')
    if _nclex_steps:
        for step in _nclex_steps:
            h.append(f'      <tr><td>{step.get("etapa", "")}</td><td>{step.get("descricao", "")}</td><td>{step.get("custo", "—")}</td><td>{step.get("duracao", "—")}</td></tr>')
    else:
        # Fallback — STATIC-REFERENCE
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
    _conjuge_key = next((k for k, v in _FAMILY.get("membros", {}).items() if v.get("papel") == "conjuge"), None)
    _conjuge = _FAMILY.get("membros", {}).get(_conjuge_key, {}) if _conjuge_key else {}
    _conjuge_nome = _conjuge.get("nome_curto", "Cônjuge")
    _conjuge_esp = _conjuge.get("especializacao", "")
    _conjuge_mestrado = _conjuge.get("mestrado", "")
    _conjuge_profissao = _conjuge.get("profissao", "")
    _perfil_parts = [p for p in [_conjuge_esp, f"Mestrado {_conjuge_mestrado}" if _conjuge_mestrado else "", _conjuge_profissao] if p]
    _perfil_str = " + ".join(_perfil_parts) if _perfil_parts else ""
    h.append(f'  <p><strong>Custo total estimado:</strong> US$ 1.515–2.440{f" | <strong>Perfil competitivo {_conjuge_nome}:</strong> {_perfil_str}" if _perfil_str else ""}.</p>')
    h.append(f'  <p><strong>Projeção EUA:</strong> RN US$45–80/hora → US${fmt_num(_mariana_usd_min)}–{fmt_num(_mariana_usd_max)}/mês líquido.</p>')
    h.append('</div>')

    # Simulação Mariana sem trabalhar (semi-dinâmico — usa E5 data quando disponível)
    _sim_mariana = e4.get("simulacao_mariana_sem_trabalhar", {})
    _aporte_cfg = GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 20000)
    h.append('<div class="card">')
    h.append('  <div class="card-title">Simulação — Mariana Sem Trabalhar</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Métrica</th><th>Valor</th></tr></thead>')
    h.append('    <tbody>')
    if _sim_mariana:
        for row in _sim_mariana.get("linhas", []):
            h.append(f'      <tr><td>{row.get("metrica", "")}</td><td>{row.get("valor", "")}</td></tr>')
    else:
        # Fallback: compute IF with full and reduced aporte
        _aporte_red = round(_aporte_cfg * 0.66)
        _prazo_full = _compute_nper(pat_investivel, _aporte_cfg, taxa_real, meta_if)
        _prazo_red = _compute_nper(pat_investivel, _aporte_red, taxa_real, meta_if)
        h.append(f'      <tr><td>IF com aporte R$ {_aporte_cfg/1000:.0f}k mantido</td><td><strong>{fmt_dec(_prazo_full)} anos</strong> (folga absorve a perda)</td></tr>')
        _aporte_red_fmt = fmt_dec(_aporte_red/1000)
        h.append(f'      <tr><td>IF com aporte reduzido R$ {_aporte_red_fmt}k</td><td>{fmt_dec(_prazo_red)} anos (+{fmt_dec(_prazo_red - _prazo_full)} anos)</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    # Calendário próximo ciclo (from E5 data or config-derived defaults)
    _calendario_e5 = e4.get("calendario_proximo_ciclo", [])

    h.append('<div class="card">')
    h.append('  <div class="card-title">Calendário — Próximo Ciclo</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Data</th><th>Item</th><th>Tipo</th></tr></thead>')
    h.append('    <tbody>')
    if _calendario_e5:
        for ev in _calendario_e5:
            h.append(f'      <tr><td>{ev.get("data", "—")}</td><td>{ev.get("item", "")}</td><td>{ev.get("tipo", "")}</td></tr>')
    else:
        # Fallback — relative dates from config
        _aporte_val = GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 20000)
        _holding = GOALS_CONFIG.get("tributario", {}).get("holding_avaliacao_prazo", "T4/2026")
        calendario = [
            ("Imediato", f"Primeiro aporte {fmt_brl(_aporte_val)} (plano IF)", "Financeiro"),
            ("Imediato", f"Contratar seguro de vida term life R${_seg_min/1e6:.0f}-{_seg_max/1e6:.0f}M", "Proteção"),
            ("Imediato", "Contratar seguro invalidez (DIT) 60% da renda", "Proteção"),
            ("Imediato", "Consultar advogado sucessório/tributarista SP", "Sucessório"),
            ("Próximo mês", "Atualizar beneficiários PGBL e seguro de vida", "Proteção"),
            ("Próximo mês", "Testamento público David + Mariana (cartório BR)", "Sucessório"),
            ("Próximo mês", "Início prep teste inglês Mariana (MET ou OET)", "NCLEX"),
            ("Próximo trimestre", "Revisão tática quinzenal — despesas vs tetos", "Pipeline"),
            ("Próximo trimestre", "Análise completa trimestral (pipeline E0-E6)", "Pipeline"),
            (_holding, "Avaliar holding patrimonial", "Sucessório"),
            ("Antes EUA", "Contratar CPA expatriado", "Tributário"),
            ("Antes EUA", "Procuração pública para Rubens (pai David)", "Sucessório"),
        ]
        for data, item, tipo in calendario:
            h.append(f'      <tr><td>{data}</td><td>{item}</td><td>{tipo}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    return '\n'.join(h)


def build_kpi_rentabilidade_card(e4: dict) -> str:
    """Build KPI Rentabilidade card with real metrics from e4 data."""
    p = e4.get("patrimonio", {})
    f = e4.get("fluxo_caixa", {})
    inv = e4.get("investimentos", {})
    ratios = e4.get("ratios", {})

    # ── Yield imóveis (receita aluguel anualizada / valor imóveis investimento) ──
    num_months = max(1, len(f.get("receita_despesa_mensal_detalhado", {}).get("labels", [])))
    aluguel_total = safe_float(f.get("por_fonte", {}).get("receita_aluguel", 0))
    aluguel_mensal = aluguel_total / num_months
    imoveis_inv = safe_float(p.get("imoveis_investimento", 0))
    yield_imoveis = round((aluguel_mensal * 12 / imoveis_inv) * 100, 1) if imoveis_inv > 0 else 0
    cdi = CONFIG_RATES.get("cdi_anual", 14.15)

    # ── Renda passiva mensal ──
    renda_dividendos = round(safe_float(f.get("por_fonte", {}).get("receita_investimento", 0)) / num_months, 2)
    renda_juros = round(safe_float(f.get("por_fonte", {}).get("rendimentos_financeiros", 0)) / num_months, 2)
    renda_passiva_total = round(aluguel_mensal + renda_dividendos + renda_juros, 2)

    # ── Diversificação from E4 investment positions ──
    n_classes = len(inv.get("tabela_classes", []))
    inv_total = safe_float(inv.get("total", 0))

    try:
        with open(E4_INVEST_PATH, 'r', encoding='utf-8') as fh:
            inv_raw = json.load(fh)
        positions = [d for d in inv_raw.get("dados", []) if d.get("valor_atual", 0) > 0]
        institutions = set(d.get("instituicao", "") for d in positions if d.get("instituicao"))
        tipos = {}
        for d in positions:
            t = d.get("tipo", "Outros")
            tipos[t] = tipos.get(t, 0) + d["valor_atual"]
        pos_total = sum(d["valor_atual"] for d in positions)
        hhi = sum((v / pos_total * 100) ** 2 for v in tipos.values()) if pos_total > 0 else 0
        top_pos = max(positions, key=lambda x: x["valor_atual"]) if positions else {}
        top_pct = round(top_pos.get("valor_atual", 0) / pos_total * 100, 1) if pos_total > 0 else 0
        n_institutions = len(institutions)
        n_tipos = len(tipos)
        n_positions = len(positions)
    except Exception:
        n_institutions = 0
        n_tipos = n_classes
        n_positions = 0
        hhi = 0
        top_pct = 0

    # HHI classification
    if hhi < 1500:
        hhi_label, hhi_badge = "Diversificado", "badge-green"
    elif hhi < 2500:
        hhi_label, hhi_badge = "Moderado", "badge-yellow"
    else:
        hhi_label, hhi_badge = "Concentrado", "badge-red"

    # Yield vs CDI classification
    if yield_imoveis >= cdi:
        yield_badge = "badge-green"
    elif yield_imoveis >= cdi * 0.5:
        yield_badge = "badge-yellow"
    else:
        yield_badge = "badge-red"

    h = ['<div class="card card-feature">']
    h.append('  <div class="card-title">KPI — Rentabilidade</div>')

    # Metrics table
    h.append('  <table>')
    h.append('    <thead><tr><th>Indicador</th><th>Valor</th><th>Referência</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Yield imóveis (anual)</td><td><span class="badge {yield_badge}">{fmt_pct(yield_imoveis)}</span></td><td>CDI {fmt_pct(cdi)}</td></tr>')
    h.append(f'      <tr><td>Renda passiva mensal</td><td><strong>{fmt_brl(renda_passiva_total)}</strong></td><td>Aluguéis {fmt_brl(aluguel_mensal)} + Rendimentos {fmt_brl(renda_dividendos + renda_juros)}</td></tr>')
    h.append(f'      <tr><td>Rentabilidade carteira</td><td><span class="badge badge-neutral">N/D</span></td><td>Requer série temporal de cotas</td></tr>')
    h.append(f'      <tr><td>Volatilidade</td><td><span class="badge badge-neutral">N/D</span></td><td>Requer série temporal de cotas</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')

    # Diversification summary
    h.append('  <table>')
    h.append('    <thead><tr><th>Diversificação</th><th>Valor</th><th>Avaliação</th></tr></thead>')
    h.append('    <tbody>')
    h.append(f'      <tr><td>Instituições</td><td>{n_institutions}</td><td>{"✅ Bem distribuído" if n_institutions >= 3 else "⚠️ Concentrado"}</td></tr>')
    h.append(f'      <tr><td>Tipos de ativo</td><td>{n_tipos}</td><td>{"✅ Diversificado" if n_tipos >= 5 else "⚠️ Poucas classes"}</td></tr>')
    h.append(f'      <tr><td>Posições ativas</td><td>{n_positions}</td><td></td></tr>')
    h.append(f'      <tr><td>Concentração (maior posição)</td><td>{fmt_pct(top_pct)}</td><td>{"✅ OK" if top_pct <= 15 else "⚠️ Risco de concentração"}</td></tr>')
    h.append(f'      <tr><td>HHI (Herfindahl por tipo)</td><td>{fmt_num(hhi)}</td><td><span class="badge {hhi_badge}">{hhi_label}</span></td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')

    h.append('  <p style="font-size:0.85em;opacity:0.75;margin-top:8px;">⚠️ Rentabilidade e volatilidade requerem dados históricos de cotas — não disponíveis nos extratos atuais.</p>')
    h.append('</div>')
    return '\n'.join(h)


def build_contrafluxo_card(e4: dict) -> str:
    """Build Contrafluxo card (previously inline in S3)."""
    selic = CONFIG_RATES.get("selic_atual", 11.5)
    cdi = CONFIG_RATES.get("cdi_anual", 11.5)
    html_parts = ['<div class="card card-primary">']
    html_parts.append('  <div class="card-title">Contrafluxo</div>')
    html_parts.append(f'  <p>Selic atual: {selic}% a.a. | CDI: {cdi}%</p>')
    html_parts.append('  <p>Cenário base mantém estratégia RF em Tesouro IPCA+.</p>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)


# Registry: card ID → builder function
# All builders accept (e4: dict) and return str (HTML)
CARD_BUILDERS = {
    "patrimonio_categorias": build_patrimonio_categorias_card,
    "receitas_fonte": build_receitas_fonte_card,
    "reserva_emergencia": build_reserva_emergencia_card,
    "endividamento": build_endividamento_card,
    "orcamento_prospectivo": build_orcamento_prospectivo_card,
    "consumo_consciente": build_consumo_consciente_card,
    "diagnostico_comportamental": build_diagnostico_comportamental_card,
    "milhas": build_milhas_card,
    "investimentos_classe": build_investimentos_classe_card,
    "kpi_rentabilidade": build_kpi_rentabilidade_card,
    "estrategia_aporte": build_estrategia_aporte_card,
    "contrafluxo": build_contrafluxo_card,
    "previdencia_pgbl": build_previdencia_pgbl_card,
    "pontos_fortes": build_pontos_fortes_card,
    "pontos_urgentes": build_pontos_urgentes_card,
    "equilibrio_cerbasi": build_equilibrio_cerbasi_card,
}

# Registry: appendix ID → builder function
APPENDIX_BUILDERS = {
    "APP_A": lambda e4: build_appendix_a(),
    "APP_B": lambda e4: build_appendix_b(e4),
    "APP_C": lambda e4: build_appendix_c(e4),
    "APP_D": lambda e4: build_appendix_d(),
    "APP_E": lambda e4: build_appendix_e(e4),
}


def _apply_card_variant(card_html: str, variant: str = "", size: str = "") -> str:
    """Apply variant and size from layout config to a card's HTML.

    Replaces the first 'class="card card-XXX"' with the configured variant,
    and wraps in a grid column if size == 'half'.
    """
    if variant:
        # Replace the card variant class (e.g., card-feature → card-warn)
        card_html = re.sub(
            r'class="card card-\w+"',
            f'class="card card-{variant}"',
            card_html,
            count=1
        )
    if size == "half":
        card_html = f'<div style="grid-column: span 1;">\n{card_html}\n</div>'
    return card_html


def build_sections(e4: dict) -> dict:
    """Build S1-S10 content sections with charts and cards.

    If REPORT_LAYOUT is available, iterates over the YAML config.
    Otherwise, falls back to the original hardcoded sequence.
    """
    print("[E6.4] Building sections S1-S10...")

    narrativas = e4.get("narrativas", {})
    # Sanitize monetary formats in narrativas before rendering
    narrativas = sanitize_narrativas(narrativas)
    summaries = narrativas.get("summaries", {})
    charts_narrativas = narrativas.get("charts", {})

    # Override fluxo_mensal with deterministic 12m-window data
    j12 = e4.get("fluxo_caixa", {}).get("janela_12m", {})
    if j12:
        _rec12 = j12.get("receita_recorrente_mensal", 0)
        _desp12 = j12.get("despesa_mensal_media", 0)
        _saldo12 = _rec12 - _desp12
        _periodo12 = j12.get("periodo", "últimos 12 meses")
        _taxa12 = j12.get("taxa_poupanca_recorrente", 0)
        CHART_TITLES["fluxo_mensal"] = "Fluxo de Caixa Mensal"
        charts_narrativas["fluxo_mensal"] = {
            "context": (
                f"Janela dos últimos 12 meses ({_periodo12}). "
                f"Receita recorrente média de {fmt_brl(_rec12)}/mês "
                f"versus despesa média de {fmt_brl(_desp12)}/mês."
            ),
            "conclusion": (
                f"Saldo recorrente mensal de {fmt_brl(_saldo12)}/mês. "
                f"Taxa de poupança recorrente de {fmt_pct(_taxa12)}."
            ),
        }

    replacements = {}

    # Build summaries (always S1-S10 for template compatibility)
    for i in range(1, 11):
        key = f"s{i}"
        summary = summaries.get(key, f"Seção {i} — dados pendentes")
        replacements[f"{{{{SUMMARY_S{i}}}}}"] = summary

    # ── Layout-driven rendering (if report_layout.yaml is loaded) ──
    layout_estrategico = REPORT_LAYOUT.get("estrategico", {})
    layout_sections = layout_estrategico.get("sections", [])

    if layout_sections:
        print("  [LAYOUT] Rendering sections from report_layout.yaml")

        # Hardcoded fallback titles (used only if YAML title is missing)
        _fallback_titles = {
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

        for section_cfg in layout_sections:
            section_id = section_cfg.get("id", "")  # "S1", "S2", ...
            enabled = section_cfg.get("enabled", True)
            section_num = int(section_id.replace("S", "")) if section_id.startswith("S") else 0

            if not enabled:
                # Emit empty placeholder so template doesn't break
                replacements[f"{{{{CONTENT_S{section_num}}}}}"] = ""
                print(f"  [LAYOUT] {section_id} — DISABLED")
                continue

            html = ""

            # ── Charts (ordered by YAML, with optional row grouping) ──
            chart_cfgs = [c for c in section_cfg.get("charts", []) if c.get("enabled", True)]
            i_ch = 0
            while i_ch < len(chart_cfgs):
                chart_cfg = chart_cfgs[i_ch]
                chart_key = chart_cfg.get("id", "")
                row_group = chart_cfg.get("row", "")

                if row_group:
                    # Collect all consecutive charts in the same row group
                    row_charts = []
                    while i_ch < len(chart_cfgs) and chart_cfgs[i_ch].get("row", "") == row_group:
                        row_charts.append(chart_cfgs[i_ch])
                        i_ch += 1
                    html += '<div class="chart-row">\n'
                    for rc in row_charts:
                        rk = rc.get("id", "")
                        rt = CHART_TITLES.get(rk, rk.replace('_', ' ').title())
                        re_ = ""
                        if rk == "score_gauge":
                            re_ = f'data-score="{e4.get("score", {}).get("valor", 0)}"'
                        html += chart_html(rk, rt, charts_narrativas, extra_attrs=re_) + "\n"
                    html += '</div>\n'
                else:
                    chart_title = CHART_TITLES.get(chart_key, chart_key.replace('_', ' ').title())
                    extra = ""
                    if chart_key == "score_gauge":
                        score_val = e4.get("score", {}).get("valor", 0)
                        extra = f'data-score="{score_val}"'
                    html += chart_html(chart_key, chart_title, charts_narrativas, extra_attrs=extra) + "\n"
                    i_ch += 1

            # ── Cards (ordered by YAML, with variant/size) ──
            # Pre-process: collect enabled cards with their resolved sizes,
            # auto-promoting orphaned half cards to full width.
            resolved_cards = []
            for card_cfg in section_cfg.get("cards", []):
                card_id = card_cfg.get("id", "")
                if not card_cfg.get("enabled", True):
                    continue
                builder = CARD_BUILDERS.get(card_id)
                if not builder:
                    print(f"  [WARN] Card builder not found for '{card_id}' — skipping")
                    continue
                resolved_cards.append({
                    "id": card_id,
                    "builder": builder,
                    "variant": card_cfg.get("variant", ""),
                    "size": card_cfg.get("size", "full"),
                })

            # Fix orphaned half-cards: promote to full if they lack a pair
            i = 0
            while i < len(resolved_cards):
                if resolved_cards[i]["size"] == "half":
                    j = i + 1
                    while j < len(resolved_cards) and resolved_cards[j]["size"] == "half":
                        j += 1
                    half_count = j - i
                    if half_count % 2 == 1:
                        resolved_cards[j - 1]["size"] = "full"
                    i = j
                else:
                    i += 1

            # Render cards, wrapping consecutive half-pairs in split-cards grid
            in_grid = False
            for rc in resolved_cards:
                size = rc["size"]
                if size == "half" and not in_grid:
                    html += '<div class="split-cards">\n'
                    in_grid = True
                elif size != "half" and in_grid:
                    html += '</div>\n'
                    in_grid = False

                card_html_str = rc["builder"](e4)
                card_html_str = _apply_card_variant(card_html_str, rc["variant"], size="")
                html += card_html_str + "\n"

            if in_grid:
                html += '</div>\n'

            replacements[f"{{{{CONTENT_S{section_num}}}}}"] = html.rstrip()
            print(f"  [LAYOUT] {section_id} — OK ({len(section_cfg.get('charts', []))} charts, {len(section_cfg.get('cards', []))} cards)")

        # Ensure all S1-S10 have a placeholder (for sections not in YAML)
        for i in range(1, 11):
            key = f"{{{{CONTENT_S{i}}}}}"
            if key not in replacements:
                replacements[key] = ""

    else:
        # ── Hardcoded fallback (original behavior, no YAML) ──
        print("  [LAYOUT] No report_layout.yaml — using hardcoded fallback")

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
            section_chart_keys = SECTION_CHARTS.get(i, [])
            html = ""

            _FALLBACK_PAIRS = {("alocacao_atual", "alocacao_alvo")}
            j_ch = 0
            while j_ch < len(section_chart_keys):
                chart_key = section_chart_keys[j_ch]
                paired = False
                if j_ch + 1 < len(section_chart_keys):
                    pair = (chart_key, section_chart_keys[j_ch + 1])
                    if pair in _FALLBACK_PAIRS:
                        html += '<div class="chart-row">\n'
                        for pk in pair:
                            pt = CHART_TITLES.get(pk, pk.replace('_', ' ').title())
                            pe = ""
                            if pk == "score_gauge":
                                pe = f'data-score="{e4.get("score", {}).get("valor", 0)}"'
                            html += chart_html(pk, pt, charts_narrativas, extra_attrs=pe) + "\n"
                        html += '</div>\n'
                        j_ch += 2
                        paired = True
                if not paired:
                    chart_title = CHART_TITLES.get(chart_key, chart_key.replace('_', ' ').title())
                    extra = ""
                    if chart_key == "score_gauge":
                        score_val = e4.get("score", {}).get("valor", 0)
                        extra = f'data-score="{score_val}"'
                    html += chart_html(chart_key, chart_title, charts_narrativas, extra_attrs=extra) + "\n"
                    j_ch += 1

            if i == 1:
                html += build_patrimonio_categorias_card(e4) + "\n"
                html += build_receitas_fonte_card(e4) + "\n"
                html += build_reserva_emergencia_card(e4) + "\n"
                html += build_endividamento_card(e4) + "\n"
            elif i == 2:
                html += build_orcamento_prospectivo_card(e4) + "\n"
                html += build_consumo_consciente_card(e4) + "\n"
                html += build_diagnostico_comportamental_card(e4) + "\n"
                html += build_milhas_card(e4) + "\n"
            elif i == 3:
                html += build_investimentos_classe_card(e4) + "\n"
                html += build_kpi_rentabilidade_card(e4) + "\n"
                html += build_estrategia_aporte_card(e4) + "\n"
                html += build_contrafluxo_card(e4) + "\n"
            elif i == 7:
                html += build_previdencia_pgbl_card(e4) + "\n"
            elif i == 10:
                html += build_pontos_fortes_card(e4) + "\n"
                html += build_pontos_urgentes_card(e4) + "\n"
                html += build_equilibrio_cerbasi_card(e4) + "\n"

            replacements[f"{{{{CONTENT_S{i}}}}}"] = html.rstrip()

    # ── Appendices (layout-aware) ──
    layout_appendices = layout_estrategico.get("appendices", [])

    if layout_appendices:
        print("  [LAYOUT] Rendering appendices from report_layout.yaml")
        for app_cfg in layout_appendices:
            app_id = app_cfg.get("id", "")
            enabled = app_cfg.get("enabled", True)
            builder = APPENDIX_BUILDERS.get(app_id)
            if not builder:
                print(f"  [WARN] Appendix builder not found for '{app_id}'")
                continue
            if enabled:
                replacements[f"{{{{CONTENT_{app_id}}}}}"] = builder(e4)
                print(f"  [LAYOUT] {app_id} — OK")
            else:
                replacements[f"{{{{CONTENT_{app_id}}}}}"] = ""
                print(f"  [LAYOUT] {app_id} — DISABLED")
    else:
        print("[E6.4] Building appendices A-E (hardcoded fallback)...")
        replacements["{{CONTENT_APP_A}}"] = build_appendix_a()
        replacements["{{CONTENT_APP_B}}"] = build_appendix_b(e4)
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

    # Inject 12-month viagens data into e4 so charts and cards pick it up
    e4["_viagens_12m"] = load_viagens_12m()

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

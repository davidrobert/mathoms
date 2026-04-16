#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E6 Renderer — HTML Standalone Exporter (ADR-076 · F9)

Gera o relatório financeiro como arquivo HTML standalone autocontido.
Desde F9, este script é um **exportador** (não mais o render primário):
a visualização online vive na rota React nativa /reports/[id].

Casos de uso do standalone HTML:
  - Compartilhar com contador por e-mail
  - Backup offline para o ano fiscal
  - Imprimir sem acesso ao app

Output: /output/relatorio_financeiro_ferreira_campos_YYYYMMDD.html

Reads E5 JSON (data + narratives), report_layout.yaml (section order) e
config/templates/report_template.html. Produz HTML via string replacement.
Design tokens consumidos de config/templates/_tokens.css (gerado por
design-tokens/build.py — ADR-076).

No LLM needed. Pure data transformation.
"""

import json
import math
import re
from pathlib import Path
from datetime import datetime
import pytz
import yaml

# ============================================================================
# HELPERS
# ============================================================================

from scripts.e6.sanitize import sanitize_monetary_format, sanitize_narrativas
from scripts.e6.validate import validate_report


def safe_float(val) -> float:
    """Convert value to float, default to 0.0 if fails."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

# ============================================================================
# CONFIGURATION
# ============================================================================

_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


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


def _load_config_rates(base: Path) -> dict:
    """Carrega taxas financeiras de config ou usa defaults com warning."""
    config_path = base / "config" / "taxas.json"
    defaults = {"cambio_usd_brl": 5.0, "cdi_anual": 11.5, "selic_atual": 11.5}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            defaults.update(loaded)
        except Exception as e:
            print(f"  [WARN] Erro ao carregar config/taxas.json: {e}")
    else:
        print(f"  [WARN] config/taxas.json não encontrado — usando defaults")
    return defaults


def _load_report_layout(base: Path) -> dict:
    """Load report_layout.yaml for section/card/chart ordering and visibility."""
    layout_path = base / "config" / "report_layout.yaml"
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


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa todos os globals de path e config a partir de base_dir."""
    global BASE_DIR
    global _FAMILY, CONFIG_RATES, GOALS_CONFIG, SCORING_CONFIG, FISCAL_CONFIG
    global CENARIOS_CONFIG, INSTITUTIONS_CONFIG, PIPELINE_CONFIG
    global REPORT_LAYOUT
    global FAMILY_SOBRENOME, _TITULAR_KEY, _MEMBROS_DATA
    global TITULAR_NOME, _CONJUGE_KEY, CONJUGE_NOME, _CONJUGE_DATA
    global PAI_TITULAR, _OUTPUT_PATTERN
    global _KEY_INV_TITULAR, _KEY_INV_CONJUGE, _KEY_CENARIOS_CONJUGE
    global _DASH_CFG, _INV_BLOCOS
    global TEMPLATE_PATH, E5_JSON_PATH, E4_INVEST_PATH, E4_DESPESAS_PATH
    global E4_RECEITAS_PATH, E4_FLUXO_PATH, DEFINITIONS_PATH
    global OUTPUT_DIR, SNAPSHOT_PATH

    BASE_DIR = base_dir

    fm_path = BASE_DIR / "config" / "family_members.json"
    _FAMILY = _load_json_config(fm_path, "family_members.json") if fm_path.exists() else {}
    CONFIG_RATES = _load_config_rates(BASE_DIR)
    GOALS_CONFIG = _load_json_config(BASE_DIR / "config" / "goals.json", "goals.json")
    SCORING_CONFIG = _load_json_config(BASE_DIR / "config" / "scoring.json", "scoring.json")
    FISCAL_CONFIG = _load_json_config(BASE_DIR / "config" / "parametros_fiscais.json", "parametros_fiscais.json")
    CENARIOS_CONFIG = _load_json_config(BASE_DIR / "config" / "cenarios.json", "cenarios.json")
    INSTITUTIONS_CONFIG = _load_json_config(BASE_DIR / "config" / "institutions.json", "institutions.json")
    PIPELINE_CONFIG = _load_json_config(BASE_DIR / "config" / "pipeline.json", "pipeline.json")

    REPORT_LAYOUT = _load_report_layout(BASE_DIR)

    FAMILY_SOBRENOME = _FAMILY.get("familia", {}).get("sobrenome", "")
    _TITULAR_KEY = _FAMILY.get("titular", "")
    _MEMBROS_DATA = _FAMILY.get("membros", {})
    TITULAR_NOME = _MEMBROS_DATA.get(_TITULAR_KEY, {}).get("nome_curto", "Titular")
    _CONJUGE_KEY = next((k for k, v in _MEMBROS_DATA.items() if isinstance(v, dict) and v.get("papel") == "conjuge"), None)
    CONJUGE_NOME = _MEMBROS_DATA.get(_CONJUGE_KEY, {}).get("nome_curto", "Cônjuge") if _CONJUGE_KEY else "Cônjuge"
    _CONJUGE_DATA = _MEMBROS_DATA.get(_CONJUGE_KEY, {}) if _CONJUGE_KEY else {}
    PAI_TITULAR = _FAMILY.get("pai_titular", "")
    _OUTPUT_PATTERN = _FAMILY.get("output_filename_pattern", "relatorio_financeiro_{date}.html")

    _KEY_INV_TITULAR = f"investimentos_{_TITULAR_KEY}" if _TITULAR_KEY else "investimentos_titular"
    _KEY_INV_CONJUGE = f"investimentos_{_CONJUGE_KEY}" if _CONJUGE_KEY else "investimentos_conjuge"
    _KEY_CENARIOS_CONJUGE = f"cenarios_{_CONJUGE_KEY}" if _CONJUGE_KEY else "cenarios_conjuge"
    _DASH_CFG = GOALS_CONFIG.get("dashboard", {})
    _INV_BLOCOS = GOALS_CONFIG.get("investimentos_blocos", {})

    TEMPLATE_PATH = BASE_DIR / "config" / "templates" / "report_template.html"
    E5_JSON_PATH = BASE_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    E4_INVEST_PATH = BASE_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
    E4_DESPESAS_PATH = BASE_DIR / "processed" / "E4_unified" / "despesas-4_unified.json"
    E4_RECEITAS_PATH = BASE_DIR / "processed" / "E4_unified" / "receitas-4_unified.json"
    E4_FLUXO_PATH = BASE_DIR / "processed" / "E4_unified" / "fluxo_mensal_detalhado-4_unified.json"
    DEFINITIONS_PATH = BASE_DIR / "config" / "definitions.md"
    OUTPUT_DIR = BASE_DIR / "output"
    SNAPSHOT_PATH = OUTPUT_DIR / "snapshot_anterior.json"


_init_config(_DEFAULT_BASE_DIR)


def _build_broker_list() -> str:
    """Build comma-separated broker display names from banco_membro + banco_canonical."""
    banco_membro = _FAMILY.get("banco_membro", {})
    canonical = INSTITUTIONS_CONFIG.get("banco_canonical", {})
    brokers = []
    for key in banco_membro:
        if key.startswith("_"):
            continue
        display = canonical.get(key, key).title()
        if display not in brokers:
            brokers.append(display)
    return ", ".join(brokers) if brokers else "corretoras configuradas"


def _load_previous_snapshot() -> dict:
    """Load previous cycle snapshot for delta calculations."""
    if SNAPSHOT_PATH.exists():
        try:
            with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
                snap = json.load(f)
            print(f"  [OK] Snapshot anterior carregado ({snap.get('data_geracao', '?')})")
            return snap
        except Exception as e:
            print(f"  [WARN] Erro ao carregar snapshot: {e}")
    else:
        print("  [INFO] Sem snapshot anterior — primeiro ciclo")
    return {}


def _save_snapshot(e4: dict):
    """Save current cycle snapshot for next run's delta calculations."""
    p = e4.get("patrimonio", {})
    f = e4.get("fluxo_caixa", {})
    snap = {
        "data_geracao": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "patrimonio_bruto": p.get("patrimonio_bruto", 0),
        "patrimonio_investivel": p.get("patrimonio_investivel", 0),
        _KEY_INV_TITULAR: p.get(_KEY_INV_TITULAR, 0),
        _KEY_INV_CONJUGE: p.get(_KEY_INV_CONJUGE, 0),
        "imoveis_investimento": p.get("imoveis_investimento", 0),
        "renda_mensal": f.get("renda_mensal", 0),
        "despesa_mensal": f.get("despesa_mensal_media", 0),
        "taxa_poupanca": f.get("taxa_poupanca", 0),
        "tarefas_status": e4.get("tarefas_status", {}),
        "periodo_dados": e4.get("periodo_dados", ""),
    }
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(SNAPSHOT_PATH, 'w', encoding='utf-8') as fout:
            json.dump(snap, fout, ensure_ascii=False, indent=2)
        print(f"  [OK] Snapshot salvo em {SNAPSHOT_PATH.name}")
    except Exception as e:
        print(f"  [WARN] Erro ao salvar snapshot: {e}")


# Color palette for charts — from report_layout.yaml
PALETTE = REPORT_LAYOUT.get("chart_palette", []) or [
    "#1A3A5C", "#1E6E8F", "#15803D", "#F4A261", "#B91C1C",
    "#457B9D", "#E63946", "#A8DADC", "#2A9D8F", "#E76F51",
    "#F4A460", "#FFB703", "#8ECAE6", "#219EBC", "#6366F1",
    "#EC4899", "#84CC16", "#F97316", "#06B6D4", "#8B5CF6",
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
    f"{_CONJUGE_KEY}_cenarios": f"chart-{_CONJUGE_KEY}-cenarios",
    f"{_CONJUGE_KEY}_cenarios_usa": f"chart-{_CONJUGE_KEY}-cenarios-usa",
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
    f"{_CONJUGE_KEY}_cenarios": f"Cenários IF — {CONJUGE_NOME}",
    f"{_CONJUGE_KEY}_cenarios_usa": f"Cenários IF — {CONJUGE_NOME}",
    "viagens": "Orçamento de Viagens",
}

# Mapping: section number → which chart keys belong to it — from report_layout.yaml
# Note: YAML keys may be ints or strings; normalize to int
_raw_section_charts = REPORT_LAYOUT.get("section_charts", {})
SECTION_CHARTS = {int(k): v for k, v in _raw_section_charts.items()} if _raw_section_charts else {
    1: ["patrimonio_doughnut", "waterfall_if"],
    2: ["fluxo_mensal", "receita_bar", "despesas_doughnut", "receita_despesa_mensal", "score_gauge"],
    3: ["alocacao_atual", "alocacao_alvo", "top15_ativos", f"{_CONJUGE_KEY}_cenarios", "viagens"],
    4: ["yield_imoveis"],
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

PERIOD_TOGGLE_CHARTS = {"fluxo_mensal", "receita_bar", "despesas_doughnut", "viagens"}


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
        parts.append('  <p class="chart-context">'
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
    elif chart_key in ("despesas_doughnut", "patrimonio_doughnut", "alocacao_atual", "alocacao_alvo"):
        parts.append(f'  <canvas id="{canvas_id}"></canvas>')
        parts.append(f'  <div id="legend-{chart_key.replace("_", "-")}" class="chart-legend-grouped"></div>')
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


def get_report_version() -> str:
    """Get report version from pipeline.json"""
    return PIPELINE_CONFIG.get("report_version", "6.1")

def load_template() -> str:
    """Load HTML template"""
    print("[E6.0] Loading HTML template...")
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()


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

def _build_prazo_if_sub(g: dict) -> str:
    """Build the subtitle for the IF prazo KPI, showing both members' ages."""
    ano_if = g.get("ano_if", 0)
    titular_idade = g.get(f"idade_{_TITULAR_KEY}_if", g.get("david_idade_if", 0))
    line1 = f"{TITULAR_NOME} com {titular_idade} em {ano_if}"
    conjuge_idade = g.get(f"idade_{_CONJUGE_KEY}_if") if _CONJUGE_KEY else None
    if conjuge_idade is not None:
        line2 = f"{CONJUGE_NOME} com {conjuge_idade} em {ano_if}"
        return f"{line1}<br>{line2}"
    return line1


def build_kpi_section(e4: dict) -> dict:
    """Build all KPI and cover replacements"""
    print("[E6.1] Building KPI section...")

    version = get_report_version()
    sp_time = get_sp_time()

    p = e4["patrimonio"]
    g = e4["goals"]
    f = e4["fluxo_caixa"]
    r = e4["racios"]
    s = e4["score"]

    _nav_icon = "".join(w[0] for w in FAMILY_SOBRENOME.split()[:2]).upper() if FAMILY_SOBRENOME else "FR"
    _export_md = _OUTPUT_PATTERN.replace("{date}", "").replace(".html", ".md").rstrip("_")

    replacements = {
        "{{COVER_FAMILIA}}": FAMILY_SOBRENOME,
        "{{COVER_PERIODO}}": e4["periodo_dados"],
        "{{COVER_VERSAO_MANUAL}}": version,
        "{{COVER_DATA_HORA}}": sp_time,
        "{{NOME}}": TITULAR_NOME,
        "{{FAMILY_SOBRENOME}}": FAMILY_SOBRENOME,
        "{{NAV_BRAND_ICON}}": _nav_icon,
        "{{EXPORT_FILENAME_MD}}": _export_md,
        "{{CONJUGE_NOME}}": CONJUGE_NOME,

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
        "{{KPI_META_IF_PROGRESS}}": f'<div class="kpi-progress"><div class="kpi-progress-fill blue" style="width:{min(g["if_pct"], 100):.0f}%"></div></div>',

        "{{KPI_GAP_IF}}": fmt_brl_m(g["if_gap"]),
        "{{KPI_GAP_IF_SUB}}": "Faltam para a meta",

        "{{KPI_PRAZO_IF}}": f"{g['prazo_anos_realista']} anos",
        "{{KPI_PRAZO_IF_SUB}}": _build_prazo_if_sub(g),

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

# Color palettes for stacked bar chart origins (must cover all categories without wrap-around)
# Receita: paleta azul → verde (18 cores únicas, saturação média-alta)
RECEITA_PALETTE = [
    "#2563EB",  # azul royal
    "#0EA5E9",  # sky blue
    "#0891B2",  # cyan escuro
    "#0D9488",  # teal
    "#059669",  # esmeralda
    "#16A34A",  # verde vivo
    "#3B82F6",  # azul médio
    "#06B6D4",  # cyan claro
    "#14B8A6",  # teal claro
    "#22C55E",  # verde claro
    "#4F46E5",  # indigo
    "#10B981",  # verde menta
    "#6366F1",  # violeta-azul
    "#7C3AED",  # violeta
    "#38BDF8",  # sky 400
    "#34D399",  # emerald 400
    "#818CF8",  # indigo 400
    "#2DD4BF",  # teal 400
]

# Despesa: paleta vermelho → laranja → rosa (20 cores únicas, saturação média-alta)
DESPESA_PALETTE = [
    "#DC2626",  # vermelho vivo
    "#E11D48",  # rosa-vermelho
    "#EA580C",  # laranja queimado
    "#D97706",  # âmbar escuro
    "#F59E0B",  # amarelo-laranja
    "#EF4444",  # vermelho médio
    "#F97316",  # laranja vivo
    "#B91C1C",  # vermelho escuro
    "#C2410C",  # terracota
    "#CA8A04",  # dourado escuro
    "#DB2777",  # magenta
    "#BE185D",  # rosa escuro
    "#9F1239",  # bordô
    "#FB923C",  # laranja 400
    "#A855F7",  # púrpura 500
    "#F472B6",  # pink 400
    "#FBBF24",  # amber 400
    "#E879F9",  # fuchsia 400
    "#FCA5A1",  # red 300
    "#FCD34D",  # amber 300
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

        num_months = len(detalhado["labels"])

        # Assign fixed colors per category (sorted by total descending)
        receita_sorted = sorted(detalhado["receita_datasets"],
                                key=lambda ds: sum(ds["data"]), reverse=True)
        despesa_sorted = sorted(detalhado["despesa_datasets"],
                                key=lambda ds: sum(ds["data"]), reverse=True)

        receita_color_map = {ds["label"]: RECEITA_PALETTE[i % len(RECEITA_PALETTE)]
                             for i, ds in enumerate(receita_sorted)}
        despesa_color_map = {ds["label"]: DESPESA_PALETTE[i % len(DESPESA_PALETTE)]
                             for i, ds in enumerate(despesa_sorted)}

        def build_sorted_slots(cat_datasets, color_map, stack_name):
            """Per-bar sorting: for each month, sort slices by value desc (largest at bottom).
            Returns slot datasets with array backgroundColor and _labels."""
            n_cats = len(cat_datasets)
            slots = [{"data": [], "backgroundColor": [], "_labels": [],
                       "stack": stack_name, "borderRadius": 4, "label": f"{stack_name}_slot_{s}"}
                      for s in range(n_cats)]
            for m in range(num_months):
                entries = [(ds["data"][m] if m < len(ds["data"]) else 0,
                            ds["label"], color_map[ds["label"]])
                           for ds in cat_datasets]
                entries.sort(key=lambda e: e[0], reverse=True)
                for s, (value, label, color) in enumerate(entries):
                    slots[s]["data"].append(value)
                    slots[s]["backgroundColor"].append(color)
                    slots[s]["_labels"].append(label)
            return slots

        receita_slots = build_sorted_slots(receita_sorted, receita_color_map, "receita")
        despesa_slots = build_sorted_slots(despesa_sorted, despesa_color_map, "despesa")
        datasets = receita_slots + despesa_slots

        # Legend metadata (fixed category → color mapping)
        legend_receita = [{"label": ds["label"], "color": receita_color_map[ds["label"]]}
                          for ds in receita_sorted]
        legend_despesa = [{"label": ds["label"], "color": despesa_color_map[ds["label"]]}
                          for ds in despesa_sorted]

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
                yy, mm = parts[0], parts[1]
                formatted_labels.append(MESES_PT.get(mm, mm) + "/" + yy)
            else:
                formatted_labels.append(lbl)

        return {
            "labels": formatted_labels,
            "_raw_labels": raw_labels,
            "datasets": datasets,
            "legend_receita": legend_receita,
            "legend_despesa": legend_despesa,
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

def build_report_data_json(e4: dict) -> tuple:
    """Build complete report-data JSON object. Returns (json_str, dashboard_dict)."""
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

    _dashboard = build_tactical_dashboard(e4)
    _modo_sugerido = _dashboard.get("modo_sugerido", "strategic")

    report_data = {
        "meta": {
            "modo_padrao": _modo_sugerido,
            "familia": FAMILY_SOBRENOME,
            "periodo": e4["periodo_dados"],
            "data_geracao": datetime.now().isoformat(),
            "versao": get_report_version(),
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
        "dashboard": _dashboard,
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

    return json.dumps(report_data, ensure_ascii=False, separators=(',', ':')), _dashboard

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
        # Jitter overlapping bubbles so they don't stack on the same pixel
        _JITTER = 0.28
        buckets: dict[tuple, list] = {}
        for r in result:
            key = (r["probabilidade"], r["impacto"])
            buckets.setdefault(key, []).append(r)
        for group in buckets.values():
            n = len(group)
            if n <= 1:
                continue
            for i, item in enumerate(group):
                angle = 2 * math.pi * i / n - math.pi / 2
                item["probabilidade"] = round(item["probabilidade"] + _JITTER * math.cos(angle), 2)
                item["impacto"] = round(item["impacto"] + _JITTER * math.sin(angle), 2)
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
        print("  ⚠️  WARNING: top5_decisoes e meta_aporte_mensal ausentes em goals.json — usando placeholder genérico")
        return [
            {"label": "Configure goals.json", "impacto_1a": 0, "impacto_10a": 0},
        ]
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
            "labels": ["Tuition", "Room & Board", "TOTAL", f"Renda {TITULAR_NOME}", "Sobra"],
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
                {"label": f"Sem {CONJUGE_NOME}", "data": [
                    round(renda - f1f2_total_usd / 12 * cb_pess),
                    round(renda - f1f2_total_usd / 12 * cb),
                    round(renda - f1f2_total_usd / 12 * cb_otim)
                ], "backgroundColor": "#F4A261"},
                {"label": f"Com {CONJUGE_NOME} (NCLEX)", "data": [
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
            GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_minima_usd", 4000),
        ),
        "projecao_3cenarios": {
            "meta_if": g["if_meta"],
            "investivel": p["investivel"],
            "imoveis": p.get("imoveis_investimento", 0),
            "aporte_mensal": g.get("aporte_mensal", GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 0)),
            "anos": CENARIOS_CONFIG.get("horizonte_projecao_anos", 20),
            "trs_pct": GOALS_CONFIG.get("independencia_financeira", {}).get("trs_pct", 5.0),
            "renda_passiva_meta": GOALS_CONFIG.get("independencia_financeira", {}).get("renda_passiva_meta_mensal", 30000),
            "taxa_imoveis_pessimista": CENARIOS_CONFIG.get("valorizacao_imoveis", {}).get("pessimista_pct", 2.0) / 100,
            "taxa_imoveis_realista": CENARIOS_CONFIG.get("valorizacao_imoveis", {}).get("realista_pct", 5.0) / 100,
            "taxa_imoveis_otimista": CENARIOS_CONFIG.get("valorizacao_imoveis", {}).get("otimista_pct", 8.0) / 100,
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
            "labels": [
                "Receita PJ (anual)",
                f"Lucro Presumido ({_lp_pct*100:.0f}%)",
                "DAS Estimado (anual)",
                f"Limite PGBL ({_pgbl_pct*100:.0f}%)",
                "Economia IR c/ PGBL"
            ],
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
                    "backgroundColor": [
                        "rgba(230,57,70,0.75)",   "rgba(244,162,97,0.75)",
                        "rgba(42,157,143,0.75)",   "rgba(233,196,106,0.75)",
                        "rgba(69,123,157,0.75)",   "rgba(231,111,81,0.75)",
                        "rgba(38,70,83,0.75)",     "rgba(142,202,230,0.75)",
                        "rgba(255,183,3,0.75)",    "rgba(2,48,71,0.75)",
                    ][i % 10]
                }
                for i, r in enumerate(riscos)
            ]
        })(e4.get("riscos", _build_riscos_fallback())),
        "top5_decisoes": (lambda decs: {
            "labels": [d["label"] for d in decs],
            "datasets": [
                {"label": "Impacto 1 ano", "data": [d.get("impacto_1a", 0) for d in decs], "backgroundColor": "#2E86AB"},
                {"label": "Impacto 10 anos", "data": [d.get("impacto_10a", 0) for d in decs], "backgroundColor": "#2DC653"}
            ]
        })(e4.get("top5_decisoes", g.get("top5_decisoes", _build_top5_decisoes_fallback()))),
        f"{_CONJUGE_KEY}_cenarios": (lambda cm, m_min, m_max: {
            "labels": cm.get("labels", ["Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card"]),
            "datasets": [
                {"label": "Aporte mensal", "data": cm.get("aportes", [0, m_min, m_max]), "backgroundColor": "#2E86AB"},
                {"label": "Prazo IF (anos)", "data": cm.get("prazos_if", [0, 0, 0]), "backgroundColor": "#2DC653", "yAxisID": "y1"}
            ]
        })(
            e4.get(_KEY_CENARIOS_CONJUGE, g.get(_KEY_CENARIOS_CONJUGE, {})),
            GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_minima_usd", 4000),
            GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_maxima_usd", 7000),
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
        f"{_TITULAR_KEY}_valor": e4["patrimonio"].get(_KEY_INV_TITULAR, 0),
        f"{_CONJUGE_KEY}_valor": e4["patrimonio"].get(_KEY_INV_CONJUGE, 0),
        "total": inv_data.get("total", e4["patrimonio"].get(_KEY_INV_TITULAR, 0) + e4["patrimonio"].get(_KEY_INV_CONJUGE, 0)),
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
            "dia_aporte": aportes_cfg.get("dia_aporte", 5),
            "periodo_inicio": aportes_cfg.get("periodo_inicio", "Imediato"),
            "destinos": destinos,
            "pct_brl": round(brl_total / total * 100) if total else 0,
            "pct_usd": round(usd_total / total * 100) if total else 0,
            "destinos_brl": brl_names,
            "destinos_usd": usd_names,
            "resumo_brl": f"Reforça reserva e patrimônio em reais ({fmt_brl(brl_total)}/mês).",
            "resumo_usd": f"Exposição ao dólar = {fmt_brl(usd_total)}/mês. Meta pré-EUA: US$ {fmt_num(GOALS_CONFIG.get('dolarizacao', {}).get('meta_usd', 20000))}.",
        }

    # Ultimate fallback: return minimal default with warning
    if total > 0:
        print("  ⚠️  WARNING: aportes_destinos_detalhados não encontrado em goals.json — usando meta_aporte_mensal genérica")
        return {
            "total_aporte": total,
            "dia_aporte": aportes_cfg.get("dia_aporte", 5),
            "periodo_inicio": aportes_cfg.get("periodo_inicio", "Imediato"),
            "destinos": [{"destino": "Investimentos", "valor": total, "moeda": "BRL", "veiculo": "—", "notas": "Configure aportes_destinos_detalhados em goals.json para detalhamento"}],
            "pct_brl": 100,
            "pct_usd": 0,
            "destinos_brl": "Investimentos",
            "destinos_usd": "",
            "resumo_brl": f"Aporte total de {fmt_brl(total)}/mês (configure goals.json para detalhamento).",
            "resumo_usd": "",
        }
    print("  ⚠️  WARNING: estratégia de aportes vazia — configure goals.json para dados reais")
    return {
        "total_aporte": 0,
        "dia_aporte": 5,
        "periodo_inicio": "—",
        "destinos": [],
        "pct_brl": 0,
        "pct_usd": 0,
        "destinos_brl": "",
        "destinos_usd": "",
        "resumo_brl": "Nenhuma estratégia de aporte configurada.",
        "resumo_usd": "",
    }


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

    Enhanced with: real deltas from snapshot, deadline awareness, changelog,
    cycle detection, and aportes cross-referenced with transactions.
    """
    prev = _load_previous_snapshot()
    f = e4.get("fluxo_caixa", {})
    p = e4.get("patrimonio", {})
    num_months = max(1, len(f.get("receita_despesa_mensal_detalhado", {}).get("labels", [])))
    now = datetime.now()

    _TETOS = GOALS_CONFIG.get("tetos_orcamentarios", {})
    _teto_fallback_mult = _DASH_CFG.get("teto_fallback_multiplier", 1.2)
    if not _TETOS:
        print(f"  [WARN] tetos_orcamentarios não encontrado em goals.json — usando {_teto_fallback_mult*100:.0f}% da média como fallback")
    _LABELS = _DASH_CFG.get("category_labels", {})

    # --- D1: Despesas por categoria (monthly average vs teto) ---
    raw_despesas = f.get("despesas_por_categoria", {})
    despesas_dash = {}
    for cat, total in raw_despesas.items():
        mensal = round(total / num_months, 2)
        teto = _TETOS.get(cat, round(mensal * _teto_fallback_mult, 2))
        despesas_dash[cat] = {
            "label": _LABELS.get(cat, cat.replace("_", " ").title()),
            "gasto": mensal,
            "teto": teto,
        }

    # --- R2: Aportes cross-referenced with real transactions ---
    destinos_cfg = GOALS_CONFIG.get("aportes_destinos_detalhados", [])
    aportes_dash = {}
    aporte_keywords = _DASH_CFG.get("aporte_match_keywords", {})
    invest_txns = []
    try:
        with open(E4_INVEST_PATH, 'r', encoding='utf-8') as fi:
            inv_raw = json.load(fi)
        for cat_data in inv_raw.get("dados", {}).values():
            if isinstance(cat_data, list):
                invest_txns.extend(cat_data)
    except Exception:
        pass

    current_month = now.strftime("%Y-%m")
    for i, d in enumerate(destinos_cfg):
        key = f"aporte_{i}"
        dest_lower = d.get("destino", "").lower()
        feito = False
        valor_feito = 0
        for kw_group, keywords in aporte_keywords.items():
            if any(kw in dest_lower for kw in keywords):
                for txn in invest_txns:
                    txn_date = txn.get("data", "")
                    if txn_date[:7] == current_month:
                        desc = txn.get("descricao", "").lower()
                        if any(kw in desc for kw in keywords):
                            valor_feito += abs(txn.get("valor", 0))
                break
        if valor_feito >= d.get("valor", 0) * (_DASH_CFG.get("aporte_feito_threshold_pct", 50) / 100):
            feito = True
        aportes_dash[key] = {
            "label": d.get("destino", f"Destino {i+1}"),
            "feito": feito,
            "valor_meta": d.get("valor", 0),
            "valor_feito": round(valor_feito, 2),
        }

    # --- R1: Real deltas from snapshot ---
    pat_atual = p.get("patrimonio_investivel", 0)
    pat_anterior = prev.get("patrimonio_investivel", 0)
    patrimonio_delta = round(pat_atual - pat_anterior) if prev else 0

    inv_delta = {}
    for k, v in _INV_BLOCOS.items():
        if not isinstance(v, dict):
            continue
        inv_delta[k] = {
            "label": v.get("label", k.title()),
            "anterior": prev.get(f"investimentos_{k}", 0),
            "atual": p.get(f"investimentos_{k}", 0),
        }
    inv_delta["imoveis"] = {
        "label": "Imóveis Investimento",
        "anterior": prev.get("imoveis_investimento", 0),
        "atual": p.get("imoveis_investimento", 0),
    }

    # --- Tarefas with deadline awareness (R6) ---
    tarefas = e4.get("tarefas", [])
    tarefas_status = e4.get("tarefas_status", {})
    today_str = now.strftime("%Y-%m-%d")

    for t in tarefas:
        prazo = t.get("e", "")
        st = str(tarefas_status.get(str(t.get("n", "")), "pendente"))
        if st == "feito":
            t["_deadline"] = "done"
        elif prazo and prazo <= today_str:
            t["_deadline"] = "vencida"
        elif prazo:
            try:
                prazo_dt = datetime.strptime(prazo, "%Y-%m-%d")
                dias = (prazo_dt - now).days
                if dias <= _DASH_CFG.get("task_urgency_days", 7):
                    t["_deadline"] = f"vence_em_{dias}d"
                else:
                    t["_deadline"] = "futura"
            except ValueError:
                t["_deadline"] = "futura"
        else:
            t["_deadline"] = "sem_prazo"

    # --- Alertas ---
    alertas = e4.get("alertas", [])
    pontos_urgentes = e4.get("pontos_urgentes", [])
    for pu in pontos_urgentes:
        txt = f"{pu.get('acao', '')} — {pu.get('impacto', '')}"
        if txt not in alertas:
            alertas.append(txt)

    # --- R3: Próximos 15 dias (filtered by real date) ---
    proximos = []
    _prox_window = _DASH_CFG.get("proximos_dias_window", 15)
    cutoff_15d = (now + __import__('datetime').timedelta(days=_prox_window)).strftime("%Y-%m-%d")
    for t in tarefas:
        prazo = t.get("e", "")
        st = str(tarefas_status.get(str(t.get("n", "")), "pendente"))
        if prazo and prazo <= cutoff_15d and st != "feito":
            proximos.append({
                "data": prazo,
                "acao": f"#{t['n']} {t['t'][:60]}",
                "status": "vencida" if prazo <= today_str else st,
                "prioridade": t.get("p", "baixa"),
            })
    proximos.sort(key=lambda x: x["data"])
    if not proximos:
        for t in tarefas[:5]:
            st = str(tarefas_status.get(str(t.get("n", "")), "pendente"))
            if st != "feito":
                proximos.append({
                    "data": t.get("e", "—"),
                    "acao": f"#{t['n']} {t['t'][:60]}",
                    "status": st,
                    "prioridade": t.get("p", "baixa"),
                })

    # --- R7: Changelog (what changed since last cycle) ---
    changelog = []
    if prev:
        prev_data = prev.get("data_geracao", "?")
        dp = patrimonio_delta
        if dp != 0:
            sinal = "+" if dp > 0 else ""
            changelog.append(f"Patrimônio investível {sinal}R$ {dp:,.0f}".replace(",", "."))
        _changelog_min = _DASH_CFG.get("changelog_min_delta_brl", 500)
        _inv_label_pairs = [(f"investimentos_{k}", v.get("label_curto", k)) for k, v in _INV_BLOCOS.items() if isinstance(v, dict)]
        if not _inv_label_pairs:
            _inv_label_pairs = [(_KEY_INV_TITULAR, f"Inv. {TITULAR_NOME}"), (_KEY_INV_CONJUGE, f"Inv. {CONJUGE_NOME}")]
        for bloc_key, label in _inv_label_pairs:
            ant = prev.get(bloc_key, 0)
            atu = p.get(bloc_key, 0)
            d = round(atu - ant)
            if abs(d) > _changelog_min:
                sinal = "+" if d > 0 else ""
                changelog.append(f"{label}: {sinal}R$ {d:,.0f}".replace(",", "."))
        prev_status = prev.get("tarefas_status", {})
        novas_feitas = sum(1 for k, v in tarefas_status.items() if str(v) == "feito" and str(prev_status.get(k, "")) != "feito")
        if novas_feitas:
            changelog.append(f"{novas_feitas} tarefa(s) concluída(s) desde último ciclo")
        acima_teto = sum(1 for c in despesas_dash.values() if c["gasto"] > c["teto"])
        if acima_teto:
            changelog.append(f"{acima_teto} categoria(s) de despesa acima do teto")
        if not changelog:
            changelog.append("Sem variações significativas desde o último ciclo")
        changelog.insert(0, f"Comparação com ciclo de {prev_data}")
    else:
        changelog.append("Primeiro ciclo — sem comparação anterior disponível")

    # --- R8: Cycle detection ---
    ciclo_label = ""
    if prev and prev.get("data_geracao"):
        try:
            prev_dt = datetime.strptime(prev["data_geracao"][:10], "%Y-%m-%d")
            dias_entre = (now - prev_dt).days
            _cyc = _DASH_CFG.get("cycle_thresholds", {})
            if dias_entre <= _cyc.get("quinzenal_max_days", 20):
                ciclo_label = "quinzenal"
            elif dias_entre <= _cyc.get("mensal_max_days", 45):
                ciclo_label = "mensal"
            else:
                ciclo_label = "trimestral"
        except ValueError:
            ciclo_label = "manual"
    else:
        ciclo_label = "primeiro"

    quinzena = 1 if now.day <= 15 else 2
    ciclo_display = f"Quinzena {quinzena}, {now.strftime('%B %Y').title()}"

    # --- Notas (structured for rich rendering) ---
    score_obj = e4.get("score", {})
    eq = e4.get("equilibrio_cerbasi", {})
    notas = {
        "score_valor": score_obj.get("valor", "N/D"),
        "score_classificacao": score_obj.get("classificacao", ""),
        "eq_pct_presente": round(eq.get("pct_presente", 0)),
        "eq_pct_futuro": round(eq.get("pct_futuro", 0)),
        "eq_classificacao": eq.get("classificacao", "N/D"),
        "periodo_dados": e4.get("periodo_dados", "N/D"),
    }

    return {
        "patrimonio_delta": patrimonio_delta,
        "aportes": aportes_dash,
        "despesas_por_categoria": despesas_dash,
        "tarefas_status": tarefas_status,
        "tarefas": tarefas,
        "investimentos_delta": inv_delta,
        "alertas": alertas,
        "proximos_15d": proximos,
        "notas": notas,
        "periodo": e4.get("periodo_dados", ""),
        "changelog": changelog,
        "ciclo": ciclo_label,
        "ciclo_display": ciclo_display,
        "modo_sugerido": "tactical" if ciclo_label in ("quinzenal", "mensal") else "strategic",
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
    html_parts.append(f'  <div class="card-subtitle">Composição do patrimônio bruto de {fmt_brl(bruto)} em {len(categorias)} categorias</div>')
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


def _aggregate_receitas_by_period(txns_compact: list) -> dict:
    """Pre-aggregate receitas by period to avoid embedding raw transactions."""
    now = datetime.now()

    def _cutoff(months_back=None, ytd=False):
        if ytd:
            return f"{now.year}-01"
        d = now.replace(day=1)
        m = d.month - months_back
        y = d.year
        while m < 1:
            m += 12
            y -= 1
        return f"{y}-{m:02d}"

    periods = {"3m": _cutoff(3), "6m": _cutoff(6), "12m": _cutoff(12), "ytd": _cutoff(ytd=True)}
    result = {}
    for pkey, cutoff in periods.items():
        grouped: dict = {}
        for t in txns_compact:
            if t["m"] >= cutoff:
                grouped[t["c"]] = grouped.get(t["c"], 0) + t["v"]
        arr = sorted(grouped.items(), key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in arr)
        result[pkey] = {"rows": [{"c": c, "v": round(v, 2)} for c, v in arr], "total": round(total, 2)}
    return result


def build_receitas_fonte_card(e4: dict) -> str:
    """Build Receitas por Fonte card with interactive period filter (3M/6M/12M/YTD).

    Pre-aggregates data server-side per period to keep HTML lightweight.
    """
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

    aggregated = _aggregate_receitas_by_period(txns_compact)
    agg_json = json.dumps(aggregated, ensure_ascii=False)

    html_parts.append('  <div class="period-toggle" id="rf-period-toggle">')
    html_parts.append('    <button class="period-btn" data-period="3m" onclick="filterRF(\'3m\')">3M</button>')
    html_parts.append('    <button class="period-btn" data-period="6m" onclick="filterRF(\'6m\')">6M</button>')
    html_parts.append('    <button class="period-btn active" data-period="12m" onclick="filterRF(\'12m\')">12M</button>')
    html_parts.append('    <button class="period-btn" data-period="ytd" onclick="filterRF(\'ytd\')">Ano</button>')
    html_parts.append('  </div>')

    html_parts.append('  <table id="rf-table">')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody></tbody>')
    html_parts.append('  </table>')

    html_parts.append('  <script>')
    html_parts.append('  (function(){')
    html_parts.append(f'    var rfAgg={agg_json};')
    html_parts.append('    function fB(v){return"R$ "+Math.round(v).toLocaleString("pt-BR");}')
    html_parts.append('    function fP(v){return v.toFixed(1).replace(".",",")+"%";}')
    html_parts.append('    window.filterRF=function(p){')
    html_parts.append('      document.querySelectorAll("#rf-period-toggle .period-btn").forEach(function(b){b.classList.remove("active")});')
    html_parts.append('      document.querySelector("#rf-period-toggle .period-btn[data-period=\\""+p+"\\"]").classList.add("active");')
    html_parts.append('      var d=rfAgg[p]||{rows:[],total:0};')
    html_parts.append('      var tb=document.querySelector("#rf-table tbody");')
    html_parts.append('      if(d.rows.length===0){')
    html_parts.append('        tb.innerHTML="<tr><td colspan=\\"3\\" class=\\"empty-state\\">Nenhuma receita no período</td></tr>";')
    html_parts.append('      }else{')
    html_parts.append('        var rows=d.rows.map(function(i){')
    html_parts.append('          var pct=d.total>0?(i.v/d.total*100):0;')
    html_parts.append('          return"<tr><td>"+i.c+"</td><td>"+fB(i.v)+"</td><td>"+fP(pct)+"</td></tr>";')
    html_parts.append('        }).join("");')
    html_parts.append('        rows+="<tr class=\\"total-row\\"><td><strong>Total</strong></td><td><strong>"+fB(d.total)+"</strong></td><td><strong>100,0%</strong></td></tr>";')
    html_parts.append('        tb.innerHTML=rows;')
    html_parts.append('      }')
    html_parts.append('    };')
    html_parts.append('    filterRF("12m");')
    html_parts.append('  })();')
    html_parts.append('  </script>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)


def _build_classes_from_e4_positions() -> list:
    """Build granular asset classes from E4 investimentos raw positions."""
    _TIPO_LABELS = {
        "CDB": "Renda Fixa — CDB",
        "CDB_Renda_Fixa": "Renda Fixa — CDB",
        "CRI": "Renda Fixa — CRI",
        "CRA": "Renda Fixa — CRA",
        "Debenture": "Renda Fixa — Debêntures",
        "Titulo_Publico": "Renda Fixa — Títulos Públicos",
        "Fundo": "Fundos de Investimento",
        "Previdencia": "Previdência Privada",
        "Cofrinhos": "Renda Fixa — Cofrinhos/Reserva",
        "COE": "COE",
        "Swap": "Derivativos",
        "Acao": "Ações",
        "FII": "Fundos Imobiliários",
        "ETF": "ETFs",
        "BDR": "BDRs",
    }
    try:
        with open(E4_INVEST_PATH, 'r', encoding='utf-8') as fh:
            positions = json.load(fh).get("dados", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    agg = {}
    for pos in positions:
        val = safe_float(pos.get("valor_atual", 0))
        if val <= 0:
            continue
        tipo_raw = pos.get("tipo", "Outros")
        label = _TIPO_LABELS.get(tipo_raw, tipo_raw)
        agg[label] = agg.get(label, 0) + val
    total = sum(agg.values())
    if total <= 0:
        return []
    result = [{"categoria": k, "valor": v, "pct": round(v / total * 100, 2)} for k, v in agg.items()]
    result.sort(key=lambda x: x["valor"], reverse=True)
    return result


def build_investimentos_classe_card(e4: dict) -> str:
    """Build Investimentos por Classe card — v4.2"""
    classes = e4.get("investimentos", {}).get("tabela_classes", [])

    if len(classes) <= 3:
        granular = _build_classes_from_e4_positions()
        if len(granular) > len(classes):
            classes = granular

    html_parts = ['<div class="card card-feature">']
    total_inv = sum(c.get("valor", 0) for c in classes)
    html_parts.append('  <div class="card-title">Investimentos por Classe de Ativo</div>')
    html_parts.append(f'  <div class="card-subtitle">Distribuição do patrimônio investível de {fmt_brl(total_inv)} por classe</div>')
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
    html_parts.append(f'  <div class="card-subtitle">Baseado na despesa mensal média de {fmt_brl(despesa_mensal)}</div>')

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
    html_parts.append('  <p class="mt-1"><strong>Composição da Liquidez Imediata:</strong></p>')
    html_parts.append('  <table>')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Componente</th><th>Valor (R$)</th><th>% do Total</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody>')

    # Use actual composition keys from E5
    comp_items = [
        (_KEY_INV_TITULAR, f"Investimentos {TITULAR_NOME}"),
        (_KEY_INV_CONJUGE, f"Investimentos {CONJUGE_NOME}"),
        ("caixa_moeda_estrangeira", "Caixa e Moeda Estrangeira"),
    ]
    for key, nome in comp_items:
        val = composicao.get(key, 0)
        if val > 0:
            pct = (val / total_liquido * 100) if total_liquido else 0
            html_parts.append(f'      <tr><td>{nome}</td><td>{fmt_brl(val)} ({pct:.0f}%)</td><td>{fmt_pct(pct)}</td></tr>')

    html_parts.append(f'      <tr class="fw-bold"><td>Total</td><td>{fmt_brl(total_liquido)}</td><td>—</td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')

    # --- Footnote: critérios de inclusão ---
    html_parts.append('  <p class="method-note">')
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

    total_saldo = sum(d.get("saldo_devedor", 0) for d in dividas)
    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Endividamento</div>')
    if dividas:
        html_parts.append(f'  <div class="card-subtitle">{len(dividas)} dívida(s) ativa(s) totalizando {fmt_brl(total_saldo)} em saldo devedor</div>')
    else:
        html_parts.append('  <div class="card-subtitle">Nenhuma dívida identificada — situação saudável</div>')
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
        parcela_display = fmt_brl(parcela) if parcela else "—"
        taxa_display = taxa if taxa and taxa != "N/D" else "—"
        html_parts.append(f'      <tr><td>{desc}</td><td>{fmt_brl(saldo)}</td><td>{parcela_display}</td><td>{taxa_display}</td></tr>')

    total = end.get("total_dividas", 0)
    html_parts.append(f'    <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total)}</strong></td><td></td><td></td></tr>')
    html_parts.append('    </tbody>')
    html_parts.append('  </table>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)

def _aggregate_orcamento_by_period(labels: list, despesa_datasets: list) -> dict:
    """Pre-aggregate orçamento prospectivo data per period server-side."""
    now = datetime.now()

    def _cutoff_yymm(months_back=None, ytd=False):
        if ytd:
            return f"{now.year % 100:02d}/01"
        d_year, d_month = now.year, now.month - months_back
        while d_month < 1:
            d_month += 12
            d_year -= 1
        return f"{d_year % 100:02d}/{d_month:02d}"

    periods = {"3m": _cutoff_yymm(3), "6m": _cutoff_yymm(6), "12m": _cutoff_yymm(12), "ytd": _cutoff_yymm(ytd=True)}
    p_labels = {"3m": "últimos 3 meses", "6m": "últimos 6 meses", "12m": "últimos 12 meses", "ytd": "ano corrente"}
    result = {}

    for pkey, cutoff in periods.items():
        idx = [i for i, l in enumerate(labels) if l >= cutoff]
        n_months = len(idx) or 1
        cats = []
        for ds in despesa_datasets:
            key = ds.get("label", "").lower().replace(" ", "_")
            data_arr = ds.get("data", [])
            total_sum = sum(data_arr[i] for i in idx if i < len(data_arr))
            if total_sum > 0:
                cats.append({"key": key, "label": ds.get("label", ""), "avg": round(total_sum / n_months, 2), "total": round(total_sum, 2)})
        cats.sort(key=lambda c: c["avg"], reverse=True)
        total_mensal = sum(c["avg"] for c in cats)
        first_label = labels[idx[0]] if idx and labels else ""
        last_label = labels[idx[-1]] if idx and labels else ""
        result[pkey] = {
            "cats": cats, "totalM": round(total_mensal, 2), "nM": n_months,
            "first": first_label, "last": last_label, "pLabel": p_labels[pkey]
        }
    return result


def build_orcamento_prospectivo_card(e4: dict) -> str:
    """Build Orçamento Prospectivo card with interactive period filter (3M/6M/12M/YTD).

    Pre-aggregates per-period data server-side to minimize embedded JS payload.
    """
    det = e4.get("fluxo_caixa", {}).get("receita_despesa_mensal_detalhado", {})
    labels = det.get("labels", [])
    despesa_datasets = det.get("despesa_datasets", [])
    num_cats = len(despesa_datasets)

    aggregated = _aggregate_orcamento_by_period(labels, despesa_datasets)
    agg_json = json.dumps(aggregated, ensure_ascii=False)

    html_parts = ['<div class="card card-feature" id="op-card">']
    html_parts.append(f'  <div class="card-title">Orçamento Prospectivo ({num_cats} Categorias)</div>')

    html_parts.append('  <div class="period-toggle" id="op-period-toggle">')
    html_parts.append('    <button class="period-btn" data-period="3m" onclick="filterOP(\'3m\')">3M</button>')
    html_parts.append('    <button class="period-btn" data-period="6m" onclick="filterOP(\'6m\')">6M</button>')
    html_parts.append('    <button class="period-btn active" data-period="12m" onclick="filterOP(\'12m\')">12M</button>')
    html_parts.append('    <button class="period-btn" data-period="ytd" onclick="filterOP(\'ytd\')">Ano</button>')
    html_parts.append('  </div>')

    html_parts.append('  <p class="chart-context" id="op-context"></p>')

    html_parts.append('  <table id="op-table">')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Categoria</th><th>Média Mensal</th><th>% do Total</th><th>Acum. %</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody></tbody>')
    html_parts.append('  </table>')

    html_parts.append('  <div id="op-treemap" class="treemap"></div>')
    html_parts.append('  <div id="op-insights"></div>')
    html_parts.append('  <p id="op-method" class="method-note"></p>')

    _pal_json = json.dumps(PALETTE[:num_cats], ensure_ascii=False)
    html_parts.append('  <script>')
    html_parts.append('  (function(){')
    html_parts.append(f'    var A={agg_json};')
    html_parts.append(f'    var PAL={_pal_json};')
    html_parts.append('    function fB(v){return"R$ "+Math.round(v).toLocaleString("pt-BR");}')
    html_parts.append('    function fP(v){return v.toFixed(1).replace(".",",")+"%";}')
    html_parts.append('    window.filterOP=function(p){')
    html_parts.append('      document.querySelectorAll("#op-period-toggle .period-btn").forEach(function(b){b.classList.remove("active")});')
    html_parts.append('      document.querySelector("#op-period-toggle .period-btn[data-period=\\""+p+"\\"]").classList.add("active");')
    html_parts.append('      var d=A[p];if(!d)return;')
    html_parts.append('      var ctx=document.getElementById("op-context");')
    html_parts.append('      ctx.innerHTML="Projeção mensal baseada na média de <strong>"+d.nM+" meses</strong>"')
    html_parts.append('        +(d.first&&d.last?" ("+d.first+" a "+d.last+")":"")')
    html_parts.append('        +". Média mensal: <strong>"+fB(d.totalM)+"</strong>"')
    html_parts.append('        +" &mdash; projeção anual: <strong>"+fB(d.totalM*12)+"</strong>.";')
    html_parts.append('      var tb=document.querySelector("#op-table tbody");')
    html_parts.append('      var rows="";var acum=0;')
    html_parts.append('      d.cats.forEach(function(c){')
    html_parts.append('        var pct=d.totalM>0?c.avg/d.totalM*100:0;acum+=pct;')
    html_parts.append('        var cls=c.key==="nao_identificado"?" class=\\"row-highlight-warn\\"":"";')
    html_parts.append('        rows+="<tr"+cls+"><td>"+c.label+"</td><td>"+fB(c.avg)+"</td><td>"+fP(pct)+"</td><td>"+fP(acum)+"</td></tr>";')
    html_parts.append('      });')
    html_parts.append('      rows+="<tr class=\\"total-row\\"><td><strong>Total Mensal</strong></td><td><strong>"+fB(d.totalM)+"</strong></td><td><strong>100,0%</strong></td><td></td></tr>";')
    html_parts.append('      tb.innerHTML=rows;')
    html_parts.append('      var tm=document.getElementById("op-treemap");if(tm){var th="";')
    html_parts.append('        d.cats.forEach(function(c,idx){var pct=d.totalM>0?c.avg/d.totalM*100:0;if(pct<1)return;')
    html_parts.append('          var bg=PAL[idx%PAL.length];var w=Math.max(pct,4);')
    html_parts.append('          th+="<div class=\\"treemap-cell\\" style=\\"flex:"+w+" 1 0;background:"+bg+"\\" title=\\""+c.label+": "+fB(c.avg)+"/mês ("+fP(pct)+")\\"><span>"+c.label.split("_").pop()+"</span></div>";')
    html_parts.append('        });tm.innerHTML=th;}')
    html_parts.append('      var ins=document.getElementById("op-insights");var h="";')
    html_parts.append('      var ni=d.cats.find(function(c){return c.key==="nao_identificado";});')
    html_parts.append('      if(ni&&d.totalM>0){var nip=ni.avg/d.totalM*100;')
    html_parts.append('        if(nip>10)h+="<p class=\\"insight-note\\"><strong>Atenção:</strong> "+fP(nip)+" das despesas estão como \\"Não Identificado\\" ("+fB(ni.avg)+"/mês). Classificar essas transações melhora a precisão do orçamento.</p>";}')
    html_parts.append('      if(d.cats.length>=3){var t3=d.cats.slice(0,3);var t3p=d.totalM>0?t3.reduce(function(s,c){return s+c.avg;},0)/d.totalM*100:0;')
    html_parts.append('        h+="<p class=\\"insight-note\\">As 3 maiores categorias ("+t3.map(function(c){return c.label}).join(", ")+") representam <strong>"+fP(t3p)+"</strong> do orçamento mensal.</p>";}')
    html_parts.append('      ins.innerHTML=h;')
    html_parts.append('      var me=document.getElementById("op-method");')
    html_parts.append('      me.innerHTML="<strong>Metodologia:</strong> Valores calculados como média aritmética das despesas por categoria nos "+d.pLabel+" ("+d.nM+" meses). Categorias ordenadas por impacto decrescente. Coluna \\"Acum. %\\" mostra concentração acumulada (análise Pareto).";')
    html_parts.append('    };')
    html_parts.append('    filterOP("12m");')
    html_parts.append('  })();')
    html_parts.append('  </script>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)

def _aggregate_consumo_consciente_by_period(itens: list, aporte_mensal: float) -> dict:
    """Pre-aggregate consumo consciente per period (top 6 + metrics)."""
    now = datetime.now()

    def _cutoff(months_back=None, ytd=False):
        if ytd:
            return f"{now.year}-01"
        d_year, d_month = now.year, now.month - months_back
        while d_month < 1:
            d_month += 12
            d_year -= 1
        return f"{d_year}-{d_month:02d}"

    periods = {"3m": _cutoff(3), "6m": _cutoff(6), "12m": _cutoff(12), "ytd": _cutoff(ytd=True)}
    result = {}
    for pkey, cutoff in periods.items():
        filtered = sorted([i for i in itens if i.get("mes", "") >= cutoff], key=lambda x: x.get("valor", 0), reverse=True)
        top6 = []
        for i in filtered[:6]:
            raw_date = i.get("data", "")
            if raw_date and len(raw_date) >= 10:
                parts = raw_date[:10].split("-")
                fmt_date = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else raw_date[:10]
            else:
                fmt_date = i.get("mes", "")
            top6.append({
                "descricao": i.get("descricao", ""),
                "valor": round(i.get("valor", 0), 2),
                "data": fmt_date,
                "det": i.get("categoria") or i.get("observacao") or i.get("conta_cartao") or "",
            })
        total = sum(i.get("valor", 0) for i in filtered)
        equiv = round(total / aporte_mensal, 1) if aporte_mensal > 0 else 0
        result[pkey] = {"top": top6, "count": len(filtered), "total": round(total, 2), "equiv": equiv}
    return result


def build_consumo_consciente_card(e4: dict) -> str:
    """Build Consumo Consciente card with interactive period filter (3M/6M/12M/YTD).

    Pre-aggregates per-period data server-side (top 6 + metrics) to keep HTML small.
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

    aggregated = _aggregate_consumo_consciente_by_period(itens, aporte_mensal)
    agg_json = json.dumps(aggregated, ensure_ascii=False)

    html_parts.append('  <div class="period-toggle" id="cc-period-toggle">')
    html_parts.append('    <button class="period-btn" data-period="3m" onclick="filterCC(\'3m\')">3M</button>')
    html_parts.append('    <button class="period-btn" data-period="6m" onclick="filterCC(\'6m\')">6M</button>')
    html_parts.append('    <button class="period-btn active" data-period="12m" onclick="filterCC(\'12m\')">12M</button>')
    html_parts.append('    <button class="period-btn" data-period="ytd" onclick="filterCC(\'ytd\')">Ano</button>')
    html_parts.append('  </div>')

    html_parts.append('  <table id="cc-table">')
    html_parts.append('    <thead>')
    html_parts.append('      <tr><th>Descrição</th><th>Valor</th><th>Data</th><th>Categoria</th></tr>')
    html_parts.append('    </thead>')
    html_parts.append('    <tbody></tbody>')
    html_parts.append('  </table>')

    html_parts.append('  <p class="metrics" id="cc-metrics"></p>')

    html_parts.append('  <script>')
    html_parts.append('  (function(){')
    html_parts.append(f'    var ccAgg={agg_json};')
    html_parts.append('    function fB(v){return"R$ "+Math.round(v).toLocaleString("pt-BR");}')
    html_parts.append('    window.filterCC=function(p){')
    html_parts.append('      document.querySelectorAll("#cc-period-toggle .period-btn").forEach(function(b){b.classList.remove("active")});')
    html_parts.append('      document.querySelector("#cc-period-toggle .period-btn[data-period=\\""+p+"\\"]").classList.add("active");')
    html_parts.append('      var d=ccAgg[p]||{top:[],count:0,total:0,equiv:0};')
    html_parts.append('      var tb=document.querySelector("#cc-table tbody");')
    html_parts.append('      if(d.top.length===0){')
    html_parts.append('        tb.innerHTML="<tr><td colspan=\\"4\\" class=\\"empty-state\\">Nenhum gasto pontual no período</td></tr>";')
    html_parts.append('      }else{')
    html_parts.append('        tb.innerHTML=d.top.map(function(i){')
    html_parts.append('          return"<tr><td>"+i.descricao+"</td><td>"+fB(i.valor)+"</td><td>"+i.data+"</td><td>"+i.det+"</td></tr>";')
    html_parts.append('        }).join("");')
    html_parts.append('      }')
    html_parts.append('      var me=document.getElementById("cc-metrics");')
    html_parts.append('      if(d.count>0){')
    html_parts.append('        me.textContent=d.count+" gastos  \\u2022  Total: "+fB(d.total)+"  \\u2022  Equivale a "+d.equiv+" meses de aporte";')
    html_parts.append('      }else{')
    html_parts.append('        me.textContent="Nenhum gasto pontual relevante no per\\u00edodo selecionado.";')
    html_parts.append('      }')
    html_parts.append('    };')
    html_parts.append('    filterCC("12m");')
    html_parts.append('  })();')
    html_parts.append('  </script>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)

def build_diagnostico_comportamental_card(e4: dict) -> str:
    """Build Diagnóstico Comportamental card"""
    diag = e4.get("diagnostico_comportamental", [])

    html_parts = ['<div class="card card-highlight">']
    html_parts.append('  <div class="card-title">Diagnóstico Comportamental</div>')
    html_parts.append(f'  <div class="card-subtitle">{len(diag)} padrão(ões) identificado(s) com base nas transações do período</div>')
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
    html_parts.append(f'  <div class="card-subtitle">Benefício fiscal de até 12% da renda bruta tributável — alíquota marginal de {pgbl.get("aliquota_marginal", 27.5)}%</div>')
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

_PONTOS_FORTES_ICON_MAP = {
    "trophy": "🏆",
    "savings": "💰",
    "shield": "🛡️",
    "emergency": "🔒",
    "diversification": "🏗️",
    "patrimony": "📈",
    "target": "🎯",
    "info": "ℹ️",
}

def build_pontos_fortes_card(e4: dict) -> str:
    """Build Pontos Fortes card with styled item blocks."""
    fortes = e4.get("pontos_fortes", [])
    n = len(fortes)

    h = ['<div class="card card-feature">']
    h.append('  <div class="card-title">✅ Pontos Fortes — O Que Já Funciona</div>')
    h.append(f'  <div class="card-subtitle">{n} destaque(s) positivo(s) identificado(s) na análise financeira</div>')
    h.append('  <div class="pontos-fortes-list">')

    for item in fortes:
        titulo = item.get("titulo", "")
        descricao = item.get("descricao", "")
        icone_key = item.get("icone", "info")
        icone = _PONTOS_FORTES_ICON_MAP.get(icone_key, "💪")
        h.append('    <div class="ponto-forte-item">')
        h.append(f'      <span class="ponto-forte-icon">{icone}</span>')
        h.append('      <div class="ponto-forte-content">')
        h.append(f'        <strong>{titulo}</strong>')
        h.append(f'        <span>{descricao}</span>')
        h.append('      </div>')
        h.append('    </div>')

    h.append('  </div>')
    h.append('</div>')
    return '\n'.join(h)

def build_pontos_urgentes_card(e4: dict) -> str:
    """Build Pontos Urgentes card"""
    urgentes = e4.get("pontos_urgentes", [])

    html_parts = ['<div class="card card-feature">']
    html_parts.append('  <div class="card-title">Pontos Urgentes</div>')
    html_parts.append(f'  <div class="card-subtitle">{len(urgentes)} ação(ões) prioritária(s) identificada(s) para atenção imediata</div>')
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
    html_parts.append(f'  <div class="card-subtitle">Metodologia de Gustavo Cerbasi para equilíbrio entre presente e futuro — {eq.get("classificacao", "N/D")}</div>')
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
    periodo = ea.get("periodo_inicio", GOALS_CONFIG.get("aportes", {}).get("periodo_inicio", "—"))
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
    h.append(f'  <div class="card-subtitle">💰 Aporte mensal de {fmt_brl(total)} no dia {dia} de cada mês, distribuído em {len(destinos)} destinos. A partir de {periodo}.</div>')

    # Tabela de destinos
    h.append('  <table>')
    h.append('    <thead>')
    h.append('      <tr>')
    h.append('        <th class="text-left">DESTINO</th>')
    h.append('        <th class="text-right">VALOR/MÊS</th>')
    h.append('        <th class="text-right">%</th>')
    h.append('        <th class="text-left">OBJETIVO</th>')
    h.append('        <th class="text-left">LIQUIDEZ</th>')
    h.append('      </tr>')
    h.append('    </thead>')
    h.append('    <tbody>')

    for d in destinos:
        h.append('      <tr>')
        h.append(f'        <td><strong>{d["destino"]}</strong></td>')
        h.append(f'        <td class="text-right">{fmt_brl(d["valor"])}</td>')
        h.append(f'        <td class="text-right">{d["pct"]}%</td>')
        h.append(f'        <td>{d["objetivo"]}</td>')
        h.append(f'        <td>{d["liquidez"]}</td>')
        h.append('      </tr>')

    # Linha TOTAL
    h.append('      <tr class="total-row">')
    h.append(f'        <td><strong>TOTAL</strong></td>')
    h.append(f'        <td class="text-right"><strong>{fmt_brl(total)}</strong></td>')
    h.append(f'        <td class="text-right"><strong>100%</strong></td>')
    h.append(f'        <td></td>')
    h.append(f'        <td></td>')
    h.append('      </tr>')
    h.append('    </tbody>')
    h.append('  </table>')

    # Resumo BRL vs USD
    h.append('  <div class="grid-2col">')
    h.append(f'    <div class="card card-success card-compact">')
    h.append(f'      <div class="card-title">💰 {pct_brl}% em BRL</div>')
    h.append(f'      <div class="card-subtitle">{destinos_brl}: {resumo_brl}</div>')
    h.append(f'    </div>')
    h.append(f'    <div class="card card-highlight card-compact">')
    h.append(f'      <div class="card-title">🇺🇸 {pct_usd}% em USD</div>')
    h.append(f'      <div class="card-subtitle">{destinos_usd}: {resumo_usd}</div>')
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

    _rp_meta = GOALS_CONFIG.get("independencia_financeira", {}).get("renda_passiva_meta_mensal", 30000)
    _trs_ref = GOALS_CONFIG.get("independencia_financeira", {}).get("trs_pct", 5.0)
    _if_meta = GOALS_CONFIG.get("independencia_financeira", {}).get("if_meta", 7200000)
    h.append('  <h3>Bruno Perini — "Viver de Renda"</h3>')
    h.append(f'  <p>Cálculo do "Número da Independência Financeira": patrimônio necessário = despesa anual desejada ÷ TRS. ')
    h.append(f'  Exemplo: {fmt_brl(_rp_meta)}/mês × 12 ÷ {_trs_ref}% = {fmt_brl(_if_meta)}. A projeção de prazo usa taxa de retorno real (acima da inflação) ')
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

    _titular_data = _MEMBROS_DATA.get(_TITULAR_KEY, {})
    _nasc = _titular_data.get("data_nascimento", "")
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
    h.append(f'    <thead><tr><th>Cenário</th><th>Retorno real a.a.</th><th>Aporte/mês</th><th>Prazo</th><th>{TITULAR_NOME} com</th></tr></thead>')
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
    cb_pess = _cc.get("pessimista", _cc.get("pessimista_pct", 7.50))
    cb_real = CONFIG_RATES.get("cambio_usd_brl", _cc.get("realista", 5.80))
    cb_otim = _cc.get("otimista", _cc.get("otimista_pct", 4.50))
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
    _selic_pess_val = _cs.get("pessimista_pct", 8.0)
    _selic_otim_val = _cs.get("otimista_pct", 15.0)
    selic_pess = _cs.get("pessimista", {}) if isinstance(_cs.get("pessimista"), dict) else {"selic": _selic_pess_val, "cdi": _selic_pess_val - 0.1}
    selic_otim = _cs.get("otimista", {}) if isinstance(_cs.get("otimista"), dict) else {"selic": _selic_otim_val, "cdi": _selic_otim_val - 0.1}
    selic_atual = CONFIG_RATES.get("selic_atual", _cs.get("realista_pct", 14.25))
    cdi_atual = CONFIG_RATES.get("cdi_anual", selic_atual - 0.1)

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
        (f"E se {CONJUGE_NOME} não conseguir o NCLEX?",
         f"A simulação '{CONJUGE_NOME} sem trabalhar' mostra prazo IF maior. {TITULAR_NOME} absorve com aporte reduzido."),
        (f"E se {TITULAR_NOME} perder o contrato principal?",
         f"Renda cai significativamente. Reserva de emergência cobre {fmt_dec(_reserva_meses)} meses. Ações: (1) buscar contratos substitutos, (2) reduzir aporte IF, (3) {CONJUGE_NOME} mantém renda."),
        (f"E se os imóveis desvalorizarem {GOALS_CONFIG.get('stress_test_imovel_queda_pct', 20)}%?",
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
    _refs = GOALS_CONFIG.get("referencias", {})
    for l in _refs.get("livros", []):
        livro, autor, tema = l.get("titulo", ""), l.get("autor", ""), l.get("tema", "")
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
    for ft in _refs.get("ferramentas", []):
        ferr, uso, link = ft.get("nome", ""), ft.get("uso", ""), ft.get("link", "")
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
    _contador = GOALS_CONFIG.get("tributario", {}).get("contador_nome", "—")
    _seg_min = GOALS_CONFIG.get("seguros", {}).get("vida_term_minimo", 0)
    _seg_max = GOALS_CONFIG.get("seguros", {}).get("vida_term_maximo", 0)
    _ct_vars = {"seg_min": f"{_seg_min/1e6:.0f}" if _seg_min else "?", "seg_max": f"{_seg_max/1e6:.0f}" if _seg_max else "?"}
    contatos = [(f"Contador ({_contador})", "Contabilidade PJ, DAS, Simples Nacional", "Mensal (DAS) + IRPF anual + mudança de regime")]
    for ct in _refs.get("contatos_templates", []):
        quando = ct.get("quando", "")
        if not quando and ct.get("quando_template"):
            try:
                quando = ct["quando_template"].format(**_ct_vars)
            except KeyError:
                quando = ct["quando_template"]
        contatos.append((ct.get("profissional", ""), ct.get("area", ""), quando))
    for prof, area, quando in contatos:
        h.append(f'      <tr><td><strong>{prof}</strong></td><td>{area}</td><td>{quando}</td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    h.append('</div>')

    return '\n'.join(h)


def _parse_usd_range(custo_str: str) -> tuple:
    """Parse 'US$ 350' or 'US$ 235–455' into (min, max) floats. Returns (0,0) for unparseable."""
    import re
    nums = re.findall(r'[\d.,]+', custo_str.replace(',', ''))
    if not nums:
        return (0.0, 0.0)
    vals = [float(n) for n in nums]
    return (vals[0], vals[-1])


def build_nclex_roadmap_card(e4: dict) -> str:
    """Card: NCLEX Roadmap — licenciamento RN nos EUA."""
    h = []
    _nclex_steps = GOALS_CONFIG.get("nclex_roadmap", [])
    _mariana_usd_min = GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_minima_usd", 4000)
    _mariana_usd_max = GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_maxima_usd", 7000)

    cost_strings = []

    h.append('<div class="card">')
    h.append(f'  <div class="card-title">NCLEX Roadmap{f" — {CONJUGE_NOME}" if CONJUGE_NOME else ""}</div>')
    h.append('  <div class="card-subtitle">Caminho para licenciamento como Registered Nurse nos EUA (estimativa 8-18 meses)</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Etapa</th><th>Descrição</th><th>Custo</th><th>Duração</th></tr></thead>')
    h.append('    <tbody>')
    if _nclex_steps:
        for step in _nclex_steps:
            custo = step.get("custo", "—")
            cost_strings.append(custo)
            h.append(f'      <tr><td>{step.get("etapa", "")}</td><td>{step.get("descricao", "")}</td><td>{custo}</td><td>{step.get("duracao", "—")}</td></tr>')
    else:
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
            cost_strings.append(custo)
            h.append(f'      <tr><td>{etapa}</td><td>{desc}</td><td>{custo}</td><td>{dur}</td></tr>')

    total_min = sum(_parse_usd_range(c)[0] for c in cost_strings)
    total_max = sum(_parse_usd_range(c)[1] for c in cost_strings)
    if total_min == total_max:
        total_str = f"US$ {fmt_num(total_min)}"
    else:
        total_str = f"US$ {fmt_num(total_min)}–{fmt_num(total_max)}"
    h.append(f'      <tr class="total-row"><td colspan="2"><strong>Total estimado</strong></td><td><strong>{total_str}</strong></td><td></td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')
    _conjuge_nome = CONJUGE_NOME
    _conjuge_esp = _CONJUGE_DATA.get("especializacao", "")
    _conjuge_mestrado = _CONJUGE_DATA.get("mestrado", "")
    _conjuge_profissao = _CONJUGE_DATA.get("profissao", "")
    _perfil_parts = [p for p in [_conjuge_esp, f"Mestrado {_conjuge_mestrado}" if _conjuge_mestrado else "", _conjuge_profissao] if p]
    _perfil_str = " + ".join(_perfil_parts) if _perfil_parts else ""
    _hourly_min = GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_hourly_min_usd", 45)
    _hourly_max = GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {})).get("renda_rn_hourly_max_usd", 80)
    _nclex_est = GOALS_CONFIG.get("nclex_estimativa_meses", "8-18")
    h.append(f'  <p><strong>Custo total estimado: {total_str}</strong>{f" | <strong>Perfil competitivo {_conjuge_nome}:</strong> {_perfil_str}" if _perfil_str else ""}.</p>')
    h.append(f'  <p><strong>Projeção EUA:</strong> RN US${_hourly_min}–{_hourly_max}/hora → US${fmt_num(_mariana_usd_min)}–{fmt_num(_mariana_usd_max)}/mês líquido.</p>')
    h.append('</div>')
    return '\n'.join(h)


def build_simulacao_conjuge_card(e4: dict) -> str:
    """Card: Simulação — Cônjuge Sem Trabalhar."""
    h = []
    goals = e4.get("goals", {})
    patrimonio = e4.get("patrimonio", {})
    pat_investivel = safe_float(patrimonio.get("investivel", 0))
    meta_if = safe_float(goals.get("if_meta",
        GOALS_CONFIG.get("independencia_financeira", {}).get("if_meta", 7200000)))
    taxa_real = CENARIOS_CONFIG.get("retorno_real", {}).get("realista_pct", 6.0)

    _sim_mariana = e4.get(f"simulacao_{_CONJUGE_KEY}_sem_trabalhar", e4.get("simulacao_mariana_sem_trabalhar", {}))
    _aporte_cfg = GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 20000)
    h.append('<div class="card">')
    _sim_fator = GOALS_CONFIG.get("simulacao", {}).get("aporte_reduzido_fator", 0.66)
    h.append(f'  <div class="card-title">Simulação — {CONJUGE_NOME} Sem Trabalhar</div>')
    h.append(f'  <div class="card-subtitle">Cenário conservador com fator de redução de {_sim_fator*100:.0f}% no aporte mensal</div>')
    h.append('  <table>')
    h.append('    <thead><tr><th>Métrica</th><th>Valor</th></tr></thead>')
    h.append('    <tbody>')
    if _sim_mariana:
        for row in _sim_mariana.get("linhas", []):
            h.append(f'      <tr><td>{row.get("metrica", "")}</td><td>{row.get("valor", "")}</td></tr>')
    else:
        _fator_red = GOALS_CONFIG.get("simulacao", {}).get("aporte_reduzido_fator", 0.66)
        _aporte_red = round(_aporte_cfg * _fator_red)
        _prazo_full = _compute_nper(pat_investivel, _aporte_cfg, taxa_real, meta_if)
        _prazo_red = _compute_nper(pat_investivel, _aporte_red, taxa_real, meta_if)
        h.append(f'      <tr><td>IF com aporte R$ {_aporte_cfg/1000:.0f}k mantido</td><td><strong>{fmt_dec(_prazo_full)} anos</strong> (folga absorve a perda)</td></tr>')
        _aporte_red_fmt = fmt_dec(_aporte_red/1000)
        h.append(f'      <tr><td>IF com aporte reduzido R$ {_aporte_red_fmt}k</td><td>{fmt_dec(_prazo_red)} anos (+{fmt_dec(_prazo_red - _prazo_full)} anos)</td></tr>')
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
        h.append(f'  <p class="text-sm mt-sm"><span class="priority-badge priority-alta">S</span> = Essencial (S) — {essenciais} tarefas &nbsp; ')
        h.append(f'  <span class="priority-badge priority-media">R</span> = Recomendada (R) — {recomendadas} tarefas &nbsp; ')
        h.append(f'  <span class="priority-badge priority-baixa">O</span> = Opcional (O) — {opcionais} tarefas</p>')
        if feitas > 0:
            h.append(f'  <p class="text-sm">✅ {feitas} tarefa(s) concluída(s) neste ciclo.</p>')

        # LLM-suggested tasks (from E5.N)
        sugeridas = e4.get("tarefas_sugeridas", [])
        if sugeridas:
            h.append('  <h3>Tarefas Sugeridas pela Análise</h3>')
            h.append('  <p class="text-sm"><em>Sugeridas automaticamente com base nos dados financeiros. Pendente aprovação do titular para inclusão no backlog.</em></p>')
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
        h.append(f'      <tr><td colspan="2" class="pt-sm"><strong>Detalhamento mensal</strong></td></tr>')
        for mes, val in _meses_com_gasto.items():
            h.append(f'      <tr><td class="pl-md">{mes}</td><td>{fmt_brl(val)}</td></tr>')

    saldo_class = "" if _saldo_viagens >= 0 else ' class="text-danger"'
    h.append(f'      <tr><td>Saldo disponível</td><td{saldo_class}><strong>{fmt_brl(_saldo_viagens)}</strong></td></tr>')
    h.append('    </tbody>')
    h.append('  </table>')

    if _txns:
        h.append('  <details><summary>Ver transações individuais ({} itens)</summary>'.format(len(_txns)))
        h.append('  <table class="method-note">')
        h.append('    <thead><tr><th>Data</th><th>Descrição</th><th>Valor</th></tr></thead>')
        h.append('    <tbody>')
        for t in _txns:
            h.append(f'      <tr><td>{t.get("data","")}</td><td>{t.get("descricao","")}</td><td>{fmt_brl(safe_float(t.get("valor",0)))}</td></tr>')
        h.append('    </tbody></table></details>')

    h.append('  <p><em>Nota: Custos da estadia EUA (F1/F2) NÃO entram no orçamento de viagens — são custo de vida.</em></p>')
    h.append('</div>')

    # NCLEX + Simulação: cross-reference to USA mode (U3/U4) to avoid duplication
    h.append('<div class="card">')
    h.append(f'  <div class="card-title">NCLEX Roadmap & Simulação {CONJUGE_NOME}</div>')
    h.append('  <p>Detalhamento completo disponível no <strong>Modo USA</strong> (seções U3 e U4). Ative o modo USA no seletor superior para visualizar o roadmap NCLEX, custos estimados e a simulação de cenários.</p>')
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
        _aporte_val = GOALS_CONFIG.get("aportes", {}).get("meta_aporte_mensal", 0)
        _holding = GOALS_CONFIG.get("tributario", {}).get("holding_avaliacao_prazo", "—")
        _cal_template_vars = {
            "aporte_mensal": fmt_brl(_aporte_val),
            "seg_min": f"{_seg_min/1e6:.0f}" if _seg_min else "?",
            "seg_max": f"{_seg_max/1e6:.0f}" if _seg_max else "?",
            "titular": TITULAR_NOME,
            "conjuge": CONJUGE_NOME,
            "pai_titular": PAI_TITULAR,
        }
        for ev in GOALS_CONFIG.get("calendario_fallback", []):
            _data = _holding if ev.get("data") == "_holding_prazo" else ev.get("data", "—")
            _item = ev.get("item", "")
            if not _item and ev.get("item_template"):
                try:
                    _item = ev["item_template"].format(**_cal_template_vars)
                except KeyError:
                    _item = ev["item_template"]
            h.append(f'      <tr><td>{_data}</td><td>{_item}</td><td>{ev.get("tipo", "")}</td></tr>')
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
    h.append('  <div class="card-subtitle">Indicadores derivados do fluxo de caixa e patrimônio — dados reais do período</div>')

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

    h.append('  <p class="note-muted">⚠️ Rentabilidade e volatilidade requerem dados históricos de cotas — não disponíveis nos extratos atuais.</p>')
    h.append('</div>')
    return '\n'.join(h)


def _classify_position_indexador(pos: dict, cfg_class: dict) -> str:
    """Classify an investment position by indexer using config rules.

    Priority: 1) taxa keywords match, 2) tipo in tipos_fallback.
    """
    taxa_str = str(pos.get("taxa", "")).upper()
    tipo_str = pos.get("tipo", "") or ""

    for idx_key in ("ipca_plus", "pos_cdi", "prefixado"):
        rule = cfg_class.get(idx_key, {})
        for kw in rule.get("keywords_taxa", []):
            if kw.upper() in taxa_str:
                return idx_key

    for idx_key, rule in cfg_class.items():
        if tipo_str in rule.get("tipos_fallback", []):
            return idx_key

    return "outros"


def build_contrafluxo_card(e4: dict) -> str:
    """Build Contrafluxo card with portfolio breakdown, Selic scenarios, and recommendation."""
    cf_cfg = CENARIOS_CONFIG.get("contrafluxo", {})
    selic_cfg = CENARIOS_CONFIG.get("selic", {})
    selic = CONFIG_RATES.get("selic_atual", 0)
    cdi = CONFIG_RATES.get("cdi_anual", 0)
    ipca = CONFIG_RATES.get("ipca_anual", 0)

    h = ['<div class="card card-primary">']
    h.append('  <div class="card-title">Contrafluxo</div>')
    h.append(f'  <div class="card-subtitle">Selic {fmt_dec(selic)}% a.a. · CDI {fmt_dec(cdi)}% · IPCA {fmt_dec(ipca)}% · Juro real ~{fmt_dec(selic - ipca)}%</div>')

    # --- Section 1: Portfolio by indexer ---
    cfg_class = cf_cfg.get("classificacao_indexador", {})
    inv_data = e4.get("_inv4_dados", [])
    if not inv_data:
        inv_raw = e4.get("_investimentos_raw", {})
        inv_data = inv_raw.get("dados", [])

    by_idx: dict = {}
    for pos in inv_data:
        val = safe_float(pos.get("valor_atual", 0))
        if val <= 0:
            continue
        idx = _classify_position_indexador(pos, cfg_class)
        by_idx.setdefault(idx, {"valor": 0.0, "count": 0})
        by_idx[idx]["valor"] += val
        by_idx[idx]["count"] += 1

    total_inv = sum(b["valor"] for b in by_idx.values())

    if total_inv > 0:
        label_map = {k: v.get("label", k) for k, v in cfg_class.items()}
        label_map.setdefault("outros", "Outros")
        sorted_idx = sorted(by_idx.items(), key=lambda x: -x[1]["valor"])

        h.append('  <table>')
        h.append('    <thead><tr><th>Indexador</th><th>Valor</th><th>%</th><th>Posições</th></tr></thead>')
        h.append('    <tbody>')
        for idx_key, info in sorted_idx:
            label = label_map.get(idx_key, idx_key)
            pct = info["valor"] / total_inv * 100
            h.append(f'      <tr><td>{label}</td><td>{fmt_brl(info["valor"])}</td><td>{fmt_dec(pct)}%</td><td>{info["count"]}</td></tr>')
        h.append(f'      <tr class="total-row"><td><strong>Total</strong></td><td><strong>{fmt_brl(total_inv)}</strong></td><td><strong>100%</strong></td><td><strong>{sum(b["count"] for b in by_idx.values())}</strong></td></tr>')
        h.append('    </tbody>')
        h.append('  </table>')

    # --- Section 2: Selic scenarios ---
    cenarios = cf_cfg.get("cenarios", [])
    if cenarios:
        h.append(f'  <div class="card-title mt-3">Cenários de Selic</div>')
        h.append('  <table>')
        h.append('    <thead><tr><th>Cenário</th><th>Selic</th><th>Pós-CDI</th><th>IPCA+</th><th>Ação</th></tr></thead>')
        h.append('    <tbody>')
        for cen in cenarios:
            campo = cen.get("campo_selic", "")
            selic_val = selic_cfg.get(campo, selic)
            cdi_est = selic_val - 0.1
            destaque = cen.get("destaque", False)
            tag_o, tag_c = ("<strong>", "</strong>") if destaque else ("", "")
            cls = ' class="total-row"' if destaque else ""
            h.append(f'      <tr{cls}>'
                     f'<td>{tag_o}{cen["nome"]}{tag_c}</td>'
                     f'<td>{tag_o}{fmt_dec(selic_val)}%{tag_c}</td>'
                     f'<td>{cen.get("impacto_pos_cdi", "")}</td>'
                     f'<td>{cen.get("impacto_ipca_plus", "")}</td>'
                     f'<td>{cen.get("acao", "")}</td></tr>')
        h.append('    </tbody>')
        h.append('  </table>')

    # --- Section 3: Dynamic recommendation ---
    rec_cfg = cf_cfg.get("recomendacao", {})
    threshold_alta = cf_cfg.get("selic_alta_pct", 10.0)
    threshold_baixa = cf_cfg.get("selic_baixa_pct", 8.0)

    if selic >= threshold_alta:
        rec_text = rec_cfg.get("selic_alta", "").replace("{threshold}", fmt_dec(threshold_alta))
    elif selic <= threshold_baixa:
        rec_text = rec_cfg.get("selic_baixa", "").replace("{threshold}", fmt_dec(threshold_baixa))
    else:
        rec_text = rec_cfg.get("selic_moderada", "")

    if rec_text:
        pct_ipca = by_idx.get("ipca_plus", {}).get("valor", 0) / total_inv * 100 if total_inv > 0 else 0
        pct_cdi = by_idx.get("pos_cdi", {}).get("valor", 0) / total_inv * 100 if total_inv > 0 else 0
        h.append(f'  <p class="method-note"><strong>Sinal contrafluxo:</strong> {rec_text} '
                 f'Posição atual: {fmt_dec(pct_ipca)}% em IPCA+, {fmt_dec(pct_cdi)}% em pós-CDI.</p>')

    h.append('</div>')
    return '\n'.join(h)


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
    "nclex_roadmap": build_nclex_roadmap_card,
    f"simulacao_{_CONJUGE_KEY}": build_simulacao_conjuge_card,
}

# Registry: appendix ID → builder function
APPENDIX_BUILDERS = {
    "APP_A": lambda e4: build_appendix_a(),
    "APP_B": lambda e4: build_appendix_b(e4),
    "APP_C": lambda e4: build_appendix_c(e4),
    "APP_D": lambda e4: build_appendix_d(),
    "APP_E": lambda e4: build_appendix_e(e4),
}


def _apply_card_variant(card_html: str, variant: str = "", size: str = "", card_id: str = "") -> str:
    """Apply variant, size, and accessibility attrs from layout config to a card's HTML."""
    if variant:
        card_html = re.sub(
            r'class="card card-\w+"',
            f'class="card card-{variant}"',
            card_html,
            count=1
        )
    # Add aria-label from card-title if not already present
    title_match = re.search(r'class="card-title"[^>]*>([^<]+)<', card_html)
    if title_match and 'aria-label=' not in card_html:
        label = title_match.group(1).strip()
        card_html = card_html.replace('<div class="card"', f'<div class="card" role="article" aria-label="{label}"', 1)
        card_html = re.sub(
            r'<div class="card (card-\w+)"',
            lambda m: f'<div class="card {m.group(1)}" role="article" aria-label="{label}"',
            card_html,
            count=1
        )
    if size == "half":
        card_html = f'<div>\n{card_html}\n</div>'
    return card_html


def build_sections(e4: dict) -> dict:
    """Build S1-S10 + U1-U4 content sections with charts and cards.

    If REPORT_LAYOUT is available, iterates over the YAML config.
    Otherwise, falls back to the original hardcoded sequence.
    USA sections (U1-U4) are rendered from the 'usa' block in YAML.
    """
    print("[E6.4] Building sections S1-S10 + U1-U4...")

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
                html += '<div class="split-cards">\n'
                html += build_pontos_fortes_card(e4) + "\n"
                html += build_pontos_urgentes_card(e4) + "\n"
                html += '</div>\n'
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

    # ── USA Mode Sections (U1-U4) ──
    layout_usa = REPORT_LAYOUT.get("usa", {})
    usa_sections = layout_usa.get("sections", [])

    _usa_summaries = {
        "u1": summaries.get("s5", summaries.get("u1", "Estrutura de custos para visto F1/F2 nos EUA.")),
        "u2": summaries.get("s6", summaries.get("u2", "Processo e compliance EB2-NIW para Green Card.")),
        "u3": summaries.get("u3", "Roadmap de licenciamento NCLEX-RN para atuação como enfermeira nos EUA."),
        "u4": summaries.get("u4", "Cenário financeiro caso a cônjuge não trabalhe nos primeiros meses nos EUA."),
    }
    for i in range(1, 5):
        replacements[f"{{{{SUMMARY_U{i}}}}}"] = _usa_summaries.get(f"u{i}", f"USA seção {i} — dados pendentes")

    # Alias narrativas so _usa suffix charts inherit from parent key
    _cenarios_usa_key = f"{_CONJUGE_KEY}_cenarios_usa"
    _cenarios_key = f"{_CONJUGE_KEY}_cenarios"
    if _cenarios_usa_key not in charts_narrativas and _cenarios_key in charts_narrativas:
        charts_narrativas[_cenarios_usa_key] = charts_narrativas[_cenarios_key]

    if usa_sections:
        print("  [LAYOUT] Rendering USA sections from report_layout.yaml")
        for section_cfg in usa_sections:
            section_id = section_cfg.get("id", "")
            enabled = section_cfg.get("enabled", True)
            section_num = int(section_id.replace("U", "")) if section_id.startswith("U") else 0

            if not enabled:
                replacements[f"{{{{CONTENT_U{section_num}}}}}"] = ""
                print(f"  [LAYOUT] {section_id} — DISABLED")
                continue

            html = ""

            chart_cfgs = [c for c in section_cfg.get("charts", []) if c.get("enabled", True)]
            for chart_cfg in chart_cfgs:
                chart_key = chart_cfg.get("id", "")
                chart_title = CHART_TITLES.get(chart_key, chart_key.replace('_', ' ').title())
                html += chart_html(chart_key, chart_title, charts_narrativas) + "\n"

            for card_cfg in section_cfg.get("cards", []):
                card_id = card_cfg.get("id", "")
                if not card_cfg.get("enabled", True):
                    continue
                builder = CARD_BUILDERS.get(card_id)
                if builder:
                    card_out = builder(e4)
                    variant = card_cfg.get("variant", "")
                    size = card_cfg.get("size", "full")
                    card_out = _apply_card_variant(card_out, variant, size)
                    html += card_out + "\n"
                else:
                    print(f"  [WARN] Card builder not found for '{card_id}' in USA mode")

            replacements[f"{{{{CONTENT_U{section_num}}}}}"] = html.rstrip()
            print(f"  [LAYOUT] {section_id} — OK ({len(chart_cfgs)} charts, {len(section_cfg.get('cards', []))} cards)")
    else:
        print("  [USA] No layout config — using fallback empty placeholders")

    for i in range(1, 5):
        key = f"{{{{CONTENT_U{i}}}}}"
        if key not in replacements:
            replacements[key] = ""

    return replacements

# ============================================================================
# STEP 6: VALIDATION
# ============================================================================


# validate_report imported from scripts.e6.validate

# ============================================================================
# MAIN RENDERER
# ============================================================================

def render_report(root_dir: Path = None):
    """Main rendering pipeline"""
    if root_dir:
        _init_config(root_dir)
    print("\n" + "="*70)
    print("E6 RENDERER — Deterministic Financial Report Generation")
    print("="*70 + "\n")

    # Load inputs
    e4 = load_e4_json()
    template = load_template()

    # Inject 12-month viagens data into e4 so charts and cards pick it up
    e4["_viagens_12m"] = load_viagens_12m()

    # Inject raw E4 investimentos for contrafluxo classification
    try:
        with open(E4_INVEST_PATH, 'r', encoding='utf-8') as _f:
            e4["_inv4_dados"] = json.load(_f).get("dados", [])
    except (FileNotFoundError, json.JSONDecodeError):
        e4["_inv4_dados"] = []

    # Build all replacements
    print("[E6.1-E6.5] Building all replacements...")
    all_replacements = {}
    all_replacements.update(build_kpi_section(e4))
    all_replacements.update(build_perfil_section(e4))
    all_replacements.update(build_sections(e4))

    # Build and inject report-data JSON
    report_data_json, _dashboard = build_report_data_json(e4)
    _modo_sugerido = _dashboard.get("modo_sugerido", "strategic")
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
    output_path = OUTPUT_DIR / _OUTPUT_PATTERN.replace("{date}", timestamp)

    print(f"\n[E6.7] Writing output to {output_path}...")
    output_path.write_text(html, encoding='utf-8')

    # R1: Save snapshot for next cycle comparison
    print("[E6.8] Saving snapshot for next cycle...")
    _save_snapshot(e4)

    print(f"[E6.9] Report size: {len(html.encode('utf-8')) / 1024:.1f}KB")
    print(f"[E6.9] Modo sugerido: {_modo_sugerido} (ciclo: {_dashboard.get('ciclo', '?')})")
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

#!/usr/bin/env python3
"""
E5 Analysis Script — NUMERIC portions only
Reads E4 unified files and computes analise_financeira-5_analysis.json
Does NOT generate narrativas (that's E5.N, done by LLM).

Author: Claude Haiku 4.5
Date: 2026-04-05
"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Tuple
import re

# ============================================================================
# PATHS
# ============================================================================
SCRIPTS_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPTS_DIR.parent

PROCESSED_DIR = PROJECT_DIR / "processed"
E4_UNIFIED_DIR = PROCESSED_DIR / "E4_unified"
E2_EXTRACTS_DIR = PROCESSED_DIR / "E2_extracts"
E5_ANALYSIS_DIR = PROCESSED_DIR / "E5_analysis"

LIFE_PLAN_GOALS = PROJECT_DIR / "life_plan" / "life_plan_goals.md"
CONFIG_DEFINITIONS = PROJECT_DIR / "config" / "definitions.md"

# Input files
FILE_RECEITAS = E4_UNIFIED_DIR / "receitas-4_unified.json"
FILE_DESPESAS = E4_UNIFIED_DIR / "despesas-4_unified.json"
FILE_PATRIMONIO = E4_UNIFIED_DIR / "patrimonio-4_unified.json"
FILE_INVESTIMENTOS = E4_UNIFIED_DIR / "investimentos-4_unified.json"
FILE_FLUXO_MENSAL = E4_UNIFIED_DIR / "fluxo_mensal_detalhado-4_unified.json"
FILE_BASELINE = E2_EXTRACTS_DIR / "baseline_patrimonial-1.5_consolidated.json"

# Output file
FILE_OUTPUT = E5_ANALYSIS_DIR / "analise_financeira-5_analysis.json"

# ============================================================================
# CONSTANTS
# ============================================================================
DAVID_DOB = date(1981, 9, 5)
TODAY = date(2026, 4, 5)

# One-time income categories (not counted in recorrente)
ONE_TIME_INCOME_KEYWORDS = ["kiwify", "fgts", "restituicao", "bolsa", "bonus"]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_float(val: Any) -> float:
    """Convert value to float, default to 0.0 if fails."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def safe_int(val: Any) -> int:
    """Convert value to int, default to 0 if fails."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file, return empty dict if missing."""
    if not path.exists():
        print(f"  ⚠️  File not found: {path.name}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  Error loading {path.name}: {e}")
        return {}


def extract_if_target_from_life_plan() -> float:
    """Extract IF meta (R$ 7,200,000) from life_plan_goals.md."""
    if not LIFE_PLAN_GOALS.exists():
        print(f"  ⚠️  {LIFE_PLAN_GOALS.name} not found, using default R$7,200,000")
        return 7200000.0

    try:
        content = LIFE_PLAN_GOALS.read_text(encoding="utf-8")
        # Search for "Número da Independência" or "meta"
        match = re.search(r'\*\*R\$\s*([\d.,]+)', content)
        if match:
            val_str = match.group(1).replace(".", "").replace(",", ".")
            return safe_float(val_str)
    except Exception as e:
        print(f"  ⚠️  Error reading life_plan_goals.md: {e}")

    return 7200000.0


def extract_if_trs() -> float:
    """Extract TRS from life_plan_goals.md, default 5.0%."""
    if not LIFE_PLAN_GOALS.exists():
        return 5.0

    try:
        content = LIFE_PLAN_GOALS.read_text(encoding="utf-8")
        match = re.search(r'TRS.*?(\d+(?:[.,]\d+)?)\s*%', content, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(",", ".")
            return safe_float(val_str)
    except Exception:
        pass

    return 5.0


def extract_renda_passiva_from_life_plan() -> float:
    """Extract current renda passiva (R$ 10.042/mês) from life_plan."""
    if not LIFE_PLAN_GOALS.exists():
        return 0.0

    try:
        content = LIFE_PLAN_GOALS.read_text(encoding="utf-8")
        # Find "Renda passiva atual:"
        match = re.search(
            r'Renda passiva atual:\s*R\$\s*([\d.,]+)',
            content,
            re.IGNORECASE
        )
        if match:
            val_str = match.group(1).replace(".", "").replace(",", ".")
            return safe_float(val_str)
    except Exception:
        pass

    return 0.0


def is_one_time_income(descricao: str) -> bool:
    """Check if income is one-time (not recurring)."""
    descricao_lower = descricao.lower()
    return any(kw in descricao_lower for kw in ONE_TIME_INCOME_KEYWORDS)


def calculate_edad(dob: date, reference_date: date = TODAY) -> int:
    """Calculate age in years."""
    delta = reference_date - dob
    return delta.days // 365


def linear_interpolate(val: float, min_val: float, max_val: float) -> float:
    """Linear interpolation: maps [min_val, max_val] → [0, 10]."""
    if max_val == min_val:
        return 0.0
    score = (val - min_val) / (max_val - min_val) * 10.0
    return max(0.0, min(10.0, score))


# ============================================================================
# PATRIMONIO ANALYSIS
# ============================================================================

def analyze_patrimonio(baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze patrimonio from baseline data."""
    print("[E5.1] Analyzing patrimonio...")

    members = baseline.get("members", {})

    david = members.get("david", {})
    mariana = members.get("mariana", {})

    total_bens = safe_float(david.get("total_bens", 0)) + safe_float(mariana.get("total_bens", 0))
    total_dividas = safe_float(david.get("total_dividas", 0)) + safe_float(mariana.get("total_dividas", 0))

    patrimonio_bruto = total_bens
    patrimonio_liquido = patrimonio_bruto - total_dividas

    # Residência: Tasso da Silveira (David's primary residence)
    residencia = 0.0
    imoveis_investimento = 0.0

    for imovel in david.get("imoveis", []):
        if "tasso da silveira" in imovel.get("description", "").lower():
            residencia = safe_float(imovel.get("valor_31_12_ano_base", 0))
        else:
            imoveis_investimento += safe_float(imovel.get("valor_31_12_ano_base", 0))

    for imovel in mariana.get("imoveis", []):
        imoveis_investimento += safe_float(imovel.get("valor_31_12_ano_base", 0))

    # Veículos
    veiculos = 0.0
    for veiculo in david.get("veiculos", []):
        veiculos += safe_float(veiculo.get("valor_31_12_ano_base", 0))
    for veiculo in mariana.get("veiculos", []):
        veiculos += safe_float(veiculo.get("valor_31_12_ano_base", 0))

    # Investment accounts
    investimentos_david = 0.0
    investimentos_mariana = 0.0

    for inv in david.get("investimentos", []):
        investimentos_david += safe_float(inv.get("valor_31_12_ano_base", 0))
    for inv in david.get("contas_bancarias", []):
        investimentos_david += safe_float(inv.get("valor_31_12_ano_base", 0))

    for inv in mariana.get("investimentos", []):
        investimentos_mariana += safe_float(inv.get("valor_31_12_ano_base", 0))
    for inv in mariana.get("contas_bancarias", []):
        investimentos_mariana += safe_float(inv.get("valor_31_12_ano_base", 0))

    # Caixa e moeda estrangeira (RESIDUAL)
    caixa_moeda_estrangeira = (
        patrimonio_bruto
        - residencia
        - imoveis_investimento
        - veiculos
        - investimentos_david
        - investimentos_mariana
    )
    caixa_moeda_estrangeira = max(0.0, caixa_moeda_estrangeira)

    # Investível
    investivel = patrimonio_bruto - residencia - veiculos

    # Composition breakdown (sorted by value desc)
    composicao = [
        {"categoria": "Residência", "valor": residencia},
        {"categoria": "Imóveis Investimento", "valor": imoveis_investimento},
        {"categoria": "Investimentos David", "valor": investimentos_david},
        {"categoria": "Investimentos Mariana", "valor": investimentos_mariana},
        {"categoria": "Caixa e Moeda Estrangeira", "valor": caixa_moeda_estrangeira},
        {"categoria": "Veículos", "valor": veiculos},
    ]

    # Sort descending, add percentage
    total_nonzero = sum(c["valor"] for c in composicao)
    if total_nonzero > 0:
        for comp in composicao:
            comp["pct"] = round((comp["valor"] / total_nonzero) * 100, 2)
        composicao.sort(key=lambda x: x["valor"], reverse=True)

    return {
        "bruto": round(patrimonio_bruto, 2),
        "dividas": round(total_dividas, 2),
        "liquido": round(patrimonio_liquido, 2),
        "residencia": round(residencia, 2),
        "imoveis_investimento": round(imoveis_investimento, 2),
        "investimentos_david": round(investimentos_david, 2),
        "investimentos_mariana": round(investimentos_mariana, 2),
        "caixa_moeda_estrangeira": round(caixa_moeda_estrangeira, 2),
        "investivel": round(investivel, 2),
        "veiculos": round(veiculos, 2),
        "composicao": composicao,
    }


# ============================================================================
# GOALS & IF ANALYSIS
# ============================================================================

def analyze_goals(patrimonio: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze IF goals."""
    print("[E5.2] Analyzing IF goals...")

    if_meta = extract_if_target_from_life_plan()
    if_trs = extract_if_trs()
    investivel = patrimonio["investivel"]

    # IF monthly target (assuming TRS, derive monthly)
    # TRS % per annum → monthly: TRS% / 12
    if_trs_monthly = (if_trs / 100.0) / 12.0
    if_trs_value = if_meta * if_trs_monthly

    # Percentage achieved
    if_pct = (investivel / if_meta * 100) if if_meta > 0 else 0.0

    # Gap
    if_gap = if_meta - investivel

    # Prazo realista (simplified: gap / annual savings)
    # Assuming R$20k/month aporte
    annual_savings = 20000 * 12
    prazo_anos = (if_gap / annual_savings) if annual_savings > 0 else 999
    prazo_anos = max(0, prazo_anos)

    # David's age at IF
    anos_restantes = int(prazo_anos)
    david_idade_if = calculate_edad(DAVID_DOB) + anos_restantes
    ano_if = TODAY.year + anos_restantes

    # Current passive income estimate (4% rule on investível)
    renda_passiva_current = investivel * 0.04 / 12  # monthly

    return {
        "if_meta": round(if_meta, 2),
        "if_trs": round(if_trs, 2),
        "if_trs_monthly_value": round(if_trs_value, 2),
        "if_pct": round(if_pct, 2),
        "if_gap": round(if_gap, 2),
        "prazo_anos_realista": round(prazo_anos, 1),
        "david_idade_if": david_idade_if,
        "ano_if": ano_if,
        "renda_passiva_estimada_4pct": round(renda_passiva_current, 2),
    }


# ============================================================================
# FLUXO DE CAIXA ANALYSIS
# ============================================================================

def analyze_fluxo_caixa(
    receitas: Dict[str, Any],
    despesas: Dict[str, Any],
    fluxo_mensal: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze cash flow."""
    print("[E5.3] Analyzing fluxo de caixa...")

    # Totals
    receita_total = safe_float(receitas.get("total_geral", 0))
    despesa_total = safe_float(despesas.get("total_geral", 0))

    # One-time vs recorrente
    receita_one_time = 0.0
    receita_recorrente = receita_total

    receita_dados = receitas.get("dados", {})
    for categoria, transacoes in receita_dados.items():
        for txn in transacoes:
            descricao = txn.get("descricao", "").lower()
            if is_one_time_income(descricao):
                receita_one_time += safe_float(txn.get("valor", 0))
                receita_recorrente -= safe_float(txn.get("valor", 0))

    # Count months in period
    periodo = receitas.get("periodo", "")
    # Parse "2025-01 a 2026-03" → count months
    num_months = len(fluxo_mensal.get("meses_ordenados", []))
    if num_months == 0:
        num_months = 15  # fallback

    receita_recorrente_mensal = receita_recorrente / num_months if num_months > 0 else 0
    despesa_mensal_media = despesa_total / num_months if num_months > 0 else 0

    fluxo_liquido = receita_total - despesa_total

    # By categoria
    por_fonte = receitas.get("totais_por_categoria", {})
    despesas_por_categoria = despesas.get("totais_por_categoria", {})

    # Build detailed monthly Chart.js format
    meses = fluxo_mensal.get("meses_ordenados", [])
    receita_por_mes = fluxo_mensal.get("receitas", {}).get("por_mes", {})
    despesa_por_mes = fluxo_mensal.get("despesas", {}).get("por_mes", {})

    labels = [f"{m[:4][-2:]}/{m[-2:]}" for m in meses]  # "25/01", "25/02", etc.

    # Gather all receita sources dynamically
    receita_sources = set()
    for mes_data in receita_por_mes.values():
        receita_sources.update(k for k in mes_data.keys() if k != "_total")

    receita_datasets = []
    for source in sorted(receita_sources):
        data = [safe_float(receita_por_mes.get(mes, {}).get(source, 0)) for mes in meses]
        if any(d > 0 for d in data):
            receita_datasets.append({
                "label": source,
                "data": data,
            })

    # Gather all despesa categories dynamically
    despesa_categories = set()
    for mes_data in despesa_por_mes.values():
        despesa_categories.update(k for k in mes_data.keys() if k != "_total")

    despesa_datasets = []
    for cat in sorted(despesa_categories):
        data = [safe_float(despesa_por_mes.get(mes, {}).get(cat, 0)) for mes in meses]
        if any(d > 0 for d in data):
            despesa_datasets.append({
                "label": cat,
                "data": data,
            })

    # Totals by month
    totais_receita = [safe_float(receita_por_mes.get(mes, {}).get("_total", 0)) for mes in meses]
    totais_despesa = [safe_float(despesa_por_mes.get(mes, {}).get("_total", 0)) for mes in meses]

    return {
        "receita_total": round(receita_total, 2),
        "receita_recorrente": round(receita_recorrente, 2),
        "receita_one_time": round(receita_one_time, 2),
        "receita_recorrente_mensal": round(receita_recorrente_mensal, 2),
        "despesa_total": round(despesa_total, 2),
        "despesa_mensal_media": round(despesa_mensal_media, 2),
        "fluxo_liquido": round(fluxo_liquido, 2),
        "por_fonte": {k: round(v, 2) for k, v in por_fonte.items()},
        "despesas_por_categoria": {k: round(v, 2) for k, v in despesas_por_categoria.items()},
        "receita_despesa_mensal_detalhado": {
            "labels": labels,
            "receita_datasets": receita_datasets,
            "despesa_datasets": despesa_datasets,
            "totais_receita": [round(v, 2) for v in totais_receita],
            "totais_despesa": [round(v, 2) for v in totais_despesa],
        },
    }


# ============================================================================
# RATIOS & FINANCIAL METRICS
# ============================================================================

def analyze_ratios(
    fluxo: Dict[str, Any],
    patrimonio: Dict[str, Any],
    goals: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute financial ratios."""
    print("[E5.4] Computing ratios...")

    receita_recorrente = fluxo["receita_recorrente"]
    despesa_total = fluxo["despesa_total"]
    receita_total = fluxo["receita_total"]
    despesa_mensal_media = fluxo["despesa_mensal_media"]

    # Taxa poupança recorrente
    taxa_poupanca_recorrente_pct = 0.0
    if receita_recorrente > 0:
        taxa_poupanca_recorrente_pct = ((receita_recorrente - despesa_total) / receita_recorrente) * 100

    # Taxa poupança total
    taxa_poupanca_total_pct = 0.0
    if receita_total > 0:
        taxa_poupanca_total_pct = ((receita_total - despesa_total) / receita_total) * 100

    # Taxa endividamento
    taxa_endividamento_pct = 0.0
    if patrimonio["bruto"] > 0:
        taxa_endividamento_pct = (patrimonio["dividas"] / patrimonio["bruto"]) * 100

    # Cobertura despesas (meses)
    cobertura_despesas_meses = 0.0
    if despesa_mensal_media > 0:
        cobertura_despesas_meses = patrimonio["investivel"] / despesa_mensal_media

    # Rentabilidade: N/D (cannot compute without real performance data)
    rentabilidade_pct = "N/D"

    # Aliquota efetiva IR (placeholder)
    aliquota_efetiva_ir_pct = "N/D"

    return {
        "taxa_poupanca_recorrente_pct": round(taxa_poupanca_recorrente_pct, 2),
        "taxa_poupanca_total_pct": round(taxa_poupanca_total_pct, 2),
        "taxa_endividamento_pct": round(taxa_endividamento_pct, 2),
        "cobertura_despesas_meses": round(cobertura_despesas_meses, 2),
        "rentabilidade_pct": rentabilidade_pct,
        "aliquota_efetiva_ir_pct": aliquota_efetiva_ir_pct,
    }


# ============================================================================
# SCORE CALCULATION
# ============================================================================

def calculate_score(
    ratios: Dict[str, Any],
    patrimonio: Dict[str, Any],
    goals: Dict[str, Any],
    fluxo: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate financial score (0-10 scale)."""
    print("[E5.5] Computing score...")

    # Component 1: Taxa poupança recorrente (0% → 0, 50% → 10)
    taxa_poup = safe_float(ratios["taxa_poupanca_recorrente_pct"])
    score_poup = linear_interpolate(taxa_poup, 0, 50)

    # Component 2: Cobertura despesas (3m → 0, 24m → 10)
    cobertura = safe_float(ratios["cobertura_despesas_meses"])
    score_cobertura = linear_interpolate(cobertura, 3, 24)

    # Component 3: Taxa endividamento (INVERTED: 50% → 0, 5% → 10)
    endiv = safe_float(ratios["taxa_endividamento_pct"])
    score_endiv = linear_interpolate(endiv, 50, 5)  # inverted range

    # Component 4: Progresso IF (5% → 0, 80% → 10)
    if_pct = safe_float(goals["if_pct"])
    score_if = linear_interpolate(if_pct, 5, 80)

    # Component 5: Diversificação (# categorias com saldo > 0)
    composicao = patrimonio.get("composicao", [])
    num_categorias = len([c for c in composicao if c["valor"] > 0])
    score_diversif = linear_interpolate(num_categorias, 1, 5)

    # Weighted average
    componentes = [
        {"nome": "Taxa Poupança Recorrente", "valor": round(taxa_poup, 2), "peso": 2.0, "nota": round(score_poup, 1)},
        {"nome": "Cobertura Despesas (meses)", "valor": round(cobertura, 2), "peso": 1.5, "nota": round(score_cobertura, 1)},
        {"nome": "Taxa Endividamento (inv)", "valor": round(endiv, 2), "peso": 1.5, "nota": round(score_endiv, 1)},
        {"nome": "Progresso IF", "valor": round(if_pct, 2), "peso": 2.0, "nota": round(score_if, 1)},
        {"nome": "Diversificação", "valor": num_categorias, "peso": 1.0, "nota": round(score_diversif, 1)},
    ]

    total_peso = sum(c["peso"] for c in componentes)
    valor_score = sum(c["nota"] * c["peso"] for c in componentes) / total_peso if total_peso > 0 else 0
    valor_score = round(valor_score, 1)

    # Classification
    if valor_score < 2:
        classificacao = "Crítico"
    elif valor_score < 4:
        classificacao = "Atenção"
    elif valor_score < 6:
        classificacao = "Regular"
    elif valor_score < 8:
        classificacao = "Bom"
    else:
        classificacao = "Excelente"

    return {
        "valor": valor_score,
        "max": 10,
        "classificacao": classificacao,
        "componentes": componentes,
    }


# ============================================================================
# ADDITIONAL ANALYSIS SECTIONS
# ============================================================================

def analyze_orcamento_prospectivo(fluxo: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze budgeting & categories."""
    print("[E5.6] Analyzing orcamento prospectivo...")

    despesas_por_cat = fluxo["despesas_por_categoria"]
    num_months = len(fluxo["receita_despesa_mensal_detalhado"]["labels"])

    categorias = {}
    if num_months > 0:
        for cat, total in despesas_por_cat.items():
            categorias[cat] = round(total / num_months, 2)

    total_mensal = sum(categorias.values())

    legenda = (
        "Orçamento prospectivo baseado na média dos últimos 15 meses. "
        "Recomenda-se revisar mensalmente e ajustar projeções."
    )

    return {
        "categorias": categorias,
        "total": round(total_mensal, 2),
        "media_mensal": round(total_mensal, 2),
        "legenda": legenda,
    }


def analyze_reserva_emergencia(
    fluxo: Dict[str, Any],
    patrimonio: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze emergency reserve."""
    print("[E5.7] Analyzing reserva emergencia...")

    despesa_mensal = fluxo["despesa_mensal_media"]
    investivel = patrimonio["investivel"]

    nivel_6_meses = despesa_mensal * 6
    nivel_12_meses = despesa_mensal * 12

    # Simplified composition (use available investment accounts)
    composicao_liquida = {
        "investimentos_david": patrimonio["investimentos_david"],
        "investimentos_mariana": patrimonio["investimentos_mariana"],
        "caixa_moeda_estrangeira": patrimonio["caixa_moeda_estrangeira"],
    }

    total_liquida = sum(composicao_liquida.values())

    # Avaliação
    if total_liquida >= nivel_12_meses:
        avaliacao = "Excelente"
    elif total_liquida >= nivel_6_meses:
        avaliacao = "Adequada"
    else:
        avaliacao = "Insuficiente"

    return {
        "despesas_mensais": round(despesa_mensal, 2),
        "nivel_6_meses": round(nivel_6_meses, 2),
        "nivel_12_meses": round(nivel_12_meses, 2),
        "composicao_liquida": {k: round(v, 2) for k, v in composicao_liquida.items()},
        "total_liquida": round(total_liquida, 2),
        "avaliacao_liquidity": avaliacao,
        "niveis": ["6 meses", "12 meses"],
    }


def analyze_endividamento(patrimonio: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze debt structure."""
    print("[E5.8] Analyzing endividamento...")

    return {
        "total_dividas": patrimonio["dividas"],
        "percentual_patrimonio": round(
            (patrimonio["dividas"] / patrimonio["bruto"] * 100) if patrimonio["bruto"] > 0 else 0,
            2
        ),
        "detalhe": "Financiamento imobiliário (Itaú) + possíveis empréstimos pessoais",
    }


def analyze_previdencia_pgbl() -> Dict[str, Any]:
    """Placeholder for PGBL analysis."""
    print("[E5.9] Analyzing PGBL...")

    return {
        "status": "N/D",
        "nota": "PGBL data não consolidado nesta análise. Revisar com contador.",
    }


def analyze_pontos_fortes(score: Dict[str, Any], ratios: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate strength points based on metrics."""
    print("[E5.10] Identifying pontos fortes...")

    pontos = []

    taxa_poup = safe_float(ratios["taxa_poupanca_recorrente_pct"])
    if taxa_poup > 30:
        pontos.append({
            "titulo": "Taxa de Poupança Saudável",
            "descricao": f"Taxa de poupança recorrente de {taxa_poup:.1f}% demonstra controle de gastos e aporte consistente."
        })

    classificacao = score.get("classificacao", "")
    if classificacao in ["Excelente", "Bom"]:
        pontos.append({
            "titulo": "Score Financeiro Positivo",
            "descricao": f"Classificação {classificacao} indica solidez financeira."
        })

    if not pontos:
        pontos.append({
            "titulo": "Análise em Andamento",
            "descricao": "Pontos fortes serão identificados após consolidação de dados."
        })

    return pontos


def analyze_pontos_urgentes() -> List[Dict[str, str]]:
    """Generate urgent action points."""
    print("[E5.11] Identifying pontos urgentes...")

    return [
        {
            "prioridade": "Alta",
            "acao": "Revisar despesas não identificadas",
            "impacto": "Melhor visualização e controle orçamentário",
            "prazo": "Próximo mês",
        },
        {
            "prioridade": "Média",
            "acao": "Consolidar dados de investimentos",
            "impacto": "Cálculo preciso de rentabilidade",
            "prazo": "T2/2026",
        },
    ]


def analyze_consumo_consciente(fluxo: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze top spending items (>= R$2000)."""
    print("[E5.12] Analyzing consumo consciente...")

    despesas_por_cat = fluxo["despesas_por_categoria"]
    top_gastos = [
        {"categoria": k, "valor": round(v, 2)}
        for k, v in despesas_por_cat.items()
        if v >= 2000
    ]
    top_gastos.sort(key=lambda x: x["valor"], reverse=True)

    return {
        "top_gastos": top_gastos[:5],
        "total_top_5": round(sum(g["valor"] for g in top_gastos[:5]), 2),
    }


def analyze_diagnostico_comportamental() -> List[Dict[str, str]]:
    """Generate behavioral diagnostics (placeholder)."""
    print("[E5.13] Analyzing comportamento...")

    return [
        {
            "comportamento": "Aporte disciplinado",
            "recomendacao": "Manter frequência mensal de R$20.000."
        },
    ]


# ============================================================================
# MAIN ANALYSIS ORCHESTRATION
# ============================================================================

def main():
    """Main orchestration."""
    print("\n" + "="*70)
    print("E5 ANALYSIS — NUMERIC PORTIONS")
    print("="*70)
    print(f"[E5.0] Starting analysis at {datetime.now().isoformat()}")

    # Create output directory
    E5_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # Load input files
    print("\n[E5.1] Loading E4 unified data...")
    receitas = load_json(FILE_RECEITAS)
    despesas = load_json(FILE_DESPESAS)
    patrimonio_input = load_json(FILE_PATRIMONIO)
    investimentos = load_json(FILE_INVESTIMENTOS)
    fluxo_mensal = load_json(FILE_FLUXO_MENSAL)
    baseline = load_json(FILE_BASELINE)

    # Load existing output if present (to preserve narrativas)
    existing_output = {}
    if FILE_OUTPUT.exists():
        existing_output = load_json(FILE_OUTPUT)

    print(f"  ✓ Receitas: {receitas.get('total_geral', 0):.2f}")
    print(f"  ✓ Despesas: {despesas.get('total_geral', 0):.2f}")

    # ========================================================================
    # COMPUTE NUMERIC SECTIONS
    # ========================================================================

    patrimonio = analyze_patrimonio(baseline)

    # Determine period string
    periodo_dados = receitas.get("periodo", "2025-01 a 2026-03")

    goals = analyze_goals(patrimonio)
    fluxo = analyze_fluxo_caixa(receitas, despesas, fluxo_mensal)
    ratios = analyze_ratios(fluxo, patrimonio, goals)
    score = calculate_score(ratios, patrimonio, goals, fluxo)

    orcamento = analyze_orcamento_prospectivo(fluxo)
    reserva = analyze_reserva_emergencia(fluxo, patrimonio)
    endividamento = analyze_endividamento(patrimonio)
    previdencia = analyze_previdencia_pgbl()

    pontos_fortes = analyze_pontos_fortes(score, ratios)
    pontos_urgentes = analyze_pontos_urgentes()
    consumo = analyze_consumo_consciente(fluxo)
    diagnostico = analyze_diagnostico_comportamental()

    # ========================================================================
    # BUILD OUTPUT JSON
    # ========================================================================

    output = {
        "periodo_dados": periodo_dados,
        "data_analise": TODAY.isoformat(),
        "patrimonio": patrimonio,
        "goals": goals,
        "fluxo_caixa": fluxo,
        "ratios": ratios,
        "score": score,
        "orcamento_prospectivo": orcamento,
        "reserva_emergencia": reserva,
        "endividamento": endividamento,
        "previdencia_pgbl": previdencia,
        "pontos_fortes": pontos_fortes,
        "pontos_urgentes": pontos_urgentes,
        "equilibrio_cerbasi": {
            "presente": "Consolidação patrimonial",
            "futuro": "Independência Financeira 2035",
        },
        "tarefas": [],
        "tarefas_status": {},
        "alertas": [],
        "consumo_consciente": consumo,
        "diagnostico_comportamental": diagnostico,
    }

    # PRESERVE narrativas from existing output (E5.N will add these later)
    if "narrativas" in existing_output:
        output["narrativas"] = existing_output["narrativas"]
        print("\n  ✓ Preserving existing narrativas from previous run")

    # ========================================================================
    # WRITE OUTPUT
    # ========================================================================

    FILE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[E5.FINAL] Analysis complete!")
    print(f"  ✓ Output saved to: {FILE_OUTPUT}")
    print(f"\n  === SUMMARY ===")
    print(f"  Score: {score['valor']}/10 ({score['classificacao']})")
    print(f"  Taxa Poupança: {ratios['taxa_poupanca_recorrente_pct']:.1f}%")
    print(f"  Patrimônio Bruto: R$ {patrimonio['bruto']:,.2f}")
    print(f"  Patrimônio Investível: R$ {patrimonio['investivel']:,.2f}")
    print(f"  IF Meta: R$ {goals['if_meta']:,.2f}")
    print(f"  IF Progresso: {goals['if_pct']:.1f}%")
    print(f"  Prazo IF (realista): {goals['prazo_anos_realista']:.1f} anos → {goals['ano_if']}")
    print(f"\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()

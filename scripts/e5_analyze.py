#!/usr/bin/env python3
"""
E5 Analysis Script — NUMERIC portions only
Reads E4 unified files and computes analise_financeira-5_analysis.json
Does NOT generate narrativas (that's E5.N, done by LLM).

Author: Claude Haiku 4.5
Date: 2026-04-05
"""

import json
import math
import sys
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
CONFIG_TAREFAS = PROJECT_DIR / "config" / "tarefas.md"

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
# CONSTANTS (loaded from config/family_members.json when available)
# ============================================================================
def _load_titular_dob() -> date:
    """Load titular date of birth from family config, with fallback."""
    fm_path = PROJECT_DIR / "config" / "family_members.json"
    if fm_path.exists():
        with open(fm_path, "r", encoding="utf-8") as f:
            fm = json.load(f)
        dob_str = fm.get("membros", {}).get("david", {}).get("data_nascimento", "1981-09-05")
        parts = dob_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    return date(1981, 9, 5)  # fallback

DAVID_DOB = _load_titular_dob()
TODAY = date.today()

# One-time income keywords and categories (not counted in recorrente)
# v5.3.1: load from categorization.json if available, with hardcoded fallback
def _load_one_time_config():
    cat_path = PROJECT_DIR / "config" / "categorization.json"
    if cat_path.exists():
        with open(cat_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        keywords = cat.get("one_time_income_keywords", None)
        categories = cat.get("one_time_income_categories", None)
        if keywords is not None and categories is not None:
            return keywords, set(categories)
    # Fallback if config key not yet added
    return (
        ["fgts", "restituicao", "bolsa", "bonus", "pompeia", "venda"],
        {"receita_venda_ativo", "receita_resgate", "receita_fgts", "receita_restituicao"}
    )

ONE_TIME_INCOME_KEYWORDS, ONE_TIME_INCOME_CATEGORIES = _load_one_time_config()


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


def load_json(path: Path, required: bool = False) -> Dict[str, Any]:
    """Load JSON file, return empty dict if missing.
    If required=True, raises FileNotFoundError / ValueError instead of returning {}."""
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {path.name}")
        print(f"  ⚠️  File not found: {path.name}")
        return {}
    try:
        # Handle 0-byte files (truncated by filesystem that doesn't allow delete)
        if path.stat().st_size == 0:
            if required:
                raise ValueError(f"Arquivo obrigatório está vazio (0 bytes): {path.name}")
            print(f"  ⚠️  File is empty (0 bytes): {path.name}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if required and not data:
            raise ValueError(f"Arquivo obrigatório está vazio: {path.name}")
        return data
    except (FileNotFoundError, ValueError):
        raise
    except Exception as e:
        if required:
            raise
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

def _resolve_members(baseline: Dict[str, Any]) -> tuple:
    """Resolve members from baseline, handling multiple formats:
    1. Dict format: members/membros as dict with david/mariana sub-dicts
    2. List-of-dicts format: membros as list of dicts with "nome" key
    3. E1.5 declarations format: membros as list of strings + declarations[]
    4. Consolidated format: top-level imoveis_consolidados, etc.
    """
    members = baseline.get("members", baseline.get("membros", {}))
    if isinstance(members, list):
        # Check if list contains dicts (format 2) or strings (format 3)
        has_dicts = any(isinstance(m, dict) for m in members)
        if has_dicts:
            david_data, mariana_data = {}, {}
            for m in members:
                if not isinstance(m, dict):
                    continue
                nome = m.get("nome", "").lower()
                if "david" in nome:
                    david_data = m
                elif "mariana" in nome:
                    mariana_data = m
            return david_data, mariana_data
        # Format 3: membros is list of strings + declarations exist
        if baseline.get("declarations"):
            return _build_members_from_declarations(baseline)
    if members and isinstance(members, dict):
        return members.get("david", {}), members.get("mariana", {})
    # --- v1.5 consolidated format: no "members" key ---
    # Build synthetic member dicts from top-level consolidated lists
    return _build_members_from_consolidated(baseline)


def _build_members_from_declarations(baseline: Dict[str, Any]) -> tuple:
    """Build synthetic david/mariana member dicts from E1.5 declarations format.

    The E1.5 baseline has declarations[] where each declaration contains
    bens_direitos[] using IRPF grupo/codigo classification:
      G01 = Imóveis, G02 = Veículos, G03 = Participações societárias (ações),
      G04 = Aplicações renda fixa, G06 = Depósitos/contas/moeda estrangeira,
      G07 = Fundos de investimento, G99 = Outros bens

    Uses the most recent declaration per member (highest ano_base).
    """
    declarations = baseline.get("declarations", [])
    if not declarations:
        return {}, {}

    # Group declarations by member, keep most recent ano_base
    member_decls: Dict[str, Dict] = {}
    for decl in declarations:
        membro = decl.get("membro", "").lower()
        ano = decl.get("ano_base", 0)
        key = "david" if "david" in membro else "mariana" if "mariana" in membro else None
        if key is None:
            continue
        if key not in member_decls or ano > member_decls[key].get("ano_base", 0):
            member_decls[key] = decl

    def _classify_bens(bens_direitos: list) -> dict:
        """Classify bens_direitos by IRPF grupo into imoveis, veiculos, etc."""
        imoveis = []
        veiculos = []
        investimentos = []
        contas_bancarias = []

        for bem in bens_direitos:
            grupo = str(bem.get("grupo", "")).zfill(2)
            valor = safe_float(bem.get("valor_31_12_atual", 0))
            descricao = bem.get("descricao", "")
            entry = {"descricao": descricao, "valor_31_12_ano_base": valor}

            if grupo == "01":  # Imóveis
                imoveis.append(entry)
            elif grupo == "02":  # Veículos
                veiculos.append(entry)
            elif grupo in ("03", "04", "07", "99"):  # Ações, RF, Fundos, Outros
                investimentos.append(entry)
            elif grupo == "06":  # Depósitos, contas, moeda estrangeira
                contas_bancarias.append(entry)
            else:
                investimentos.append(entry)

        return {
            "imoveis": imoveis,
            "veiculos": veiculos,
            "investimentos": investimentos,
            "contas_bancarias": contas_bancarias,
        }

    results = {}
    for key in ("david", "mariana"):
        decl = member_decls.get(key)
        if not decl:
            results[key] = {}
            continue

        bens = _classify_bens(decl.get("bens_direitos", []))
        total_bens = safe_float(decl.get("total_bens", 0))
        # total_dividas not directly in declarations — compute from dívidas if present
        total_dividas = 0.0
        for dv in baseline.get("dividas", []):
            if key == "david" and "david" in dv.get("proprietario", "").lower():
                total_dividas += safe_float(dv.get("saldo_31_12", 0))
            elif key == "mariana" and "mariana" in dv.get("proprietario", "").lower():
                total_dividas += safe_float(dv.get("saldo_31_12", 0))

        # Synthetic total from classified bens
        synthetic_total = sum(
            safe_float(b.get("valor_31_12_ano_base", 0))
            for cat in bens.values()
            for b in cat
        )

        # Use declaration total_bens as authoritative if available
        if total_bens > 0 and abs(synthetic_total - total_bens) > 1.0:
            print(f"  [INFO] {key}: synthetic bens (R$ {synthetic_total:,.2f}) vs declaration total_bens (R$ {total_bens:,.2f})")

        results[key] = {
            "total_bens": total_bens if total_bens > 0 else synthetic_total,
            "total_dividas": total_dividas,
            "bens": bens,
        }

    print(f"  [E5.1] Built members from declarations: David R$ {results.get('david', {}).get('total_bens', 0):,.2f}, Mariana R$ {results.get('mariana', {}).get('total_bens', 0):,.2f}")
    return results.get("david", {}), results.get("mariana", {})


def _build_members_from_consolidated(baseline: Dict[str, Any]) -> tuple:
    """Build synthetic david/mariana member dicts from the v1.5 consolidated
    baseline format (top-level lists keyed by imoveis_consolidados, etc.)."""
    # Determine the most recent year available
    pat_ano = baseline.get("patrimonio_por_ano", {})
    anos = sorted(pat_ano.keys())
    ano_ref = anos[-1] if anos else "2024"

    # Totals from patrimonio_por_ano
    ano_data = pat_ano.get(ano_ref, {})
    total_bens = safe_float(ano_data.get("total_bens", 0))
    total_dividas = safe_float(ano_data.get("total_dividas", 0))

    # Split imoveis by proprietario
    david_imoveis, mariana_imoveis = [], []
    for im in baseline.get("imoveis_consolidados", []):
        val = safe_float(im.get("valores_31_12", {}).get(ano_ref, 0))
        entry = {
            "descricao": im.get("descricao", ""),
            "valor_31_12_ano_base": val,
        }
        if im.get("proprietario", "").lower() == "mariana":
            mariana_imoveis.append(entry)
        else:
            david_imoveis.append(entry)

    # Split investimentos by proprietario
    david_inv, mariana_inv = [], []
    for inv in baseline.get("investimentos_consolidados", []):
        val = safe_float(inv.get("valores_31_12", {}).get(ano_ref, 0))
        entry = {
            "descricao": inv.get("descricao", ""),
            "tipo": inv.get("tipo", ""),
            "valor_31_12_ano_base": val,
        }
        if inv.get("proprietario", "").lower() == "mariana":
            mariana_inv.append(entry)
        else:
            david_inv.append(entry)

    # Veiculos
    david_veiculos, mariana_veiculos = [], []
    for v in baseline.get("veiculos_consolidados", []):
        val = safe_float(v.get("valores_31_12", {}).get(ano_ref, 0))
        entry = {"descricao": v.get("descricao", ""), "valor_31_12_ano_base": val}
        if v.get("proprietario", "").lower() == "mariana":
            mariana_veiculos.append(entry)
        else:
            david_veiculos.append(entry)

    # Dividas — sum per proprietario
    david_dividas, mariana_dividas = 0.0, 0.0
    for dv in baseline.get("dividas", []):
        val = safe_float(dv.get("saldo_31_12", {}).get(ano_ref, 0))
        if dv.get("proprietario", "").lower() == "mariana":
            mariana_dividas += val
        else:
            david_dividas += val

    # Sum bens per member
    david_bens_total = (
        sum(safe_float(im.get("valor_31_12_ano_base", 0)) for im in david_imoveis)
        + sum(safe_float(inv.get("valor_31_12_ano_base", 0)) for inv in david_inv)
        + sum(safe_float(v.get("valor_31_12_ano_base", 0)) for v in david_veiculos)
    )
    mariana_bens_total = (
        sum(safe_float(im.get("valor_31_12_ano_base", 0)) for im in mariana_imoveis)
        + sum(safe_float(inv.get("valor_31_12_ano_base", 0)) for inv in mariana_inv)
        + sum(safe_float(v.get("valor_31_12_ano_base", 0)) for v in mariana_veiculos)
    )

    david_data = {
        "total_bens": david_bens_total,
        "total_dividas": david_dividas,
        "bens": {
            "imoveis": david_imoveis,
            "investimentos": david_inv,
            "veiculos": david_veiculos,
            "contas_bancarias": [],
        },
    }
    mariana_data = {
        "total_bens": mariana_bens_total,
        "total_dividas": mariana_dividas,
        "bens": {
            "imoveis": mariana_imoveis,
            "investimentos": mariana_inv,
            "veiculos": mariana_veiculos,
            "contas_bancarias": [],
        },
    }

    # Sanity check: synthetic totals vs patrimonio_por_ano
    synthetic_total = david_bens_total + mariana_bens_total
    if abs(synthetic_total - total_bens) > 1.0:
        print(f"  [INFO] Synthetic total_bens (R$ {synthetic_total:,.2f}) vs patrimonio_por_ano (R$ {total_bens:,.2f})")
        print(f"  [INFO] Using patrimonio_por_ano total_bens as authoritative")
        # Distribute the difference proportionally or assign to david
        diff = total_bens - synthetic_total
        david_data["total_bens"] += diff

    return david_data, mariana_data


def _get_bens(member: Dict[str, Any]) -> Dict[str, Any]:
    """Get bens sub-dict, handling nested (bens.imoveis) or flat (imoveis) layouts."""
    if "bens" in member and isinstance(member["bens"], dict):
        return member["bens"]
    return member


def _imovel_valor(imovel: Dict[str, Any]) -> float:
    """Extract property value from baseline imovel, trying multiple field names."""
    for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
        v = imovel.get(key)
        if v is not None:
            return safe_float(v)
    return 0.0


def _imovel_desc(imovel: Dict[str, Any]) -> str:
    """Get imovel description, trying multiple field names."""
    return (imovel.get("description") or imovel.get("descricao") or "").lower()


def _veiculo_valor(veiculo: Dict[str, Any]) -> float:
    """Extract vehicle value from baseline."""
    for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
        v = veiculo.get(key)
        if v is not None:
            return safe_float(v)
    return 0.0


def _investimento_valor(inv) -> float:
    """Extract investment value — handles both dict-with-valor and scalar."""
    if isinstance(inv, dict):
        for key in ("valor_31_12_ano_base", "valor"):
            v = inv.get(key)
            if v is not None:
                return safe_float(v)
    return safe_float(inv)


def analyze_patrimonio(baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze patrimonio from baseline data."""
    print("[E5.1] Analyzing patrimonio...")

    david, mariana = _resolve_members(baseline)

    total_bens = safe_float(david.get("total_bens", 0)) + safe_float(mariana.get("total_bens", 0))
    total_dividas = safe_float(david.get("total_dividas", david.get("dividas", 0))) + safe_float(mariana.get("total_dividas", mariana.get("dividas", 0)))

    patrimonio_bruto = total_bens
    patrimonio_liquido = patrimonio_bruto - total_dividas

    david_bens = _get_bens(david)
    mariana_bens = _get_bens(mariana)

    # Residência: Tasso da Silveira (David's primary residence)
    residencia = 0.0
    imoveis_investimento = 0.0

    for imovel in david_bens.get("imoveis", []):
        if "tasso da silveira" in _imovel_desc(imovel):
            residencia = _imovel_valor(imovel)
        else:
            imoveis_investimento += _imovel_valor(imovel)

    for imovel in mariana_bens.get("imoveis", []):
        imoveis_investimento += _imovel_valor(imovel)

    # Veículos
    veiculos = 0.0
    for veiculo in david_bens.get("veiculos", []):
        veiculos += _veiculo_valor(veiculo)
    for veiculo in mariana_bens.get("veiculos", []):
        veiculos += _veiculo_valor(veiculo)

    # Investment accounts
    investimentos_david = 0.0
    investimentos_mariana = 0.0

    for inv in david_bens.get("investimentos", []):
        investimentos_david += _investimento_valor(inv)
    contas_d = david_bens.get("contas_bancarias", [])
    if isinstance(contas_d, list):
        for inv in contas_d:
            investimentos_david += _investimento_valor(inv)
    else:
        investimentos_david += safe_float(contas_d)
    # saldo_corretora + moeda_estrangeira + outros
    for extra_key in ("saldo_corretora", "moeda_estrangeira", "outros"):
        investimentos_david += safe_float(david_bens.get(extra_key, 0))

    for inv in mariana_bens.get("investimentos", []):
        investimentos_mariana += _investimento_valor(inv)
    contas_m = mariana_bens.get("contas_bancarias", [])
    if isinstance(contas_m, list):
        for inv in contas_m:
            investimentos_mariana += _investimento_valor(inv)
    else:
        investimentos_mariana += safe_float(contas_m)
    for extra_key in ("outros",):
        investimentos_mariana += safe_float(mariana_bens.get(extra_key, 0))

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
    investivel = max(0, investivel)
    if investivel >= patrimonio_bruto and patrimonio_bruto > 0:
        print(f"  [WARN] patrimonio_investivel ({investivel}) >= patrimonio_bruto ({patrimonio_bruto})")

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
        "tabela_categorias": composicao,
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

    # Prazo realista (juros compostos: PV crescendo + aportes mensais)
    # Resolve para n em: PV*(1+r)^n + PMT*((1+r)^n - 1)/r = FV
    # onde PV=investivel, PMT=aporte mensal, FV=if_meta, r=taxa mensal
    # Try to extract from life_plan or config with fallback and warning
    aporte_mensal = 20000
    retorno_real_anual = 0.06  # 6% a.a. real (cenário realista)

    # TODO: Try to load aporte_mensal and retorno_real_anual from config/tarefas.md or life_plan
    # For now, use hardcoded defaults with warning
    print(f"  [WARN] aporte_mensal={aporte_mensal} e retorno_real_anual={retorno_real_anual} — values hardcoded, should load from config/tarefas.md")

    r = (1 + retorno_real_anual) ** (1 / 12) - 1  # taxa mensal equivalente

    if investivel >= if_meta:
        prazo_anos = 0.0
    elif r > 0 and aporte_mensal > 0:
        # FV = PV*(1+r)^n + PMT*((1+r)^n - 1)/r
        # Seja X = (1+r)^n => FV = PV*X + PMT*(X-1)/r
        # FV = X*(PV + PMT/r) - PMT/r
        # X = (FV + PMT/r) / (PV + PMT/r)
        numerator = if_meta + aporte_mensal / r
        denominator = investivel + aporte_mensal / r
        if denominator > 0 and numerator / denominator > 0:
            n_meses = math.log(numerator / denominator) / math.log(1 + r)
            prazo_anos = max(0, n_meses / 12)
        else:
            prazo_anos = 999
    else:
        prazo_anos = 999

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
    # v5.2: check BOTH description keywords AND category for one-time classification
    receita_one_time = 0.0
    receita_recorrente = receita_total

    receita_dados = receitas.get("dados", {})
    for categoria, transacoes in receita_dados.items():
        # v5.2: entire category is one-time (venda_ativo, resgate, fgts, restituicao)
        if categoria in ONE_TIME_INCOME_CATEGORIES:
            cat_total = sum(safe_float(txn.get("valor", 0)) for txn in transacoes)
            receita_one_time += cat_total
            receita_recorrente -= cat_total
            continue
        # Fallback: check individual descriptions
        for txn in transacoes:
            descricao = txn.get("descricao", "").lower()
            if is_one_time_income(descricao):
                receita_one_time += safe_float(txn.get("valor", 0))
                receita_recorrente -= safe_float(txn.get("valor", 0))

    # Count months in period
    periodo = receitas.get("periodo", "")
    # Parse "YYYY-MM a YYYY-MM" → count months from fluxo_mensal
    num_months = len(fluxo_mensal.get("meses_ordenados", []))
    if num_months == 0:
        print("  [WARN] num_months=0, calculando do período...")
        # Try to derive from periodo key if available, else warn
        num_months = 1  # minimum
        print(f"  [WARN] Usando num_months={num_months} como fallback — verifique o dado")

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
                "label": cat.replace("_", " ").title(),
                "data": data,
            })

    # Totals by month
    totais_receita = [safe_float(receita_por_mes.get(mes, {}).get("_total", 0)) for mes in meses]
    totais_despesa = [safe_float(despesa_por_mes.get(mes, {}).get("_total", 0)) for mes in meses]

    # Build tabela_receitas for E6 card (list of {categoria, valor, pct})
    total_receita_por_fonte = sum(v for v in por_fonte.values() if v > 0)
    tabela_receitas = []
    for cat, val in sorted(por_fonte.items(), key=lambda x: x[1], reverse=True):
        if val > 0:
            tabela_receitas.append({
                "categoria": cat.replace("_", " ").title(),
                "valor": round(val, 2),
                "pct": round((val / total_receita_por_fonte) * 100, 2) if total_receita_por_fonte > 0 else 0,
            })

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
        "tabela_receitas": tabela_receitas,
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
    # TODO: Attempt to load rentabilidade from investimentos tracking data before defaulting to N/D
    # For now, mark as pending data integration rather than false urgent action
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
    score_diversif = linear_interpolate(num_categorias, 1, 6)

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

    # Composition of liquid reserves
    # E6 card expects: total_liquido and cobertura_meses inside composicao_liquida
    inv_david = patrimonio["investimentos_david"]
    inv_mariana = patrimonio["investimentos_mariana"]
    caixa = patrimonio["caixa_moeda_estrangeira"]
    total_liquida = inv_david + inv_mariana + caixa

    cobertura_meses = total_liquida / despesa_mensal if despesa_mensal > 0 else 0

    composicao_liquida = {
        "investimentos_david": inv_david,
        "investimentos_mariana": inv_mariana,
        "caixa_moeda_estrangeira": caixa,
        "total_liquido": round(total_liquida, 2),
        "cobertura_meses": round(cobertura_meses, 1),
    }

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
        "cobertura_meses": round(cobertura_meses, 1),
        "avaliacao_liquidity": avaliacao,
        "niveis": ["6 meses", "12 meses"],
    }


def analyze_investimentos_classes(baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze investments by asset class from baseline data."""
    print("[E5.7b] Analyzing investimentos por classe...")

    david, mariana = _resolve_members(baseline)
    david_bens = _get_bens(david)
    mariana_bens = _get_bens(mariana)

    classes = {
        "Renda Fixa": 0.0,
        "Ações": 0.0,
        "Imóveis Investimento": 0.0,
        "Cripto": 0.0,
        "Contas Bancárias": 0.0,
        "Outros": 0.0,
    }

    def classify_investment(tipo_str: str, valor: float):
        tipo_lower = tipo_str.lower()
        if any(kw in tipo_lower for kw in ["acoes", "ações", "itsa", "brkm", "petr", "etf", "ivvb"]):
            classes["Ações"] += valor
        elif any(kw in tipo_lower for kw in ["renda fixa", "cdb", "rdb", "lci", "lca", "tesouro", "debenture", "certificado de deposito"]):
            classes["Renda Fixa"] += valor
        elif any(kw in tipo_lower for kw in ["cripto", "bitcoin", "ethereum", "binance"]):
            classes["Cripto"] += valor
        elif any(kw in tipo_lower for kw in ["banco", "picpay", "nubank", "saldo", "conta"]):
            classes["Contas Bancárias"] += valor
        else:
            classes["Outros"] += valor

    for inv in david_bens.get("investimentos", []):
        tipo = inv.get("tipo", "")
        valor = safe_float(inv.get("valor", inv.get("valor_31_12_ano_base", 0)))
        if valor > 0:
            classify_investment(tipo, valor)

    for inv in mariana_bens.get("investimentos", []):
        tipo = inv.get("tipo", "")
        valor = safe_float(inv.get("valor", inv.get("valor_31_12_ano_base", 0)))
        if valor > 0:
            classify_investment(tipo, valor)

    # Add cripto from top-level fields
    classes["Cripto"] += safe_float(david_bens.get("criptos", 0))
    classes["Cripto"] += safe_float(mariana_bens.get("criptos", 0))

    # Add contas bancárias from top-level
    contas_d = david_bens.get("contas_bancarias", 0)
    if isinstance(contas_d, (int, float)):
        classes["Contas Bancárias"] += safe_float(contas_d)
    contas_m = mariana_bens.get("contas_bancarias", 0)
    if isinstance(contas_m, (int, float)):
        classes["Contas Bancárias"] += safe_float(contas_m)

    # Add imoveis investimento
    for imovel in david_bens.get("imoveis", []):
        if "tasso da silveira" not in _imovel_desc(imovel):
            classes["Imóveis Investimento"] += _imovel_valor(imovel)
    for imovel in mariana_bens.get("imoveis", []):
        classes["Imóveis Investimento"] += _imovel_valor(imovel)

    total = sum(classes.values())
    tabela_classes = []
    for cat, val in sorted(classes.items(), key=lambda x: x[1], reverse=True):
        if val > 0:
            tabela_classes.append({
                "categoria": cat,
                "valor": round(val, 2),
                "pct": round((val / total) * 100, 2) if total > 0 else 0,
            })

    return {
        "tabela_classes": tabela_classes,
        "total": round(total, 2),
    }


def analyze_endividamento(patrimonio: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze debt structure."""
    print("[E5.8] Analyzing endividamento...")

    david, mariana = _resolve_members(baseline)

    dividas_lista = []
    # Extract dividas from baseline members
    for member, nome in [(david, "David"), (mariana, "Mariana")]:
        divida_val = safe_float(member.get("total_dividas", member.get("dividas", 0)))
        if divida_val > 0:
            dividas_lista.append({
                "descricao": f"Financiamento imobiliário ({nome})",
                "saldo_devedor": round(divida_val, 2),
                "parcela_mensal": 0,
                "taxa_juros": "N/D",
            })

    return {
        "total_dividas": patrimonio["dividas"],
        "percentual_patrimonio": round(
            (patrimonio["dividas"] / patrimonio["bruto"] * 100) if patrimonio["bruto"] > 0 else 0,
            2
        ),
        "dividas": dividas_lista,
        "detalhe": "Financiamento imobiliário (Itaú)",
    }


def analyze_previdencia_pgbl(fluxo: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze PGBL optimization potential from PJ income."""
    print("[E5.9] Analyzing PGBL...")

    receita_pj = safe_float(fluxo.get("por_fonte", {}).get("receita_pj", 0))
    num_months = len(fluxo.get("receita_despesa_mensal_detalhado", {}).get("labels", []))
    if num_months == 0:
        num_months = 15

    receita_pj_anual = receita_pj * (12 / num_months) if num_months > 0 else 0

    # Lucro presumido: 32% do faturamento como base tributável
    renda_tributavel = receita_pj_anual * 0.32

    if renda_tributavel <= 0:
        return {
            "status": "N/D",
            "nota": "Sem receita PJ identificada para cálculo de PGBL.",
            "renda_tributavel_anual": 0,
            "limite_pgbl_anual": 0,
            "aporte_mensal": 0,
            "aliquota_marginal": 0,
            "economia_ir_anual": 0,
        }

    limite_pgbl = renda_tributavel * 0.12

    # Alíquota marginal IRPF (tabela progressiva simplificada)
    if renda_tributavel > 55976.16 * 1:  # acima da faixa de 27.5%
        aliquota_marginal = 27.5
    elif renda_tributavel > 33919.80 * 1:
        aliquota_marginal = 22.5
    elif renda_tributavel > 24556.65 * 1:
        aliquota_marginal = 15.0
    else:
        aliquota_marginal = 7.5

    economia_ir = limite_pgbl * (aliquota_marginal / 100)

    return {
        "status": "Calculado",
        "nota": f"Base: receita PJ anualizada R$ {receita_pj_anual:,.0f}, lucro presumido 32%.",
        "renda_tributavel_anual": round(renda_tributavel, 2),
        "limite_pgbl_anual": round(limite_pgbl, 2),
        "aporte_mensal": round(limite_pgbl / 12, 2),
        "aliquota_marginal": aliquota_marginal,
        "economia_ir_anual": round(economia_ir, 2),
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


def parse_tarefas_md() -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Parse config/tarefas.md into structured task list.

    Returns:
        (tarefas, tarefas_status) where:
        - tarefas: list of {n, t, p, e, categoria, impacto, ref} for template JS
        - tarefas_status: dict {str(n): "pendente"|"feito"|"cancelado"}
    """
    print("[E5.10a] Parsing config/tarefas.md...")

    if not CONFIG_TAREFAS.exists():
        print("  ⚠ config/tarefas.md not found — falling back to dynamic generation")
        return [], {}

    text = CONFIG_TAREFAS.read_text(encoding="utf-8")

    # Priority mapping: S=alta, R=media, O=baixa
    prio_map = {"S": "alta", "R": "media", "O": "baixa"}

    tarefas = []
    tarefas_status = {}

    # Parse each section (Essenciais, Recomendadas, Opcionais)
    # Match table rows: | # | Tarefa | Categoria | Prazo | Status | Ref |
    # Skip header rows (containing "---" or "Tarefa")
    section_prio = None
    for line in text.split("\n"):
        line = line.strip()

        # Detect section headers for priority
        if line.startswith("## Essenciais"):
            section_prio = "S"
        elif line.startswith("## Recomendadas"):
            section_prio = "R"
        elif line.startswith("## Opcionais"):
            section_prio = "O"
        elif line.startswith("## Concluídas") or line.startswith("## Canceladas") or line.startswith("## Notas"):
            section_prio = None  # Stop parsing active tasks

        if section_prio is None:
            continue

        # Parse table row
        if not line.startswith("|") or "---" in line or "Tarefa" in line:
            continue

        parts = [p.strip() for p in line.split("|")]
        # parts[0] = "" (before first |), parts[1] = #, parts[2] = Tarefa, ...
        if len(parts) < 7:
            continue

        try:
            num = int(parts[1])
        except (ValueError, IndexError):
            continue

        tarefa_text = parts[2]
        categoria = parts[3]
        prazo = parts[4]
        status = parts[5].lower().strip()
        ref = parts[6] if len(parts) > 6 else ""

        prio = prio_map.get(section_prio, "media")

        tarefas.append({
            "n": num,
            "t": tarefa_text,
            "p": prio,
            "e": prazo,
            "categoria": categoria,
            "ref": ref,
        })
        tarefas_status[str(num)] = status if status in ("pendente", "feito", "cancelado") else "pendente"

    print(f"  ✓ Parsed {len(tarefas)} tasks from tarefas.md")
    essenciais = sum(1 for t in tarefas if t["p"] == "alta")
    recomendadas = sum(1 for t in tarefas if t["p"] == "media")
    opcionais = sum(1 for t in tarefas if t["p"] == "baixa")
    print(f"    Essenciais: {essenciais} | Recomendadas: {recomendadas} | Opcionais: {opcionais}")
    feitas = sum(1 for v in tarefas_status.values() if v == "feito")
    print(f"    Pendentes: {len(tarefas) - feitas} | Feitas: {feitas}")

    return tarefas, tarefas_status


def analyze_pontos_urgentes(ratios: Dict[str, Any], reserva: Dict[str, Any], patrimonio: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate urgent action points based on real metrics."""
    print("[E5.11] Identifying pontos urgentes...")

    urgentes = []

    # Check: emergency reserve below 6 months
    cobertura = reserva.get("cobertura_meses", 0)
    if cobertura < 6:
        urgentes.append({
            "prioridade": "Alta",
            "acao": "Reforçar reserva de emergência",
            "impacto": f"Cobertura atual de {cobertura:.0f} meses — abaixo do mínimo de 6",
            "prazo": "Imediato",
        })

    # Check: high debt ratio
    endiv = safe_float(ratios.get("taxa_endividamento_pct", 0))
    if endiv > 20:
        urgentes.append({
            "prioridade": "Alta",
            "acao": "Reduzir endividamento",
            "impacto": f"Taxa de endividamento em {endiv:.1f}% — meta < 20%",
            "prazo": "Próximo trimestre",
        })

    # Check: no insurance data found
    urgentes.append({
        "prioridade": "Alta",
        "acao": "Contratar seguro de vida e invalidez",
        "impacto": "Proteção patrimonial da família — nenhuma apólice identificada",
        "prazo": "Abr/2026",
    })

    # Check: rentabilidade not measured
    if ratios.get("rentabilidade_pct") == "N/D":
        urgentes.append({
            "prioridade": "Média",
            "acao": "Consolidar dados de rentabilidade dos investimentos",
            "impacto": "Sem dados de performance, impossível otimizar alocação",
            "prazo": "T2/2026",
        })

    return urgentes


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


def analyze_diagnostico_comportamental(fluxo: Dict[str, Any], ratios: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate behavioral diagnostics from financial data."""
    print("[E5.13] Analyzing comportamento...")

    diagnosticos = []

    taxa_poup = safe_float(ratios.get("taxa_poupanca_recorrente_pct", 0))
    if taxa_poup > 25:
        diagnosticos.append({
            "padrao": "Disciplina de poupança",
            "evidencia": f"Taxa de poupança recorrente de {taxa_poup:.1f}% — acima da referência de 25%",
            "mudanca_sugerida": "Manter e automatizar aportes mensais",
        })
    elif taxa_poup > 0:
        diagnosticos.append({
            "padrao": "Poupança abaixo do ideal",
            "evidencia": f"Taxa de {taxa_poup:.1f}% — referência mínima: 25%",
            "mudanca_sugerida": "Revisar despesas variáveis e aumentar aporte",
        })

    despesa_total = safe_float(fluxo.get("despesa_total", 0))
    receita_total = safe_float(fluxo.get("receita_total", 0))
    if receita_total > 0:
        one_time_pct = safe_float(fluxo.get("receita_one_time", 0)) / receita_total * 100
        if one_time_pct > 30:
            diagnosticos.append({
                "padrao": "Alta dependência de receita pontual",
                "evidencia": f"{one_time_pct:.0f}% da receita é não-recorrente (resgates, vendas)",
                "mudanca_sugerida": "Não contar com receita pontual para orçamento; alocar direto para investimentos",
            })

    if not diagnosticos:
        diagnosticos.append({
            "padrao": "Análise em andamento",
            "evidencia": "Dados insuficientes para diagnóstico comportamental",
            "mudanca_sugerida": "Consolidar mais meses de dados",
        })

    return diagnosticos


def analyze_equilibrio_cerbasi(fluxo: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze Cerbasi balance: presente vs futuro spending."""
    print("[E5.14] Analyzing equilíbrio Cerbasi...")

    despesas = fluxo.get("despesas_por_categoria", {})

    # Categorias "presente" (gastos correntes)
    cats_presente = {"moradia", "alimentacao", "transporte", "saude", "lazer",
                     "servicos_domesticos", "pets", "cuidados_pessoais",
                     "assinaturas", "vestuario", "compras_online"}
    # Categorias "futuro" (investimento no futuro)
    cats_futuro = {"educacao", "investimentos", "previdencia", "financeiro",
                   "reserva_desejos", "poupanca", "aportes"}

    gasto_presente = sum(v for k, v in despesas.items() if k in cats_presente)
    gasto_futuro = sum(v for k, v in despesas.items() if k in cats_futuro)
    gasto_total = gasto_presente + gasto_futuro

    # Add uncategorized to presente
    gasto_nao_classificado = sum(v for k, v in despesas.items()
                                  if k not in cats_presente and k not in cats_futuro)
    gasto_presente += gasto_nao_classificado
    gasto_total += gasto_nao_classificado

    pct_presente = round((gasto_presente / gasto_total * 100), 1) if gasto_total > 0 else 0
    pct_futuro = round((gasto_futuro / gasto_total * 100), 1) if gasto_total > 0 else 0

    # Cerbasi classification
    if pct_futuro >= 30:
        classificacao = "Investidor"
    elif pct_futuro >= 20:
        classificacao = "Equilibrado"
    elif pct_futuro >= 10:
        classificacao = "Endividado consciente"
    else:
        classificacao = "Gastador"

    return {
        "pct_presente": pct_presente,
        "pct_futuro": pct_futuro,
        "classificacao": classificacao,
        "presente": "Consolidação patrimonial",
        "futuro": "Independência Financeira",
    }


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
    receitas = load_json(FILE_RECEITAS, required=True)
    despesas = load_json(FILE_DESPESAS, required=True)
    patrimonio_input = load_json(FILE_PATRIMONIO)
    investimentos = load_json(FILE_INVESTIMENTOS)
    fluxo_mensal = load_json(FILE_FLUXO_MENSAL, required=True)
    baseline = load_json(FILE_BASELINE)

    # Validate baseline
    if not baseline:
        print("  [CRITICAL] Baseline patrimonial vazio ou ausente — patrimônio será reportado como R$ 0!")

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
    investimentos_classes = analyze_investimentos_classes(baseline)

    # Determine period string
    # v5.3.1: derive period dynamically from data instead of hardcoded fallback
    periodo_dados = receitas.get("periodo", "")
    if not periodo_dados:
        meses = fluxo_mensal.get("meses_ordenados", [])
        if meses:
            periodo_dados = f"{meses[0]} a {meses[-1]}"
        else:
            periodo_dados = f"{TODAY.strftime('%Y-%m')} a {TODAY.strftime('%Y-%m')}"
            print(f"  WARN: periodo not found in receitas nor fluxo_mensal, using today: {periodo_dados}")

    goals = analyze_goals(patrimonio)
    fluxo = analyze_fluxo_caixa(receitas, despesas, fluxo_mensal)
    ratios = analyze_ratios(fluxo, patrimonio, goals)
    score = calculate_score(ratios, patrimonio, goals, fluxo)

    orcamento = analyze_orcamento_prospectivo(fluxo)
    reserva = analyze_reserva_emergencia(fluxo, patrimonio)
    endividamento = analyze_endividamento(patrimonio, baseline)
    previdencia = analyze_previdencia_pgbl(fluxo)

    pontos_fortes = analyze_pontos_fortes(score, ratios)
    pontos_urgentes = analyze_pontos_urgentes(ratios, reserva, patrimonio)
    consumo = analyze_consumo_consciente(fluxo)
    diagnostico = analyze_diagnostico_comportamental(fluxo, ratios)
    cerbasi = analyze_equilibrio_cerbasi(fluxo)

    # Parse tarefas.md (curated backlog) — falls back to pontos_urgentes if file missing
    tarefas_parsed, tarefas_status_parsed = parse_tarefas_md()

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
        "investimentos": investimentos_classes,
        "equilibrio_cerbasi": cerbasi,
        # tarefas: from tarefas.md (curated) or fallback to pontos_urgentes (dynamic)
        "tarefas": tarefas_parsed if tarefas_parsed else [
            {"n": i + 1, "t": pu.get("acao", str(pu)), "p": pu.get("prioridade", "media").lower(), "e": pu.get("prazo", "—"), "impacto": pu.get("impacto", "")}
            for i, pu in enumerate(pontos_urgentes)
        ],
        "tarefas_status": tarefas_status_parsed if tarefas_status_parsed else {str(i + 1): "pendente" for i in range(len(pontos_urgentes))},
        # alertas: array of strings expected by template JS
        "alertas": [
            f"Score financeiro: {score['valor']}/10 ({score['classificacao']})",
        ] + ([f"Rentabilidade: {ratios['rentabilidade_pct']}"] if ratios['rentabilidade_pct'] == 'N/D' else []),
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
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n[E5] FATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

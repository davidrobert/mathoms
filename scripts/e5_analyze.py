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
CONFIG_GOALS = PROJECT_DIR / "config" / "goals.json"
CONFIG_SCORING = PROJECT_DIR / "config" / "scoring.json"
CONFIG_FISCAL = PROJECT_DIR / "config" / "parametros_fiscais.json"
CONFIG_FAMILY = PROJECT_DIR / "config" / "family_members.json"

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


def _load_json_config(path: Path) -> Dict[str, Any]:
    """Load a JSON config file, return empty dict if missing."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️  Error loading {path.name}: {e}")
    return {}


def _load_goals_config() -> Dict[str, Any]:
    """Load goals.json — strategic parameters (aportes, IF, thresholds)."""
    return _load_json_config(CONFIG_GOALS)


def _load_scoring_config() -> Dict[str, Any]:
    """Load scoring.json — score ranges, weights, classifications."""
    return _load_json_config(CONFIG_SCORING)


def _load_fiscal_config() -> Dict[str, Any]:
    """Load parametros_fiscais.json — IRPF table, lucro presumido, PGBL."""
    return _load_json_config(CONFIG_FISCAL)


def _load_family_config() -> Dict[str, Any]:
    """Load family_members.json — family data, residência keyword."""
    return _load_json_config(CONFIG_FAMILY)


# Preload configs at module level for use by all functions
GOALS_CONFIG = _load_goals_config()
SCORING_CONFIG = _load_scoring_config()
FISCAL_CONFIG = _load_fiscal_config()
FAMILY_CONFIG = _load_family_config()


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
    """Extract IF meta from goals.json → life_plan_goals.md → hardcoded fallback."""
    # Priority 1: goals.json (structured, canonical)
    goals_if = GOALS_CONFIG.get("independencia_financeira", {}).get("if_meta")
    if goals_if is not None:
        return safe_float(goals_if)

    # Priority 2: life_plan_goals.md (regex)
    if LIFE_PLAN_GOALS.exists():
        try:
            content = LIFE_PLAN_GOALS.read_text(encoding="utf-8")
            match = re.search(r'\*\*R\$\s*([\d.,]+)', content)
            if match:
                val_str = match.group(1).replace(".", "").replace(",", ".")
                return safe_float(val_str)
        except Exception as e:
            print(f"  ⚠️  Error reading life_plan_goals.md: {e}")

    # Priority 3: hardcoded fallback with warning
    print("  ⚠️  IF meta not found in goals.json or life_plan_goals.md, using fallback R$7,200,000")
    return 7200000.0


def extract_if_trs() -> float:
    """Extract TRS from goals.json → life_plan_goals.md → hardcoded fallback."""
    # Priority 1: goals.json
    goals_trs = GOALS_CONFIG.get("independencia_financeira", {}).get("trs_pct")
    if goals_trs is not None:
        return safe_float(goals_trs)

    # Priority 2: life_plan_goals.md (regex)
    if LIFE_PLAN_GOALS.exists():
        try:
            content = LIFE_PLAN_GOALS.read_text(encoding="utf-8")
            match = re.search(r'TRS.*?(\d+(?:[.,]\d+)?)\s*%', content, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", ".")
                return safe_float(val_str)
        except Exception:
            pass

    # Priority 3: hardcoded fallback with warning
    print("  ⚠️  TRS not found in goals.json or life_plan_goals.md, using fallback 5.0%")
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
            print("  [WARN] Baseline em formato E1.5 declarations — usando fallback. Considere regenerar E1.5 com schema consolidado.")
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
        # Support both "membro" (E1.5 format) and "declarante.nome" (IRPF extract format)
        membro = decl.get("membro", "")
        if not membro:
            declarante = decl.get("declarante", {})
            if isinstance(declarante, dict):
                membro = declarante.get("nome", "")
        membro = membro.lower()
        ano = decl.get("ano_base", 0)
        # If ano_base missing, try to infer from source_file name
        if not ano:
            import re as _re
            src = decl.get("source_file", "")
            if isinstance(src, str):
                _m = _re.search(r'(\d{4})', src.split("/")[-1] if "/" in src else src)
                if _m:
                    ano = int(_m.group(1))
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
    baseline format (top-level lists keyed by imoveis_consolidados, etc.).

    Handles TWO key naming conventions from E1.5:
      - Original: imoveis_consolidados, investimentos_consolidados, dividas, patrimonio_por_ano
      - E1.5 v2: bens_imoveis_consolidados, investimentos_financeiros_consolidados,
                  dividas_consolidadas, resumo_patrimonial, cálculo_patrimonio_liquido

    Value field resolution (tries multiple names):
      - valores_31_12.{ano_ref}  (original format)
      - valor_{ano_ref}          (E1.5 v2 format: valor_2024)
      - valor                    (fallback)

    Proprietário field resolution:
      - proprietario (string)
      - proprietarios (list) — assigns to David unless Mariana listed exclusively
    """
    # --- Determine ano_ref and totals ---
    # Try original format first, then E1.5 v2
    pat_ano = baseline.get("patrimonio_por_ano", {})
    if pat_ano:
        anos = sorted(pat_ano.keys())
        ano_ref = anos[-1] if anos else "2024"
        ano_data = pat_ano.get(ano_ref, {})
        total_bens = safe_float(ano_data.get("total_bens", 0))
        total_dividas = safe_float(ano_data.get("total_dividas", 0))
    else:
        # E1.5 v2: use resumo_patrimonial and cálculo_patrimonio_liquido
        resumo = baseline.get("resumo_patrimonial", {})
        calculo = baseline.get("cálculo_patrimonio_liquido", baseline.get("calculo_patrimonio_liquido", {}))

        # Find most recent year in resumo (keys like "31_12_2024")
        ano_ref = "2024"
        for key in sorted(resumo.keys()):
            m = re.search(r'(\d{4})$', key)
            if m and key != "variacao_2024":
                ano_ref = m.group(1)

        # Get totals from resumo or calculo
        resumo_key = f"31_12_{ano_ref}"
        total_bens = safe_float(resumo.get(resumo_key, {}).get("total", 0))
        if not total_bens and calculo:
            total_bens = safe_float(calculo.get(ano_ref, {}).get("ativo_total", 0))
        total_dividas = safe_float(calculo.get(ano_ref, {}).get("passivo_total", 0))

    print(f"  [E5.1] ano_ref={ano_ref}, total_bens from summary=R$ {total_bens:,.2f}, total_dividas=R$ {total_dividas:,.2f}")

    def _resolve_valor(item: dict, ano: str) -> float:
        """Resolve value from item, trying multiple field names."""
        # Try: valores_31_12.{ano} → valor_{ano} → valor
        vals_dict = item.get("valores_31_12", {})
        if isinstance(vals_dict, dict):
            v = vals_dict.get(ano, vals_dict.get(f"31_12_{ano}"))
            if v is not None:
                return safe_float(v)
        # E1.5 v2: valor_YYYY
        v = item.get(f"valor_{ano}")
        if v is not None:
            return safe_float(v)
        # Fallback
        return safe_float(item.get("valor", 0))

    def _is_mariana_exclusive(item: dict) -> bool:
        """Check if item belongs exclusively to Mariana."""
        # Check single proprietario field
        prop = item.get("proprietario", "")
        if isinstance(prop, str) and prop.lower() == "mariana":
            return True
        # Check proprietarios list — Mariana only if she's the sole owner
        props = item.get("proprietarios", [])
        if isinstance(props, list):
            names_lower = [p.lower() for p in props]
            if "mariana" in names_lower and "david" not in names_lower:
                return True
        return False

    # --- Split imoveis by proprietario ---
    # Accept both key names
    imoveis_list = baseline.get("imoveis_consolidados", baseline.get("bens_imoveis_consolidados", []))
    david_imoveis, mariana_imoveis = [], []
    for im in imoveis_list:
        val = _resolve_valor(im, ano_ref)
        # Build a rich description from available fields so downstream
        # classification (e.g. _imovel_desc) can identify the property.
        descricao = im.get("descricao", "")
        if not descricao:
            # E1.5 v2 consolidated format uses endereco / dados_completos
            dc = im.get("dados_completos", {})
            descricao = dc.get("imovel", "") or im.get("endereco", "") or ""
        entry = {
            "descricao": descricao,
            "endereco": im.get("endereco", ""),
            "tipo": im.get("tipo", ""),
            "valor_31_12_ano_base": val,
        }
        if _is_mariana_exclusive(im):
            mariana_imoveis.append(entry)
        else:
            david_imoveis.append(entry)

    # --- Split investimentos by proprietario ---
    # Handle both formats:
    #   Original: list of {proprietario, descricao, valores_31_12}
    #   E1.5 v2: dict {david_YYYY: {category: value}, mariana_YYYY: {category: value}}
    inv_raw = baseline.get("investimentos_consolidados",
                           baseline.get("investimentos_financeiros_consolidados", {}))

    david_inv, mariana_inv = [], []
    if isinstance(inv_raw, list):
        # Original format: list of individual investments
        for inv in inv_raw:
            val = _resolve_valor(inv, ano_ref)
            entry = {
                "descricao": inv.get("descricao", ""),
                "tipo": inv.get("tipo", ""),
                "valor_31_12_ano_base": val,
            }
            if _is_mariana_exclusive(inv):
                mariana_inv.append(entry)
            else:
                david_inv.append(entry)
    elif isinstance(inv_raw, dict):
        # E1.5 v2: dict with member keys like "david_2024", "mariana_2024"
        for member_key, categories in inv_raw.items():
            member_lower = member_key.lower()
            if not isinstance(categories, dict):
                continue
            is_mariana = "mariana" in member_lower
            for cat_name, cat_value in categories.items():
                if cat_name in ("total",):
                    continue  # Skip summary key
                val = safe_float(cat_value)
                if val == 0:
                    continue
                entry = {
                    "descricao": cat_name.replace("_", " ").title(),
                    "tipo": cat_name,
                    "valor_31_12_ano_base": val,
                }
                if is_mariana:
                    mariana_inv.append(entry)
                else:
                    david_inv.append(entry)

    # --- Veiculos ---
    david_veiculos, mariana_veiculos = [], []
    for v in baseline.get("veiculos_consolidados", []):
        val = _resolve_valor(v, ano_ref)
        entry = {"descricao": v.get("descricao", ""), "valor_31_12_ano_base": val}
        if _is_mariana_exclusive(v):
            mariana_veiculos.append(entry)
        else:
            david_veiculos.append(entry)

    # --- Dividas — sum per proprietario ---
    # Accept both key names
    dividas_list = baseline.get("dividas", baseline.get("dividas_consolidadas", []))
    david_dividas, mariana_dividas = 0.0, 0.0
    for dv in dividas_list:
        # Try: saldo_31_12.{ano} → valor_{ano} → valor
        saldo = dv.get("saldo_31_12", {})
        if isinstance(saldo, dict):
            val = safe_float(saldo.get(ano_ref, 0))
        else:
            val = _resolve_valor(dv, ano_ref)
        prop = dv.get("proprietario", "").lower()
        if "mariana" in prop and "david" not in prop:
            mariana_dividas += val
        else:
            david_dividas += val  # Shared debts assigned to david for totaling

    # --- Sum bens per member ---
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

    # Sanity check: synthetic totals vs summary totals
    synthetic_total = david_bens_total + mariana_bens_total
    print(f"  [E5.1] Synthetic total_bens: R$ {synthetic_total:,.2f} (David: R$ {david_bens_total:,.2f}, Mariana: R$ {mariana_bens_total:,.2f})")

    if total_bens > 0 and abs(synthetic_total - total_bens) > 1.0:
        print(f"  [INFO] Synthetic total_bens (R$ {synthetic_total:,.2f}) vs resumo_patrimonial (R$ {total_bens:,.2f})")
        print(f"  [INFO] Using resumo_patrimonial total_bens as authoritative")
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
    """Get imovel description, trying multiple field names.

    Checks descricao, description, endereco, and dados_completos.imovel
    so that property classification works regardless of data format.
    """
    desc = imovel.get("description") or imovel.get("descricao") or ""
    if not desc:
        desc = imovel.get("endereco") or ""
    if not desc:
        dc = imovel.get("dados_completos", {})
        if isinstance(dc, dict):
            desc = dc.get("imovel", "") or ""
    return desc.lower()


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


def analyze_patrimonio(baseline: Dict[str, Any], investimentos_atuais: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze patrimonio from baseline data, optionally enriched with current
    investment positions from investimentos-4_unified.json.

    Strategy:
    - Imóveis and veículos: always from IRPF baseline (updated annually)
    - Investimentos: prefer current positions (E2-llm extracts, monthly) over IRPF
    - When current positions available: patrimonio_bruto is recalculated as
      imóveis + veículos + investimentos_atuais + contas_bancárias
    """
    print("[E5.1] Analyzing patrimonio...")

    david, mariana = _resolve_members(baseline)

    total_bens_irpf = safe_float(david.get("total_bens", 0)) + safe_float(mariana.get("total_bens", 0))
    total_dividas = safe_float(david.get("total_dividas", david.get("dividas", 0))) + safe_float(mariana.get("total_dividas", mariana.get("dividas", 0)))

    david_bens = _get_bens(david)
    mariana_bens = _get_bens(mariana)

    # Residência principal (keyword de family_members.json)
    _residencia_kw = FAMILY_CONFIG.get("membros", {}).get("david", {}).get(
        "residencia_principal_keyword", "tasso da silveira"
    ).lower()
    residencia = 0.0
    imoveis_investimento = 0.0

    for imovel in david_bens.get("imoveis", []):
        if _residencia_kw in _imovel_desc(imovel):
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

    # Investment accounts — prefer current positions over IRPF
    investimentos_david = 0.0
    investimentos_mariana = 0.0
    fonte_investimentos = "irpf"

    has_current_positions = (
        investimentos_atuais
        and isinstance(investimentos_atuais, dict)
        and len(investimentos_atuais.get("dados", [])) > 0
    )

    if has_current_positions:
        # Use current E2-llm position extracts (more recent than IRPF)
        fonte_investimentos = "posicoes_atuais"
        totais = investimentos_atuais.get("total_por_membro", {})
        investimentos_david = safe_float(totais.get("david", 0))
        investimentos_mariana = safe_float(totais.get("mariana", 0))
        # Positions without member attribution (membro="") are assigned to titular (david)
        unattributed = safe_float(totais.get("", 0))
        if unattributed > 0:
            investimentos_david += unattributed
            print(f"  [INFO] R$ {unattributed:,.2f} sem membro atribuído → alocado ao titular (david)")
        n_pos = investimentos_atuais.get("n_posicoes", 0)
        data_ref = investimentos_atuais.get("data_consolidacao", "?")
        print(f"  [INFO] Usando posições atuais ({n_pos} posições, ref: {data_ref})")
        print(f"  [INFO] David: R$ {investimentos_david:,.2f}, Mariana: R$ {investimentos_mariana:,.2f}")
    else:
        # Fallback to IRPF baseline
        for inv in david_bens.get("investimentos", []):
            investimentos_david += _investimento_valor(inv)
        contas_d = david_bens.get("contas_bancarias", [])
        if isinstance(contas_d, list):
            for inv in contas_d:
                investimentos_david += _investimento_valor(inv)
        else:
            investimentos_david += safe_float(contas_d)
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
        print(f"  [INFO] Usando investimentos do IRPF (fallback)")

    # Compute patrimonio_bruto
    if has_current_positions:
        # Recalculate: imóveis + veículos from IRPF + investimentos from current positions
        patrimonio_bruto = (
            residencia
            + imoveis_investimento
            + veiculos
            + investimentos_david
            + investimentos_mariana
        )
        print(f"  [INFO] Patrimônio recalculado com fontes mistas: R$ {patrimonio_bruto:,.2f} (IRPF imóveis+veículos + posições atuais)")
    else:
        patrimonio_bruto = total_bens_irpf

    patrimonio_liquido = patrimonio_bruto - total_dividas

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
        "fonte_investimentos": fonte_investimentos,
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
    # Load from goals.json with hardcoded fallback
    _if_cfg = GOALS_CONFIG.get("independencia_financeira", {})
    _aportes_cfg = GOALS_CONFIG.get("aportes", {})
    aporte_mensal = safe_float(_aportes_cfg.get("meta_aporte_mensal", 20000))
    retorno_real_anual = safe_float(_if_cfg.get("retorno_real_anual_pct", 6.0)) / 100.0

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
    # Taxa de retirada segura (regra dos 4%) — carregada de goals.json
    taxa_retirada = safe_float(_if_cfg.get("taxa_retirada_segura_pct", 4.0)) / 100.0
    renda_passiva_current = investivel * taxa_retirada / 12  # monthly

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

    # =====================================================================
    # 12-MONTH ROLLING WINDOW — used for ratios / score / taxa poupança
    # =====================================================================
    # The full-period totals (40 months) distort savings rate because
    # one-time income (Kiwify, vendas) inflates total but not recorrente,
    # making recorrente < despesa → negative savings rate.
    # A 12-month window gives a more accurate snapshot of current habits.
    # =====================================================================
    n_janela = min(12, len(meses))
    meses_12m = meses[-n_janela:] if n_janela > 0 else []
    janela_12m_inicio = meses_12m[0] if meses_12m else ""
    janela_12m_fim = meses_12m[-1] if meses_12m else ""

    # One-time origin detection for fluxo_mensal display names.
    # Category-based origins (receita_resgate etc.) are already handled,
    # but fluxo_mensal uses user-friendly names, so we match both ways.
    ONE_TIME_ORIGIN_NAMES = {"Resgates", "Restituições", "Venda de Ativo"}

    receita_12m_total = 0.0
    receita_12m_recorrente = 0.0
    despesa_12m_total = 0.0

    for mes in meses_12m:
        # Receitas: split recorrente vs one-time per origin
        mes_rec = receita_por_mes.get(mes, {})
        for origem, valor in mes_rec.items():
            if origem == "_total":
                continue
            v = safe_float(valor)
            receita_12m_total += v
            if origem in ONE_TIME_ORIGIN_NAMES or is_one_time_income(origem.lower()):
                pass  # one-time — excluded from recorrente
            else:
                receita_12m_recorrente += v

        # Despesas: full total
        mes_desp = despesa_por_mes.get(mes, {})
        despesa_12m_total += safe_float(mes_desp.get("_total", 0))

    receita_12m_one_time = receita_12m_total - receita_12m_recorrente
    receita_12m_recorrente_mensal = receita_12m_recorrente / n_janela if n_janela > 0 else 0
    despesa_12m_mensal_media = despesa_12m_total / n_janela if n_janela > 0 else 0
    fluxo_12m_liquido = receita_12m_total - despesa_12m_total

    print(f"  [E5.3] Janela 12m ({janela_12m_inicio} a {janela_12m_fim}, {n_janela} meses):")
    print(f"         Receita total 12m: R$ {receita_12m_total:,.2f}")
    print(f"         Receita recorrente 12m: R$ {receita_12m_recorrente:,.2f}")
    print(f"         Receita one-time 12m: R$ {receita_12m_one_time:,.2f}")
    print(f"         Despesa total 12m: R$ {despesa_12m_total:,.2f}")
    print(f"         Fluxo líquido 12m: R$ {fluxo_12m_liquido:,.2f}")

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
        # 12-month rolling window — preferred for ratios / score
        "janela_12m": {
            "periodo": f"{janela_12m_inicio} a {janela_12m_fim}",
            "n_meses": n_janela,
            "receita_total": round(receita_12m_total, 2),
            "receita_recorrente": round(receita_12m_recorrente, 2),
            "receita_one_time": round(receita_12m_one_time, 2),
            "receita_recorrente_mensal": round(receita_12m_recorrente_mensal, 2),
            "despesa_total": round(despesa_12m_total, 2),
            "despesa_mensal_media": round(despesa_12m_mensal_media, 2),
            "fluxo_liquido": round(fluxo_12m_liquido, 2),
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
    """Compute financial ratios.

    Uses the 12-month rolling window (fluxo.janela_12m) for savings rate
    and expense metrics, since the full-period accumulation distorts ratios
    when the data spans multiple years with varying income composition.
    """
    print("[E5.4] Computing ratios...")

    # Prefer 12-month rolling window for ratios (more representative)
    j12m = fluxo.get("janela_12m", {})
    if j12m:
        receita_recorrente = j12m["receita_recorrente"]
        despesa_total = j12m["despesa_total"]
        receita_total = j12m["receita_total"]
        despesa_mensal_media = j12m["despesa_mensal_media"]
        janela_periodo = j12m["periodo"]
        janela_n_meses = j12m["n_meses"]
        print(f"  [E5.4] Usando janela 12m ({janela_periodo}, {janela_n_meses} meses) para rácios")
    else:
        receita_recorrente = fluxo["receita_recorrente"]
        despesa_total = fluxo["despesa_total"]
        receita_total = fluxo["receita_total"]
        despesa_mensal_media = fluxo["despesa_mensal_media"]
        janela_periodo = "período completo"
        janela_n_meses = 0
        print("  [WARN] janela_12m não disponível, usando período completo para rácios")

    # Taxa poupança recorrente (12m)
    taxa_poupanca_recorrente_pct = 0.0
    if receita_recorrente > 0:
        taxa_poupanca_recorrente_pct = ((receita_recorrente - despesa_total) / receita_recorrente) * 100

    # Taxa poupança total (12m)
    taxa_poupanca_total_pct = 0.0
    if receita_total > 0:
        taxa_poupanca_total_pct = ((receita_total - despesa_total) / receita_total) * 100

    print(f"  [E5.4] Taxa poupança recorrente (12m): {taxa_poupanca_recorrente_pct:.1f}%")
    print(f"  [E5.4] Taxa poupança total (12m): {taxa_poupanca_total_pct:.1f}%")

    # Taxa endividamento (patrimonio — not windowed)
    taxa_endividamento_pct = 0.0
    if patrimonio["bruto"] > 0:
        taxa_endividamento_pct = (patrimonio["dividas"] / patrimonio["bruto"]) * 100

    # Cobertura despesas (meses) — uses 12m expense average
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
        "janela_referencia": janela_periodo,
        "janela_n_meses": janela_n_meses,
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
    """Calculate financial score (0-10 scale). Parameters loaded from config/scoring.json."""
    print("[E5.5] Computing score...")

    score_cfg = SCORING_CONFIG.get("score_componentes", {})

    # Helper: get range/weight from config with fallback
    def _get_comp(key, default_min, default_max, default_peso):
        c = score_cfg.get(key, {})
        return (
            safe_float(c.get("range_min", default_min)),
            safe_float(c.get("range_max", default_max)),
            safe_float(c.get("peso", default_peso)),
            c.get("nome_display", key),
            c.get("invertido", False),
        )

    # Load component configs
    tp_min, tp_max, tp_peso, tp_nome, _ = _get_comp("taxa_poupanca_recorrente", 0, 50, 2.0)
    co_min, co_max, co_peso, co_nome, _ = _get_comp("cobertura_despesas", 3, 24, 1.5)
    en_min, en_max, en_peso, en_nome, en_inv = _get_comp("taxa_endividamento", 5, 50, 1.5)
    if_min, if_max, if_peso, if_nome, _ = _get_comp("progresso_if", 5, 80, 2.0)
    di_min, di_max, di_peso, di_nome, _ = _get_comp("diversificacao", 1, 6, 1.0)

    # Compute component scores
    taxa_poup = safe_float(ratios["taxa_poupanca_recorrente_pct"])
    score_poup = linear_interpolate(taxa_poup, tp_min, tp_max)

    cobertura = safe_float(ratios["cobertura_despesas_meses"])
    score_cobertura = linear_interpolate(cobertura, co_min, co_max)

    endiv = safe_float(ratios["taxa_endividamento_pct"])
    # Inverted: high value → low score (swap min/max)
    score_endiv = linear_interpolate(endiv, en_max, en_min) if en_inv else linear_interpolate(endiv, en_min, en_max)

    if_pct = safe_float(goals["if_pct"])
    score_if = linear_interpolate(if_pct, if_min, if_max)

    composicao = patrimonio.get("composicao", [])
    num_categorias = len([c for c in composicao if c["valor"] > 0])
    score_diversif = linear_interpolate(num_categorias, di_min, di_max)

    # Weighted average
    componentes = [
        {"nome": tp_nome, "valor": round(taxa_poup, 2), "peso": tp_peso, "nota": round(score_poup, 1)},
        {"nome": co_nome, "valor": round(cobertura, 2), "peso": co_peso, "nota": round(score_cobertura, 1)},
        {"nome": en_nome, "valor": round(endiv, 2), "peso": en_peso, "nota": round(score_endiv, 1)},
        {"nome": if_nome, "valor": round(if_pct, 2), "peso": if_peso, "nota": round(score_if, 1)},
        {"nome": di_nome, "valor": num_categorias, "peso": di_peso, "nota": round(score_diversif, 1)},
    ]

    total_peso = sum(c["peso"] for c in componentes)
    valor_score = sum(c["nota"] * c["peso"] for c in componentes) / total_peso if total_peso > 0 else 0
    valor_score = round(valor_score, 1)

    # Classification from config/scoring.json
    classificacao = "N/D"
    for faixa in SCORING_CONFIG.get("score_classificacao", []):
        if valor_score >= safe_float(faixa.get("min", 0)) and valor_score < safe_float(faixa.get("max", 10)):
            classificacao = faixa["label"]
    # Handle edge: score == 10 → last band
    if valor_score >= 10:
        bands = SCORING_CONFIG.get("score_classificacao", [])
        classificacao = bands[-1]["label"] if bands else "Excelente"
    # Fallback if config missing
    if classificacao == "N/D":
        if valor_score < 2: classificacao = "Crítico"
        elif valor_score < 4: classificacao = "Atenção"
        elif valor_score < 6: classificacao = "Regular"
        elif valor_score < 8: classificacao = "Bom"
        else: classificacao = "Excelente"

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

    # Níveis de reserva carregados de scoring.json
    _reserva_cfg = SCORING_CONFIG.get("reserva_emergencia", {})
    _niveis = _reserva_cfg.get("niveis_meses", [6, 12])
    _classif = _reserva_cfg.get("classificacao", [
        {"minimo_meses": 12, "label": "Excelente"},
        {"minimo_meses": 6,  "label": "Adequada"},
        {"minimo_meses": 0,  "label": "Insuficiente"},
    ])

    niveis_calc = {}
    for n in _niveis:
        niveis_calc[n] = despesa_mensal * n

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

    # Avaliação dinâmica de scoring.json (faixas ordenadas por minimo_meses desc)
    avaliacao = "Insuficiente"
    for faixa in sorted(_classif, key=lambda x: x.get("minimo_meses", 0), reverse=True):
        if cobertura_meses >= faixa.get("minimo_meses", 0):
            avaliacao = faixa["label"]
            break

    # Build niveis list and dict for output (backward-compatible keys)
    nivel_keys = sorted(niveis_calc.keys())
    return {
        "despesas_mensais": round(despesa_mensal, 2),
        "nivel_6_meses": round(niveis_calc.get(6, despesa_mensal * 6), 2),
        "nivel_12_meses": round(niveis_calc.get(12, despesa_mensal * 12), 2),
        "composicao_liquida": {k: round(v, 2) for k, v in composicao_liquida.items()},
        "total_liquida": round(total_liquida, 2),
        "cobertura_meses": round(cobertura_meses, 1),
        "avaliacao_liquidity": avaliacao,
        "niveis": [f"{n} meses" for n in nivel_keys],
    }


def analyze_investimentos_classes(baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze investments by asset class from baseline data."""
    print("[E5.7b] Analyzing investimentos por classe...")

    david, mariana = _resolve_members(baseline)
    david_bens = _get_bens(david)
    mariana_bens = _get_bens(mariana)

    # Asset class keywords loaded from scoring.json
    _acl_kw = SCORING_CONFIG.get("asset_class_keywords", {})
    _kw_acoes = _acl_kw.get("Ações", ["acoes", "ações", "itsa", "brkm", "petr", "etf", "ivvb"])
    _kw_rf = _acl_kw.get("Renda Fixa", ["renda fixa", "cdb", "rdb", "lci", "lca", "tesouro", "debenture", "certificado de deposito"])
    _kw_cripto = _acl_kw.get("Cripto", ["cripto", "bitcoin", "ethereum", "binance"])
    _kw_contas = _acl_kw.get("Contas Bancárias", ["banco", "picpay", "nubank", "saldo", "conta"])

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
        if any(kw in tipo_lower for kw in _kw_acoes):
            classes["Ações"] += valor
        elif any(kw in tipo_lower for kw in _kw_rf):
            classes["Renda Fixa"] += valor
        elif any(kw in tipo_lower for kw in _kw_cripto):
            classes["Cripto"] += valor
        elif any(kw in tipo_lower for kw in _kw_contas):
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

    # Add imoveis investimento (excluindo residência principal)
    _residencia_kw = FAMILY_CONFIG.get("membros", {}).get("david", {}).get(
        "residencia_principal_keyword", "tasso da silveira"
    ).lower()
    for imovel in david_bens.get("imoveis", []):
        if _residencia_kw not in _imovel_desc(imovel):
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

    # Parâmetros fiscais carregados de config/parametros_fiscais.json
    _lp_cfg = FISCAL_CONFIG.get("lucro_presumido", {})
    _pgbl_cfg = FISCAL_CONFIG.get("pgbl", {})
    _irpf_cfg = FISCAL_CONFIG.get("irpf_tabela_progressiva", {})

    lucro_presumido_pct = safe_float(_lp_cfg.get("percentual_servicos_pct", 32.0)) / 100.0
    pgbl_limite_pct = safe_float(_pgbl_cfg.get("limite_deducao_pct", 12.0)) / 100.0

    renda_tributavel = receita_pj_anual * lucro_presumido_pct

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

    limite_pgbl = renda_tributavel * pgbl_limite_pct

    # Alíquota marginal IRPF (tabela progressiva de parametros_fiscais.json)
    faixas_irpf = _irpf_cfg.get("faixas", [])
    aliquota_marginal = 7.5  # fallback
    if faixas_irpf:
        # Faixas ordenadas por limite_anual ascending, última tem limite null
        aliquota_marginal = safe_float(faixas_irpf[0].get("aliquota_pct", 7.5))
        for faixa in faixas_irpf:
            limite = faixa.get("limite_anual")
            if limite is not None and renda_tributavel > safe_float(limite):
                aliquota_marginal = safe_float(faixa.get("aliquota_pct", aliquota_marginal))
            elif limite is None:
                # Última faixa (sem teto)
                aliquota_marginal = safe_float(faixa.get("aliquota_pct", aliquota_marginal))

    economia_ir = limite_pgbl * (aliquota_marginal / 100)

    lp_pct_display = int(lucro_presumido_pct * 100)
    return {
        "status": "Calculado",
        "nota": f"Base: receita PJ anualizada R$ {receita_pj_anual:,.0f}, lucro presumido {lp_pct_display}%.",
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

    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})
    taxa_poup = safe_float(ratios["taxa_poupanca_recorrente_pct"])
    _poup_forte_min = safe_float(_alertas_cfg.get("pontos_fortes_taxa_poupanca_min_pct", 30))
    if taxa_poup > _poup_forte_min:
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
    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})
    _reserva_min = safe_float(_alertas_cfg.get("reserva_minima_meses", 6))
    _endiv_max = safe_float(_alertas_cfg.get("endividamento_maximo_pct", 20))

    # Check: emergency reserve below minimum
    cobertura = reserva.get("cobertura_meses", 0)
    if cobertura < _reserva_min:
        urgentes.append({
            "prioridade": "Alta",
            "acao": "Reforçar reserva de emergência",
            "impacto": f"Cobertura atual de {cobertura:.0f} meses — abaixo do mínimo de {_reserva_min:.0f}",
            "prazo": "Imediato",
        })

    # Check: high debt ratio
    endiv = safe_float(ratios.get("taxa_endividamento_pct", 0))
    if endiv > _endiv_max:
        urgentes.append({
            "prioridade": "Alta",
            "acao": "Reduzir endividamento",
            "impacto": f"Taxa de endividamento em {endiv:.1f}% — meta < {_endiv_max:.0f}%",
            "prazo": "Próximo trimestre",
        })

    # Check: no insurance data found
    urgentes.append({
        "prioridade": "Alta",
        "acao": "Contratar seguro de vida e invalidez",
        "impacto": "Proteção patrimonial da família — nenhuma apólice identificada",
        "prazo": "Imediato",
    })

    # Check: rentabilidade not measured
    if ratios.get("rentabilidade_pct") == "N/D":
        urgentes.append({
            "prioridade": "Média",
            "acao": "Consolidar dados de rentabilidade dos investimentos",
            "impacto": "Sem dados de performance, impossível otimizar alocação",
            "prazo": "Próximo trimestre",
        })

    return urgentes


def analyze_consumo_consciente(fluxo: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze top spending items above threshold from scoring.json."""
    print("[E5.12] Analyzing consumo consciente...")

    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})
    _consumo_min = safe_float(_alertas_cfg.get("consumo_consciente_min", 2000))

    despesas_por_cat = fluxo["despesas_por_categoria"]
    top_gastos = [
        {"categoria": k, "valor": round(v, 2)}
        for k, v in despesas_por_cat.items()
        if v >= _consumo_min
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
    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})
    _poup_ref = safe_float(_alertas_cfg.get("poupanca_referencia_pct", 25))
    _one_time_alerta = safe_float(_alertas_cfg.get("receita_one_time_alerta_pct", 30))

    taxa_poup = safe_float(ratios.get("taxa_poupanca_recorrente_pct", 0))
    if taxa_poup > _poup_ref:
        diagnosticos.append({
            "padrao": "Disciplina de poupança",
            "evidencia": f"Taxa de poupança recorrente de {taxa_poup:.1f}% — acima da referência de {_poup_ref:.0f}%",
            "mudanca_sugerida": "Manter e automatizar aportes mensais",
        })
    elif taxa_poup > 0:
        diagnosticos.append({
            "padrao": "Poupança abaixo do ideal",
            "evidencia": f"Taxa de {taxa_poup:.1f}% — referência mínima: {_poup_ref:.0f}%",
            "mudanca_sugerida": "Revisar despesas variáveis e aumentar aporte",
        })

    despesa_total = safe_float(fluxo.get("despesa_total", 0))
    receita_total = safe_float(fluxo.get("receita_total", 0))
    if receita_total > 0:
        one_time_pct = safe_float(fluxo.get("receita_one_time", 0)) / receita_total * 100
        if one_time_pct > _one_time_alerta:
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
    """Analyze Cerbasi balance: presente vs futuro spending. Categories from scoring.json."""
    print("[E5.14] Analyzing equilíbrio Cerbasi...")

    despesas = fluxo.get("despesas_por_categoria", {})

    # Categorias carregadas de scoring.json
    _cerbasi_cfg = SCORING_CONFIG.get("cerbasi", {})
    cats_presente = set(_cerbasi_cfg.get("categorias_presente", [
        "moradia", "alimentacao", "transporte", "saude", "lazer",
        "servicos_domesticos", "pets", "cuidados_pessoais",
        "assinaturas", "vestuario", "compras_online"
    ]))
    cats_futuro = set(_cerbasi_cfg.get("categorias_futuro", [
        "educacao", "investimentos", "previdencia", "financeiro",
        "reserva_desejos", "poupanca", "aportes"
    ]))

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

    # Cerbasi classification from scoring.json
    _cerbasi_classif = _cerbasi_cfg.get("classificacao", [
        {"minimo_futuro_pct": 30, "label": "Investidor"},
        {"minimo_futuro_pct": 20, "label": "Equilibrado"},
        {"minimo_futuro_pct": 10, "label": "Endividado consciente"},
        {"minimo_futuro_pct": 0,  "label": "Gastador"},
    ])
    classificacao = "Gastador"
    for faixa in sorted(_cerbasi_classif, key=lambda x: x.get("minimo_futuro_pct", 0), reverse=True):
        if pct_futuro >= safe_float(faixa.get("minimo_futuro_pct", 0)):
            classificacao = faixa["label"]
            break

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

    patrimonio = analyze_patrimonio(baseline, investimentos_atuais=investimentos)
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

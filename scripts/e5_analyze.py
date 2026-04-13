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
# PATHS & CONFIG — inicializados por _init_config(), re-invocável via root_dir
# ============================================================================
_DEFAULT_BASE_DIR = Path(__file__).parent.parent


def _load_json_config(path: Path) -> Dict[str, Any]:
    """Load a JSON config file, return empty dict if missing."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️  Error loading {path.name}: {e}")
    return {}


def _load_dob(fm: dict, member_key: str) -> date:
    """Parse data_nascimento de um membro, retorna date ou None."""
    dob_str = fm.get("membros", {}).get(member_key, {}).get("data_nascimento", "")
    if dob_str:
        parts = dob_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    return None


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa todos os globals de path e config a partir de base_dir."""
    global SCRIPTS_DIR, PROJECT_DIR
    global PROCESSED_DIR, E4_UNIFIED_DIR, E2_EXTRACTS_DIR, E3_RECONCILED_DIR, E5_ANALYSIS_DIR
    global LIFE_PLAN_GOALS, CONFIG_DEFINITIONS, CONFIG_TAREFAS
    global CONFIG_GOALS, CONFIG_SCORING, CONFIG_FISCAL, CONFIG_FAMILY, CONFIG_TAXAS, CONFIG_MILHAS
    global FILE_RECEITAS, FILE_DESPESAS, FILE_PATRIMONIO, FILE_INVESTIMENTOS
    global FILE_FLUXO_MENSAL, FILE_BASELINE, FILE_OUTPUT
    global _TITULAR_DOB, _CONJUGE_DOB, TODAY
    global ONE_TIME_INCOME_KEYWORDS, ONE_TIME_INCOME_CATEGORIES
    global GOALS_CONFIG, SCORING_CONFIG, FISCAL_CONFIG, FAMILY_CONFIG
    global _TITULAR_KEY, _MEMBROS, _CONJUGE_KEY
    global _TITULAR_NOME, _CONJUGE_NOME
    global _KEY_INV_TITULAR, _KEY_INV_CONJUGE, _KEY_CENARIOS_CONJUGE

    SCRIPTS_DIR = base_dir / "scripts"
    PROJECT_DIR = base_dir

    PROCESSED_DIR = PROJECT_DIR / "processed"
    E4_UNIFIED_DIR = PROCESSED_DIR / "E4_unified"
    E2_EXTRACTS_DIR = PROCESSED_DIR / "E2_extracts"
    E3_RECONCILED_DIR = PROCESSED_DIR / "E3_reconciled"
    E5_ANALYSIS_DIR = PROCESSED_DIR / "E5_analysis"

    LIFE_PLAN_GOALS = PROJECT_DIR / "life_plan" / "life_plan_goals.md"
    CONFIG_DEFINITIONS = PROJECT_DIR / "config" / "definitions.md"
    CONFIG_TAREFAS = PROJECT_DIR / "config" / "tarefas.md"
    CONFIG_GOALS = PROJECT_DIR / "config" / "goals.json"
    CONFIG_SCORING = PROJECT_DIR / "config" / "scoring.json"
    CONFIG_FISCAL = PROJECT_DIR / "config" / "parametros_fiscais.json"
    CONFIG_FAMILY = PROJECT_DIR / "config" / "family_members.json"
    CONFIG_TAXAS = PROJECT_DIR / "config" / "taxas.json"
    CONFIG_MILHAS = PROJECT_DIR / "config" / "milhas.md"

    FILE_RECEITAS = E4_UNIFIED_DIR / "receitas-4_unified.json"
    FILE_DESPESAS = E4_UNIFIED_DIR / "despesas-4_unified.json"
    FILE_PATRIMONIO = E4_UNIFIED_DIR / "patrimonio-4_unified.json"
    FILE_INVESTIMENTOS = E4_UNIFIED_DIR / "investimentos-4_unified.json"
    FILE_FLUXO_MENSAL = E4_UNIFIED_DIR / "fluxo_mensal_detalhado-4_unified.json"
    FILE_BASELINE = E2_EXTRACTS_DIR / "baseline_patrimonial-1.5_consolidated.json"

    FILE_OUTPUT = E5_ANALYSIS_DIR / "analise_financeira-5_analysis.json"

    # Family config + DOBs
    fm = _load_json_config(CONFIG_FAMILY)
    titular_key = fm.get("titular", "david")
    _TITULAR_DOB = _load_dob(fm, titular_key)
    if not _TITULAR_DOB:
        print("  ⚠️  data_nascimento do titular não encontrada — usando placeholder")
        _TITULAR_DOB = date(date.today().year - 40, 1, 1)

    conjuge_key = next((k for k, v in fm.get("membros", {}).items() if v.get("papel") == "conjuge"), "")
    _CONJUGE_DOB = _load_dob(fm, conjuge_key) if conjuge_key else None

    TODAY = date.today()

    # One-time income config
    cat_path = PROJECT_DIR / "config" / "categorization.json"
    cat = _load_json_config(cat_path)
    kw = cat.get("one_time_income_keywords", None)
    cats = cat.get("one_time_income_categories", None)
    if kw is not None and cats is not None:
        ONE_TIME_INCOME_KEYWORDS, ONE_TIME_INCOME_CATEGORIES = kw, set(cats)
    else:
        ONE_TIME_INCOME_KEYWORDS = ["fgts", "restituicao", "bolsa", "bonus", "venda"]
        ONE_TIME_INCOME_CATEGORIES = {"receita_venda_ativo", "receita_resgate", "receita_fgts", "receita_restituicao"}

    GOALS_CONFIG = _load_json_config(CONFIG_GOALS)
    SCORING_CONFIG = _load_json_config(CONFIG_SCORING)
    FISCAL_CONFIG = _load_json_config(CONFIG_FISCAL)
    FAMILY_CONFIG = fm

    _TITULAR_KEY = FAMILY_CONFIG.get("titular", "")
    _MEMBROS = FAMILY_CONFIG.get("membros", {})
    _CONJUGE_KEY = next((k for k, v in _MEMBROS.items() if v.get("papel") == "conjuge"), "")
    _TITULAR_NOME = _MEMBROS.get(_TITULAR_KEY, {}).get("nome_curto", _TITULAR_KEY.title())
    _CONJUGE_NOME = _MEMBROS.get(_CONJUGE_KEY, {}).get("nome_curto", _CONJUGE_KEY.title())

    _KEY_INV_TITULAR = f"investimentos_{_TITULAR_KEY}"
    _KEY_INV_CONJUGE = f"investimentos_{_CONJUGE_KEY}"
    _KEY_CENARIOS_CONJUGE = f"cenarios_{_CONJUGE_KEY}"


_init_config(_DEFAULT_BASE_DIR)


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

    # Priority 3: fail — no hardcoded fallback
    raise ValueError("IF meta não encontrada em goals.json nem life_plan_goals.md. Configure 'independencia_financeira.if_meta' em config/goals.json.")


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

    # Priority 3: fail — no hardcoded fallback
    raise ValueError("TRS não encontrado em goals.json nem life_plan_goals.md. Configure 'independencia_financeira.trs_pct' em config/goals.json.")


def extract_renda_passiva_from_life_plan() -> float:
    """Extract current renda passiva from life_plan."""
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
    """Calculate age in years (calendar-accurate)."""
    age = reference_date.year - dob.year
    if (reference_date.month, reference_date.day) < (dob.month, dob.day):
        age -= 1
    return age


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
    1. Dict format: members/membros as dict with titular/conjuge sub-dicts
    2. List-of-dicts format: membros as list of dicts with "nome" key
    3. E1.5 declarations format: membros as list of strings + declarations[]
    4. Consolidated format: top-level imoveis_consolidados, etc.
    """
    members = baseline.get("members", baseline.get("membros", {}))
    if isinstance(members, list):
        # Check if list contains dicts (format 2) or strings (format 3)
        has_dicts = any(isinstance(m, dict) for m in members)
        if has_dicts:
            titular_data, conjuge_data = {}, {}
            for m in members:
                if not isinstance(m, dict):
                    continue
                nome = m.get("nome", "").lower()
                if _TITULAR_KEY in nome:
                    titular_data = m
                elif _CONJUGE_KEY in nome:
                    conjuge_data = m
            return titular_data, conjuge_data
        # Format 3: membros is list of strings + declarations exist
        # Prefer consolidated path if imoveis_consolidados was generated by e15_consolidate
        if baseline.get("imoveis_consolidados") is not None or baseline.get("patrimonio_por_ano"):
            print("  [INFO] Baseline com chaves consolidadas — usando path consolidado.")
            return _build_members_from_consolidated(baseline)
        if baseline.get("declarations"):
            print("  [WARN] Baseline em formato E1.5 declarations sem chaves consolidadas — usando fallback. Execute: python scripts/e15_consolidate.py")
            return _build_members_from_declarations(baseline)
    if members and isinstance(members, dict):
        return members.get(_TITULAR_KEY, {}), members.get(_CONJUGE_KEY, {})
    # --- v1.5 consolidated format: no "members" key ---
    # Build synthetic member dicts from top-level consolidated lists
    return _build_members_from_consolidated(baseline)


def _build_members_from_declarations(baseline: Dict[str, Any]) -> tuple:
    """Build synthetic titular/conjuge member dicts from E1.5 declarations format.

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
        key = _TITULAR_KEY if _TITULAR_KEY in membro else _CONJUGE_KEY if _CONJUGE_KEY in membro else None
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
            # Normalize grupo: "G01" → "01", "1" → "01", 1 → "01"
            raw_grupo = str(bem.get("grupo", "")).strip().upper()
            if raw_grupo.startswith("G"):
                raw_grupo = raw_grupo[1:]
            grupo = raw_grupo.zfill(2)
            # Value field: try situacao_atual first (IRPF format), then valor_31_12_atual
            valor = safe_float(
                bem.get("situacao_atual",
                    bem.get("valor_31_12_atual", 0))
            )
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
    for key in (_TITULAR_KEY, _CONJUGE_KEY):
        decl = member_decls.get(key)
        if not decl:
            results[key] = {}
            continue

        bens = _classify_bens(decl.get("bens_direitos", []))
        total_bens = safe_float(decl.get("total_bens", 0))
        # total_dividas not directly in declarations — compute from dívidas if present
        total_dividas = 0.0
        for dv in baseline.get("dividas", []):
            prop_lower = dv.get("proprietario", "").lower()
            if key == _TITULAR_KEY and _TITULAR_KEY in prop_lower:
                total_dividas += safe_float(dv.get("saldo_31_12", 0))
            elif key == _CONJUGE_KEY and _CONJUGE_KEY in prop_lower:
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

    print(f"  [E5.1] Built members from declarations: {_TITULAR_KEY} R$ {results.get(_TITULAR_KEY, {}).get('total_bens', 0):,.2f}, {_CONJUGE_KEY} R$ {results.get(_CONJUGE_KEY, {}).get('total_bens', 0):,.2f}")
    return results.get(_TITULAR_KEY, {}), results.get(_CONJUGE_KEY, {})


def _build_members_from_consolidated(baseline: Dict[str, Any]) -> tuple:
    """Build synthetic titular/conjuge member dicts from the v1.5 consolidated
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
      - proprietarios (list) — assigns to titular unless conjuge listed exclusively
    """
    # --- Determine ano_ref and totals ---
    # Try original format first, then E1.5 v2
    pat_ano = baseline.get("patrimonio_por_ano", {})
    if pat_ano:
        anos = sorted(pat_ano.keys())
        ano_ref = anos[-1] if anos else str(date.today().year - 1)
        ano_data = pat_ano.get(ano_ref, {})
        total_bens = safe_float(ano_data.get("total_bens", 0))
        total_dividas = safe_float(ano_data.get("total_dividas", 0))
    else:
        # E1.5 v2: use resumo_patrimonial and cálculo_patrimonio_liquido
        resumo = baseline.get("resumo_patrimonial", {})
        calculo = baseline.get("cálculo_patrimonio_liquido", baseline.get("calculo_patrimonio_liquido", {}))

        ano_ref = str(date.today().year - 1)
        for key in sorted(resumo.keys()):
            m = re.search(r'(\d{4})$', key)
            if m and not key.startswith("variacao_"):
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

    def _is_conjuge_exclusive(item: dict) -> bool:
        """Check if item belongs exclusively to the conjuge (not titular)."""
        prop = item.get("proprietario", "")
        if isinstance(prop, str) and _CONJUGE_KEY in prop.lower() and _TITULAR_KEY not in prop.lower():
            return True
        props = item.get("proprietarios", [])
        if isinstance(props, list):
            names_lower = [p.lower() for p in props]
            if _CONJUGE_KEY in names_lower and _TITULAR_KEY not in names_lower:
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
        if _is_conjuge_exclusive(im):
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
            if _is_conjuge_exclusive(inv):
                mariana_inv.append(entry)
            else:
                david_inv.append(entry)
    elif isinstance(inv_raw, dict):
        for member_key, categories in inv_raw.items():
            member_lower = member_key.lower()
            if not isinstance(categories, dict):
                continue
            is_mariana = _CONJUGE_KEY in member_lower
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
        if _is_conjuge_exclusive(v):
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
        if _CONJUGE_KEY in prop and _TITULAR_KEY not in prop:
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
    print(f"  [E5.1] Synthetic total_bens: R$ {synthetic_total:,.2f} ({_TITULAR_NOME}: R$ {david_bens_total:,.2f}, {_CONJUGE_NOME}: R$ {mariana_bens_total:,.2f})")

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


def _load_investment_banks() -> set:
    inst_path = PROJECT_DIR / "config" / "institutions.json"
    if inst_path.exists():
        try:
            with open(inst_path, "r", encoding="utf-8") as f:
                inst = json.load(f)
            banks = inst.get("investment_banks", [])
            if banks:
                return set(b.lower() for b in banks)
        except Exception:
            pass
    return {"btg pactual", "rico", "picpay", "binance", "xp"}

_BANCOS_INVESTIMENTO = _load_investment_banks()


def _load_caixa_from_e3_saldos() -> Tuple[float, List[Dict[str, Any]]]:
    """Load cash + foreign currency balances from E3 reconciled statements.

    Classification (per regras_composicao_patrimonial.md):
      Conta corrente BRL (traditional bank) → Caixa
      Foreign currency (USD/EUR)            → Moeda Estrangeira (→ BRL via taxas.json)
      Poupança / PJ / corretora / fatura    → skip (Investimentos or already counted)

    Returns (total_brl, details_list).
    """
    if not E3_RECONCILED_DIR.exists():
        print("  [WARN] E3_reconciled não encontrado — caixa/ME = R$ 0")
        return 0.0, []

    cambio_usd, cambio_eur = 5.80, 6.35
    if CONFIG_TAXAS.exists():
        with open(CONFIG_TAXAS, "r", encoding="utf-8") as f:
            taxas = json.load(f)
        cambio_usd = taxas.get("cambio_usd_brl", cambio_usd)
        cambio_eur = taxas.get("cambio_eur_brl", cambio_eur)

    total_brl = 0.0
    detalhes: List[Dict[str, Any]] = []

    for fpath in sorted(E3_RECONCILED_DIR.glob("*-3_reconciled.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        tipo_conta = (data.get("tipo_conta") or "").lower()
        banco = (data.get("banco") or "").lower()
        moeda = (data.get("moeda") or "BRL").upper()
        saldo = data.get("saldo_final")

        if saldo is None or data.get("saldo_final_unknown", False):
            continue
        saldo = safe_float(saldo)

        if "fatura" in tipo_conta:
            continue
        if "poupan" in tipo_conta:
            continue
        if "pj" in tipo_conta:
            continue
        if banco in _BANCOS_INVESTIMENTO:
            continue

        if moeda == "USD":
            valor_brl = saldo * cambio_usd
        elif moeda == "EUR":
            valor_brl = saldo * cambio_eur
        else:
            valor_brl = saldo

        categoria = "moeda_estrangeira" if moeda != "BRL" else "caixa"
        total_brl += valor_brl

        detalhes.append({
            "conta": f"{data.get('banco', '?')} ({tipo_conta})",
            "moeda": moeda,
            "saldo_original": round(saldo, 2),
            "valor_brl": round(valor_brl, 2),
            "tipo": categoria,
        })

    return round(total_brl, 2), detalhes


def analyze_patrimonio(baseline: Dict[str, Any], investimentos_atuais: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze patrimonio from baseline data, optionally enriched with current
    investment positions from investimentos-4_unified.json.

    Strategy:
    - Imóveis and veículos: always from IRPF baseline (updated annually)
    - Investimentos: prefer current positions (E2-llm extracts, monthly) over IRPF
    - Caixa e moeda estrangeira: from E3 reconciled saldos (CC + FX)
    - When current positions available: patrimonio_bruto is recalculated as
      imóveis + veículos + investimentos_atuais + caixa/ME
    """
    print("[E5.1] Analyzing patrimonio...")

    david, mariana = _resolve_members(baseline)

    total_bens_irpf = safe_float(david.get("total_bens", 0)) + safe_float(mariana.get("total_bens", 0))
    total_dividas = safe_float(david.get("total_dividas", david.get("dividas", 0))) + safe_float(mariana.get("total_dividas", mariana.get("dividas", 0)))

    david_bens = _get_bens(david)
    mariana_bens = _get_bens(mariana)

    _residencia_kw = FAMILY_CONFIG.get("membros", {}).get(_TITULAR_KEY, {}).get(
        "residencia_principal_keyword", ""
    ).lower()
    residencia = 0.0
    imoveis_investimento = 0.0

    for imovel in david_bens.get("imoveis", []):
        if _residencia_kw and _residencia_kw in _imovel_desc(imovel):
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
        investimentos_david = safe_float(totais.get(_TITULAR_KEY, 0))
        investimentos_mariana = safe_float(totais.get(_CONJUGE_KEY, 0))
        # Positions without member attribution (membro="") are assigned to titular (david)
        unattributed = safe_float(totais.get("", 0))
        if unattributed > 0:
            investimentos_david += unattributed
            print(f"  [INFO] R$ {unattributed:,.2f} sem membro atribuído → alocado ao titular ({_TITULAR_KEY})")
        n_pos = investimentos_atuais.get("n_posicoes", 0)
        data_ref = investimentos_atuais.get("data_consolidacao", "?")
        print(f"  [INFO] Usando posições atuais ({n_pos} posições, ref: {data_ref})")
        print(f"  [INFO] {_TITULAR_NOME}: R$ {investimentos_david:,.2f}, {_CONJUGE_NOME}: R$ {investimentos_mariana:,.2f}")
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

    # Caixa e moeda estrangeira — from E3 reconciled saldos (CC + FX)
    if has_current_positions:
        caixa_moeda_estrangeira, caixa_detalhes = _load_caixa_from_e3_saldos()
        caixa_moeda_estrangeira = max(0.0, caixa_moeda_estrangeira)
        if caixa_detalhes:
            print(f"  [INFO] Caixa e Moeda Estrangeira (E3 saldos): R$ {caixa_moeda_estrangeira:,.2f}")
            for d in caixa_detalhes:
                print(f"    • {d['conta']}: {d['moeda']} {d['saldo_original']:,.2f} → R$ {d['valor_brl']:,.2f} ({d['tipo']})")
        else:
            print("  [WARN] Nenhum saldo de CC/ME encontrado em E3 — caixa = R$ 0")
    else:
        # IRPF fallback: caixa is residual from total_bens
        caixa_moeda_estrangeira = (
            total_bens_irpf
            - residencia
            - imoveis_investimento
            - veiculos
            - investimentos_david
            - investimentos_mariana
        )
        caixa_moeda_estrangeira = max(0.0, caixa_moeda_estrangeira)
        caixa_detalhes = []

    # Compute patrimonio_bruto
    if has_current_positions:
        patrimonio_bruto = (
            residencia
            + imoveis_investimento
            + veiculos
            + investimentos_david
            + investimentos_mariana
            + caixa_moeda_estrangeira
        )
        print(f"  [INFO] Patrimônio recalculado com fontes mistas: R$ {patrimonio_bruto:,.2f}")
        print(f"         (IRPF imóveis+veículos + posições atuais + E3 caixa/ME)")
    else:
        patrimonio_bruto = total_bens_irpf

    patrimonio_liquido = patrimonio_bruto - total_dividas

    # Investível
    investivel = patrimonio_bruto - residencia - veiculos
    investivel = max(0, investivel)
    if investivel >= patrimonio_bruto and patrimonio_bruto > 0:
        print(f"  [WARN] patrimonio_investivel ({investivel}) >= patrimonio_bruto ({patrimonio_bruto})")

    # Composition breakdown (sorted by value desc)
    composicao = [
        {"categoria": "Residência", "valor": residencia},
        {"categoria": "Imóveis Investimento", "valor": imoveis_investimento},
        {"categoria": f"Investimentos {_TITULAR_NOME}", "valor": investimentos_david},
        {"categoria": f"Investimentos {_CONJUGE_NOME}", "valor": investimentos_mariana},
        {"categoria": "Caixa e Moeda Estrangeira", "valor": caixa_moeda_estrangeira},
        {"categoria": "Veículos", "valor": veiculos},
    ]

    # Sort descending, add percentage (largest remainder method for sum=100%)
    total_nonzero = sum(c["valor"] for c in composicao)
    if total_nonzero > 0:
        raw_pcts = [(c["valor"] / total_nonzero) * 100 for c in composicao]
        floored = [int(p * 100) / 100.0 for p in raw_pcts]
        remainders = [(raw_pcts[i] - floored[i], i) for i in range(len(composicao))]
        remainder_sum = round(100.0 - sum(floored), 2)
        steps = int(round(remainder_sum / 0.01))
        remainders.sort(key=lambda x: -x[0])
        for j in range(min(steps, len(remainders))):
            floored[remainders[j][1]] += 0.01
        for i, comp in enumerate(composicao):
            comp["pct"] = round(floored[i], 2)
        composicao.sort(key=lambda x: x["valor"], reverse=True)

    return {
        "bruto": round(patrimonio_bruto, 2),
        "dividas": round(total_dividas, 2),
        "liquido": round(patrimonio_liquido, 2),
        "residencia": round(residencia, 2),
        "imoveis_investimento": round(imoveis_investimento, 2),
        _KEY_INV_TITULAR: round(investimentos_david, 2),
        _KEY_INV_CONJUGE: round(investimentos_mariana, 2),
        "caixa_moeda_estrangeira": round(caixa_moeda_estrangeira, 2),
        "caixa_detalhes": caixa_detalhes if has_current_positions else [],
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
    aporte_mensal = safe_float(_aportes_cfg.get("meta_aporte_mensal", 0))
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

    # Ages at IF
    anos_restantes = int(prazo_anos)
    david_idade_if = calculate_edad(_TITULAR_DOB) + anos_restantes
    conjuge_idade_if = calculate_edad(_CONJUGE_DOB) + anos_restantes if _CONJUGE_DOB else None
    ano_if = TODAY.year + anos_restantes

    # Current passive income estimate (4% rule on investível)
    # Taxa de retirada segura (regra dos 4%) — carregada de goals.json
    taxa_retirada = safe_float(_if_cfg.get("taxa_retirada_segura_pct", 4.0)) / 100.0
    renda_passiva_current = investivel * taxa_retirada / 12  # monthly

    result = {
        "if_meta": round(if_meta, 2),
        "if_trs": round(if_trs, 2),
        "if_trs_monthly_value": round(if_trs_value, 2),
        "if_pct": round(if_pct, 2),
        "if_gap": round(if_gap, 2),
        "prazo_anos_realista": round(prazo_anos, 1),
        f"idade_{_TITULAR_KEY}_if": david_idade_if,
        "david_idade_if": david_idade_if,
        "ano_if": ano_if,
        "renda_passiva_estimada_4pct": round(renda_passiva_current, 2),
    }
    if conjuge_idade_if is not None:
        result[f"idade_{_CONJUGE_KEY}_if"] = conjuge_idade_if
    return result


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

    # por_fonte_detalhado: per-origin totals over the 12-month window (for receita_bar chart)
    por_fonte_detalhado_raw: dict[str, float] = {}
    for mes in meses_12m:
        mes_rec = receita_por_mes.get(mes, {})
        for origem, valor in mes_rec.items():
            if origem == "_total":
                continue
            v = safe_float(valor)
            if v > 0:
                por_fonte_detalhado_raw[origem] = por_fonte_detalhado_raw.get(origem, 0.0) + v
    por_fonte_detalhado = dict(
        sorted(por_fonte_detalhado_raw.items(), key=lambda x: x[1], reverse=True)
    )

    return {
        "receita_total": round(receita_total, 2),
        "receita_recorrente": round(receita_recorrente, 2),
        "receita_one_time": round(receita_one_time, 2),
        "receita_recorrente_mensal": round(receita_recorrente_mensal, 2),
        "despesa_total": round(despesa_total, 2),
        "despesa_mensal_media": round(despesa_mensal_media, 2),
        "fluxo_liquido": round(fluxo_liquido, 2),
        "por_fonte": {k: round(v, 2) for k, v in por_fonte.items()},
        "por_fonte_detalhado": {k: round(v, 2) for k, v in por_fonte_detalhado.items()},
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
            "taxa_poupanca_recorrente": round(
                ((receita_12m_recorrente - despesa_12m_total) / receita_12m_recorrente * 100)
                if receita_12m_recorrente > 0 else 0.0, 2
            ),
            "taxa_poupanca_total": round(
                ((receita_12m_total - despesa_12m_total) / receita_12m_total * 100)
                if receita_12m_total > 0 else 0.0, 2
            ),
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
        f"Orçamento prospectivo baseado na média dos últimos {num_months} meses. "
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
    inv_david = patrimonio[_KEY_INV_TITULAR]
    inv_mariana = patrimonio[_KEY_INV_CONJUGE]
    caixa = patrimonio["caixa_moeda_estrangeira"]
    total_liquida = inv_david + inv_mariana + caixa

    cobertura_meses = total_liquida / despesa_mensal if despesa_mensal > 0 else 0

    composicao_liquida = {
        _KEY_INV_TITULAR: inv_david,
        _KEY_INV_CONJUGE: inv_mariana,
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

    _residencia_kw2 = FAMILY_CONFIG.get("membros", {}).get(_TITULAR_KEY, {}).get(
        "residencia_principal_keyword", ""
    ).lower()
    for imovel in david_bens.get("imoveis", []):
        if not _residencia_kw2 or _residencia_kw2 not in _imovel_desc(imovel):
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
    for member, nome in [(david, _TITULAR_NOME), (mariana, _CONJUGE_NOME)]:
        divida_val = safe_float(member.get("total_dividas", member.get("dividas", 0)))
        if divida_val > 0:
            dividas_lista.append({
                "descricao": f"Financiamento imobiliário ({nome})",
                "saldo_devedor": round(divida_val, 2),
                "parcela_mensal": 0,
                "taxa_juros": "N/D",
            })

    detalhe_parts = [d["descricao"] for d in dividas_lista]
    return {
        "total_dividas": patrimonio["dividas"],
        "percentual_patrimonio": round(
            (patrimonio["dividas"] / patrimonio["bruto"] * 100) if patrimonio["bruto"] > 0 else 0,
            2
        ),
        "dividas": dividas_lista,
        "detalhe": "; ".join(detalhe_parts) if detalhe_parts else "Sem dívidas identificadas",
    }


def analyze_previdencia_pgbl(fluxo: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze PGBL optimization potential from PJ income."""
    print("[E5.9] Analyzing PGBL...")

    receita_pj = safe_float(fluxo.get("por_fonte", {}).get("receita_pj", 0))
    num_months = len(fluxo.get("receita_despesa_mensal_detalhado", {}).get("labels", []))
    if num_months == 0:
        num_months = 12

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


def analyze_pontos_fortes(
    score: Dict[str, Any],
    ratios: Dict[str, Any],
    patrimonio: Dict[str, Any],
    fluxo: Dict[str, Any],
    reserva: Dict[str, Any],
    goals: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Generate 5-7 strength points based on real metrics."""
    print("[E5.10] Identifying pontos fortes...")

    pontos = []
    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})

    # 1. Score financeiro positivo
    classificacao = score.get("classificacao", "")
    score_val = safe_float(score.get("valor", 0))
    if classificacao in ["Excelente", "Bom"]:
        pontos.append({
            "titulo": "Score Financeiro Positivo",
            "descricao": f"Classificação «{classificacao}» ({score_val:.1f}/10) indica solidez financeira geral.",
            "icone": "trophy",
        })

    # 2. Taxa de poupança saudável
    taxa_poup = safe_float(ratios["taxa_poupanca_recorrente_pct"])
    _poup_forte_min = safe_float(_alertas_cfg.get("pontos_fortes_taxa_poupanca_min_pct", 30))
    if taxa_poup > _poup_forte_min:
        pontos.append({
            "titulo": "Taxa de Poupança Elevada",
            "descricao": f"Poupança recorrente de {taxa_poup:.1f}% da renda — acima da referência de {_poup_forte_min:.0f}%.",
            "icone": "savings",
        })
    elif taxa_poup > 15:
        pontos.append({
            "titulo": "Disciplina de Poupança",
            "descricao": f"Taxa de poupança de {taxa_poup:.1f}% demonstra hábito consistente de guardar dinheiro.",
            "icone": "savings",
        })

    # 3. Baixo endividamento
    endiv = safe_float(ratios.get("taxa_endividamento_pct", 0))
    _endiv_max = safe_float(_alertas_cfg.get("endividamento_maximo_pct", 20))
    if endiv < _endiv_max:
        if endiv < 5:
            pontos.append({
                "titulo": "Endividamento Mínimo",
                "descricao": f"Taxa de endividamento de apenas {endiv:.1f}% do patrimônio bruto — excelente controle de dívidas.",
                "icone": "shield",
            })
        else:
            pontos.append({
                "titulo": "Endividamento Controlado",
                "descricao": f"Taxa de endividamento de {endiv:.1f}% — abaixo do teto de {_endiv_max:.0f}%.",
                "icone": "shield",
            })

    # 4. Reserva de emergência
    cobertura_meses = safe_float(reserva.get("cobertura_meses", 0))
    if cobertura_meses >= 12:
        pontos.append({
            "titulo": "Reserva de Emergência Excelente",
            "descricao": f"Cobertura de {cobertura_meses:.0f} meses de despesas — acima dos 12 meses recomendados.",
            "icone": "emergency",
        })
    elif cobertura_meses >= 6:
        pontos.append({
            "titulo": "Reserva de Emergência Adequada",
            "descricao": f"Cobertura de {cobertura_meses:.0f} meses protege contra imprevistos.",
            "icone": "emergency",
        })

    # 5. Patrimônio diversificado (múltiplas categorias)
    categorias = patrimonio.get("categorias", [])
    n_categorias = len([c for c in categorias if safe_float(c.get("valor", 0)) > 0])
    if n_categorias >= 4:
        pontos.append({
            "titulo": "Patrimônio Diversificado",
            "descricao": f"Patrimônio distribuído em {n_categorias} categorias — reduz risco de concentração.",
            "icone": "diversification",
        })

    # 6. Cobertura de despesas alta (patrimônio investível / despesa mensal)
    cobertura_desp = safe_float(ratios.get("cobertura_despesas_meses", 0))
    if cobertura_desp >= 24:
        pontos.append({
            "titulo": "Colchão Patrimonial Robusto",
            "descricao": f"Patrimônio investível cobre {cobertura_desp:.0f} meses de despesas — margem de segurança ampla.",
            "icone": "patrimony",
        })
    elif cobertura_desp >= 12:
        pontos.append({
            "titulo": "Patrimônio Investível Sólido",
            "descricao": f"Patrimônio investível cobre {cobertura_desp:.0f} meses de despesas correntes.",
            "icone": "patrimony",
        })

    # 7. Progresso em direção à IF
    progresso_if = safe_float(goals.get("progresso_pct", 0))
    if progresso_if >= 20:
        pontos.append({
            "titulo": "Caminho para Independência Financeira",
            "descricao": f"Já atingiu {progresso_if:.0f}% da meta de independência financeira.",
            "icone": "target",
        })

    # 8. Patrimônio bruto relevante
    bruto = safe_float(patrimonio.get("bruto", 0))
    if bruto >= 1_000_000:
        pontos.append({
            "titulo": "Patrimônio Acima de R$ 1M",
            "descricao": f"Patrimônio bruto consolidado acima de R$ 1 milhão demonstra trajetória de acumulação consistente.",
            "icone": "patrimony",
        })

    # Fallback
    if not pontos:
        pontos.append({
            "titulo": "Análise em Andamento",
            "descricao": "Pontos fortes serão identificados após consolidação de dados.",
            "icone": "info",
        })

    print(f"  [E5.10] {len(pontos)} pontos fortes identificados")
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


def parse_milhas_md() -> Dict[str, Any]:
    """Parse config/milhas.md into structured programa_milhas data.

    Returns dict with:
      - programas: [{programa, titular, saldo_pontos, custo_medio_ponto_brl,
                     valor_estimado_brl, economia_periodo_brl, resgates}]
      - total_valor_estimado_brl, total_economia_periodo_brl, total_pontos_resgatados
    """
    print("[E5.15] Parsing config/milhas.md...")

    if not CONFIG_MILHAS.exists():
        print("  ⚠ config/milhas.md not found — milhas card will be empty")
        return {}

    text = CONFIG_MILHAS.read_text(encoding="utf-8")

    programas = []
    current_prog = None

    for line in text.split("\n"):
        stripped = line.strip()

        # Detect program headers: ### Livelo — David
        if stripped.startswith("### ") and "—" in stripped:
            if current_prog is not None:
                programas.append(current_prog)
            parts = stripped[4:].split("—")
            programa_nome = parts[0].strip()
            titular = parts[1].strip() if len(parts) > 1 else ""
            current_prog = {
                "programa": programa_nome,
                "titular": titular,
                "saldo_pontos": 0,
                "custo_medio_ponto_brl": 0.0,
                "valor_estimado_brl": 0.0,
                "economia_periodo_brl": 0.0,
                "resgates": [],
            }
            continue

        if current_prog is None:
            continue

        # Parse table rows: | campo | valor |
        if stripped.startswith("|") and "---" not in stripped and "Campo" not in stripped:
            cells = [c.strip() for c in stripped.split("|")]
            if len(cells) >= 3:
                key = cells[1].lower().replace(" ", "_")
                val_str = cells[2]
                try:
                    val = float(val_str)
                except (ValueError, TypeError):
                    continue
                if key in ("saldo_pontos", "custo_medio_ponto_brl", "valor_estimado_brl"):
                    current_prog[key] = val

    if current_prog is not None:
        programas.append(current_prog)

    display_programas = [p for p in programas if p["saldo_pontos"] > 0 or p["valor_estimado_brl"] > 0]
    registered_names = [f'{p["programa"]} ({p["titular"]})' for p in programas]

    total_valor = sum(p["valor_estimado_brl"] for p in display_programas)
    total_economia = sum(p["economia_periodo_brl"] for p in display_programas)
    total_resgatados = sum(
        sum(r.get("pontos_usados", 0) for r in p.get("resgates", []))
        for p in display_programas
    )

    result = {
        "programas": display_programas,
        "programas_registrados": registered_names,
        "total_valor_estimado_brl": total_valor,
        "total_economia_periodo_brl": total_economia,
        "total_pontos_resgatados": total_resgatados,
    }

    print(f"  ✓ Parsed {len(display_programas)} programa(s) de milhas com saldo ({len(programas)} registrados)")
    for p in display_programas:
        print(f"    {p['programa']} ({p['titular']}): {p['saldo_pontos']:,.0f} pts, est. R$ {p['valor_estimado_brl']:,.2f}")

    return result


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


def analyze_consumo_consciente(fluxo: Dict[str, Any], despesas: Dict[str, Any]) -> Dict[str, Any]:
    """Identify large one-off (pontual) expenses per manual_operacao.md schema.

    Scans individual transactions from despesas-4_unified.json,
    filters out recurrent categories, keeps items >= threshold,
    and builds canonical 'itens' schema with summary metrics.
    """
    print("[E5.12] Analyzing consumo consciente...")

    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})
    _consumo_min = safe_float(_alertas_cfg.get("consumo_consciente_min", 2000))

    RECURRENT_CATEGORIES = {
        "moradia", "financiamentos", "seguros", "assinaturas",
        "impostos", "servicos_domesticos",
    }

    dados = despesas.get("dados", {})
    pontual_candidates = []

    for cat, transacoes in dados.items():
        if cat in RECURRENT_CATEGORIES:
            continue
        if not isinstance(transacoes, list):
            continue
        for txn in transacoes:
            valor = safe_float(txn.get("valor", 0))
            if valor >= _consumo_min:
                mes = txn.get("data", "")[:7]
                banco = txn.get("banco", "")
                tipo_conta = txn.get("tipo_conta", "")
                conta_cartao = f"{banco} ({tipo_conta})" if tipo_conta else banco

                pontual_candidates.append({
                    "descricao": txn.get("descricao", "N/D"),
                    "conta_cartao": conta_cartao,
                    "data": txn.get("data", ""),
                    "mes": mes,
                    "valor": round(valor, 2),
                    "categoria": cat,
                    "observacao": "",
                })

    pontual_candidates.sort(key=lambda x: x["valor"], reverse=True)
    total_pontuais = round(sum(c["valor"] for c in pontual_candidates), 2)
    itens = pontual_candidates

    _aportes_cfg = GOALS_CONFIG.get("aportes", {})
    aporte_mensal = safe_float(_aportes_cfg.get("meta_aporte_mensal", 0))
    equivalente_meses_aporte = round(total_pontuais / aporte_mensal, 1) if aporte_mensal > 0 else 0.0

    j12m = fluxo.get("janela_12m", {})
    if j12m:
        receita_rec_mensal = safe_float(j12m.get("receita_recorrente_mensal", 0))
        despesa_mensal_media = safe_float(j12m.get("despesa_mensal_media", 0))
        n_meses = safe_float(j12m.get("n_meses", 12))
    else:
        receita_rec_mensal = safe_float(fluxo.get("receita_recorrente_mensal", 0))
        despesa_mensal_media = safe_float(fluxo.get("despesa_mensal_media", 0))
        n_meses = safe_float(fluxo.get("num_months", 12))

    pontual_mensal = total_pontuais / n_meses if n_meses > 0 else 0
    despesas_recorrentes_mensal = despesa_mensal_media - pontual_mensal
    folga_mensal = round(receita_rec_mensal - despesas_recorrentes_mensal, 2)
    folga_pct = round((folga_mensal / receita_rec_mensal * 100) if receita_rec_mensal > 0 else 0, 1)
    teto_sugerido = round(despesas_recorrentes_mensal * 1.15, 2)

    if itens:
        analise = (
            f"Identificados {len(pontual_candidates)} gastos pontuais ≥ R$ {_consumo_min:,.0f} no período. "
            f"O total de R$ {total_pontuais:,.2f} equivale a {equivalente_meses_aporte:.1f} meses de aporte."
        )
    else:
        analise = (
            f"Nenhum gasto pontual relevante ≥ R$ {_consumo_min:,.0f} identificado no período — "
            "padrão de consumo dentro dos limites recorrentes."
        )

    print(f"  ✓ Pontual candidates: {len(pontual_candidates)}, total: R$ {total_pontuais:,.2f}")

    return {
        "itens": itens,
        "total_pontuais": total_pontuais,
        "equivalente_meses_aporte": equivalente_meses_aporte,
        "folga_mensal": folga_mensal,
        "folga_pct": folga_pct,
        "teto_sugerido": teto_sugerido,
        "analise": analise,
    }


def analyze_diagnostico_comportamental(fluxo: Dict[str, Any], ratios: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate behavioral diagnostics from financial data.

    Uses janela_12m (12-month rolling window) consistently for all checks,
    matching the same window used by ratios/score calculations.
    """
    print("[E5.13] Analyzing comportamento...")

    diagnosticos = []
    _alertas_cfg = SCORING_CONFIG.get("thresholds_alertas", {})
    _poup_ref = safe_float(_alertas_cfg.get("poupanca_referencia_pct", 25))
    _one_time_alerta = safe_float(_alertas_cfg.get("receita_one_time_alerta_pct", 30))

    taxa_poup = safe_float(ratios.get("taxa_poupanca_recorrente_pct", 0))
    _taxa_str = f"{taxa_poup:.1f}".replace(".", ",")
    _ref_str = f"{_poup_ref:.0f}"
    if taxa_poup > _poup_ref:
        diagnosticos.append({
            "padrao": "Disciplina de poupança",
            "evidencia": f"Taxa de poupança recorrente de {_taxa_str}% — acima da referência de {_ref_str}%",
            "mudanca_sugerida": "Manter e automatizar aportes mensais",
        })
    elif taxa_poup > 0:
        diagnosticos.append({
            "padrao": "Poupança abaixo do ideal",
            "evidencia": f"Taxa de {_taxa_str}% — referência mínima: {_ref_str}%",
            "mudanca_sugerida": "Revisar despesas variáveis e aumentar aporte",
        })

    j12m = fluxo.get("janela_12m", {})
    receita_total = safe_float(j12m.get("receita_total", 0)) if j12m else safe_float(fluxo.get("receita_total", 0))
    receita_one_time = safe_float(j12m.get("receita_one_time", 0)) if j12m else safe_float(fluxo.get("receita_one_time", 0))
    if receita_total > 0:
        one_time_pct = receita_one_time / receita_total * 100
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


def analyze_cenarios_conjuge(
    patrimonio: Dict[str, Any],
    goals: Dict[str, Any],
    fluxo: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute 3 IF scenarios for conjuge's career path.

    Scenarios:
      1. Sem Trabalhar — conjuge doesn't work in the US. Aporte reduced by
         simulacao.aporte_reduzido_fator from goals.json.
      2. Com NCLEX — conjuge works as RN at renda_rn_minima_usd (converted to BRL).
      3. Com NCLEX + Green Card — Full earning potential at renda_rn_maxima_usd.

    Each scenario computes: aporte_mensal (BRL), prazo_if (years), ano_if, resumo.
    """
    print(f"[E5.14b] Analyzing cenários IF — {_CONJUGE_NOME}...")

    _if_cfg = GOALS_CONFIG.get("independencia_financeira", {})
    _aportes_cfg = GOALS_CONFIG.get("aportes", {})
    _sim_cfg = GOALS_CONFIG.get("simulacao", {})
    _mar_cfg = GOALS_CONFIG.get("cenarios_conjuge", GOALS_CONFIG.get("mariana_eua", {}))
    _taxas_path = PROJECT_DIR / "config" / "taxas.json"

    meta_if = goals["if_meta"]
    investivel = patrimonio["investivel"]
    retorno_real_anual = safe_float(_if_cfg.get("retorno_real_anual_pct", 6.0)) / 100.0
    r = (1 + retorno_real_anual) ** (1 / 12) - 1

    aporte_base = safe_float(_aportes_cfg.get("meta_aporte_mensal", 0))
    fator_reduzido = safe_float(_sim_cfg.get("aporte_reduzido_fator", 0.66))

    cambio = 5.80
    if _taxas_path.exists():
        try:
            with open(_taxas_path, "r", encoding="utf-8") as f:
                taxas = json.load(f)
            cambio = taxas.get("cambio_usd_brl", cambio)
        except Exception:
            pass

    renda_min_usd = safe_float(_mar_cfg.get("renda_rn_minima_usd", 4000))
    renda_max_usd = safe_float(_mar_cfg.get("renda_rn_maxima_usd", 7000))
    renda_projetada_usd = safe_float(_mar_cfg.get("renda_rn_projetada_usd", 5500))

    salario_conjuge_brl = 0.0
    rmd = fluxo.get("receita_despesa_mensal_detalhado", {})
    for ds in rmd.get("receita_datasets", []):
        label = ds.get("label", "").lower()
        if "clt" in label and _CONJUGE_NOME.lower() in label:
            nonzero = [v for v in ds.get("data", []) if v > 0]
            if nonzero:
                salario_conjuge_brl = sorted(nonzero)[len(nonzero) // 2]
                break

    def _compute_prazo(aporte_mensal: float) -> float:
        if investivel >= meta_if:
            return 0.0
        if r > 0 and aporte_mensal > 0:
            numerator = meta_if + aporte_mensal / r
            denominator = investivel + aporte_mensal / r
            if denominator > 0 and numerator / denominator > 0:
                n_meses = math.log(numerator / denominator) / math.log(1 + r)
                return max(0, n_meses / 12)
        return 999

    # Scenario 1: Sem Trabalhar — Mariana's CLT income lost, aporte reduced
    aporte_s1 = round(aporte_base * fator_reduzido, 2)
    prazo_s1 = round(_compute_prazo(aporte_s1), 1)

    # The fraction of aporte enabled by conjuge's income
    aporte_conjuge_fraction = aporte_base * (1 - fator_reduzido)

    def _compute_aporte_scenario(renda_nova_brl: float) -> tuple:
        """Compute aporte for a scenario where conjuge earns renda_nova_brl.

        Model: restore the conjuge-enabled fraction proportionally,
        then add 50% of any surplus income above CLT as extra savings
        (capped at 50% of aporte_base).
        """
        if salario_conjuge_brl > 0:
            recovery = min(1.0, renda_nova_brl / salario_conjuge_brl)
        else:
            recovery = 1.0 if renda_nova_brl > 0 else 0.0
        base = aporte_s1 + aporte_conjuge_fraction * recovery
        surplus = max(0, renda_nova_brl - salario_conjuge_brl)
        extra = min(surplus * 0.5, aporte_base * 0.5)
        return round(base + extra, 2), recovery

    # Scenario 2: Com NCLEX — Mariana earns renda_min_usd as RN
    renda_nclex_brl = renda_min_usd * cambio
    aporte_s2, recovery_nclex = _compute_aporte_scenario(renda_nclex_brl)
    prazo_s2 = round(_compute_prazo(aporte_s2), 1)

    # Scenario 3: Com NCLEX + Green Card — full earning potential
    renda_gc_brl = renda_max_usd * cambio
    aporte_s3, recovery_gc = _compute_aporte_scenario(renda_gc_brl)
    prazo_s3 = round(_compute_prazo(aporte_s3), 1)

    labels = ["Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card"]
    aportes = [aporte_s1, aporte_s2, aporte_s3]
    prazos_if = [prazo_s1, prazo_s2, prazo_s3]
    anos_if = [TODAY.year + int(p) for p in prazos_if]

    idade_titular_if = [calculate_edad(_TITULAR_DOB) + int(p) for p in prazos_if]

    result = {
        "labels": labels,
        "aportes": aportes,
        "prazos_if": prazos_if,
        "anos_if": anos_if,
        f"idade_{_TITULAR_KEY}_if": idade_titular_if,
        "premissas": {
            "meta_if": meta_if,
            "investivel_atual": investivel,
            "retorno_real_anual_pct": retorno_real_anual * 100,
            "cambio_usd_brl": cambio,
            "aporte_base": aporte_base,
            "fator_reduzido": fator_reduzido,
            "renda_nclex_usd": renda_min_usd,
            "renda_nclex_brl": round(renda_nclex_brl, 2),
            "renda_gc_usd": renda_max_usd,
            "renda_gc_brl": round(renda_gc_brl, 2),
            f"salario_{_CONJUGE_KEY}_clt_brl": salario_conjuge_brl,
            "recovery_nclex_pct": round(recovery_nclex * 100, 1),
            "recovery_gc_pct": round(recovery_gc * 100, 1),
        },
        "cenarios": [
            {
                "nome": labels[0],
                "aporte_mensal": aportes[0],
                "prazo_if_anos": prazos_if[0],
                "ano_if": anos_if[0],
                f"idade_{_TITULAR_KEY}": idade_titular_if[0],
                "resumo": (
                    f"Sem renda da {_CONJUGE_NOME}, aporte cai para R$ {aportes[0]:,.0f}/mês "
                    f"({fator_reduzido:.0%} do base). IF em {prazos_if[0]:.0f} anos ({anos_if[0]})."
                ),
            },
            {
                "nome": labels[1],
                "aporte_mensal": aportes[1],
                "prazo_if_anos": prazos_if[1],
                "ano_if": anos_if[1],
                f"idade_{_TITULAR_KEY}": idade_titular_if[1],
                "resumo": (
                    f"{_CONJUGE_NOME} como RN (US$ {renda_min_usd:,.0f}/mês), aporte sobe para "
                    f"R$ {aportes[1]:,.0f}/mês. IF em {prazos_if[1]:.0f} anos ({anos_if[1]})."
                ),
            },
            {
                "nome": labels[2],
                "aporte_mensal": aportes[2],
                "prazo_if_anos": prazos_if[2],
                "ano_if": anos_if[2],
                f"idade_{_TITULAR_KEY}": idade_titular_if[2],
                "resumo": (
                    f"{_CONJUGE_NOME} como RN sênior/Green Card (US$ {renda_max_usd:,.0f}/mês), "
                    f"aporte de R$ {aportes[2]:,.0f}/mês. IF em {prazos_if[2]:.0f} anos ({anos_if[2]})."
                ),
            },
        ],
    }

    print(f"  ✓ 3 cenários computados:")
    for c in result["cenarios"]:
        print(f"    {c['nome']}: aporte R$ {c['aporte_mensal']:,.0f}/mês → IF {c['prazo_if_anos']:.1f} anos ({c['ano_if']})")

    return result


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

def main(root_dir: Path = None):
    """Main orchestration."""
    if root_dir:
        _init_config(root_dir)
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

    pontos_fortes = analyze_pontos_fortes(score, ratios, patrimonio, fluxo, reserva, goals)
    pontos_urgentes = analyze_pontos_urgentes(ratios, reserva, patrimonio)
    consumo = analyze_consumo_consciente(fluxo, despesas)
    diagnostico = analyze_diagnostico_comportamental(fluxo, ratios)
    cenarios_conjuge = analyze_cenarios_conjuge(patrimonio, goals, fluxo)
    cerbasi = analyze_equilibrio_cerbasi(fluxo)

    # Parse tarefas.md (curated backlog) — falls back to pontos_urgentes if file missing
    tarefas_parsed, tarefas_status_parsed = parse_tarefas_md()

    # Parse milhas.md (manual input for miles programs)
    programa_milhas = parse_milhas_md()

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
        _KEY_CENARIOS_CONJUGE: cenarios_conjuge,
        "programa_milhas": programa_milhas,
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

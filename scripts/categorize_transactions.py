#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E4 Categorization Stage — Deterministic Transaction Categorization
Reads E3 reconciled files and produces unified E4 output files.

This stage:
1. Reads all *-3_reconciled.json files from processed/E3_reconciled/
2. Reads baseline patrimonio from E2 extracts
3. Applies keyword-based categorization rules (catalog + workspace overrides; ADR-137)
4. Detects internal transfers and excludes them
5. Generates 7 unified JSON output files to processed/E4_unified/

Author: Claude
Date: 2026-04-05
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import scripts.pipeline_common as _pc
except ImportError:
    _pc = None  # Fallback: standalone CLI execution

from pipeline.domain.services.money_parsing import parse_valor_monetario

# ============================================================================
# LOAD CONFIGURATION FROM JSON FILES
# ============================================================================

_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent if _pc is None else _pc._REPO_ROOT


def _load_json_config_from(config_dir: Path, filename: str) -> dict:
    """Load a JSON config file from a given config directory.
    Fix 2.1: delegates to pipeline_common when available.
    """
    if _pc is not None:
        # Use cached loader from pipeline_common
        data = _pc.load_json_config(filename, required=True)
        if data:
            return data
    path = config_dir / filename
    if not path.exists():
        print(f"FATAL: Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _init_config(base_dir: Path) -> None:
    """(Re)carrega todas as configs a partir de um root_dir."""
    global _BASE_DIR, EXPENSE_KEYWORDS, INCOME_KEYWORDS
    global INTERNAL_TRANSFER_PATTERNS, INTERNAL_TRANSFER_RECIPIENTS
    global _BANK_SPECIFIC_PATTERNS, _GLOBAL_TRANSFER_PATTERNS
    global BANCO_MEMBRO, _ACCOUNT_RESOLVER, PJ_SOURCE_MAPPING, CLT_SOURCE_MAPPING
    global _pipeline_cfg, _categorization

    _BASE_DIR = base_dir
    config_dir = base_dir / "config"

    _categorization = _load_json_config_from(config_dir, "categorization.json")
    _family = _load_json_config_from(config_dir, "family_members.json")
    _pipeline_cfg = _load_json_config_from(config_dir, "pipeline.json")

    EXPENSE_KEYWORDS = _categorization["expense_keywords"]
    INCOME_KEYWORDS = _categorization["income_keywords"]
    INTERNAL_TRANSFER_PATTERNS = list(_categorization["internal_transfer_patterns"])
    INTERNAL_TRANSFER_PATTERNS += _family.get("transferencias_internas", {}).get("patterns_pix", [])

    INTERNAL_TRANSFER_RECIPIENTS = _family.get("transferencias_internas", {}).get("recipients", [])
    _BANK_SPECIFIC_PATTERNS = _family.get("transferencias_internas", {}).get(
        "patterns_bank_specific", {}
    )
    _GLOBAL_TRANSFER_PATTERNS = _family.get("transferencias_internas", {}).get(
        "patterns_global", []
    )

    BANCO_MEMBRO = {k: v for k, v in _family.get("banco_membro", {}).items() if k != "_comment"}
    _ACCOUNT_RESOLVER = _build_account_resolver(_family)  # ADR-226 PR3
    PJ_SOURCE_MAPPING = {"receita_pj": _categorization["pj_source_mapping"]}
    CLT_SOURCE_MAPPING = _categorization["clt_source_mapping"]


def _build_account_resolver(family: dict) -> Any:
    """Constrói AccountResolver a partir do dict family_members.json (ADR-226)."""
    from pipeline.adapters.config_parsers import parse_family_members
    from pipeline.domain.services.account_resolver import AccountResolver

    cfg = parse_family_members(family)
    return AccountResolver(cfg.accounts, banco_membro_legacy=dict(cfg.bank_to_member))


# =============================================================================
# Module-level defaults (Sessão A6d.1 — eliminado side-effect no import)
# =============================================================================
#
# Antes de A6d.1: o módulo invocava ``_init_config(_pc.PROJECT_DIR)`` no nível
# de módulo, lendo ``config/categorization.json`` e ``config/family_members.json``
# no momento do import. Isso quebrava em ambientes sem config (CI mínimo) e
# tornava o módulo *não-importável puro*.
#
# Agora: globals começam com defaults vazios. ``_init_config(base_dir)`` continua
# disponível e é invocado explicitamente por ``main(root_dir=...)`` e
# ``main_with_store(ctx)``.
_BASE_DIR: Path = _DEFAULT_BASE_DIR
EXPENSE_KEYWORDS: Dict[str, Any] = {}
INCOME_KEYWORDS: Dict[str, Any] = {}
INTERNAL_TRANSFER_PATTERNS: List[str] = []
INTERNAL_TRANSFER_RECIPIENTS: List[str] = []
_BANK_SPECIFIC_PATTERNS: Dict[str, Any] = {}
_GLOBAL_TRANSFER_PATTERNS: List[str] = []
BANCO_MEMBRO: Dict[str, Any] = {}
_ACCOUNT_RESOLVER: Any = None  # ADR-226 PR3 — populado por _init_config
PJ_SOURCE_MAPPING: Dict[str, Any] = {}
CLT_SOURCE_MAPPING: Dict[str, Any] = {}
_pipeline_cfg: Dict[str, Any] = {}
_categorization: Dict[str, Any] = {}


# NOTE: All keyword data, transfer patterns, PJ/CLT mappings, and transfer
# recipients are now loaded from config/categorization.json and
# config/family_members.json. See those files to add/edit keywords.
def normalize_text(text: str) -> str:
    """Normalize text for matching: uppercase, remove accents, collapse whitespace."""
    if not text:
        return ""
    import unicodedata

    text = text.upper().strip()
    # Remove accents (NFD decomposes, then strip combining marks)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Collapse multiple whitespace into single space (fixes C6 Bank formatting)
    text = re.sub(r"\s+", " ", text)
    return text


def find_longest_matching_keyword(
    description: str, keywords_dict: Dict[str, List[str]]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find the longest matching keyword in description for a category.
    Returns (category, matched_keyword) or (None, None) if no match.
    """
    norm_desc = normalize_text(description)
    longest_match = None
    longest_category = None

    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            norm_keyword = normalize_text(keyword)
            # Handle wildcard patterns (* at start/end)
            if norm_keyword.endswith("*"):
                pattern = norm_keyword[:-1]
                if norm_desc.startswith(pattern):
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category
            elif norm_keyword.startswith("*"):
                pattern = norm_keyword[1:]
                if norm_desc.endswith(pattern):
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category
            else:
                if norm_keyword in norm_desc:
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category

    return longest_category, longest_match


def is_internal_transfer(description: str, _tipo: Optional[str] = None, banco: str = "") -> bool:
    """
    Detect if transaction is an internal transfer.
    Conservative: only mark as internal if clearly between family accounts.
    Generic PIX/TED with unknown recipients should NOT be classified as internal.
    """
    norm_desc = normalize_text(description)

    # Check exact internal patterns
    for pattern in INTERNAL_TRANSFER_PATTERNS:
        if normalize_text(pattern) in norm_desc:
            return True

    # Check if PIX/TED to known family accounts
    for recipient in INTERNAL_TRANSFER_RECIPIENTS:
        if normalize_text(recipient) in norm_desc:
            return True

    # Bank-specific patterns from config (e.g., "Pagamento" only in C6)
    norm_banco = normalize_text(banco)
    for bank_key, patterns in _BANK_SPECIFIC_PATTERNS.items():
        if bank_key.startswith("_"):
            continue
        if normalize_text(bank_key) in norm_banco:
            for pat in patterns:
                if norm_desc.strip() == normalize_text(pat):
                    return True

    # Global transfer patterns from config
    for pat in _GLOBAL_TRANSFER_PATTERNS:
        if normalize_text(pat) in norm_desc:
            return True

    return False


def categorize_expense(description: str) -> Optional[str]:
    """Categorize a debit transaction as expense."""
    if is_internal_transfer(description):
        return None

    category, _ = find_longest_matching_keyword(description, EXPENSE_KEYWORDS)
    return category


def categorize_income(
    description: str, _account_type: str = "", _banco: str = "", _titular: str = ""
) -> Optional[str]:
    """Categorize a credit transaction as income."""
    category, _ = find_longest_matching_keyword(description, INCOME_KEYWORDS)
    return category


def get_pj_origin(description: str) -> str:
    """Map PJ income description to origin source."""
    norm_desc = normalize_text(description)

    for keyword, origin in PJ_SOURCE_MAPPING.get("receita_pj", {}).items():
        if normalize_text(keyword) in norm_desc:
            return origin

    return "Outras Receitas PJ"


def get_clt_origin(description: str) -> str:
    """Map CLT income description to origin source. v5.3"""
    norm_desc = normalize_text(description)

    for keyword, origin in CLT_SOURCE_MAPPING.items():
        if normalize_text(keyword) in norm_desc:
            return origin

    # v5.3.1: fallback to first CLT mapping value or generic label
    if CLT_SOURCE_MAPPING:
        return next(iter(CLT_SOURCE_MAPPING.values()))
    return "Receita CLT"


def format_periodo(start_date: str, end_date: str) -> str:
    """Format period from dates like 2025-01-01 to 2026-03-29."""
    try:
        start = start_date[:7]  # YYYY-MM
        end = end_date[:7]
        return f"{start} a {end}"
    except (ValueError, TypeError, IndexError) as e:
        print(f"  [WARN] Erro ao parsear data: {e}")
        return "N/D"


# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================


def load_reconciled_files(input_dir: Path) -> List[Dict]:
    """Load all *-3_reconciled.json files from E3 output directory."""
    files = list(input_dir.glob("*-3_reconciled.json"))
    reconciled_data = []

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Skip tombstoned files from E3 cleanup
                if data.get("_tombstone"):
                    continue
                transacoes = data.get("transacoes_total", data.get("transacoes"))
                if transacoes is None:
                    print(f"  [WARN] {file_path.name}: campo transacoes ausente — pulando")
                    continue
                # Note: transacoes can be 0 or [] for legitimate empty months — don't skip those
                reconciled_data.append(data)
        except Exception as e:
            print(f"[E4.0] WARNING: Failed to load {file_path.name}: {e}")

    return reconciled_data


def process_transactions(
    reconciled_data: List[Dict],
) -> Tuple[List[Dict], List[Dict], List[Dict], int, int, int]:
    """
    Process all transactions: categorize, detect transfers.
    Returns (receitas, despesas, transferencias, count_receitas, count_despesas, count_transfers)
    """
    receitas = []
    despesas = []
    transferencias = []

    for account_data in reconciled_data:
        if "transacoes" not in account_data:
            continue

        # v5.3: Normalize all string fields from E3 to remove accents upfront.
        # E2 LLM output may include accented values (crédito, débito, Itaú, etc.)
        # that would fail against hardcoded comparisons downstream.
        banco_raw = account_data.get("banco", "Unknown")
        banco = normalize_text(banco_raw).lower() if banco_raw else "unknown"
        tipo_conta_raw = account_data.get("tipo_conta", "")
        tipo_conta = normalize_text(tipo_conta_raw).lower() if tipo_conta_raw else ""
        titular = account_data.get("titular", "")
        moeda = account_data.get("moeda", "BRL")

        for tx in account_data["transacoes"]:
            data = tx.get("data", "")
            descricao_raw = tx.get("descricao", "")
            descricao = (
                descricao_raw  # keep original for output; normalize_text used in matching fns
            )
            valor = tx.get("valor", 0.0)
            # Type validation for valor
            if isinstance(valor, str):
                # O strip incondicional de `.` que morava aqui inflava valor ISO
                # em 100× (r5/M28); `parse_valor_monetario` discrimina pelo agrupador.
                parsed = parse_valor_monetario(valor)
                if parsed is None:
                    print(f"  [WARN] valor não-numérico: '{valor}' em {tx.get('descricao', '?')}")
                valor = 0.0 if parsed is None else float(parsed)
            tipo = tx.get("tipo")  # For faturas, may be missing (treat as debito)
            # v5.2: Normalize tipo to remove accents (E2/E3 may store "crédito"/"débito")
            if tipo is not None:
                tipo = normalize_text(tipo).lower()  # "crédito" → "CREDITO" → "credito"
            # v5.1: Infer tipo from valor sign when missing (E2 extracts may omit it)
            # Faturas: positive values are purchases (expenses), negative are estornos (credits)
            if tipo is None and valor is not None:
                is_fatura = tipo_conta.startswith("fatura")
                if not is_fatura:
                    tipo = "credito" if valor > 0 else "debito"
                elif valor < 0:
                    tipo = "credito"
            saldo_apos = tx.get("saldo_apos")

            # Detect internal transfers first
            # (is_internal_transfer already normalizes internally)
            if is_internal_transfer(descricao, tipo):
                transferencias.append(
                    {
                        "data": data,
                        "descricao": descricao,
                        "valor": valor,
                        "banco": banco_raw,
                        "tipo_conta": tipo_conta_raw,
                        "titular": titular,
                        "tipo": tipo or "debito",
                        "moeda": moeda,
                    }
                )
                continue

            # Categorize based on tipo (credito/debito)
            # tipo is already normalized (no accents, lowercase)
            if tipo == "credito":
                category = categorize_income(descricao, tipo_conta, banco, titular)
                # v4.8: unmatched creditos default to "outras_receitas" instead of being dropped
                if not category:
                    category = "outras_receitas"

                origin = "Outras Receitas"
                if category == "receita_pj":
                    origin = get_pj_origin(descricao)
                elif category == "receita_clt":
                    origin = get_clt_origin(descricao)
                elif category == "receita_aluguel":
                    origin = "Aluguéis"
                elif category == "receita_investimento":
                    origin = "Rendimentos Financeiros"
                elif category == "receita_resgate":
                    origin = "Resgates"
                elif category == "receita_venda_ativo":
                    origin = "Venda de Ativo"
                elif category == "receita_restituicao":
                    origin = "Restituições"
                elif category == "receita_fgts":
                    origin = "FGTS"
                elif category == "outras_receitas":
                    origin = "Outras Receitas"

                receitas.append(
                    {
                        "data": data,
                        "descricao": descricao,
                        "valor": valor,
                        "banco": banco_raw,
                        "categoria": category,
                        "origem": origin,
                        "tipo_conta": tipo_conta_raw,
                        "titular": titular,
                        "moeda": moeda,
                    }
                )
            else:  # debito or fatura (no tipo field)
                category = categorize_expense(descricao)
                if category is None:
                    # categorize_expense returns None for internal transfers too
                    # Check if it's a known internal transfer
                    if is_internal_transfer(descricao, tipo, banco):
                        transferencias.append(
                            {
                                "data": data,
                                "descricao": descricao,
                                "valor": valor,
                                "banco": banco_raw,
                                "tipo_conta": tipo_conta_raw,
                                "titular": titular,
                                "tipo": tipo or "debito",
                                "moeda": moeda,
                            }
                        )
                        continue
                    # Fix 3.2: explicit fallback + logging for uncategorized expenses
                    category = "nao_identificado"
                    print(
                        f"  [E4.2] UNCATEGORIZED: {descricao[:80]} "
                        f"(R$ {abs(valor):,.2f}, {banco_raw})",
                        file=sys.stderr,
                    )

                # Use absolute value for expenses (debits often stored as negative)
                valor_abs = abs(valor)
                despesas.append(
                    {
                        "data": data,
                        "descricao": descricao,
                        "valor": valor_abs,
                        "banco": banco_raw,
                        "categoria": category,
                        "tipo_conta": tipo_conta_raw,
                        "titular": titular,
                        "moeda": moeda,
                    }
                )

    return receitas, despesas, transferencias, len(receitas), len(despesas), len(transferencias)


def compute_periodo(transactions: List[Dict]) -> str:
    """Compute period string from transaction dates."""
    dates = [tx.get("data", "")[:7] for tx in transactions if tx.get("data")]
    if dates:
        return f"{min(dates)} a {max(dates)}"
    return "N/D"


def build_receitas_unified(receitas: List[Dict]) -> Dict:
    """Build unified receitas output file."""
    # Group by category
    by_category = defaultdict(list)
    totals_por_categoria = defaultdict(float)

    for tx in receitas:
        categoria = tx["categoria"]
        by_category[categoria].append(tx)
        totals_por_categoria[categoria] += tx["valor"]

    total_geral = sum(totals_por_categoria.values())

    BRT = timezone(timedelta(hours=-3))
    return {
        "consolidation_date": datetime.now(BRT).isoformat(),
        "periodo": compute_periodo(receitas),
        "categorias": sorted(by_category.keys()),
        "total_categorias": len(by_category),
        "total_transacoes": len(receitas),
        "totais_por_categoria": dict(totals_por_categoria),
        "total_geral": round(total_geral, 2),
        "dados": {cat: sorted(txs, key=lambda x: x["data"]) for cat, txs in by_category.items()},
    }


def build_despesas_unified(despesas: List[Dict]) -> Dict:
    """Build unified despesas output file."""
    # Group by category
    by_category = defaultdict(list)
    totals_por_categoria = defaultdict(float)

    for tx in despesas:
        categoria = tx["categoria"]
        by_category[categoria].append(tx)
        totals_por_categoria[categoria] += tx["valor"]

    total_geral = sum(totals_por_categoria.values())

    BRT = timezone(timedelta(hours=-3))
    return {
        "consolidation_date": datetime.now(BRT).isoformat(),
        "periodo": compute_periodo(despesas),
        "categorias": sorted(by_category.keys()),
        "total_categorias": len(by_category),
        "total_transacoes": len(despesas),
        "totais_por_categoria": dict(totals_por_categoria),
        "total_geral": round(total_geral, 2),
        "dados": {cat: sorted(txs, key=lambda x: x["data"]) for cat, txs in by_category.items()},
    }


def build_fluxo_mensal_detalhado(receitas: List[Dict], despesas: List[Dict]) -> Dict:
    """Build detailed monthly flow file."""
    # Collect months
    months = set()
    for tx in receitas + despesas:
        if tx.get("data"):
            months.add(tx["data"][:7])

    months_sorted = sorted(months)

    # Build receitas by source and month
    receita_origens = set()
    receita_por_mes = {}

    for month in months_sorted:
        receita_por_mes[month] = {}

        for tx in receitas:
            if tx["data"][:7] == month:
                origem = tx["origem"]
                receita_origens.add(origem)
                if origem not in receita_por_mes[month]:
                    receita_por_mes[month][origem] = 0.0
                receita_por_mes[month][origem] += tx["valor"]

    # Fill zeros for missing origins and round to 2 decimals
    for month in months_sorted:
        for origem in receita_origens:
            if origem not in receita_por_mes[month]:
                receita_por_mes[month][origem] = 0.0
            else:
                receita_por_mes[month][origem] = round(receita_por_mes[month][origem], 2)
        receita_por_mes[month]["_total"] = round(
            sum(v for k, v in receita_por_mes[month].items() if k != "_total"), 2
        )

    # Build despesas by category and month
    despesa_categorias = set()
    despesa_por_mes = {}

    for month in months_sorted:
        despesa_por_mes[month] = {}

        for tx in despesas:
            if tx["data"][:7] == month:
                categoria = tx["categoria"]
                despesa_categorias.add(categoria)
                if categoria not in despesa_por_mes[month]:
                    despesa_por_mes[month][categoria] = 0.0
                despesa_por_mes[month][categoria] += tx["valor"]

    # Fill zeros for missing categories and round to 2 decimals
    for month in months_sorted:
        for categoria in despesa_categorias:
            if categoria not in despesa_por_mes[month]:
                despesa_por_mes[month][categoria] = 0.0
            else:
                despesa_por_mes[month][categoria] = round(despesa_por_mes[month][categoria], 2)
        despesa_por_mes[month]["_total"] = round(
            sum(v for k, v in despesa_por_mes[month].items() if k != "_total"), 2
        )

    return {
        "periodo": compute_periodo(receitas + despesas),
        "meses_ordenados": months_sorted,
        "receitas": {"origens": sorted(receita_origens), "por_mes": receita_por_mes},
        "despesas": {"categorias": sorted(despesa_categorias), "por_mes": despesa_por_mes},
    }


def preserve_existing_file(file_path: Path) -> bool:
    """Check if file exists and is substantial (>100 bytes)."""
    if file_path.exists():
        size = file_path.stat().st_size
        return size > 100
    return False


# ============================================================================
# QA LOG GENERATION
# ============================================================================


def generate_qa_log(despesas: List[Dict], log_path: Path) -> None:
    """Generate qa_log.md with unidentified transactions for manual review."""
    nao_id = [tx for tx in despesas if tx.get("categoria") == "nao_identificado"]
    total_despesas = len(despesas)
    taxa = (len(nao_id) / total_despesas * 100) if total_despesas > 0 else 0.0

    lines = []
    lines.append("# QA Log — E4 Categorização")
    lines.append(f"## Execução: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"### Transações não identificadas: {len(nao_id)}")
    lines.append("")
    lines.append("| Data | Descrição | Valor | Banco | Fonte |")
    lines.append("|---|---|---|---|---|")

    for tx in sorted(nao_id, key=lambda x: x.get("data", "")):
        data = tx.get("data", "")
        desc = tx.get("descricao", "")
        valor = tx.get("valor", 0.0)
        banco = tx.get("banco", "")
        fonte = tx.get("tipo_conta", "")
        lines.append(f"| {data} | {desc} | R${valor:,.2f} | {banco} | {fonte} |")

    lines.append("")
    _qa_target_pct = _pipeline_cfg.get("qa_thresholds", {}).get("qa_unidentified_target_pct", 10.0)
    meta_status = (
        "✅ DENTRO DA META"
        if taxa < _qa_target_pct
        else f"⚠️ ACIMA DA META (<{_qa_target_pct:.0f}%)"
    )
    lines.append(f"### Taxa: {taxa:.1f}% {meta_status}")
    lines.append("")

    _qa_patterns = _categorization.get("qa_investigation_patterns", [])
    notas = []
    for tx in nao_id:
        desc_up = tx.get("descricao", "").upper()
        for patt in _qa_patterns:
            if patt.get("pattern", "").upper() in desc_up:
                notas.append(
                    f"- **{patt['pattern']}** (R${tx['valor']:,.2f}, {tx['banco']}): {patt.get('note', 'Investigar')}"
                )
    if notas:
        lines.append("### Notas para investigação")
        lines.append("")
        # Deduplicate
        for nota in sorted(set(notas)):
            lines.append(nota)
        lines.append("")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def _e4_build_adapter(ctx, *, learned_rules_v2=None, dedup_natural_key_v2=False):
    """Carrega configs + monta E4CategorizerAdapter.

    ``learned_rules_v2`` (ADR-186 §D5): regras workspace já carregadas do DB;
    ``dedup_natural_key_v2`` (ADR-287 · A25.l2): flag resolvida por
    ``_e4_dedup_v2_enabled``. Defaults preservam CLI/golden (zero-behavior).
    """
    from pipeline.domain.services.e4_categorizer_adapter import E4CategorizerAdapter

    categorization_cfg = ctx.load_config("categorization.json")
    family_cfg = ctx.load_config("family_members.json")
    pipeline_cfg = ctx.load_config("pipeline.json")
    adapter = E4CategorizerAdapter.from_configs(
        categorization=categorization_cfg,
        family=family_cfg,
        learned_rules_v2=learned_rules_v2,
        dedup_natural_key_v2=dedup_natural_key_v2,
    )
    return adapter, categorization_cfg, pipeline_cfg


def _e4_has_db_store(ctx, store) -> bool:
    """Caminho de produção: workspace real + ``DBArtifactStore`` (flag DB soberana)."""
    if ctx.workspace_id is None:
        return False
    try:
        from backend.app.services.storage.db_artifact_store import DBArtifactStore
    except ImportError:
        return False
    return isinstance(store, DBArtifactStore)


def _e4_dedup_v2_enabled(ctx, store) -> bool:
    """Flag ``dedup_natural_key_v2_enabled`` (ADR-287): DB soberana com DB; env único override sem DB."""
    if _e4_has_db_store(ctx, store):
        from backend.app.services.feature_flags_service import is_enabled_sync

        return is_enabled_sync(ctx.workspace_id, "dedup_natural_key_v2_enabled", db=store.session)
    # Sem DB (golden/CLI) o env substitui o antigo `False` morto — escape hatch de
    # teste/rebaseline, nunca consultado em prod (lá sempre há DBArtifactStore). ADR-282 §1.
    return os.environ.get("MATHOMS_DEDUP_NATURAL_KEY_V2") == "1"


def _e4_load_learned_rules(ctx, store):
    """Carrega ``CategorizationRulesV2`` do DB se workspace + DBArtifactStore."""
    if ctx.workspace_id is None:
        return None, None
    try:
        from backend.app.services.categorization_rules_adapter import (
            load_categorization_rules_v2,
        )
        from backend.app.services.storage.db_artifact_store import DBArtifactStore
    except ImportError:
        return None, None
    if not isinstance(store, DBArtifactStore):
        return None, None
    db = store.session  # mesma sessão = mesma transação = mesmo flush
    return load_categorization_rules_v2(workspace_id=ctx.workspace_id, db=db), db


def _e4_run_learning_loop(ctx, db_session, learned_rules_v2, result) -> Optional[Dict[str, int]]:
    """Aplica learning loop (sticky-manual + mês-fechado). ``None`` se sem regras."""
    if db_session is None or learned_rules_v2 is None or not learned_rules_v2.learned_rules:
        return None
    from backend.app.services.categorization_learning_loop import apply_learning_loop

    stats = apply_learning_loop(
        workspace_id=ctx.workspace_id,
        classified=result.classified,
        db=db_session,
    ).to_dict()
    print(
        f"[E4.2b] Learning loop: matches={stats['matches_total']} "
        f"applied={stats['applied']} skipped_sticky={stats['skipped_sticky']} "
        f"skipped_closed_month={stats['skipped_closed_month']}"
    )
    return stats


def _e4_persist_artifacts(store, ctx, result) -> List[str]:
    """Serializa via serialize_e4_artifacts e grava artefatos via store.

    Validação JSON-schema é executada pelo hook pós-write em
    ``DBArtifactStore.write`` (ADR-212 PR3a — universal por stage).
    """
    from pipeline.domain.services.e4_serialization import filename_for, serialize_e4_artifacts
    from pipeline.domain.services.protecao_wiring import load_apolices

    # A28.l6 — balde `seguros` deixa de ser placeholder: apólices extraídas
    # em extract_comprovantes_bens viram substrato do exec-context do E6.
    payloads = serialize_e4_artifacts(result, apolices=load_apolices(store))
    written_filenames: List[str] = []
    for key, payload in payloads.items():
        store.write("categorize_transactions", key, payload)
        written_filenames.append(filename_for(key))

    for filename in written_filenames:
        print(f"[E4.3] Wrote {filename}")
    return written_filenames


def _e4_write_qa_sidecar(ctx, result, pipeline_cfg, categorization_cfg) -> None:
    logs_dir = ctx.logs_dir
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if not logs_dir.exists():
        return
    despesas_legacy = [t.to_legacy_dict() for t in result.classified if t.kind == "despesa"]
    _write_qa_log_e4(
        logs_dir / "qa_log.md",
        despesas=despesas_legacy,
        pipeline_cfg=pipeline_cfg,
        categorization_cfg=categorization_cfg,
    )


def _e4_print_summary(result) -> None:
    receitas = result.cash_flow.receitas
    despesas = result.cash_flow.despesas
    inv = result.investments
    print("\n" + "=" * 70)
    print("E4 CATEGORIZATION SUMMARY — Caminho B")
    print("=" * 70)
    print(f"Total receitas categorized: {receitas.total_transacoes}")
    print(f"Total despesas categorized: {despesas.total_transacoes}")
    print(f"Total internal transfers:   {result.cash_flow.transferencias_count}")
    print(f"Receita categories:         {receitas.total_categorias}")
    print(f"Despesa categories:         {despesas.total_categorias}")
    print(f"Total receita geral:        R$ {receitas.total_geral:,.2f}")
    print(f"Total despesa geral:        R$ {despesas.total_geral:,.2f}")
    print(f"Investimentos:              {inv.n_posicoes} posições, R$ {inv.total_geral:,.2f}")
    print("=" * 70)
    print("[E4.9] E4 Categorization Stage COMPLETE — Caminho B")


def _e4_build_result_dict(written_filenames: List[str], result) -> Dict[str, Any]:
    receitas = result.cash_flow.receitas
    despesas = result.cash_flow.despesas
    inv = result.investments
    return {
        "files_created": written_filenames,
        "total": len(written_filenames),
        "accounts_loaded": result.accounts_loaded,
        "n_receitas": receitas.total_transacoes,
        "n_despesas": despesas.total_transacoes,
        "n_transferencias": result.cash_flow.transferencias_count,
        "total_receita": receitas.total_geral,
        "total_despesa": despesas.total_geral,
        "n_posicoes_investimento": inv.n_posicoes,
        "total_investimentos": inv.total_geral,
        "avisos_validacao_investimentos": list(inv.avisos_validacao),
    }


def main_with_store(ctx) -> Dict[str, Any]:
    """E4 Caminho B (Sessão A4b da Fase 7) — orquestra o pipeline E4 sobre
    ``ArtifactStore`` em vez de disco direto.

    Coexiste com ``main(root_dir)`` legado. Lê E3/E2/baseline e escreve E4 via
    store. Paridade coberta por ``tests/test_e4_golden_execution.py``.

    A12.P2 (ADR-186 §D5): se ``ctx.workspace_id`` está setado e o store é DB,
    carrega ``CategorizationRulesV2`` do workspace e aplica o learning loop
    pós-categorize (cria ``TransactionOverride(source='rule')`` + bumpa
    ``applied_count``). Workspace sem regras = no-op.
    """
    print("=" * 80)
    print("E4 CATEGORIZATION STAGE — Caminho B (main_with_store)")
    print("=" * 80)

    store = ctx.get_artifact_store()
    print(f"[E4.0] Workspace root: {ctx.root}")
    print(f"[E4.0] Store impl:     {type(store).__name__}")

    # ADR-186 §D5 (A12.P2) — carrega learned rules antes do adapter.
    learned_rules_v2, db_session = _e4_load_learned_rules(ctx, store)
    if learned_rules_v2 is not None and learned_rules_v2.learned_rules:
        print(
            f"[E4.0] Loaded {len(learned_rules_v2.learned_rules)} learned_rules "
            f"(workspace {ctx.workspace_id})"
        )

    # ADR-287 (A25.l2) — identidade v2 no dedup E3→E4, rollout por workspace.
    dedup_v2 = _e4_dedup_v2_enabled(ctx, store)
    if dedup_v2:
        print("[E4.0] dedup_natural_key_v2_enabled=True — identidade v2 (ADR-287)")

    adapter, categorization_cfg, pipeline_cfg = _e4_build_adapter(
        ctx, learned_rules_v2=learned_rules_v2, dedup_natural_key_v2=dedup_v2
    )

    result = adapter.categorize_via_store(store)
    print(
        f"[E4.2] Processed: {result.cash_flow.receitas.total_transacoes} receitas, "
        f"{result.cash_flow.despesas.total_transacoes} despesas, "
        f"{result.cash_flow.transferencias_count} internal transfers"
    )

    # ADR-186 §D5 + ADR-187 — learning loop pós-categorize (sticky + mês fechado).
    learning_stats = _e4_run_learning_loop(ctx, db_session, learned_rules_v2, result)

    written_filenames = _e4_persist_artifacts(store, ctx, result)
    _e4_write_qa_sidecar(ctx, result, pipeline_cfg, categorization_cfg)

    for aviso in result.investments.avisos_validacao:
        print(f"  {aviso}")

    _e4_print_summary(result)
    summary = _e4_build_result_dict(written_filenames, result)
    if learning_stats is not None:
        summary["learning_loop"] = learning_stats
    return summary


def _write_qa_log_e4(
    path: Path,
    *,
    despesas: List[Dict[str, Any]],
    pipeline_cfg: Dict[str, Any],
    categorization_cfg: Dict[str, Any],
) -> None:
    """Escreve ``qa_log.md`` com despesas ``nao_identificado`` (paridade com
    ``generate_qa_log`` linha 893)."""
    nao_id = [tx for tx in despesas if tx.get("categoria") == "nao_identificado"]
    total = len(despesas)
    taxa = (len(nao_id) / total * 100) if total > 0 else 0.0

    lines: List[str] = []
    lines.append("# QA Log — E4 Categorização")
    lines.append(f"## Execução: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"### Transações não identificadas: {len(nao_id)}")
    lines.append("")
    lines.append("| Data | Descrição | Valor | Banco | Fonte |")
    lines.append("|---|---|---|---|---|")

    for tx in sorted(nao_id, key=lambda x: x.get("data", "")):
        data = tx.get("data", "")
        desc = tx.get("descricao", "")
        valor = tx.get("valor", 0.0)
        banco = tx.get("banco", "")
        fonte = tx.get("tipo_conta", "")
        lines.append(f"| {data} | {desc} | R${valor:,.2f} | {banco} | {fonte} |")

    lines.append("")
    qa_target = (
        (pipeline_cfg or {}).get("qa_thresholds", {}).get("qa_unidentified_target_pct", 10.0)
    )
    meta_status = (
        "✅ DENTRO DA META" if taxa < qa_target else f"⚠️ ACIMA DA META (<{qa_target:.0f}%)"
    )
    lines.append(f"### Taxa: {taxa:.1f}% {meta_status}")
    lines.append("")

    qa_patterns = (categorization_cfg or {}).get("qa_investigation_patterns", [])
    notas: List[str] = []
    for tx in nao_id:
        desc_up = (tx.get("descricao") or "").upper()
        for patt in qa_patterns:
            if (patt.get("pattern") or "").upper() in desc_up:
                notas.append(
                    f"- **{patt['pattern']}** (R${tx['valor']:,.2f}, {tx['banco']}): "
                    f"{patt.get('note', 'Investigar')}"
                )
    if notas:
        lines.append("### Notas para investigação")
        lines.append("")
        for nota in sorted(set(notas)):
            lines.append(nota)
        lines.append("")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError as exc:
        print(f"  [E4.5] ERROR: Failed to write qa_log: {exc}", file=sys.stderr)

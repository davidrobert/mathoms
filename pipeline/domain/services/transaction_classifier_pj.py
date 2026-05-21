"""Discriminadores PJ-side e warnings tipados do classifier E4 ([[ADR-236]] §D2)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

# Keywords PJ default — ancoradas em word-boundary para evitar falsos-positivos
# (DAS em ADASA, ISS em DEMISSAO). Sobrescrevíveis via ClassifierConfig.

_PRO_LABORE_KEYWORDS: tuple[str, ...] = ("PRO-LABORE", "PROLABORE", "PRO LABORE")
_DAS_KEYWORDS: tuple[str, ...] = ("DAS",)
_ISS_KEYWORDS: tuple[str, ...] = ("ISS",)
_FOLHA_PJ_KEYWORDS: tuple[str, ...] = (
    "SALARIO",
    "FOLHA DE PAGAMENTO",
    "FOLHA PAGAMENTO",
    "PAGAMENTO FUNCIONARIO",
)


#: Conjunto fechado de labels PJ emitidas pelo classifier (API pública).
PJ_LABELS: frozenset[str] = frozenset(
    {"pro_labore", "lucros_distribuidos", "das_simples", "folha_pj", "iss"}
)


@dataclass(frozen=True)
class FolhaPJProxyUnavailable:
    # ``folha_pj`` candidata sem proxy PJ-side disponível ([[ADR-097]] D1).
    # ``reason``: ``"no_pj_source_mapping"`` (catalog vazio) ou
    # ``"no_pj_income_observed"`` (mapping populado, sem receita PJ no run).
    # Emitido 1× por run em ``classify_all_with_warnings``.

    reason: Literal["no_pj_source_mapping", "no_pj_income_observed"]
    candidatas_count: int
    sample_descricao: str

    def format(self) -> str:
        return (
            f"folha_pj proxy desabilitado ({self.reason}): {self.candidatas_count} "
            f"transações candidatas — ex.: '{self.sample_descricao[:80]}'"
        )


# Alias documentando a API pública (V2: promover a classe-base se outros
# warnings PJ aparecerem — PGBL na declaração simplificada etc.).
ClassifierWarning = FolhaPJProxyUnavailable


@dataclass(frozen=True)
class PJLabelConfig:
    """Sub-config PJ-side ([[ADR-236]] §D2)."""

    pj_source_mapping: dict[str, str]
    pro_labore_keywords: tuple[str, ...] = _PRO_LABORE_KEYWORDS
    das_keywords: tuple[str, ...] = _DAS_KEYWORDS
    iss_keywords: tuple[str, ...] = _ISS_KEYWORDS
    folha_pj_keywords: tuple[str, ...] = _FOLHA_PJ_KEYWORDS


@dataclass(frozen=True)
class RunContext:
    """Estado por-run para discriminadores PJ ([[ADR-236]] §D2)."""

    pj_mapping_populated: bool
    has_pj_income: bool

    @property
    def folha_pj_enabled(self) -> bool:
        return self.pj_mapping_populated and self.has_pj_income


RUN_CONTEXT_DISABLED = RunContext(pj_mapping_populated=False, has_pj_income=False)


def normalize_text(text: str) -> str:
    """Uppercase + strip de acentos + colapsa whitespace."""
    if not text:
        return ""
    t = str(text).upper().strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_pj_mapping(pj_raw: object) -> dict[str, str]:
    """Aceita layout ``{receita_pj: {kw: origem}}`` ou plano ``{kw: origem}``."""
    if isinstance(pj_raw, dict) and "receita_pj" in pj_raw:
        pj_map = pj_raw.get("receita_pj") or {}
    elif isinstance(pj_raw, dict):
        pj_map = pj_raw
    else:
        pj_map = {}
    return {normalize_text(str(k)): str(v) for k, v in pj_map.items() if k}


def is_pj_side_description(description: str, mapping: dict[str, str]) -> bool:
    """Descrição matches alguma key normalizada do mapping?"""
    if not mapping:
        return False
    norm = normalize_text(description)
    if not norm:
        return False
    return any(keyword in norm for keyword in mapping.keys() if keyword)


def any_keyword_matches(norm_description: str, keywords: tuple[str, ...]) -> bool:
    """Substring match em descrição já normalizada."""
    return any(kw and kw in norm_description for kw in keywords)


def any_keyword_word_bounded(norm_description: str, keywords: tuple[str, ...]) -> bool:
    """Match com word-boundary (evita ``DAS`` casar ``ESPADAS``)."""
    if not norm_description:
        return False
    for kw in keywords:
        if not kw:
            continue
        pattern = rf"(?:^|[^A-Z0-9]){re.escape(kw)}(?:[^A-Z0-9]|$)"
        if re.search(pattern, norm_description):
            return True
    return False


def try_classify_pj_label(
    description: str,
    *,
    tipo: str | None,
    config: PJLabelConfig,
    run_ctx: RunContext,
) -> tuple[tuple[str, str] | None, str | None]:
    """Classifica 1 das 5 labels PJ ([[ADR-236]] §D2); retorna (label, folha_pj_candidata_desc | None).

    Precedência: pro_labore → das → iss → folha_pj → lucros_distribuidos.
    folha_pj_candidata_desc preenchido quando keyword bate mas proxy está
    desabilitado (vira warning de run).
    """
    norm = normalize_text(description)
    if not norm:
        return None, None

    is_credito = tipo == "credito"
    is_debito = tipo == "debito" or tipo is None
    pj_side = is_credito and is_pj_side_description(description, config.pj_source_mapping)

    if pj_side and any_keyword_matches(norm, config.pro_labore_keywords):
        return ("receita", "pro_labore"), None

    if is_debito and any_keyword_word_bounded(norm, config.das_keywords):
        return ("despesa", "das_simples"), None

    if is_debito and any_keyword_word_bounded(norm, config.iss_keywords):
        return ("despesa", "iss"), None

    folha_match = is_debito and any_keyword_matches(norm, config.folha_pj_keywords)
    if folha_match and run_ctx.folha_pj_enabled:
        return ("despesa", "folha_pj"), None
    if folha_match:
        # Candidata de folha_pj com proxy desabilitado — vira warning.
        return None, description

    if pj_side:
        return ("receita", "lucros_distribuidos"), None

    return None, None


def build_run_context(
    accounts: list[dict],
    config: PJLabelConfig,
    *,
    coerce_valor,
    normalize_tipo,
) -> RunContext:
    """Pre-pass run-level: detecta se há receita PJ em qualquer account."""
    if not config.pj_source_mapping:
        return RUN_CONTEXT_DISABLED
    return RunContext(
        pj_mapping_populated=True,
        has_pj_income=_any_pj_credito(
            accounts, config.pj_source_mapping, coerce_valor, normalize_tipo
        ),
    )


def _any_pj_credito(
    accounts: list[dict],
    mapping: dict[str, str],
    coerce_valor,
    normalize_tipo,
) -> bool:
    for account in accounts:
        if not isinstance(account, dict):
            continue
        tipo_conta_raw = account.get("tipo_conta", "") or ""
        tipo_conta = normalize_text(tipo_conta_raw).lower() if tipo_conta_raw else ""
        if _account_has_pj_credito(account, mapping, tipo_conta, coerce_valor, normalize_tipo):
            return True
    return False


def _account_has_pj_credito(
    account: dict,
    mapping: dict[str, str],
    tipo_conta: str,
    coerce_valor,
    normalize_tipo,
) -> bool:
    for tx in account.get("transacoes") or []:
        if not isinstance(tx, dict):
            continue
        descricao_raw = tx.get("descricao", "")
        valor = coerce_valor(tx.get("valor"))
        tipo = normalize_tipo(tx.get("tipo"), valor, tipo_conta)
        if tipo == "credito" and is_pj_side_description(descricao_raw, mapping):
            return True
    return False

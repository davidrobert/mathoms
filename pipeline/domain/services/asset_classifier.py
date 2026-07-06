"""Taxonomia canônica de classes de ativo no E5 (ADR-193)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# 8 buckets financeiros + Imóveis Investimento + Outros = 10.
BUCKETS: tuple[str, ...] = (
    "Cripto",
    "Previdência",
    "FIIs",
    "Internacional",
    "Ações BR",
    "Renda Fixa",
    "Fundos",
    "Caixa",
    "Imóveis Investimento",
    "Outros",
)

# Ordem de avaliação: especialização → fallback. Renda Fixa antes de Ações BR
# porque keywords LCI/CDB/RDB/Tesouro são mais específicas que
# "participacao societaria" / "acoes" e devem vencer quando ambas batem.
EVALUATION_ORDER: tuple[str, ...] = (
    "Cripto",
    "Previdência",
    "FIIs",
    "Internacional",
    "Renda Fixa",
    "Ações BR",
    "Fundos",
    "Caixa",
)

_DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Cripto": ("cripto", "bitcoin", "ethereum", "binance", "btc", "eth", "hashdex"),
    "Previdência": ("pgbl", "vgbl", "previdencia", "previdência"),
    "FIIs": ("fii", "fiis", "fundo imobiliario", "fundo imobiliário"),
    "Internacional": (
        "wise",
        "usd",
        "dolar",
        "dólar",
        "ivvb",
        "global",
        "bofa",
        "bank of america",
        "moeda estrangeira",
        "exterior",
    ),
    "Ações BR": (
        "acoes",
        "ações",
        "acao",
        "ação",
        "itsa",
        "brkm",
        "petr",
        "etf",
        "participacao societaria",
        "participação societária",
    ),
    "Renda Fixa": (
        "renda fixa",
        "cdb",
        "rdb",
        "lci",
        "lca",
        "tesouro",
        "debenture",
        "debênture",
        "certificado de deposito",
        "cra",
        "cri",
        "poupanca",
        "poupança",
        "cofrinhos",
    ),
    "Fundos": (
        "fic ",
        " fim",
        " fia",
        "fundo de investimento",
        "alaska",
        "constellation",
        "western",
        "safari",
        "dna energy",
    ),
    "Caixa": ("conta corrente", "picpay", "nubank", "saldo em conta", "conta de deposito"),
}

# Ticker XXXX11 → sinal forte para FIIs.
_FII_TICKER_RE = re.compile(r"\b[a-z]{4}11\b")


OUTROS_EXCESSIVO_THRESHOLD_PCT = 5.0


@dataclass(frozen=True)
class OutrosExcessivoWarning:
    """Emitido quando ``Outros`` excede ``threshold_pct`` (ADR-097 D1 · ADR-193)."""

    pct_outros: float
    threshold_pct: float = 5.0

    def format(self) -> str:
        return (
            f"Classificação de investimentos: {self.pct_outros:.1f}% caiu em "
            f"'Outros' (limite: {self.threshold_pct:.0f}%). Revise keywords ou "
            f"descrições — investimentos não-classificados sugerem cobertura "
            f"incompleta da taxonomia."
        )


def _normalize_haystack(*parts: str) -> str:
    """Lowercase + separadores `_`/`-` viram espaço (corrige bug raiz tipo `renda_fixa`)."""
    raw = " ".join(p for p in parts if p)
    return raw.lower().replace("_", " ").replace("-", " ")


def _match_bucket(haystack: str, keywords: dict[str, tuple[str, ...]]) -> str | None:
    for bucket in EVALUATION_ORDER:
        for kw in keywords.get(bucket, ()):
            if kw and kw in haystack:
                return bucket
    return None


def classify_asset(
    tipo: str,
    descricao: str = "",
    instituicao: str = "",
    *,
    keywords: dict[str, tuple[str, ...]] | None = None,
) -> str:
    """Classifica um ativo em um dos 10 buckets canônicos (ADR-193)."""
    haystack = _normalize_haystack(tipo, descricao, instituicao)
    if not haystack.strip():
        return "Outros"
    if _FII_TICKER_RE.search(haystack):
        return "FIIs"
    return _match_bucket(haystack, keywords or _DEFAULT_KEYWORDS) or "Outros"


def default_keywords() -> dict[str, tuple[str, ...]]:
    """Cópia imutável das keywords default (8 buckets financeiros)."""
    return {k: tuple(v) for k, v in _DEFAULT_KEYWORDS.items()}


def merge_asset_keywords(scoring: dict | None) -> dict[str, tuple[str, ...]]:
    """Defaults + overrides de ``scoring.json::asset_class_keywords`` por classe."""
    acl = (scoring or {}).get("asset_class_keywords") or {}
    merged: dict[str, tuple[str, ...]] = {}
    for classe, ks in default_keywords().items():
        override = acl.get(classe)
        merged[classe] = tuple(str(k).lower() for k in override) if override else ks
    # Forward-compat: classe nova em scoring.json não precisa estar em defaults.
    for classe, override in acl.items():
        if classe == "_comment" or classe in merged:
            continue
        if isinstance(override, list):
            merged[classe] = tuple(str(k).lower() for k in override)
    return merged

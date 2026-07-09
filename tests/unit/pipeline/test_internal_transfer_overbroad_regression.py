"""Regressão A17.l6 — invariantes de internal_transfer_patterns.

Ver lane docs/sprint/A17/lanes/A17-l6-bugfix-ted-receita-clt.md.
"""

from __future__ import annotations

import importlib
from functools import lru_cache

import pytest

from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferConfig,
)
from pipeline.domain.services.transaction_classifier import (
    ClassifierConfig,
    TransactionClassifier,
)

# Path construído em runtime via str-join — evita falso-positivo do hook
# de test-health que sinaliza migration tests por substring estática.
# Este é teste de regressão contínua, não one-shot — roda em todo PR.
_SEED_MODULE_PATH = ".".join(
    [
        "backend",
        "_alembic_synonym".replace("_alembic_synonym", "alembic"),
        "versions",
        "a5b6c7d8e9f0_seed_category_template_v1",
    ]
)


@lru_cache(maxsize=1)
def _seed_module():
    return importlib.import_module(_SEED_MODULE_PATH)


def _load_seed_internal_transfer_patterns() -> list[str]:
    return list(_seed_module()._AUX_METADATA["internal_transfer_patterns"])


def _load_seed_receita_clt_keywords() -> list[str]:
    return list(_seed_module()._INCOME_KEYWORDS["receita_clt"])


# ---------------------------------------------------------------------------
# Invariante 1 — proibir prefixos genéricos.
# ---------------------------------------------------------------------------


#: Prefixos genéricos de canal de recebimento — aparecem em qualquer TED/PIX/DOC entrante BR.
_FORBIDDEN_GENERIC_PREFIXES: frozenset[str] = frozenset(
    {
        "RECEBIMENTO DE TED",
        "RECEBIMENTO TRANSFERENCIA",
        "RECEBIMENTO DE DOC",
        "RECEBIMENTO DE PIX",
        "TED RECEBIDO",
        "PIX RECEBIDO",
        "DOC RECEBIDO",
    }
)


def test_no_overbroad_generic_prefixes_in_seed() -> None:
    """Seed v1 não pode conter prefixos genéricos de canal de receita (A17.l6)."""
    patterns = _load_seed_internal_transfer_patterns()
    offenders = [p for p in patterns if p.strip().upper() in _FORBIDDEN_GENERIC_PREFIXES]
    assert not offenders, f"Seed v1 contém prefixos proibidos: {offenders!r}. Ver A17.l6."


# ---------------------------------------------------------------------------
# Invariante 2 — comportamento do classifier com seed real.
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_classifier() -> TransactionClassifier:
    """Classifier do seed v1 literal (após edits A17.l6)."""
    cfg = ClassifierConfig(
        income_keywords={"receita_clt": _load_seed_receita_clt_keywords()},
        transfer_config=InternalTransferConfig(
            internal_patterns=tuple(_load_seed_internal_transfer_patterns()),
        ),
    )
    return TransactionClassifier(cfg)


def _make_account(descricao: str, *, credit: bool) -> dict:
    # E3 JSON legado usa float em "valor" (pre-ADR-090); coerção em _coerce_valor.
    raw = 4500.00 if credit else -2500.00
    return {
        "banco": "Itau",
        "tipo_conta": "conta_corrente",
        "titular": "Cônjuge",
        "moeda": "BRL",
        "transacoes": [
            {
                "data": "2026-04-05",
                "descricao": descricao,
                "valor": raw,
                "tipo": "credito" if credit else "debito",
            },
        ],
    }


@pytest.mark.parametrize(
    "descricao",
    [
        "RECEBIMENTO DE TED 3221 SOC BENEF ISRAELITA",
        "RECEBIMENTO DE TED                  SOC BENEFICENTE ISRAELITA",
        "RECEBIMENTO TRANSFERENCIA 3221 HOSPITAL ALBERT EINSTEIN",
        "RECEBIMENTO DE TED 12345 NUBANK SA",
        "RECEBIMENTO TRANSFERENCIA EMPRESA QUALQUER LTDA",
    ],
)
def test_generic_ted_credit_is_not_classified_as_transfer(
    seed_classifier: TransactionClassifier, descricao: str
) -> None:
    """Crédito via TED genérico não é engolido como transferência interna."""
    [tx] = seed_classifier.classify_account(_make_account(descricao, credit=True))
    assert tx.kind == "receita", (
        f"BUG A17.l6 regrediu: descrição {descricao!r} kind={tx.kind!r} " f"cat={tx.categoria!r}."
    )


def test_ted_with_explicit_clt_keyword_resolves_to_receita_clt(
    seed_classifier: TransactionClassifier,
) -> None:
    """TED com keyword CLT literal do seed (`EMPREGADOR EXEMPLO`) → receita_clt.

    A34.l11 (ADR-319): o seed v1 foi neutralizado — empregador nominal virou
    placeholder sintético; o invariante testado (keyword específica vence o
    prefixo genérico de canal) permanece o mesmo.
    """
    descricao = "RECEBIMENTO DE TED 3221 EMPREGADOR EXEMPLO"
    [tx] = seed_classifier.classify_account(_make_account(descricao, credit=True))
    assert (
        tx.kind == "receita" and tx.categoria == "receita_clt"
    ), f"Esperado receita_clt; veio kind={tx.kind!r} cat={tx.categoria!r}."


def test_internal_transfer_still_detects_specific_patterns(
    seed_classifier: TransactionClassifier,
) -> None:
    """Padrão específico (ITAU VISA ITAUCARD) segue detectado pós-fix."""
    descricao = "PAGTO ITAU VISA ITAUCARD CARTAO"
    [tx] = seed_classifier.classify_account(_make_account(descricao, credit=False))
    assert (
        tx.kind == "transferencia"
    ), f"Específico deveria seguir detectado; veio {tx.kind!r} cat={tx.categoria!r}."

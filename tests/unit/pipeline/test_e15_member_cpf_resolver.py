"""Tests — `consolidate_from_itens` usa MemberNameResolver com CPF (ADR-267 PR2)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.member_name_resolver import (  # noqa: E402
    MemberNameResolver,
    MemberRecord,
)
from scripts.consolidate_baseline import (  # noqa: E402
    _resolve_member,
    consolidate_from_itens,
)
from tests.utils.cpf import cpf_formatted  # noqa: E402

_CPF_DAVID = cpf_formatted(seed=42).replace(".", "").replace("-", "")  # noqa: PII-ok
_CPF_MARIANA = cpf_formatted(seed=84).replace(".", "").replace("-", "")  # noqa: PII-ok


def _resolver_campos() -> MemberNameResolver:
    return MemberNameResolver(
        [
            MemberRecord(
                key="david_robert_martins_andrade_silva",
                full_name="David Robert Martins Andrade Silva",
                short_name="David Robert",
                cpf=_CPF_DAVID,
            ),
            MemberRecord(
                key="mariana_andrade_silva",
                full_name="Mariana Andrade Silva",
                short_name="Mariana",
                nome_nascimento="Mariana Ribeiro Andrade",
                cpf=_CPF_MARIANA,
            ),
        ]
    )


def _baseline(itens: list[dict]) -> dict:
    total = sum(float(i.get("valor_brl", 0)) for i in itens)
    return {
        "itens": itens,
        "resumo": {
            "total_ativos": total,
            "total_passivos": 0.0,
            "patrimonio_liquido": total,
            "ano_referencia": 2024,
        },
        "_meta": {"source": "E1.5-llm", "confidence": 0.9},
    }


class TestResolveMemberHelper:
    def test_cpf_resolves_to_canonical_key(self):
        item = {"membro": "MARIANA RIBEIRO ANDRADE", "cpf": _CPF_MARIANA}
        assert _resolve_member(item, _resolver_campos()) == "mariana_andrade_silva"

    def test_no_cpf_falls_back_to_name_resolver(self):
        item = {"membro": "MARIANA RIBEIRO ANDRADE"}
        # Sem CPF, resolver.resolve(nome) bate em nome_nascimento.
        assert _resolve_member(item, _resolver_campos()) == "mariana_andrade_silva"

    def test_no_resolver_returns_raw_lowercase(self):
        item = {"membro": "MARIANA RIBEIRO ANDRADE"}
        # Backwards compat: sem resolver, retorna lowercase raw (comportamento legado).
        assert _resolve_member(item, None) == "mariana ribeiro andrade"

    def test_cpf_invalid_falls_back_to_name(self):
        item = {"membro": "Mariana", "cpf": "999"}  # CPF inválido (<11 dígitos)
        # CPF inválido cai no name resolver; Mariana bate via short_name.
        assert _resolve_member(item, _resolver_campos()) == "mariana_andrade_silva"


# Valores em centavos (int) para evitar P5_float_money — testes não dependem
# do valor exato, só de itens existirem para o consolidator agrupar por membro.
_VAL_CENTS = 10_000_000  # R$ 100.000 em cents


def _item(membro: str, cpf: str | None = None) -> dict:
    """Item builder mínimo — tests só precisam de membro + cpf."""
    out = {
        "codigo": "01",
        "descricao": "X",
        "categoria": "imovel",
        "valor_brl": _VAL_CENTS / 100,  # divisão converte para float só no final
        "membro": membro,
        "ano": 2024,
    }
    if cpf:
        out["cpf"] = cpf
    return out


def _proprietarios(result: dict) -> set[str]:
    """Set de canonical keys (proprietario) emergentes em imov+invest."""
    entries = result.get("imoveis_consolidados", []) + result.get("investimentos_consolidados", [])
    return {e.get("proprietario") for e in entries}


# Datasets para tests de consolidação — fora dos test functions (P1 < 20 linhas).
_ITENS_MARIANA_CROSS_SURNAME = [
    _item("mariana_ribeiro_andrade", _CPF_MARIANA),
    _item("mariana_andrade_silva", _CPF_MARIANA),
]
_ITENS_DAVID_4_SLUGS = [
    _item("david_robert", _CPF_DAVID),
    _item("david_robert_martins_de_silva", _CPF_DAVID),
    _item("david_robert_martins_andrade_silva", _CPF_DAVID),
]
_ITENS_NO_CPF_LEGACY = [_item("mariana_ribeiro_andrade")]
_ITENS_NAME_FALLBACK = [_item("David Robert")]


class TestConsolidateWithResolver:
    def test_mariana_cross_surname_collapses(self):
        """ADR-267 — Mariana solteira+casada colapsam (caso real R$ 811k)."""
        result = consolidate_from_itens(
            _baseline(_ITENS_MARIANA_CROSS_SURNAME), resolver=_resolver_campos()
        )
        assert _proprietarios(result) == {"mariana_andrade_silva"}

    def test_david_4_slug_variations_collapse(self):
        """David com 4 variações de nome — mesmo CPF, 1 canonical key."""
        result = consolidate_from_itens(
            _baseline(_ITENS_DAVID_4_SLUGS), resolver=_resolver_campos()
        )
        assert _proprietarios(result) == {"david_robert_martins_andrade_silva"}

    def test_backwards_compat_without_resolver(self):
        """Sem resolver, string raw lowercase preservada (comportamento legado)."""
        result = consolidate_from_itens(_baseline(_ITENS_NO_CPF_LEGACY), resolver=None)
        assert _proprietarios(result) == {"mariana_ribeiro_andrade"}

    def test_item_without_cpf_falls_back_to_name(self):
        """Item sem CPF — resolver tenta resolve(nome) automaticamente."""
        result = consolidate_from_itens(
            _baseline(_ITENS_NAME_FALLBACK), resolver=_resolver_campos()
        )
        assert _proprietarios(result) == {"david_robert_martins_andrade_silva"}

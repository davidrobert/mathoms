"""Unit tests A17 L3 P5 — narrate_wise_fiscal_flags (tributario_narrator)."""

from __future__ import annotations

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.tributario_narrator import (
    narrate_wise_fiscal_flags,
)


def _ctx(titular: str = "Maria") -> NarrativasContext:
    return NarrativasContext.from_family_config(
        {
            "titular": "t",
            "membros": {
                "t": {"papel": "titular", "nome_curto": titular},
                "c": {"papel": "conjuge", "nome_curto": "João"},
            },
        }
    )


def _flag(**overrides) -> dict:
    base = {
        "code": "CBE",
        "severity": "info",
        "title": "Capital Brasileiro no Exterior (CBE BACEN)",
        "descricao": "Total de ativos no exterior: USD 1.100.000,00.",
        "codigo_rfb": "",
        "moeda": "USD",
        "metadata": {},
    }
    base.update(overrides)
    return base


def test_narrate_wise_flags_lista_vazia_retorna_estrutura_vazia():
    out = narrate_wise_fiscal_flags([], _ctx())
    assert out == {"context": "", "conclusion": "", "items": [], "pontos_revisao": 0}


def test_narrate_wise_flags_agrega_pontos_revisao():
    """Anti-fadiga (A33.l2 P5.7): needs_review agregados num bloco único."""
    flags = [
        _flag(code="RFB41_ME", needs_review=True),
        _flag(code="GCAP_ISENTO", needs_review=True),
        _flag(code="CBE", needs_review=False),
    ]
    out = narrate_wise_fiscal_flags(flags, _ctx())
    assert out["pontos_revisao"] == 2
    assert "2 pontos a revisar com contador" in out["conclusion"]
    assert [i["needs_review"] for i in out["items"]] == [True, True, False]


def test_narrate_wise_flags_um_ponto_singular():
    out = narrate_wise_fiscal_flags([_flag(needs_review=True)], _ctx())
    assert "1 ponto a revisar com contador" in out["conclusion"]


def test_narrate_wise_flags_none_retorna_estrutura_vazia():
    out = narrate_wise_fiscal_flags(None, _ctx())
    assert out["items"] == []


def test_narrate_wise_flags_uma_flag_cbe():
    out = narrate_wise_fiscal_flags([_flag()], _ctx(titular="Maria"))
    assert len(out["items"]) == 1
    assert out["items"][0]["code"] == "CBE"
    assert "Maria" in out["context"]
    assert "Capital Brasileiro no Exterior" in out["context"]
    assert "contador" in out["conclusion"]


def test_narrate_wise_flags_tres_codigos_listados_no_summary():
    flags = [
        _flag(code="CBE"),
        _flag(code="CARNELEAO", title="Carnê-leão"),
        _flag(code="GCAP", title="GCAP cambial"),
    ]
    out = narrate_wise_fiscal_flags(flags, _ctx())
    assert "Capital Brasileiro no Exterior" in out["context"]
    assert "Carnê-leão" in out["context"]
    assert "GCAP" in out["context"]
    assert len(out["items"]) == 3

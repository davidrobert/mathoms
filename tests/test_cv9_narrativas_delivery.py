"""CV9 — os quatro predicados de ENTREGA de narrativa de seção (A40.l4 · ADR-355 §D6)."""

from __future__ import annotations

# O CV9 antigo media GERAÇÃO (presença + não-vazio de s1..s10), o que
# `validate_narrativas` já hard-falhava a montante: era verde por construção
# enquanto o nome e o `entregues=N/esperadas=M` prometiam render.
#
# Denominador aqui = entradas do layout que enabled + summary: true +
# summary_source, ou seja, as que de fato montam <SectionSummary>. A
# correspondência `summary: true` ⟺ <SectionSummary sectionId="…"> é enforçada
# em PR pela regra 6 de `dev/check_chart_conclusion_parity.py` — é essa premissa
# que faz o "entregues" ser sobre entrega e não sobre o join.
#
# O caso `sem_render` é o gerado-mas-não-entregue: destino mapeado numa seção
# que não exibe parágrafo. Antes ficava verde nas duas pernas.
from typing import Any

import pytest

import scripts.validate_cross as vc

_SUMMARIES_OK = {f"s{i}": f"texto do s{i}." for i in range(1, 11)}


def _layout(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {"estrategico": {"sections": entries, "appendices": []}}


def _section(sid: str, source: str | None, *, summary: bool = True, enabled: bool = True) -> dict:
    return {"id": sid, "enabled": enabled, "summary": summary, "summary_source": source}


# Cenário saudável: todo `sN` emitido tem destino OU está em
# ORPHAN_SUMMARY_KEYS (s2/s5/s6) — senão o predicado `orfas` dispara.
_DESTINOS_SAOS = [
    _section("S2", None),
    *(_section(f"S{i}", f"s{i}") for i in (1, 3, 4, 7, 8, 9, 10)),
]


@pytest.fixture
def pinned_layout(monkeypatch: pytest.MonkeyPatch):
    """Substitui o layout lido pelo CV9 — o teste declara o cenário."""

    def _pin(entries: list[dict[str, Any]]) -> None:
        monkeypatch.setattr(vc, "_REPORT_LAYOUT", _layout(entries))

    return _pin


def _run(summaries: dict[str, Any]) -> vc.CrossValidationResult:
    return vc._cv9_summaries_delivery({"narrativas": {"summaries": summaries}})


def test_layout_saudavel_passa_com_contagem_honesta(pinned_layout) -> None:
    pinned_layout(_DESTINOS_SAOS)
    res = _run({**_SUMMARIES_OK, "s2": "score", "s5": "viagens", "s6": "cambial"})
    assert res.passed, res.details
    assert "entregues=7/esperadas=7" in res.details


def test_destino_em_secao_que_nao_renderiza_falha(pinned_layout) -> None:
    """`summary: false` + `summary_source` = texto gerado, mapeado e invisível."""
    pinned_layout([*_DESTINOS_SAOS[:-1], _section("S10", "s10", summary=False)])
    res = _run(_SUMMARIES_OK)
    assert not res.passed, res.details
    assert res.severity == "error"
    assert "sem_render=['S10->s10']" in res.details


def test_destino_em_secao_desabilitada_falha(pinned_layout) -> None:
    pinned_layout([*_DESTINOS_SAOS[:-2], _section("S_PROTECAO", "s9", enabled=False)])
    res = _run(_SUMMARIES_OK)
    assert not res.passed
    assert "S_PROTECAO->s9" in res.details


def test_destino_sem_chave_no_produtor_falha(pinned_layout) -> None:
    """Layout aponta `s11` (ou produtor renomeia) ⇒ parágrafo vazio em silêncio."""
    pinned_layout([*_DESTINOS_SAOS, _section("S_NOVA", "s11")])
    res = _run(_SUMMARIES_OK)
    assert not res.passed
    assert "sem_texto=['s11']" in res.details
    assert "entregues=7/esperadas=8" in res.details


def test_shape_de_chart_sob_summaries_falha(pinned_layout) -> None:
    """`{context, conclusion}` passa por `validate_narrativas` e cai no derivado."""
    pinned_layout(_DESTINOS_SAOS)
    res = _run({**_SUMMARIES_OK, "s1": {"context": "c", "conclusion": "x"}})
    assert not res.passed
    assert "shape_invalido=['s1']" in res.details


def test_chave_nova_sem_destino_nem_allowlist_falha(pinned_layout) -> None:
    pinned_layout(_DESTINOS_SAOS)
    res = _run({**_SUMMARIES_OK, "s11": "chave nova sem destino"})
    assert not res.passed
    assert "s11" in res.details


def test_layout_real_do_repo_entrega_todos_os_destinos() -> None:
    """Sanidade sobre o layout versionado — não sobre um cenário sintético."""
    res = _run(_SUMMARIES_OK)
    assert res.passed, res.details
    assert "entregues=7/esperadas=7" in res.details

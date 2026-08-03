"""CV9 — os quatro predicados de ENTREGA de narrativa de seção (A40.l4 · ADR-356 §D6)."""

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


def _section(
    sid: str,
    source: str | None,
    *,
    summary: bool = True,
    enabled: bool = True,
    suppressed_by: str | None = None,
) -> dict:
    return {
        "id": sid,
        "enabled": enabled,
        "summary": summary,
        "summary_source": source,
        "summary_suppressed_by": suppressed_by,
    }


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


def _run(
    summaries: dict[str, Any], charts: dict[str, Any] | None = None
) -> vc.CrossValidationResult:
    narrativas: dict[str, Any] = {"summaries": summaries}
    if charts is not None:
        narrativas["charts"] = charts
    return vc._cv9_summaries_delivery({"narrativas": narrativas})


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
    assert "entregues=6/esperadas=6" in res.details


# ── Supressão condicional (o furo que a 1ª versão do CV9 deixava verde) ──
#
# O 4º predicado lia só flags ESTÁTICAS do layout: seção com `summary: true` e
# `<SectionSummary>` presente passava, mesmo quando o render curto-circuitava por
# `data_state`. Medido: workspace sem risco cadastrado renderiza 6 de 7 e o CV9
# dizia 7/7.

_RISCOS_VAZIO = {"bubble_riscos": {"data_state": "empty"}}
_RISCOS_OK = {"bubble_riscos": {"data_state": "ok"}}


def test_secao_em_empty_state_nao_conta_o_destino_como_entregue(pinned_layout) -> None:
    """Workspace sem riscos: o `s9` é gerado e a S9 o engole ⇒ 6/7, não 7/7."""
    pinned_layout(
        [
            *(e for e in _DESTINOS_SAOS if e["id"] != "S9"),
            _section("S9", "s9", suppressed_by="bubble_riscos"),
        ]
    )
    res = _run(_SUMMARIES_OK, charts=_RISCOS_VAZIO)
    assert "entregues=6/esperadas=7" in res.details, res.details
    assert "suprimido=['S9->s9']" in res.details, res.details
    # Supressão é a decisão de produto da §D7, não defeito: reprovar deixaria o
    # CV9 vermelho em todo workspace sem risco — vermelho decorativo.
    assert res.passed, res.details


def test_secao_com_dados_conta_o_destino_normalmente(pinned_layout) -> None:
    """A supressão é condicional ao run, não ao layout."""
    pinned_layout(
        [
            *(e for e in _DESTINOS_SAOS if e["id"] != "S9"),
            _section("S9", "s9", suppressed_by="bubble_riscos"),
        ]
    )
    res = _run(_SUMMARIES_OK, charts=_RISCOS_OK)
    assert "entregues=7/esperadas=7" in res.details, res.details
    assert "suprimido=nenhuma" in res.details, res.details


def test_layout_real_sem_riscos_reporta_5_de_6() -> None:
    """Prova sobre o layout VERSIONADO, não sintético: workspace sem risco
    cadastrado (`bubble_riscos.data_state == "empty"`) põe o `s9` fora da
    entrega. É o caso vivo — a 1ª versão do CV9 dizia 7/7 aqui."""
    res = _run(_SUMMARIES_OK, charts=_RISCOS_VAZIO)
    assert "entregues=5/esperadas=6" in res.details, res.details
    assert "suprimido=['S9->s9']" in res.details, res.details


def test_gate_nao_declarado_nao_suprime(pinned_layout) -> None:
    """Sem `summary_suppressed_by`, `data_state: empty` não desconta nada — é a
    regra 7 do gate estático que impede a declaração de faltar."""
    pinned_layout(_DESTINOS_SAOS)
    res = _run(_SUMMARIES_OK, charts=_RISCOS_VAZIO)
    assert "entregues=7/esperadas=7" in res.details, res.details

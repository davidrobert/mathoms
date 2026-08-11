"""Emenda ADR-356 (2026-08-11) — o `perfil_familia` é prosa sobre pessoas."""

# Gates de CLASSE: a regra é "este narrador não publica valor monetário nem
# juízo qualitativo", não "a frase X saiu". Gate por instância deixaria a
# re-introdução por outra redação passar verde.

from __future__ import annotations

from datetime import date
from typing import Any

from pipeline.domain.services.narrativas import NarrativasContext, PerfilFamiliaNarrator
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics

_TODAY = date(2026, 4, 20)


def _left(today: date = _TODAY) -> str:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    return PerfilFamiliaNarrator(ctx).narrate(_build_metrics(), _FAMILY_BASE, today=today)["left"]


def test_perfil_nao_publica_valor_monetario_nem_percentual():
    """Qualquer `R$`/`%` novo no perfil quebra aqui — sem depender do literal."""
    left = _left()
    assert "R$" not in left, left
    assert "%" not in left, left


def test_perfil_nao_emite_juizo_qualitativo():
    """Os três adjetivos incondicionais que a coluna `right` carregava."""
    left = _left().lower()
    for veredito in ("saudável", "base sólida", "diversificada"):
        assert veredito not in left, veredito


# `today` não é decorativo: se alguém trocar o parâmetro por `date.today()`
# dentro do narrador, os dois `left` viram iguais e este teste fica vermelho.
def test_perfil_honra_o_today_injetado():
    """Idade impressa é a do período do relatório, não a de hoje."""
    assert _left(date(2026, 4, 20)) != _left(date(2031, 4, 20))


def test_today_de_data_analise_nao_inventa_default():
    """Ausência/lixo devolve `None` — o chamador decide, sem default silencioso."""
    import scripts.generate_narratives as gn

    assert gn._today_from_data_analise({"data_analise": "2026-04-20"}) == _TODAY
    assert gn._today_from_data_analise({"data_analise": "2026-04-20T12:00:00"}) == _TODAY
    assert gn._today_from_data_analise({}) is None
    assert gn._today_from_data_analise({"data_analise": "nao-e-data"}) is None


# Gate de CALL SITE: o narrador honrar `today` não prova que alguém o injeta.
# Sem isto, remover `today=` do stage passa verde e a idade volta a depender de
# quando o pipeline rodou (classe do "gate de call-site não protege o default").
def test_call_site_do_stage_injeta_o_today(monkeypatch):
    """`_e5n_build_and_validate` deriva `today` do `data_analise` do E5."""
    import scripts.generate_narratives as gn

    recebido: dict[str, Any] = {}

    def _spy(*, today=None):
        recebido["today"] = today
        return {"perfil_familia": {"left": "<p>x</p>"}, "summaries": {}, "charts": {}}

    monkeypatch.setattr(gn, "build_narrativas", _spy)
    gn._e5n_build_and_validate({"data_analise": "2026-04-20T12:00:00"})
    assert recebido["today"] == _TODAY

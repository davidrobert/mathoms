"""Marcador de base de comparação alterada ([[A40.l2]] §3c2b · eixo 10 do §Critério de saída).

`_base_de_comparacao_mudou` é DIFERENÇA entre as pontas do par, não presença no lado atual.
A distinção só aparece no rollback: lá o lado atual **não** tem o bloco, e um gatilho por
presença leria `False` — a V0 voltaria a julgar exatamente quando o método mudou de volta.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.application.report.get_report_data import _base_de_comparacao_mudou
from pipeline.domain.types.snapshot_changelog import AnalyzeFinancesSnapshot

_CONSOLIDADO = {"fluxo_caixa": {"consolidacao_cross_documento": {"linhas_unificadas": 261}}}
_SEM_CONSOLIDACAO = {"fluxo_caixa": {"total_receitas": 1000}}


def _snap(content: dict) -> AnalyzeFinancesSnapshot:
    return AnalyzeFinancesSnapshot(
        workspace_id="ws",
        period_yyyymm="202604",
        analysis_hash="h",
        content_json=content,
        created_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    ("prev", "curr", "esperado"),
    [
        (_SEM_CONSOLIDACAO, _CONSOLIDADO, True),
        (_CONSOLIDADO, _SEM_CONSOLIDACAO, True),
        (_CONSOLIDADO, _CONSOLIDADO, False),
        (_SEM_CONSOLIDACAO, _SEM_CONSOLIDACAO, False),
    ],
    ids=["flip", "rollback", "ambos_consolidados", "ambos_sem"],
)
def test_marcador_e_diferenca_entre_as_pontas__nao_presenca(prev, curr, esperado):
    """Mutação: trocar `!=` por `_consolidou(curr)`. O caso `rollback` fica vermelho."""
    assert _base_de_comparacao_mudou(_snap(prev), _snap(curr)) is esperado


def test_bloco_vazio_conta_como_ausencia():
    """`{}` é o E5 que rodou a consolidação e não achou par — mesmo método do lado sem bloco.
    Tratá-lo como presente acenderia o marcador em todo run de workspace sem sobreposição."""
    assert (
        _base_de_comparacao_mudou(
            _snap({"fluxo_caixa": {"consolidacao_cross_documento": {}}}), _snap(_SEM_CONSOLIDACAO)
        )
        is False
    )


# Quem impede a legenda no relatório inaugural NÃO é esta função — é o early-return de
# `_build_snapshot_diff` em `not has_previous`, que devolve `False` sem chegar a consultar.
# Registrado porque a leitura ingênua ("sem prev ⇒ não mudou") convidaria a mover a guarda
# para cá, e aí o rollback — que também compara contra um lado sem o bloco — sairia junto.
def test_sozinha_a_funcao_trata_ausencia_de_prev_como_metodo_diferente():
    assert _base_de_comparacao_mudou(None, _snap(_CONSOLIDADO)) is True
    assert _base_de_comparacao_mudou(None, _snap(_SEM_CONSOLIDACAO)) is False

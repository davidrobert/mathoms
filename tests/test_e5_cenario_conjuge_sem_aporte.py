"""Golden de execução: casal sem meta de aporte publica ausência no E5, nunca 0 (ADR-373).

Casal com `papel: conjuge` e meta de IF é elegível com ou sem o gate da ADR-167
ligado, então este caso segue exercitando o caminho do `null` quando as fixtures
de solteiro passarem a sair `{}`.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.domain.services.narrativas.format_helpers import CENARIO_CONJUGE_SEM_APORTE
from tests.test_e5_golden_execution import _E3_FIXTURE, _new_e5_ctx, _write_e5_config

_FAMILY_CASAL = {
    "titular": "david",
    "membros": {
        "david": {"nome_curto": "David", "data_nascimento": "1985-06-15", "papel": "titular"},
        "ana": {"nome_curto": "Ana", "data_nascimento": "1987-03-02", "papel": "conjuge"},
    },
}


def _e5_do_casal_sem_aporte(tmp_path: Path) -> dict:
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    _write_e5_config(tmp_path)
    (tmp_path / "config" / "family_members.json").write_text(
        json.dumps(_FAMILY_CASAL, ensure_ascii=False), encoding="utf-8"
    )
    ctx = _new_e5_ctx(tmp_path, e3_fixture=_E3_FIXTURE)
    e4_mws(ctx)
    e5_mws(ctx)
    return ctx.artifact_store.read("E5", "analise_financeira")


def test_casal_sem_aporte_publica_ausencia_validada_pelo_schema(tmp_path: Path):
    from scripts.pipeline_common import validate_dict

    payload = _e5_do_casal_sem_aporte(tmp_path)
    cenarios = payload["cenarios_conjuge"]

    assert validate_dict(payload, "e5_analysis.schema.json") is True
    assert cenarios["labels"] == ["Sem renda do cônjuge"]
    assert cenarios["aportes"] == [None]
    assert cenarios["premissas"]["aporte_base"] is None
    assert cenarios["cenarios"][0]["aporte_mensal"] is None
    assert cenarios["cenarios"][0]["resumo"] == CENARIO_CONJUGE_SEM_APORTE

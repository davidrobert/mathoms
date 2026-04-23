"""Regressão: artifact key de E1.5 precisa casar com o nome esperado por
``document_pipeline_sync._e15a_json_name`` — caso contrário, IRPF aparece
como "Sem extrato" na UI mesmo após processamento.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.stages.e15 import _artifact_key_for


def test_artifact_key_strips_zero_original_suffix() -> None:
    p = Path("/ws/data/income_tax_br/receitafederal_irpfdeclaracao_2024-0_original.pdf")
    assert _artifact_key_for(p) == "receitafederal_irpfdeclaracao_2024"


def test_artifact_key_casa_nome_esperado_pelo_sync() -> None:
    from backend.app.services.document_pipeline_sync import _e15a_json_name

    stored = "receitafederal_irpfdeclaracao_2024-0_original.pdf"
    key = _artifact_key_for(Path("/ws/data/income_tax_br") / stored)
    assert f"{key}-1.5a_extract.json" == _e15a_json_name(stored)


def test_artifact_key_sem_zero_original() -> None:
    p = Path("/ws/data/income_tax_br/foo.pdf")
    assert _artifact_key_for(p) == "foo"


def test_artifact_key_extensao_desconhecida() -> None:
    p = Path("/ws/data/income_tax_br/something.weird")
    assert _artifact_key_for(p) == "something"

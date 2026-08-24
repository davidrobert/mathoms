"""Gate do flip warn→strict: o instrumento mede pela chave do gate e não chama GO sem massa (ADR-284 · A40.l58)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from dev.measure_schema_drift import SchemaDrift, _measure, _window_start

SCHEMA_OF = {"E2": "e2_extract.schema.json"}


def _row(payload: dict, *, run: str = "run-1", key: str = "art-1", created: str = "2026-08-18"):
    return SimpleNamespace(
        stage="E2",
        content_json=json.dumps(payload),
        created_at=created,
        pipeline_run_id=run,
        document_id=None,
        artifact_key=key,
    )


def _e2_payload(**overrides) -> dict:
    """Shape mínimo que o `e2_extract.schema.json` aceita; `overrides` remove/força campo."""
    payload = {"banco": "itau", "tipo": "extrato", "moeda": "BRL", "transacoes": []}
    payload.update(overrides)
    for field, value in list(overrides.items()):
        if value is None:
            payload.pop(field, None)
    return payload


class TestVeredito:
    def test_schema_sem_massa_nao_e_go(self):
        """Zero artefato não é 'zero WARN' — é ausência de medição (a janela de 7d pode não ter run)."""
        assert SchemaDrift().is_go is False

    def test_massa_sem_drift_e_go(self):
        stats = SchemaDrift()
        stats.artifacts = 5
        assert stats.is_go is True

    def test_um_drift_derruba_o_go(self):
        stats = SchemaDrift()
        stats.artifacts, stats.drifted = 5, 1
        assert stats.is_go is False


class TestJanela:
    def test_since_explicito_vence_days(self):
        assert _window_start(7, "2026-01-01", "2026-08-18") == "2026-01-01"

    def test_days_conta_do_write_mais_recente_e_inclui_o_dia(self):
        assert _window_start(7, None, "2026-08-18") == "2026-08-12"

    def test_sem_corpus_nao_ha_janela(self):
        assert _window_start(7, None, None) is None


class TestMedicao:
    def test_payload_valido_nao_drifta(self):
        results = _measure([_row(_e2_payload())], SCHEMA_OF)
        assert results["e2_extract.schema.json"].is_go is True

    @pytest.mark.parametrize("faltante", ["banco", "moeda"])
    def test_path_emitido_e_o_mesmo_da_telemetria(self, faltante: str):
        """Regressão do drift real medido em 2026-08-24: o stub de `generate_llm_fallback`
        entra sem `banco`/`moeda`. O path tem de ser o campo, não a raiz `$` — é a chave
        que o go/no-go do runbook agrega."""
        results = _measure([_row(_e2_payload(**{faltante: None}))], SCHEMA_OF)
        stats = results["e2_extract.schema.json"]
        assert stats.drifted == 1
        assert (f"$.{faltante}", "required") in stats.paths

    def test_conta_run_e_documento_distintos(self):
        """`docs` separa massa real de repetição por run — 6 artefatos de 1 documento não são 6 evidências."""
        rows = [_row(_e2_payload(), run=f"run-{i}", key="mesmo-doc") for i in range(3)]
        stats = _measure(rows, SCHEMA_OF)["e2_extract.schema.json"]
        assert (stats.artifacts, len(stats.runs), len(stats.documents)) == (3, 3, 1)

    def test_payload_ilegivel_conta_separado_e_nao_vira_drift(self):
        row = _row(_e2_payload())
        row.content_json = "{nao é json"
        stats = _measure([row], SCHEMA_OF)["e2_extract.schema.json"]
        assert (stats.unreadable, stats.drifted) == (1, 0)
        assert stats.is_go is False

    def test_stage_sem_schema_mapeado_e_ignorado(self):
        """Passthrough (E6-parecer, extract_members) não entra na conta — não há contrato a medir."""
        row = _row(_e2_payload())
        row.stage = "review_finances_holistic"
        assert _measure([row], SCHEMA_OF) == {}

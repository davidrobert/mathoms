"""ADR-284 — telemetria de drift de schema + mode_overrides per-schema."""

import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.pipeline_common as pc
from scripts.pipeline_common import validate_dict
from scripts.schema_drift_telemetry import _TELEMETRY_MAX_PATHS

_TELEMETRY_LOGGER = "mathoms.pipeline.schema_validation"

_E2_BASE = {
    "pipeline_stage": "E2",
    "banco": "c6bank",
    "tipo": "faturaunique",
    "moeda": "BRL",
}


def _drift_records(caplog):
    return [
        r
        for r in caplog.records
        if r.name == _TELEMETRY_LOGGER and r.getMessage() == "schema_validation_drift"
    ]


def _e2_with_transacoes(transacoes):
    return {**_E2_BASE, "transacoes": transacoes}


def _validate_e2(data, **kwargs):
    return validate_dict(data, "e2_extract.schema.json", source="E2/x", **kwargs)


def _patch_overrides(monkeypatch, overrides):
    monkeypatch.setitem(
        pc._config_cache,
        "pipeline.json",
        {"schema_validation": {"enabled": True, "mode": "warn", "mode_overrides": overrides}},
    )


class TestSchemaValidationTelemetry:
    def test_dedup_por_path_normalizado_com_occurrence_count(self, caplog, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        caplog.set_level(logging.WARNING)
        tx = {"data": "2026-01-15", "descricao": "PIX", "valor": -1.0, "campo_fantasma": "x"}
        data = _e2_with_transacoes([dict(tx), dict(tx), dict(tx)])
        context = {"workspace_id": "ws-1", "stage": "E2", "artifact_key": "itau_x"}
        assert _validate_e2(data, context=context) is True
        drift = _drift_records(caplog)
        assert len(drift) == 1
        self._assert_record(drift[0])

    @staticmethod
    def _assert_record(rec):
        assert rec.validation_path == "$.transacoes[].campo_fantasma"
        assert rec.validator_keyword == "additionalProperties"
        assert rec.occurrence_count == 3
        assert rec.workspace_id == "ws-1"
        assert rec.stage == "E2"
        assert rec.artifact_key == "itau_x"
        assert rec.schema_name == "e2_extract.schema.json"
        assert rec.mode == "warn"
        assert rec.outcome == "warn"

    def test_telemetria_nunca_vaza_valor_da_instancia(self, caplog, monkeypatch):
        """error.message do jsonschema embute o valor ofensor — não pode chegar ao log."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        caplog.set_level(logging.WARNING)
        sentinel = "98765.43"
        data = _e2_with_transacoes([{"data": "2026-01-15", "descricao": "PIX", "valor": sentinel}])
        assert _validate_e2(data) is True
        assert sentinel not in caplog.text

    def test_required_expande_para_campo_faltante(self, caplog, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        caplog.set_level(logging.WARNING)
        data = {"pipeline_stage": "E2", "tipo": "extratoconta", "moeda": "BRL"}
        assert _validate_e2(data) is True
        assert "$.banco" in {r.validation_path for r in _drift_records(caplog)}

    def test_cap_de_paths_distintos_emite_record_de_truncamento(self, caplog, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        caplog.set_level(logging.WARNING)
        tx = {"data": "2026-01-15", "descricao": "PIX", "valor": -1.0}
        tx.update({f"campo_fantasma_{i:02d}": "x" for i in range(_TELEMETRY_MAX_PATHS + 5)})
        assert _validate_e2(_e2_with_transacoes([tx])) is True
        truncated = [
            r
            for r in caplog.records
            if r.name == _TELEMETRY_LOGGER and r.getMessage() == "schema_validation_drift_truncated"
        ]
        assert len(_drift_records(caplog)) == _TELEMETRY_MAX_PATHS
        assert len(truncated) == 1
        assert truncated[0].distinct_paths == _TELEMETRY_MAX_PATHS + 5


class TestModeOverridesPerSchema:
    _E2_INVALID = {"pipeline_stage": "E2", "tipo": "extratoconta", "moeda": "BRL"}

    def test_override_strict_per_schema_rejeita(self, monkeypatch):
        monkeypatch.delenv("MATHOMS_PIPELINE_SCHEMA_MODE", raising=False)
        _patch_overrides(monkeypatch, {"e2_extract.schema.json": "strict"})
        assert _validate_e2(self._E2_INVALID) is False

    def test_schema_sem_override_continua_warn(self, monkeypatch):
        monkeypatch.delenv("MATHOMS_PIPELINE_SCHEMA_MODE", raising=False)
        _patch_overrides(monkeypatch, {"e2_extract.schema.json": "strict"})
        assert validate_dict({}, "e5_analysis.schema.json", source="E5/x") is True

    def test_env_global_vence_override(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        _patch_overrides(monkeypatch, {"e2_extract.schema.json": "strict"})
        assert _validate_e2(self._E2_INVALID) is True

    def test_mode_overrides_do_repo_referenciam_schemas_existentes(self):
        """Gate de typo (ADR-284): key órfã em mode_overrides = falso senso de strict."""
        config_path = Path(__file__).resolve().parent.parent / "config"
        pipeline_cfg = json.loads((config_path / "pipeline.json").read_text())
        overrides = pipeline_cfg.get("schema_validation", {}).get("mode_overrides", {})
        existing = {p.name for p in (config_path / "schemas").glob("*.schema.json")}
        unknown = set(overrides) - existing
        assert not unknown, f"mode_overrides com schema(s) inexistente(s): {sorted(unknown)}"

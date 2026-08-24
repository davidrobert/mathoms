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


def _cfg_writer(path):
    """Devolve ``write(overrides)`` que grava um `pipeline.json` mínimo em ``path``."""

    def write(overrides):
        payload = {
            "schema_validation": {"enabled": True, "mode": "warn", "mode_overrides": overrides}
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    return write


class TestKillSwitchDeRollback:
    """A40.l58 + ADR-409 §C — o que faltava ao lado do `test_env_global_vence_override`: a metade *logar*, o blast radius global do lever de emergência, e por que o revert do §5 do runbook exige restart."""

    _E2_INVALID = {"pipeline_stage": "E2", "tipo": "extratoconta", "moeda": "BRL"}

    def test_rollback_por_env_volta_a_logar_E_passar(self, caplog, monkeypatch):
        """O critério tem duas metades. Um rollback que passasse **calado** seria
        indistinguível deste — e o operador perderia o sinal de drift justo quando
        precisa dele para decidir se re-promove."""
        caplog.set_level(logging.WARNING, logger=_TELEMETRY_LOGGER)
        _patch_overrides(monkeypatch, {"e2_extract.schema.json": "strict"})
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")

        assert _validate_e2(dict(self._E2_INVALID)) is True  # passar
        drift = _drift_records(caplog)
        assert drift, "rollback não pode silenciar a telemetria"  # logar
        assert {r.mode for r in drift} == {"warn"}
        assert {r.outcome for r in drift} == {"warn"}
        assert "$.banco" in {r.validation_path for r in drift}

    def test_lever_de_emergencia_despromove_TODOS_os_schemas(self, monkeypatch):
        """[[ADR-409]] §C: a env é global. Com 1 schema promovido os dois levers
        empatam; do 2º em diante, usar a env despromove tudo — e quem a usa precisa
        registrar no §7 do runbook quais schemas voltaram a `warn`."""
        _patch_overrides(
            monkeypatch,
            {"e2_extract.schema.json": "strict", "e5_analysis.schema.json": "strict"},
        )
        monkeypatch.delenv("MATHOMS_PIPELINE_SCHEMA_MODE", raising=False)
        assert _validate_e2(dict(self._E2_INVALID)) is False
        assert validate_dict({}, "e5_analysis.schema.json", source="E5/x") is False

        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        assert _validate_e2(dict(self._E2_INVALID)) is True
        assert validate_dict({}, "e5_analysis.schema.json", source="E5/x") is True

    def test_revert_no_disco_so_vale_apos_restart(self, tmp_path, monkeypatch):
        """Tripwire runbook §5 ↔ código: `load_json_config` cacheia, então o revert no disco só vale após restart — e se alguém implementar hot-reload, este teste cai junto com o "restart" do §5."""
        monkeypatch.delenv("MATHOMS_PIPELINE_SCHEMA_MODE", raising=False)
        monkeypatch.setattr(pc, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(pc, "_config_cache", {})
        write = _cfg_writer(tmp_path / "pipeline.json")

        write({"e2_extract.schema.json": "strict"})
        assert pc._effective_schema_validation_mode("e2_extract.schema.json") == "strict"

        write({})  # o revert de 1 linha do §5
        assert pc._effective_schema_validation_mode("e2_extract.schema.json") == "strict", (
            "revert no disco não pode valer sem restart — se passou a valer, "
            "atualize o §5 do runbook no mesmo PR"
        )

        pc._config_cache.clear()  # ≡ restart do worker
        assert pc._effective_schema_validation_mode("e2_extract.schema.json") == "warn"

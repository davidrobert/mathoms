"""Testes unitários dos mappers dos 3 blobs de config.

Cobrem:

- ``pipeline_blob_to_response``: valida dict via Pydantic + preserva
  campos tipados (llm, qa_thresholds) e livres (reconciliation,
  artifact_names, period_regex, log_files).
- ``institution_blob_to_response`` / ``report_layout_to_response``:
  wrappers opacos — ``config_json`` passa inalterado.
- ``deep_merge``: merge recursivo, listas substituem (não concatenam),
  override vence no leaf, base e override não mutam.

Mappers não recebem ``AsyncSession`` — puros.
"""

from __future__ import annotations

import copy

from backend.app.schemas.dto.config_blob.mapper import (
    deep_merge,
    institution_blob_to_response,
    pipeline_blob_to_response,
    report_layout_to_response,
)


class TestPipelineBlobToResponse:
    def test_empty_dict_valid(self):
        resp = pipeline_blob_to_response({})
        # Todos os campos são Optional — blob vazio é válido.
        assert resp.llm is None
        assert resp.file_limits is None
        assert resp.qa_thresholds is None
        assert resp.reconciliation is None

    def test_typed_sub_schemas_parsed(self):
        cfg = {
            "llm": {
                "model": "claude-opus-4.7",
                "max_tokens": 8000,
                "confidence_threshold": 0.85,
            },
            "qa_thresholds": {"score_diff_max": 0.3},
        }

        resp = pipeline_blob_to_response(cfg)

        assert resp.llm is not None
        assert resp.llm.model == "claude-opus-4.7"
        assert resp.llm.max_tokens == 8000
        assert resp.llm.confidence_threshold == 0.85
        # qa_thresholds é parcial — defaults preenchem o resto.
        assert resp.qa_thresholds is not None
        assert resp.qa_thresholds.score_diff_max == 0.3
        assert resp.qa_thresholds.cv_fluxo_diff_max == 100  # default

    def test_free_form_fields_passthrough(self):
        cfg = {
            "reconciliation": {"saldo_diff": 0.5, "custom_flag": True},
            "artifact_names": {"e3": "reconciled.json"},
            "log_files": {"e5": "qa_log.md"},
            "period_regex": {"c6bank": r"(\d{4})_(\d{4})"},
        }

        resp = pipeline_blob_to_response(cfg)

        assert resp.reconciliation == {"saldo_diff": 0.5, "custom_flag": True}
        assert resp.artifact_names == {"e3": "reconciled.json"}
        assert resp.log_files == {"e5": "qa_log.md"}
        assert resp.period_regex == {"c6bank": r"(\d{4})_(\d{4})"}

    def test_file_limits_validation_applies(self):
        cfg = {"file_limits": {"preview_max_chars": 5000}}
        resp = pipeline_blob_to_response(cfg)
        assert resp.file_limits is not None
        assert resp.file_limits.preview_max_chars == 5000
        assert resp.file_limits.preview_max_rows == 20  # default


class TestInstitutionBlobToResponse:
    def test_wraps_arbitrary_dict(self):
        cfg = {
            "c6bank": {
                "doc_type_patterns": {"extratoconta": "c6bank_extratoconta_"},
                "layouts": {"extratoconta": "csv_layout_a"},
            },
            "itau": {},
        }

        resp = institution_blob_to_response(cfg)

        # Wrapper opaco — config_json passa inalterado.
        assert resp.config_json == cfg

    def test_empty_dict_allowed(self):
        resp = institution_blob_to_response({})
        assert resp.config_json == {}


class TestReportLayoutToResponse:
    def test_wraps_yaml_shape(self):
        cfg = {
            "sections": [
                {"id": "cover", "enabled": True},
                {"id": "summary", "enabled": False},
            ],
            "charts": {"cashflow": {"type": "line"}},
        }

        resp = report_layout_to_response(cfg)

        assert resp.config_json == cfg

    def test_empty_dict_allowed(self):
        resp = report_layout_to_response({})
        assert resp.config_json == {}


class TestDeepMerge:
    def test_empty_override_preserves_base(self):
        base = {"a": 1, "b": {"c": 2}}
        merged = deep_merge(base, {})
        assert merged == base
        assert merged is not base  # cópia, não referência

    def test_empty_base_uses_override(self):
        assert deep_merge({}, {"x": 1}) == {"x": 1}

    def test_override_wins_at_leaf(self):
        assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_recursive_merge_on_nested_dict(self):
        base = {"llm": {"model": "old", "max_tokens": 500}}
        override = {"llm": {"model": "new"}}

        merged = deep_merge(base, override)

        # Campo sobrescrito + campo preservado.
        assert merged == {"llm": {"model": "new", "max_tokens": 500}}

    def test_three_level_nesting(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 99}}}

        merged = deep_merge(base, override)

        assert merged == {"a": {"b": {"c": 99, "d": 2}}}

    def test_type_conflict_override_wins(self):
        # Mesma chave, tipos diferentes: override vence (não tenta merge).
        base = {"k": {"nested": "dict"}}
        override = {"k": "string"}

        assert deep_merge(base, override) == {"k": "string"}

    def test_list_replaces_not_concatenates(self):
        # Listas NÃO são concatenadas (documentado na docstring).
        base = {"keywords": ["a", "b"]}
        override = {"keywords": ["c"]}

        assert deep_merge(base, override) == {"keywords": ["c"]}

    def test_does_not_mutate_inputs(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        base_snapshot = copy.deepcopy(base)
        override_snapshot = copy.deepcopy(override)

        deep_merge(base, override)

        assert base == base_snapshot
        assert override == override_snapshot

    def test_realistic_pipeline_partial_update(self):
        """Caso real: usuário só edita 1 campo do ``llm`` e espera que o
        resto do ``PipelineConfig`` fique intacto."""
        base = {
            "llm": {
                "model": "claude-sonnet-4",
                "max_tokens": 500,
                "confidence_threshold": 0.7,
            },
            "qa_thresholds": {"score_diff_max": 0.5},
            "file_limits": {"preview_max_chars": 2000},
        }
        override = {"llm": {"max_tokens": 8000}}

        merged = deep_merge(base, override)

        assert merged["llm"]["model"] == "claude-sonnet-4"
        assert merged["llm"]["max_tokens"] == 8000
        assert merged["llm"]["confidence_threshold"] == 0.7
        assert merged["qa_thresholds"] == {"score_diff_max": 0.5}
        assert merged["file_limits"] == {"preview_max_chars": 2000}

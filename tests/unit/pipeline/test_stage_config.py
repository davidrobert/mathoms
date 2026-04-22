"""Tests — ``pipeline.stage_config`` (Fase 1.5.5).

Cobre:
- Imutabilidade (pydantic frozen): tentativa de mutação levanta ``ValidationError``.
- ``from_context`` com WorkspaceContext via ``config_overrides``.
- ``ConfigError`` quando config obrigatório está ausente.
- ``empty()`` para testes de domínio.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.context import WorkspaceContext  # noqa: E402
from pipeline.stage_config import ConfigError, StageConfig  # noqa: E402

_MIN_OVERRIDES = {
    "family_members.json": {"titular": "x"},
    "pipeline.json": {"llm": {"model": "test"}},
    "institutions.json": {"banks": {}},
    "categorization.json": {"Alimentacao": ["MERCADO"]},
}


class TestFromContext:
    def test_loads_all_required_configs(self, tmp_path):
        ctx = WorkspaceContext(root=tmp_path, config_overrides=_MIN_OVERRIDES)
        cfg = StageConfig.from_context(ctx)
        assert cfg.family_members == {"titular": "x"}
        assert cfg.pipeline == {"llm": {"model": "test"}}
        assert cfg.institutions == {"banks": {}}
        assert cfg.categorization == {"Alimentacao": ["MERCADO"]}
        # Opcionais default para {}
        assert cfg.goals == {}
        assert cfg.scoring == {}
        assert cfg.fiscal == {}

    def test_optional_configs_respected(self, tmp_path):
        overrides = dict(_MIN_OVERRIDES)
        overrides["goals.json"] = {"ret": "100k"}
        overrides["scoring.json"] = {"weights": {"a": 1}}
        overrides["parametros_fiscais.json"] = {"teto_irpf": 10000}
        ctx = WorkspaceContext(root=tmp_path, config_overrides=overrides)
        cfg = StageConfig.from_context(ctx)
        assert cfg.goals == {"ret": "100k"}
        assert cfg.scoring == {"weights": {"a": 1}}
        assert cfg.fiscal == {"teto_irpf": 10000}

    @pytest.mark.parametrize(
        "missing_key",
        ["family_members.json", "pipeline.json", "institutions.json", "categorization.json"],
    )
    def test_missing_required_raises_config_error(self, tmp_path, missing_key):
        overrides = {k: v for k, v in _MIN_OVERRIDES.items() if k != missing_key}
        ctx = WorkspaceContext(root=tmp_path, config_overrides=overrides)
        with pytest.raises(ConfigError):
            StageConfig.from_context(ctx)


class TestImmutability:
    def test_cannot_reassign_fields(self, tmp_path):
        ctx = WorkspaceContext(root=tmp_path, config_overrides=_MIN_OVERRIDES)
        cfg = StageConfig.from_context(ctx)
        with pytest.raises(ValidationError):
            cfg.pipeline = {"mutated": True}  # type: ignore[misc]


class TestEmpty:
    def test_empty_returns_zero_configs(self):
        cfg = StageConfig.empty()
        assert cfg.family_members == {}
        assert cfg.pipeline == {}
        assert cfg.institutions == {}
        assert cfg.categorization == {}

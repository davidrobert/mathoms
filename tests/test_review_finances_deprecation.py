"""Regressão T-25 — ``review_finances`` deprecated (ADR-199 supersede ADR-128). Stage continua executável (não-quebra), emite DeprecationWarning + StageSpec.is_deprecated=True."""

from __future__ import annotations

import warnings

import pytest

from pipeline.stage_spec import STAGE_REGISTRY


class TestStageRegistry:
    def test_review_finances_marked_deprecated(self):
        """``review_finances`` (E7-review) deve estar marcado is_deprecated=True."""
        spec = STAGE_REGISTRY["review_finances"]
        assert spec.is_deprecated is True

    def test_review_finances_holistic_not_deprecated(self):
        """``review_finances_holistic`` (parecer planejador) é o substituto — não-deprecated."""
        spec = STAGE_REGISTRY["review_finances_holistic"]
        assert spec.is_deprecated is False

    def test_other_stages_default_not_deprecated(self):
        """Demais stages mantêm default ``is_deprecated=False`` (segurança)."""
        for name, spec in STAGE_REGISTRY.items():
            if name == "review_finances":
                continue
            assert spec.is_deprecated is False, f"{name} marcado deprecated inesperadamente"


class TestRunEmitsDeprecationWarning:
    """Stage deve emitir DeprecationWarning quando ``run()`` é invocado."""

    def test_run_emits_deprecation_warning(self, tmp_path):
        """run() emite DeprecationWarning como primeiro side-effect (antes do skip por llm_config)."""
        from pipeline.artifact_store import InMemoryArtifactStore
        from pipeline.context import WorkspaceContext
        from pipeline.stages import review_finances

        store = InMemoryArtifactStore()
        ctx = WorkspaceContext(root=tmp_path, artifact_store=store, workspace_id="ws-deprec")

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            review_finances.run(ctx)

        deprec_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(deprec_warnings) >= 1
        msg = str(deprec_warnings[0].message)
        assert "review_finances" in msg
        assert "deprecated" in msg.lower()
        assert "ADR-199" in msg or "review_finances_holistic" in msg


class TestStageSpecDataclass:
    def test_is_deprecated_default_false(self):
        """``StageSpec.is_deprecated`` deve ter default False (backward-compat)."""
        from pipeline.stage_spec import StageSpec

        spec = StageSpec(name="test_stage")
        assert spec.is_deprecated is False

    def test_is_deprecated_settable(self):
        """``StageSpec`` aceita ``is_deprecated=True`` explícito."""
        from pipeline.stage_spec import StageSpec

        spec = StageSpec(name="legacy_stage", is_deprecated=True)
        assert spec.is_deprecated is True

"""Gate de pureza de extração (ADR-280): verde hoje, detecta leak, exclui Transform,
sentinela de cobertura do REGISTRY, precisão anti-falso-positivo (`dedup_metrics`)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "check_extract_no_domain_imports", _REPO / "dev" / "check_extract_no_domain_imports.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GATE = _load_gate()


class TestForbiddenMatcher:
    def test_domain_modules_forbidden(self):
        assert GATE._is_forbidden("pipeline.domain.services.entity_dedup")
        assert GATE._is_forbidden("pipeline.domain.services.irpf_declaration_deduplicator")
        assert GATE._is_forbidden("backend.app.models.category_template")
        assert GATE._is_forbidden("backend.app.repositories.category_template_repository")
        assert GATE._is_forbidden("pipeline.ports.config_store")
        assert GATE._is_forbidden("backend.app.services.db_config_store")

    def test_precision_no_false_positive(self):
        # `dedup_metrics` não termina em _dedup nem contém deduplicator → permitido.
        assert not GATE._is_forbidden("pipeline.metrics.dedup_metrics")
        assert not GATE._is_forbidden("scripts.e2.common")
        assert not GATE._is_forbidden("pipeline.context")


class TestRepoState:
    def test_gate_green_today(self):
        assert GATE.collect_violations() == []

    def test_extraction_surface_nonempty(self):
        files = {p.name for p in GATE.extraction_files()}
        assert "extract_baseline.py" in files
        assert "extract_irpf_full.py" in files
        # consolidate_baseline (Transform) NÃO está coberto pelo glob extract_*.
        assert "consolidate_baseline.py" not in files

    def test_every_registry_extract_stage_covered(self):
        # Sentinela: extract_* movido de pasta (sem pipeline/stages/<name>.py) é pego aqui.
        from pipeline.stage_spec import STAGE_REGISTRY

        covered = {p.relative_to(_REPO).as_posix() for p in GATE.extraction_files()}
        for name in STAGE_REGISTRY:
            if name.startswith("extract_"):
                assert f"pipeline/stages/{name}.py" in covered, name


class TestDetectsViolation:
    def test_synthetic_leak_detected(self, tmp_path: Path, monkeypatch):
        leaky = tmp_path / "scripts" / "e2" / "banks" / "leaky.py"
        leaky.parent.mkdir(parents=True)
        leaky.write_text(
            "from pipeline.domain.services.entity_dedup import dedupe\n", encoding="utf-8"
        )
        monkeypatch.setattr(GATE, "_REPO_ROOT", tmp_path)
        monkeypatch.setattr(GATE, "_EXTRACTION_GLOBS", ("scripts/e2/**/*.py",))
        violations = GATE.collect_violations()
        assert len(violations) == 1
        assert "entity_dedup" in violations[0] and "leaky.py" in violations[0]

    def test_consolidate_baseline_allowed_outside_glob(self, tmp_path: Path, monkeypatch):
        # Transform fora do glob extract_* PODE importar dedup — não vira violação.
        transform = tmp_path / "pipeline" / "stages" / "consolidate_baseline.py"
        transform.parent.mkdir(parents=True)
        transform.write_text(
            "from pipeline.domain.services.imoveis_dedup import dedupe\n", encoding="utf-8"
        )
        monkeypatch.setattr(GATE, "_REPO_ROOT", tmp_path)
        monkeypatch.setattr(GATE, "_EXTRACTION_GLOBS", ("pipeline/stages/extract_*.py",))
        assert GATE.collect_violations() == []

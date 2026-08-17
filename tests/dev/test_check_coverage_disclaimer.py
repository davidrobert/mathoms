"""Prova por mutação do gate A40.l60: superfície nova sem ressalva falha."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))

from check_coverage_disclaimer import MARK, has_disclaimer, main, offenders  # noqa: E402


def test_orphan_surface_without_disclaimer_fails(tmp_path: Path) -> None:
    orphan = tmp_path / "NewCoverageCard.tsx"
    orphan.write_text('export const copy = "Contratar seguro de vida e invalidez";\n')
    assert main(["--root", str(tmp_path)]) == 1
    assert orphan in offenders((tmp_path,))


def test_surface_with_mark_passes(tmp_path: Path) -> None:
    ok = tmp_path / "CoveredCard.tsx"
    ok.write_text(f'export const copy = "Cobertura recomendada. {MARK}";\n')
    assert main(["--root", str(tmp_path)]) == 0


def test_hook_call_counts_as_disclaimer() -> None:
    assert has_disclaimer("fiduciaryDisclaimer(date)")
    assert has_disclaimer("fiduciary_disclaimer(method)")
    assert not has_disclaimer("Contratar seguro de vida e invalidez")

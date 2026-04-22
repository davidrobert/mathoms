#!/usr/bin/env python3
"""
Pipeline Regression Tests — garante que outputs não mudam após refactoring.

Fluxo:
1. Gerar golden files:   python tests/test_regression.py --capture
2. Rodar regressão:      pytest tests/test_regression.py -v

Golden files ficam em _scratch/golden/ (não versionados, regenerados por run).
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_DIR = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJECT_DIR / "_scratch" / "golden"
GOLDEN_MANIFEST = GOLDEN_DIR / "manifest.json"

TRACKED_DIRS = [
    ("E2_extracts", PROJECT_DIR / "processed" / "E2_extracts"),
    ("E3_reconciled", PROJECT_DIR / "processed" / "E3_reconciled"),
    ("E4_unified", PROJECT_DIR / "processed" / "E4_unified"),
    ("E5_analysis", PROJECT_DIR / "processed" / "E5_analysis"),
    ("output", PROJECT_DIR / "output"),
]


def _hash_file(path: Path) -> str:
    """SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_manifest() -> dict:
    """Gera manifesto com hash de cada arquivo nos diretórios rastreados."""
    manifest = {}
    for label, dir_path in TRACKED_DIRS:
        if not dir_path.exists():
            continue
        files = sorted(
            f
            for f in dir_path.iterdir()
            if f.is_file() and f.suffix in (".json", ".html") and f.name != ".DS_Store"
        )
        for f in files:
            key = f"{label}/{f.name}"
            manifest[key] = {
                "hash": _hash_file(f),
                "size": f.stat().st_size,
            }
    return manifest


def capture_golden():
    """Captura o estado atual dos outputs como golden files."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _build_manifest()

    if not manifest:
        print("WARN: Nenhum output encontrado para capturar.")
        print("  Execute o pipeline (e_reset.py) antes de capturar golden files.")
        return

    with open(GOLDEN_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Golden manifest salvo: {GOLDEN_MANIFEST}")
    print(f"  Arquivos rastreados: {len(manifest)}")
    for key, info in manifest.items():
        print(f"    {key} ({info['size']:,} bytes)")


# ---- Pytest tests ----


class TestRegression:
    def test_golden_manifest_exists(self):
        """Verifica se golden files foram capturados."""
        if not GOLDEN_MANIFEST.exists():
            import pytest

            pytest.skip(
                "Golden manifest não encontrado. "
                "Execute: python tests/test_regression.py --capture"
            )

    def test_outputs_match_golden(self):
        """Compara outputs atuais com golden files."""
        if not GOLDEN_MANIFEST.exists():
            import pytest

            pytest.skip("Golden manifest não encontrado.")

        with open(GOLDEN_MANIFEST, "r") as f:
            golden = json.load(f)

        if not golden:
            import pytest

            pytest.skip("Golden manifest está vazio.")

        current = _build_manifest()
        errors = []

        for key, golden_info in golden.items():
            if key not in current:
                errors.append(f"MISSING: {key} (existia no golden, não existe mais)")
                continue
            if current[key]["hash"] != golden_info["hash"]:
                errors.append(
                    f"CHANGED: {key} "
                    f"(golden={golden_info['hash'][:12]}... "
                    f"current={current[key]['hash'][:12]}...)"
                )

        for key in current:
            if key not in golden:
                errors.append(f"NEW: {key} (não existia no golden)")

        if errors:
            msg = f"{len(errors)} diferenças encontradas:\n" + "\n".join(f"  - {e}" for e in errors)
            assert False, msg


if __name__ == "__main__":
    if "--capture" in sys.argv:
        capture_golden()
    else:
        print("Uso:")
        print("  python tests/test_regression.py --capture   # Salva golden files")
        print("  pytest tests/test_regression.py -v          # Roda regressão")

"""O gate de amostragem pega call-site novo sem os kwargs ([[A40.l66]] cauda)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE = REPO_ROOT / "dev" / "check_extraction_sampling.py"


def _roda() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE)], capture_output=True, text=True, cwd=REPO_ROOT
    )


def test_arvore_atual_passa() -> None:
    assert _roda().returncode == 0


def test_call_site_sem_os_kwargs_reprova(tmp_path: Path) -> None:
    """Mutação plausível: alguém adiciona um stage novo e esquece os dois kwargs."""
    novo = REPO_ROOT / "pipeline" / "stages" / "extract_zz_gate_probe.py"
    novo.write_text(
        "def run(service, prompt):\n    return service.call(system_prompt=prompt)\n",
        encoding="utf-8",
    )
    try:
        resultado = _roda()
    finally:
        novo.unlink()
    assert resultado.returncode == 1
    assert "temperature" in resultado.stdout and "seed" in resultado.stdout


def test_kwarg_pela_metade_tambem_reprova() -> None:
    """Passar só `temperature` é o erro mais provável — o gate tem de pegá-lo."""
    novo = REPO_ROOT / "pipeline" / "stages" / "extract_zz_gate_probe.py"
    novo.write_text(
        "def run(service, prompt):\n    return service.call(system_prompt=prompt, temperature=0.0)\n",
        encoding="utf-8",
    )
    try:
        resultado = _roda()
    finally:
        novo.unlink()
    assert resultado.returncode == 1
    assert "seed" in resultado.stdout

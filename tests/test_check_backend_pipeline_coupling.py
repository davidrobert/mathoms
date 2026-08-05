"""Gate de coupling backend↔pipeline (ADR-210 §Adendo 2026-08-05): import fora do allowlist falha, entrada não-exercida falha, forma reconstruída de `from X import Y` casa o prefixo certo, e o estado real do repo está verde — prova de mutação nos dois sentidos."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MOD = "check_backend_pipeline_coupling"


def _load_gate():
    spec = importlib.util.spec_from_file_location(_MOD, _REPO / "dev" / f"{_MOD}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MOD] = module
    spec.loader.exec_module(module)
    return module


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_import_fora_do_allowlist_reprova(tmp_path):
    gate = _load_gate()
    f = _write(tmp_path, "mod.py", "import scripts.some_new_thing\n")
    violations, exercised = gate.scan_file(f)
    assert len(violations) == 1
    assert "scripts.some_new_thing" in violations[0]
    assert exercised == set()


def test_from_import_reconstroi_o_prefixo_certo(tmp_path):
    """`from tests import fakes` tem de casar `tests.fakes`, não `tests`."""
    gate = _load_gate()
    f = _write(tmp_path, "mod.py", "from tests import fakes\n")
    violations, exercised = gate.scan_file(f)
    assert violations == []
    assert exercised == {"tests.fakes"}


def test_import_dentro_do_allowlist_passa(tmp_path):
    gate = _load_gate()
    f = _write(tmp_path, "mod.py", "import scripts.pipeline_common as _pc\n")
    violations, exercised = gate.scan_file(f)
    assert violations == []
    assert exercised == {"scripts.pipeline_common"}


def test_import_backend_tests_nao_e_boundary_crossing(tmp_path):
    """`backend.tests.fakes` não é o `tests.fakes` de raiz — falso-positivo
    aqui reprovaria todo módulo que só usa suas próprias fixtures."""
    gate = _load_gate()
    f = _write(tmp_path, "mod.py", "from backend.tests.fakes import Something\n")
    violations, exercised = gate.scan_file(f)
    assert violations == []
    assert exercised == set()


def test_entrada_nao_exercida_reprova():
    gate = _load_gate()
    assert gate._unexercised_entries(set()) == list(gate._ALLOWED_CROSS_BOUNDARY_PREFIXES)
    assert gate._unexercised_entries(set(gate._ALLOWED_CROSS_BOUNDARY_PREFIXES)) == []


def test_estado_real_do_repo_esta_verde():
    gate = _load_gate()
    violations, exercised = gate.scan_all()
    assert violations == []
    assert gate._unexercised_entries(exercised) == []


def test_import_novo_de_verdade_reprova_o_estado_real(tmp_path):
    """Mutação: soma um arquivo com import cross-boundary não-registrado ao
    scan real — prova que o teste anterior não passa por o allowlist cobrir
    tudo por acidente (ex.: allowlist vazio + nenhum import em lugar nenhum)."""
    gate = _load_gate()
    backend_root = tmp_path / "backend"
    (backend_root / "app").mkdir(parents=True)
    (backend_root / "app" / "novo.py").write_text(
        "import scripts.novo_modulo_sem_dono\n", encoding="utf-8"
    )
    violations, _ = gate.scan_all(backend_root)
    assert any("scripts.novo_modulo_sem_dono" in v for v in violations)

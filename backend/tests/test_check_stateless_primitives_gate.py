"""ADR-359 — o gate que torna verdadeira a afirmação de §5 do STATELESS_AUDIT.

O defeito de origem não foi drift: a afirmação "zero `threading.Thread` em app
code" nasceu falsa e nada a verificava por 3,5 meses. Estes testes provam que o
gate pega o que o audit prometia, e que não pega o que ele legitimamente permite.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = _REPO_ROOT / "dev" / "check_stateless_primitives.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("_stateless_gate", _GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate():
    return _load_gate()


def test_repo_is_clean(gate):
    assert gate.main() == 0


@pytest.mark.parametrize(
    "snippet",
    [
        "import threading\nthreading.Thread(target=f, daemon=True).start()\n",
        "from threading import Thread\nThread(target=f).start()\n",
        "import asyncio\nasyncio.create_task(f())\n",
        "from fastapi import BackgroundTasks\ndef h(t: BackgroundTasks): ...\n",
        "import fcntl\n",
        "import functools\n@functools.lru_cache\ndef f(): ...\n",
        "from functools import cached_property\nclass C:\n    @cached_property\n    def p(self): ...\n",
    ],
)
def test_forbidden_primitive_is_caught(gate, tmp_path, snippet):
    target = tmp_path / "offender.py"
    target.write_text(snippet, encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(gate, "_REPO_ROOT", tmp_path)
        assert gate._violations_in(target)


@pytest.mark.parametrize(
    "snippet",
    [
        # Concorrência intra-processo sobre objeto local — categoria (b) do audit.
        "import threading\nlock = threading.Lock()\n",
        "import asyncio\nsem = asyncio.Semaphore(2)\n",
        # `create_task` de DOMÍNIO (agregado Tarefas) — a colisão que derrubou o
        # suffix-match durante o desenho do gate.
        "async def f(svc, cmd):\n    return await svc.create_task(cmd)\n",
        "from backend.app.application.task import create_task\n"
        "async def f(c):\n    return await create_task(c)\n",
        # Prosa que AFIRMA a ausência — `category_cache.py` faz exatamente isso e
        # um gate textual a acusaria como violação.
        '"""Stateless rigoroso (ADR-111): sem ``@lru_cache`` em processo."""\n',
        "# usar threading.Thread aqui seria violação da ADR-111\n",
    ],
)
def test_legitimate_code_is_not_flagged(gate, tmp_path, snippet):
    target = tmp_path / "legit.py"
    target.write_text(snippet, encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(gate, "_REPO_ROOT", tmp_path)
        assert gate._violations_in(target) == []


def test_allowlist_entry_requires_a_mention_in_the_audit(gate):
    """Fecha o loop doc↔código: exceção invisível no audit é o defeito de origem."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(gate, "_ALLOWLIST", {("backend/app/inexistente.py", "Thread"): "motivo"})
        assert gate._allowlist_drift()

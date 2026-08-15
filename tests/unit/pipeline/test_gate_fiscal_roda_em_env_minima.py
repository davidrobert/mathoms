"""O gate fiscal roda na env MÍNIMA do job de lint (A40.l56).

Duas vezes seguidas o gate passou local e quebrou no runner — `pydantic` e depois
`sqlalchemy` — porque a simulação era calibrada na falha JÁ OBSERVADA, e não no
ambiente. Este teste bloqueia o conjunto inteiro de dependências pesadas de uma
vez, e prova nos dois sentidos: sem elas o gate passa, e um gate que importasse
por pacote falharia.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_GATE = _REPO / "dev" / "check_fiscal_brackets_continuity.py"

# O job `lint-all` instala só pre-commit + ruff. Nada de runtime de aplicação.
_AUSENTES_NO_LINT = ("pydantic", "sqlalchemy", "alembic", "litellm", "fastapi", "redis")


@pytest.fixture
def env_minima(tmp_path):
    """PYTHONPATH com stubs que levantam ModuleNotFoundError, como o runner."""
    for nome in _AUSENTES_NO_LINT:
        (tmp_path / f"{nome}.py").write_text(
            f'raise ModuleNotFoundError("No module named {nome!r}")\n', encoding="utf-8"
        )
    return {**os.environ, "PYTHONPATH": str(tmp_path)}


def _roda(script: Path, env) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)], env=env, capture_output=True, text=True, cwd=_REPO
    )


def test_gate_passa_sem_as_dependencias_pesadas(env_minima):
    r = _roda(_GATE, env_minima)
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
    assert "passam os invariantes" in r.stdout


def test_a_simulacao_pega_import_por_pacote(env_minima, tmp_path):
    """Sem este braço, o verde acima não distingue gate robusto de gate que não roda."""
    sonda = tmp_path / "sonda_import_por_pacote.py"
    sonda.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(_REPO)!r})\n"
        "from pipeline.domain.services.tabela_progressiva_coerencia import Violacao\n"
        "print(Violacao)\n",
        encoding="utf-8",
    )
    r = _roda(sonda, env_minima)
    assert r.returncode != 0
    assert "ModuleNotFoundError" in r.stderr

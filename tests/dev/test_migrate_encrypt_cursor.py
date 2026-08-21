"""Testes do cursor de `dev/migrate_encrypt_existing_artifacts.py`.

O cursor é o `id` (INTEGER) da última row commitada e faz round-trip por
disco, onde vira texto. Dois bugs viviam nessa fronteira, achados em
2026-08-21 rodando o backfill dos 418 artifacts em plaintext do dogfood:

1. `_write_cursor` fazia `write_text(int)` — `TypeError` que derrubava o
   script DEPOIS de commitar o primeiro batch (o corpus ficava parcial).
2. `_read_cursor` devolvia o texto cru, e `_query_pending` comparava
   `id > '500'`. No SQLite todo INTEGER ordena antes de todo TEXT, então o
   predicado é sempre falso: o resume varreria zero rows e o script diria
   "Done. 0 rows encrypted" sem ter feito nada. Falso-verde silencioso.

O bug 2 é o que exige teste: o 1 falha alto, o 2 falha calado.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MOD = "migrate_encrypt_existing_artifacts"


def _load(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(_MOD, _REPO / "dev" / f"{_MOD}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MOD] = module
    spec.loader.exec_module(module)
    module.CURSOR_DIR = tmp_path
    return module


def test_cursor_faz_round_trip_como_int(tmp_path):
    """O que sai do disco tem que comparar com uma coluna INTEGER."""
    mod = _load(tmp_path)
    mod._write_cursor(None, 4321)
    lido = mod._read_cursor(None)
    assert lido == 4321
    assert isinstance(lido, int)


def test_cursor_lido_nao_e_str(tmp_path):
    """A regressão silenciosa: `id > '4321'` casa zero rows no SQLite."""
    mod = _load(tmp_path)
    mod._write_cursor(None, 4321)
    assert not isinstance(mod._read_cursor(None), str)


def test_write_cursor_aceita_int_sem_typeerror(tmp_path):
    """O caller passa `row.id`, que é int — `write_text` exige str."""
    mod = _load(tmp_path)
    mod._write_cursor(None, 1)  # levantava TypeError antes do fix
    assert mod._read_cursor(None) == 1


def test_cursor_ausente_devolve_none(tmp_path):
    mod = _load(tmp_path)
    assert mod._read_cursor(None) is None


def test_cursor_vazio_devolve_none(tmp_path):
    """Arquivo truncado por crash no meio do write não vira `int('')`."""
    mod = _load(tmp_path)
    mod._cursor_path(None).write_text("")
    assert mod._read_cursor(None) is None


def test_cursor_por_workspace_nao_colide(tmp_path):
    mod = _load(tmp_path)
    mod._write_cursor("ws-a", 10)
    mod._write_cursor("ws-b", 99)
    assert mod._read_cursor("ws-a") == 10
    assert mod._read_cursor("ws-b") == 99


def test_clear_cursor_remove(tmp_path):
    mod = _load(tmp_path)
    mod._write_cursor(None, 7)
    mod._clear_cursor(None)
    assert mod._read_cursor(None) is None

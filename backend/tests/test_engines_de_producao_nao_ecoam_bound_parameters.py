"""Os engines de produção não ecoam bound parameters no texto do erro.

`str(StatementError)` traz `[parameters: ...]`. Medido em 2026-10-08 em PG 16: o
`DataError` de `match_or_create` levou endereço e nome do imóvel ao `stage_log`, ao
canal do WS e ao traceback — e o mesmo texto vai a log do worker, span e result
backend do Celery. ``hide_parameters`` corta na fonte, para todo sink.

O conftest troca `database.sync_engine` pelo engine de teste. O módulo é carregado
de novo, isolado, para medir os objetos que produção constrói — o efeito, não o
texto do call-site (o gate AST cobre o texto: `dev/check_engine_hide_parameters.py`).
"""

from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path
from types import ModuleType

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import StatementError

_DATABASE_PY = Path(__file__).resolve().parents[1] / "app" / "core" / "database.py"
_ENDERECO = "Rua Exemplo, 100"  # sintético, PII-zero
_STATEMENT = text("SELECT * FROM tabela_inexistente WHERE descricao = :descricao")


def _texto_do_erro(exc: BaseException) -> str:
    return str(exc) + "".join(traceback.format_exception(exc))


@pytest_asyncio.fixture
async def database_isolado(monkeypatch, tmp_path) -> ModuleType:
    """Executa `database.py` de novo, sem a troca do conftest, sobre um SQLite temporário."""
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'p.db'}")
    spec = importlib.util.spec_from_file_location("_database_isolado", _DATABASE_PY)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    yield modulo
    modulo.sync_engine.dispose()
    await modulo.engine.dispose()


def test_engine_sync_do_pipeline_nao_ecoa_o_parametro(database_isolado):
    with pytest.raises(StatementError) as caught, database_isolado.sync_engine.connect() as conn:
        conn.execute(_STATEMENT, {"descricao": _ENDERECO})

    texto = _texto_do_erro(caught.value)
    assert _ENDERECO not in texto
    # Não-vácuo: o erro é o do statement, e o SQL — sem valor — segue legível.
    assert "tabela_inexistente" in texto


@pytest.mark.asyncio
async def test_engine_async_da_api_nao_ecoa_o_parametro(database_isolado):
    with pytest.raises(StatementError) as caught:
        async with database_isolado.engine.connect() as conn:
            await conn.execute(_STATEMENT, {"descricao": _ENDERECO})

    texto = _texto_do_erro(caught.value)
    assert _ENDERECO not in texto
    assert "tabela_inexistente" in texto

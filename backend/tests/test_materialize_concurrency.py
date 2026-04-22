"""Concurrency test para `materialize_config` — F6.5E.7.

# Por que

`materialize_config(workspace_id, tenant_root, db)` é chamado antes de cada
PipelineRun. Em produção, Celery usa **fork pool** — múltiplos workers
podem executar `materialize_config` de workspaces diferentes
simultaneamente.

O fluxo interno:
1. `_copy_global(global → tenant_config)` — `shutil.rmtree(dst)` + `copytree`
2. Override de 6 configs no DB → escreve JSONs/YAML

Risco: se dois tenants compartilhassem o mesmo `tenant_root` (bug
teórico), `rmtree` de um quebraria o outro. Queremos garantir:
- Tenants diferentes → paths diferentes → zero interferência
- Execução paralela não corrompe configs de um workspace

# Escopo do test

- Cria 2 workspaces com dados distintos
- Materialize em threads paralelas (simula fork worker behavior)
- Assert: cada `tenant_root` tem **apenas** os dados do seu workspace
- Assert: `familia.sobrenome` de A ≠ B em disco após paralelização
- Assert: nenhum arquivo contém signatures cruzadas

# Limite

- `materialize_config` recebe DB `Session` sync. Tests usam threads
  do `concurrent.futures` com sync engine dedicado (não async).
- Em Celery real, cada fork tem seu próprio connection pool. Aqui
  simulamos com thread-local sessions.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.models  # noqa: F401
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import FamilyMember, User, Workspace
from backend.app.services.config_materializer import materialize_config

# SQLite file-based (tmp dir) + check_same_thread=False para permitir uso
# em múltiplas threads simultâneas. NÃO usar in-memory aqui (não é thread-safe).
_engine = None
_Session = None


@pytest.fixture(autouse=True)
def setup_sync_db(tmp_path_factory):
    global _engine, _Session
    db_path = tmp_path_factory.mktemp("concurrency_db") / "test.db"
    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    _Session = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)
    _engine.dispose()


def _seed_workspace(label: str) -> tuple[str, str]:
    """Cria user + workspace + family_surname + 1 member. Retorna (ws_id, surname)."""
    session = _Session()
    try:
        u = User(
            email=f"{label.lower()}@concurrency.test",
            hashed_password=hash_password("x"),
            full_name=f"User {label}",
        )
        session.add(u)
        session.flush()
        ws = Workspace(
            name=f"WS {label}",
            family_surname=f"Sobrenome {label}",
            owner_id=u.id,
        )
        session.add(ws)
        session.flush()
        m = FamilyMember(
            workspace_id=ws.id,
            key=f"titular_{label.lower()}",
            full_name=f"Titular {label}",
            short_name=label,
            role="titular",
            order=0,
        )
        session.add(m)
        session.commit()
        return ws.id, ws.family_surname or ""
    finally:
        session.close()


def _materialize_in_thread(ws_id: str, tenant_root: Path) -> None:
    """Cada thread tem sua própria Session (paradigm Celery fork worker)."""
    session = _Session()
    try:
        materialize_config(ws_id, tenant_root, session)
    finally:
        session.close()


class TestMaterializeConcurrency:
    """F6.5E.7 — paralelização de materialize_config não corrompe configs."""

    def test_two_workspaces_in_parallel_keep_own_data(self, tmp_path):
        """2 workspaces materializando ao mesmo tempo → cada tenant_root
        contém apenas seus próprios dados (nome, sobrenome, member)."""
        ws_a_id, surname_a = _seed_workspace("Alfa")
        ws_b_id, surname_b = _seed_workspace("Beta")

        tenant_a = tmp_path / "tenant_a"
        tenant_b = tmp_path / "tenant_b"

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_a = pool.submit(_materialize_in_thread, ws_a_id, tenant_a)
            fut_b = pool.submit(_materialize_in_thread, ws_b_id, tenant_b)
            for fut in as_completed([fut_a, fut_b]):
                fut.result()  # raises se falhou

        # Ambos os tenant_roots existem
        assert (tenant_a / "config" / "family_members.json").exists()
        assert (tenant_b / "config" / "family_members.json").exists()

        import json

        data_a = json.loads((tenant_a / "config" / "family_members.json").read_text())
        data_b = json.loads((tenant_b / "config" / "family_members.json").read_text())

        # Cada JSON tem APENAS seus próprios dados
        assert data_a["familia"]["sobrenome"] == surname_a
        assert data_b["familia"]["sobrenome"] == surname_b
        assert "titular_alfa" in data_a["membros"]
        assert "titular_beta" in data_b["membros"]

        # CRUZAMENTO NÃO PODE ACONTECER (regressão de isolation)
        assert (
            "titular_beta" not in data_a["membros"]
        ), "LEAK: workspace Alfa vê dados de Beta no JSON materializado"
        assert "titular_alfa" not in data_b["membros"], "LEAK: workspace Beta vê dados de Alfa"
        assert data_a["familia"]["sobrenome"] != surname_b
        assert data_b["familia"]["sobrenome"] != surname_a

    def test_same_workspace_materialized_twice_in_parallel_idempotent(self, tmp_path):
        """Corrida improvável mas defensiva: 2 materializes do mesmo workspace
        para o mesmo tenant_root devem terminar com estado consistente."""
        ws_id, surname = _seed_workspace("Gamma")
        tenant_root = tmp_path / "tenant_same"

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [
                pool.submit(_materialize_in_thread, ws_id, tenant_root),
                pool.submit(_materialize_in_thread, ws_id, tenant_root),
            ]
            errors = []
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    # Race em `shutil.rmtree` + `copytree` pode crashar;
                    # documentamos o comportamento aceitável.
                    errors.append(str(exc))

        # Resultado final tem que ser válido independente da ordem
        family_json = tenant_root / "config" / "family_members.json"
        assert family_json.exists()
        import json

        data = json.loads(family_json.read_text())
        assert data["familia"]["sobrenome"] == surname
        # Se houve race errors, devem ser relacionados a filesystem
        # (copyfile existe, rmtree parcial) e NÃO a corrupção de dados.
        for err in errors:
            assert any(k in err.lower() for k in ["file", "directory", "exist"])

    def test_10_workspaces_in_parallel_all_succeed(self, tmp_path):
        """Stress suave: 10 tenants materializando simultaneamente, todos
        devem terminar com seus dados íntegros."""
        ws_surnames: list[tuple[str, str]] = []
        for i in range(10):
            ws_id, surname = _seed_workspace(f"T{i}")
            ws_surnames.append((ws_id, surname))

        tenant_roots = {ws_id: tmp_path / f"tenant_{i}" for i, (ws_id, _) in enumerate(ws_surnames)}

        with ThreadPoolExecutor(max_workers=10) as pool:
            futs = {
                pool.submit(_materialize_in_thread, ws_id, tenant_roots[ws_id]): ws_id
                for ws_id, _ in ws_surnames
            }
            for fut in as_completed(futs):
                fut.result()

        # Valida cada tenant_root tem exatamente seus próprios dados
        import json

        for ws_id, surname in ws_surnames:
            family_json = tenant_roots[ws_id] / "config" / "family_members.json"
            assert family_json.exists(), f"tenant {ws_id} sem family_members.json"
            data = json.loads(family_json.read_text())
            assert data["familia"]["sobrenome"] == surname

            # Não pode conter sobrenome de outro tenant
            for other_ws_id, other_surname in ws_surnames:
                if other_ws_id == ws_id:
                    continue
                assert other_surname not in json.dumps(
                    data
                ), f"LEAK: tenant {ws_id} contém sobrenome de {other_ws_id}"

"""Tests — ``dev/dump_artifact.py`` (dump read-only de pipeline_artifacts)."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    """Importa o CLI por path — `dev/` não é pacote (sem `__init__.py`)."""
    spec = importlib.util.spec_from_file_location(
        "dump_artifact", REPO_ROOT / "dev" / "dump_artifact.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["dump_artifact"] = module
    spec.loader.exec_module(module)
    return module


dump_artifact = _load_module()


@pytest.fixture
def conn() -> sqlite3.Connection:
    """DB em memória com o shape mínimo das duas tabelas lidas (nunca mocar DB)."""
    db = sqlite3.connect(":memory:")
    db.execute("create table pipeline_runs (id text, started_at text)")
    db.execute(
        "create table pipeline_artifacts (pipeline_run_id text, stage text, "
        "artifact_key text, content_json text, created_at text)"
    )
    db.execute("insert into pipeline_runs values ('run-abc-1', '2026-08-18')")
    db.execute("insert into pipeline_runs values ('run-xyz-2', '2026-08-19')")
    return db


def _add_artifact(db: sqlite3.Connection, stage: str, key: str, payload: dict, when: str) -> None:
    db.execute(
        "insert into pipeline_artifacts values (?,?,?,?,?)",
        ("run-abc-1", stage, key, json.dumps(payload), when),
    )


# =============================================================================
# resolve_run_id — prefixo
# =============================================================================


def test_resolve_run_id_expande_prefixo(conn):
    assert dump_artifact.resolve_run_id(conn, "run-abc") == "run-abc-1"


def test_resolve_run_id_recusa_prefixo_ambiguo(conn):
    with pytest.raises(dump_artifact.DumpError, match="ambíguo"):
        dump_artifact.resolve_run_id(conn, "run-")


def test_resolve_run_id_recusa_prefixo_sem_match(conn):
    with pytest.raises(dump_artifact.DumpError, match="nenhum run"):
        dump_artifact.resolve_run_id(conn, "nao-existe")


# =============================================================================
# read_payload — alias legacy ↔ descritivo (ADR-093) e recência
# =============================================================================


def test_read_payload_aceita_stage_legacy_para_artefato_descritivo(conn):
    """`--stage E5` acha o artefato gravado como `analyze_finances`."""
    _add_artifact(conn, "analyze_finances", "analise_financeira", {"pl": 1}, "2026-08-18")
    assert dump_artifact.read_payload(conn, "run-abc-1", "E5", None) == {"pl": 1}


def test_read_payload_aceita_stage_descritivo_para_artefato_legacy(conn):
    _add_artifact(conn, "E5", "analise_financeira", {"pl": 2}, "2026-08-18")
    assert dump_artifact.read_payload(conn, "run-abc-1", "analyze_finances", None) == {"pl": 2}


def test_read_payload_pega_o_mais_recente(conn):
    _add_artifact(conn, "E5", "analise_financeira", {"v": "velho"}, "2026-08-01")
    _add_artifact(conn, "E5", "analise_financeira", {"v": "novo"}, "2026-08-18")
    assert dump_artifact.read_payload(conn, "run-abc-1", "E5", None) == {"v": "novo"}


def test_read_payload_filtra_por_key(conn):
    _add_artifact(conn, "E4", "despesas", {"k": "d"}, "2026-08-18")
    _add_artifact(conn, "E4", "receitas", {"k": "r"}, "2026-08-18")
    assert dump_artifact.read_payload(conn, "run-abc-1", "E4", "receitas") == {"k": "r"}


def test_read_payload_erra_nomeando_stage_e_key(conn):
    with pytest.raises(dump_artifact.DumpError, match="E7"):
        dump_artifact.read_payload(conn, "run-abc-1", "E7", None)


# =============================================================================
# select_path
# =============================================================================


def test_select_path_desce_dict_e_lista():
    payload = {"a": {"b": [{"c": 42}]}}
    assert dump_artifact.select_path(payload, "a.b.0.c") == 42


def test_select_path_erra_nomeando_o_segmento_ausente():
    with pytest.raises(dump_artifact.DumpError, match="`z`"):
        dump_artifact.select_path({"a": 1}, "a.z")


# =============================================================================
# render — a máscara é o default, `--raw` é o ato consciente
# =============================================================================


def test_render_mascara_valor_monetario_e_cpf_por_default():
    out = dump_artifact.render({"valor": "110.130,67", "doc": "123.456.789-00"}, raw=False)
    assert "110.130,67" not in out
    assert "123.456.789-00" not in out
    assert "<VAL>" in out and "<CPF>" in out


def test_render_raw_devolve_json_valido_com_o_numero():
    out = dump_artifact.render({"valor": 110130.67}, raw=True)
    assert json.loads(out) == {"valor": 110130.67}


def test_render_default_nao_e_json_valido_por_construcao():
    """A máscara corrompe o JSON de propósito — quem quer parsear pede `--raw`."""
    with pytest.raises(json.JSONDecodeError):
        json.loads(dump_artifact.render({"valor": 110130.67}, raw=False))


# =============================================================================
# Ambiente
# =============================================================================


def test_load_environment_erra_apontando_o_worktree(tmp_path):
    with pytest.raises(dump_artifact.DumpError, match="--env-file"):
        dump_artifact.load_environment(tmp_path / "nao-existe.env", None)


def test_connect_read_only_recusa_escrita(tmp_path):
    db_file = tmp_path / "t.db"
    sqlite3.connect(db_file).execute("create table t (x int)")
    conn = dump_artifact.connect_read_only(db_file)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("insert into t values (1)")


def test_connect_read_only_erra_com_db_ausente(tmp_path):
    with pytest.raises(dump_artifact.DumpError, match="--db"):
        dump_artifact.connect_read_only(tmp_path / "nao-existe.db")

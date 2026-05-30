"""Restore drill — prova de mecanismo do ciclo dump→restore (A21.l9)."""

# NÃO é o drill real de DR (snapshot R2 → host prod-like, RTO/RPO medidos —
# gate G1 de ADR-228, pós-cutover). Aqui provamos, com dado sintético
# zero-PII, que o MECANISMO de restore não regride silenciosamente:
#   1. manifesto pré (source) — row-count + sha256 por tabela-chave;
#   2. `pg_dump -Fc` → `CREATE DATABASE` separado → `pg_restore --exit-on-error`;
#   3. manifesto pós + asserts: row-count/sha256 idênticos, alembic_version
#      preservado, round-trip Fernet do vault, e tempo de restore < 60s (sanity).
# Requer Postgres + MATHOMS_FERNET_KEY no env. Driver: psycopg v3.
# Runbook: docs/reference/runbooks/disaster_recovery.md.

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dev.drill_seed import DRILL_SECRET_LABEL, DRILL_SECRET_PLAINTEXT  # noqa: E402

# Ordem de FK; manifesto cobre as tabelas-chave do tenancy + run + vault.
_KEY_TABLES = (
    "users",
    "workspaces",
    "workspace_members",
    "pipeline_runs",
    "pipeline_artifacts",
    "password_vault",
)
_RESTORE_TIME_SANITY_S = 60.0


def _libpq(url: str, dbname: str | None = None) -> str:
    """Normaliza URL SQLAlchemy → conninfo libpq; troca o dbname se dado."""
    for suffix in ("+asyncpg", "+psycopg", "+psycopg2", "+aiosqlite"):
        url = url.replace(suffix, "")
    parts = urlsplit(url)
    if dbname is not None:
        parts = parts._replace(path=f"/{dbname}")
    return urlunsplit(parts)


def _table_digest(conninfo: str, table: str) -> tuple[int, str]:
    with psycopg.connect(conninfo) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table} ORDER BY id")
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
    digest = hashlib.sha256()
    for row in rows:
        record = dict(zip(cols, row))
        digest.update(json.dumps(record, sort_keys=True, default=str, ensure_ascii=False).encode())
    return len(rows), digest.hexdigest()


def _manifest(conninfo: str) -> dict[str, tuple[int, str]]:
    return {table: _table_digest(conninfo, table) for table in _KEY_TABLES}


def _alembic_version(conninfo: str) -> str:
    with psycopg.connect(conninfo) as conn, conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        return cur.fetchone()[0]


def _fernet_roundtrip(conninfo: str) -> str | None:
    with psycopg.connect(conninfo) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT encrypted_password FROM password_vault WHERE label = %s",
            (DRILL_SECRET_LABEL,),
        )
        ciphertext = cur.fetchone()[0]
    from backend.app.services.vault import get_vault

    return get_vault().decrypt(ciphertext)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FALHA: {' '.join(cmd[:2])} (rc={result.returncode})")
        print(result.stderr.strip())
        sys.exit(1)


def _recreate_db(maintenance: str, dbname: str) -> None:
    with psycopg.connect(maintenance, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        cur.execute(f'CREATE DATABASE "{dbname}"')


def _dump_and_restore(source: str, maintenance: str, restore: str, restore_db: str) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        dump_path = str(Path(tmp) / "drill.dump")
        _run(["pg_dump", "-Fc", "-d", source, "-f", dump_path])
        _recreate_db(maintenance, restore_db)
        started = time.monotonic()
        restore_cmd = ["pg_restore", "--exit-on-error", "--no-owner", "--no-privileges"]
        _run([*restore_cmd, "-d", restore, dump_path])
        return time.monotonic() - started


def _collect_failures(pre, post, src_version, rst_version, decrypted, secs) -> list[str]:
    failures: list[str] = []
    for table in _KEY_TABLES:
        if pre[table] != post[table]:
            failures.append(f"{table}: pré={pre[table]} ≠ pós={post[table]} (row-count/sha256)")
    if src_version != rst_version:
        failures.append(f"alembic_version: {src_version} ≠ {rst_version} (schema drift)")
    if decrypted != DRILL_SECRET_PLAINTEXT:
        failures.append("Fernet round-trip falhou: segredo restaurado não decifra no original")
    if secs >= _RESTORE_TIME_SANITY_S:
        failures.append(f"restore {secs:.1f}s ≥ {_RESTORE_TIME_SANITY_S:.0f}s (sanity)")
    return failures


def _report_ok(post, rst_version: str, secs: float) -> None:
    total = sum(count for count, _ in post.values())
    print("RESTORE DRILL: OK")
    print(f"  ✓ {len(_KEY_TABLES)} tabelas, {total} linhas — manifesto pré == pós")
    print(f"  ✓ alembic_version preservado: {rst_version}")
    print("  ✓ round-trip Fernet do vault: decifrou para o plaintext esperado")
    print(f"  ✓ restore em {secs:.2f}s (< {_RESTORE_TIME_SANITY_S:.0f}s sanity)")


def drill(source_dsn: str, restore_db: str) -> None:
    source = _libpq(source_dsn)
    restore = _libpq(source_dsn, restore_db)
    pre = _manifest(source)
    src_version = _alembic_version(source)
    secs = _dump_and_restore(source, _libpq(source_dsn, "postgres"), restore, restore_db)
    post = _manifest(restore)
    rst_version = _alembic_version(restore)
    failures = _collect_failures(
        pre, post, src_version, rst_version, _fernet_roundtrip(restore), secs
    )
    if failures:
        print("RESTORE DRILL: FALHOU")
        for line in failures:
            print(f"  ✗ {line}")
        sys.exit(1)
    _report_ok(post, rst_version, secs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore drill — prova de mecanismo dump→restore")
    parser.add_argument("--source-dsn", required=True, help="DSN do DB de origem (com seed)")
    parser.add_argument("--restore-db", default="fin_restore", help="DB de restore (recriado)")
    args = parser.parse_args()
    drill(args.source_dsn, args.restore_db)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Dump READ-ONLY de `pipeline_artifacts` decriptado ([[ADR-231]]), mascarado por default.

Entrypoint nomeado para medição sobre run real. As auditorias existentes
(`audit_member_identity_drift.py`, `audit_patrimonio_ano_base_divergence.py`)
decriptam para responder **uma** pergunta fixa; esta responde "o que o stage X
gravou no run Y", que é o insumo de ataque/closeout de lane.

`mask_text` (importada de `certify_parse_local`, fonte única) apaga CPF, valor
monetário e sequência numérica longa. `--raw` desliga a máscara e é o ato
consciente do operador — o default nunca imprime dinheiro real.

Uso:
    python3 dev/dump_artifact.py --run 33514dc4                    # stages do run
    python3 dev/dump_artifact.py --run 33514dc4 --stage analyze_finances
    python3 dev/dump_artifact.py --run 33514dc4 --stage E1.5c --key baseline_patrimonial
    python3 dev/dump_artifact.py --run 33514dc4 --stage E5 --path patrimonio.investimentos_conjuge --raw

Worktree não tem `.env` nem `mathoms.db` — aponte para o checkout principal:
    python3 dev/dump_artifact.py --env-file ../../.env --db ../../mathoms.db --run 33514dc4
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


class DumpError(RuntimeError):
    """Falha esperada de CLI — vira mensagem, não traceback."""


# =============================================================================
# Ambiente (antes de qualquer import de backend — settings lê env no import)
# =============================================================================


def load_environment(env_file: Path | None, db_path: Path | None) -> None:
    """Carrega `.env` e fixa o DB alvo. Precede o import de `backend.*`."""
    resolved = env_file or (REPO_ROOT / ".env")
    if not resolved.is_file():
        raise DumpError(
            f"`.env` não encontrado em {resolved}. Worktree não herda o do checkout "
            "principal — passe --env-file <caminho>."
        )
    from dotenv import load_dotenv

    load_dotenv(resolved, override=False)
    if db_path is not None:
        os.environ["MATHOMS_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.resolve()}"


def resolve_db_file(db_path: Path | None) -> Path:
    """Caminho do sqlite a abrir em `mode=ro`, do argumento ou de `MATHOMS_DATABASE_URL`."""
    if db_path is not None:
        return db_path.resolve()
    url = os.environ.get("MATHOMS_DATABASE_URL", "")
    if "sqlite" in url:
        return Path(url.split("///")[-1]).resolve()
    return (REPO_ROOT / "mathoms.db").resolve()


def connect_read_only(db_file: Path) -> sqlite3.Connection:
    """Conexão sqlite `mode=ro` — a garantia de read-only é do driver, não da disciplina."""
    if not db_file.is_file():
        raise DumpError(f"DB não encontrado em {db_file}. Passe --db <caminho>.")
    return sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)


# =============================================================================
# Leitura
# =============================================================================


def resolve_run_id(conn: sqlite3.Connection, prefix: str) -> str:
    """Expande prefixo de run para o id completo; erro se ambíguo ou ausente."""
    rows = conn.execute(
        "select id from pipeline_runs where id like ? order by started_at desc", (f"{prefix}%",)
    ).fetchall()
    if not rows:
        raise DumpError(f"nenhum run casa com `{prefix}`.")
    if len(rows) > 1:
        found = ", ".join(r[0][:12] for r in rows[:5])
        raise DumpError(f"prefixo `{prefix}` é ambíguo ({len(rows)} runs): {found}…")
    return str(rows[0][0])


def list_stages(conn: sqlite3.Connection, run_id: str) -> list[tuple[str, str, str]]:
    """`(stage, artifact_key, created_at)` do run, ordenado por stage."""
    return [
        (str(s), str(k), str(c))
        for s, k, c in conn.execute(
            "select stage, artifact_key, created_at from pipeline_artifacts "
            "where pipeline_run_id=? order by stage, artifact_key",
            (run_id,),
        ).fetchall()
    ]


def read_payload(conn: sqlite3.Connection, run_id: str, stage: str, key: str | None) -> Any:
    """Payload decriptado do artefato mais recente de `(run, stage[, key])`."""
    from pipeline.stage_spec import STAGE_RENAME_MAP

    candidates = [stage, STAGE_RENAME_MAP.get(stage, "")]
    candidates += [legacy for legacy, desc in STAGE_RENAME_MAP.items() if desc == stage]
    sql = (
        "select content_json from pipeline_artifacts where pipeline_run_id=? "
        f"and stage in ({','.join('?' * len(candidates))})"
    )
    params: list[str] = [run_id, *candidates]
    if key:
        sql += " and artifact_key=?"
        params.append(key)
    row = conn.execute(sql + " order by created_at desc limit 1", params).fetchone()
    if row is None:
        raise DumpError(f"nenhum artefato para stage=`{stage}` key=`{key or '*'}` no run.")
    return decrypt(row[0])


def decrypt(content_json: Any) -> Any:
    """Sentinel [[ADR-231]] → payload de domínio; idempotente em plaintext."""
    from backend.app.services.security.crypto import read_artifact_content

    payload = json.loads(content_json) if isinstance(content_json, (str, bytes)) else content_json
    return read_artifact_content(payload)


def _descend(cursor: Any, segment: str, dot_path: str) -> Any:
    """Um passo do dot-path: índice de lista ou chave de dict."""
    if isinstance(cursor, list) and segment.isdigit():
        return cursor[int(segment)]
    if isinstance(cursor, dict) and segment in cursor:
        return cursor[segment]
    raise DumpError(f"segmento `{segment}` não existe em `{dot_path}`.")


def select_path(payload: Any, dot_path: str) -> Any:
    """Recorta `a.b.0.c` do payload; erro nomeando o segmento que não existe."""
    cursor = payload
    for segment in dot_path.split("."):
        cursor = _descend(cursor, segment, dot_path)
    return cursor


# =============================================================================
# Saída
# =============================================================================


def render(payload: Any, *, raw: bool) -> str:
    """JSON válido com `--raw`; texto mascarado (CPF/valor/número longo) por default."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if raw:
        return text
    return _mask_text()(text)


def _mask_text():
    """`mask_text` do harness certificado — fonte única da máscara PII."""
    try:
        from certify_parse_local import mask_text
    except ModuleNotFoundError:  # pragma: no cover
        from dev.certify_parse_local import mask_text
    return mask_text


def render_stage_list(rows: list[tuple[str, str, str]]) -> str:
    """Inventário `stage · artifact_key · created_at` — nomes de chave não são PII."""
    if not rows:
        return "run sem artefatos."
    width = max(len(stage) for stage, _, _ in rows)
    lines = [f"{stage:<{width}}  {key:<44}  {created}" for stage, key, created in rows]
    return "\n".join([f"{len(rows)} artefatos:", *lines])


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run", required=True, help="id do run (prefixo basta)")
    parser.add_argument("--stage", help="stage legacy ou descritivo; omitido → lista o run")
    parser.add_argument("--key", help="artifact_key; omitido → o mais recente do stage")
    parser.add_argument("--path", help="recorte dot-path do payload (ex.: patrimonio.bruto)")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="desliga a máscara PII e imprime JSON válido (ato consciente)",
    )
    parser.add_argument("--env-file", type=Path, help="`.env` alternativo (worktree)")
    parser.add_argument("--db", type=Path, help="sqlite alternativo (worktree)")
    return parser


def run(args: argparse.Namespace) -> str:
    """Resolve run, lê e formata. Toda falha esperada sobe como `DumpError`."""
    load_environment(args.env_file, args.db)
    conn = connect_read_only(resolve_db_file(args.db))
    run_id = resolve_run_id(conn, args.run)
    if not args.stage:
        return render_stage_list(list_stages(conn, run_id))
    payload = read_payload(conn, run_id, args.stage, args.key)
    if args.path:
        payload = select_path(payload, args.path)
    return render(payload, raw=args.raw)


def main() -> int:
    # Payload de E5 tem MBs; `| head` fecha o pipe e o default do Python vira
    # traceback com o texto já entregue. SIG_DFL faz o processo morrer calado.
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = build_parser().parse_args()
    try:
        print(run(args))
    except DumpError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:  # pragma: no cover
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

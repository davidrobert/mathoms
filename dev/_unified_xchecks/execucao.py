"""X5 — proveniencia declarada: stage `completed` sem artefato do run."""

from __future__ import annotations

from dev._unified_xchecks.base import _db, veredito


def _consulta(ws: str, run: str) -> tuple:
    text, SyncSessionLocal, _r, _d, _l = _db()
    logs_sql = (
        "SELECT stage, status FROM pipeline_stage_logs "
        "WHERE pipeline_run_id=:r ORDER BY started_at"
    )
    art_sql = (
        "SELECT stage, COUNT(*) FROM pipeline_artifacts "
        "WHERE workspace_id=:w AND pipeline_run_id=:r GROUP BY stage"
    )
    outros_sql = (
        "SELECT COUNT(*), COUNT(DISTINCT pipeline_run_id) FROM pipeline_artifacts "
        "WHERE workspace_id=:w AND pipeline_run_id IS NOT NULL AND pipeline_run_id<>:r"
    )
    with SyncSessionLocal() as s:
        logs = s.execute(text(logs_sql), {"r": run}).fetchall()
        rows = s.execute(text(art_sql), {"w": ws, "r": run}).fetchall()
        outros = s.execute(text(outros_sql), {"w": ws, "r": run}).first()
    return logs, rows, outros


def _por_stage(rows: list) -> dict[str, int]:
    from pipeline.stage_spec import resolve_stage_name

    acc: dict[str, int] = {}
    for st, n in rows:
        canon = resolve_stage_name(st)
        acc[canon] = acc.get(canon, 0) + n
    return acc


def _linha(stage: str, status: str, por_stage: dict) -> tuple:
    """(canon, n, writes, e_ofensor) — `writes` vem do StageSpec, nao da prosa."""
    from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

    canon = resolve_stage_name(stage)
    n = por_stage.get(canon, 0)
    spec = STAGE_REGISTRY.get(canon) or STAGE_REGISTRY.get(stage)
    writes = tuple(getattr(spec, "writes", ()) or ()) if spec else ()
    return canon, n, writes, status == "completed" and n == 0


def _tabela(logs: list, por_stage: dict) -> list[tuple]:
    print("| stage | status log | artefatos deste run | StageSpec.writes |")
    print("|---|---|---|---|")
    ofensores = []
    for stage, status in logs:
        canon, n, writes, e_ofensor = _linha(stage, status, por_stage)
        if e_ofensor:
            ofensores.append((canon, writes))
        print(f"| {canon} | {status}{' ⚠️' if e_ofensor else ''} | {n} | {list(writes)} |")
    return ofensores


def _veredito_ofensores(ofensores: list) -> None:
    print(f"\n**X5 ofensores (completed + 0 artefatos): {len(ofensores)}**")
    for canon, writes in ofensores:
        v = "DECLARA writes ⇒ contrato falso (PV9-30)" if writes else "writes=∅ ⇒ legitimo"
        print(f"- `{canon}` — {v}")


def x5(ws: str, run: str) -> None:
    logs, rows, outros = _consulta(ws, run)
    por_stage = _por_stage(rows)
    print(f"## X5 — stage `completed` sem artefato do run  (run {run[:8]})")
    print(f"stages logados: {len(logs)} · stages com artefato deste run: {len(por_stage)}\n")
    ofensores = _tabela(logs, por_stage)
    _veredito_ofensores(ofensores)
    print(
        f"\nartefatos do workspace de OUTROS runs: {outros[0]} em {outros[1]} runs "
        f"(substrato workspace-latest pode alcanca-los — ver PV9-01)"
    )
    veredito(
        "X5",
        len(logs),
        len(logs),
        len([o for o in ofensores if o[1]]),
        nota="ofensor = completed + 0 artefatos + writes declarados",
    )

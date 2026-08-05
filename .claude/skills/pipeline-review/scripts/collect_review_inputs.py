"""Coleta os insumos da revisão de um report em ``<out_dir>/`` (Passo 1, pós-run).

Escreve, fiel ao que a UI consome (sem HTTP/auth):
- ``report_data.json``  — view-model E5 (``get_report_data``: 35+ chaves + lineage)
- ``parecer.json``      — parecer_planejador decriptado
- ``cross_validation.json`` — os checks CV (conservação/consistência) com mensagens
- ``run_meta.md``       — status/duração, needs_review por tipo, telemetria LLM (2 tabelas)
- ``review_snapshot.json`` — snapshot PII-safe p/ ``dev/compare_reviews.py`` (ADR-343)

Rode da RAIZ do repo (carrega ``.env`` + Fernet):
``.venv/bin/python .claude/skills/pipeline-review/scripts/collect_review_inputs.py <ws_id> <report_id> <out_dir>``
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import text

from backend.app.application.report.get_report_data import get_report_data
from backend.app.core.database import async_session
from backend.app.services.security.crypto import read_artifact_content
from dev.build_info import ancestry, commits_ahead_of
from dev.compare_reviews import build_snapshot, elapsed_minutes
from dev.run_scope import mixed_execution, revisions_in, scope_sentence
from scripts.validate_cross import run_cross_validation


async def _dump_report_data(db, ws: str, report_id: str, out: Path) -> list[str]:
    resp = await get_report_data(ws, report_id, db=db)
    data = json.loads(resp.body)
    (out / "report_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


async def _dump_parecer(db, ws: str, run_id: str | None, out: Path) -> dict | None:
    """Parecer deste run, nunca o último do workspace."""
    # Sem o filtro por pipeline_run_id, run que não produziu parecer (free tier,
    # skip_llm, falha do stage) carregava silenciosamente o parecer de um run
    # anterior: o snapshot dizia `status: ok` e o --compare media run A vs run B.
    row = (
        await db.execute(
            text(
                "SELECT content_json FROM pipeline_artifacts WHERE workspace_id = :ws "
                "AND pipeline_run_id = :run "
                "AND stage IN ('review_finances_holistic','E6-parecer') ORDER BY id DESC LIMIT 1"
            ),
            {"ws": ws, "run": run_id},
        )
    ).first()
    if row is None:
        return None
    raw = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    content = read_artifact_content(raw)
    (out / "parecer.json").write_text(json.dumps(content, ensure_ascii=False, indent=2))
    return content if isinstance(content, dict) else {"_raw": content}


def _dump_cross_validation(data: dict, out: Path) -> list[dict]:
    results = [
        {
            "check_id": r.check_id,
            "name": r.name,
            "severity": r.severity,
            "passed": r.passed,
            "details": r.details,
        }
        for r in run_cross_validation(data)
    ]
    (out / "cross_validation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    return results


async def _rows(db, sql: str, params: dict) -> list[dict]:
    return [dict(m) for m in (await db.execute(text(sql), params)).mappings().all()]


async def _fetch_run_meta(
    db, ws: str, run_id: str
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    run = await _rows(
        db,
        "SELECT status, tier_at_run, total_documents, failed_at_stage, started_at, "
        "completed_at, base_run_id, incremental FROM pipeline_runs WHERE id = :r",
        {"r": run_id},
    )
    if run:
        run[0]["minutes"] = elapsed_minutes(run[0].get("started_at"), run[0].get("completed_at"))
    nr = await _rows(
        db,
        "SELECT doc_type, COUNT(*) AS n FROM documents WHERE workspace_id = :ws "
        "AND needs_review IS TRUE GROUP BY doc_type",
        {"ws": ws},
    )
    costs = await _rows(
        db,
        "SELECT stage, model_id, tokens_in, tokens_out, cost_usd_cents, latency_ms, "
        "tool_iterations FROM pipeline_run_costs WHERE pipeline_run_id = :r",
        {"r": run_id},
    )
    calls = await _rows(
        db,
        "SELECT stage, model_name, ROUND(cost_usd,4) AS usd, duration_ms FROM llm_call_log "
        "WHERE pipeline_run_id = :r",
        {"r": run_id},
    )
    return (run[0] if run else {}), nr, costs, calls


async def _fetch_stage_logs(db, run_id: str) -> list[dict]:
    """Stage logs com a revisão do executor — a fonte da frase de escopo (ADR-362)."""
    return await _rows(
        db,
        "SELECT stage, status, executor_revision, started_at FROM pipeline_stage_logs "
        "WHERE pipeline_run_id = :r ORDER BY started_at",
        {"r": run_id},
    )


_UNKNOWN_EXECUTOR = (
    "- executor: **desconhecido** — nenhum stage declarou revisão "
    "(processo subiu sem MATHOMS_BUILD_SHA)"
)
_MIXED_EXECUTION = (
    "- ⚠️ **execução mista**: o run atravessou mais de uma revisão — "
    "stages diferentes rodaram códigos diferentes"
)
_NO_REPRODUCIBILITY = (
    "- reprodutibilidade: **NÃO garantida**. Mesmo executor pode produzir output "
    "diferente — o parecer roda com temperature 0,1 e cache de 7 dias; câmbio, "
    "parâmetros fiscais e regras de categorização vivem em DB e mudam sem commit."
)


def _executor_line(revs: list[str]) -> str:
    if not revs:
        return _UNKNOWN_EXECUTOR
    return f"- executor: `{revs[0] if len(revs) == 1 else ', '.join(revs)}`"


def _ancestry_line(revs: list[str]) -> str:
    """Responde "a main andou desde o run?" — ausência nunca colapsa em zero."""
    rev = revs[0] if revs else None
    ahead = commits_ahead_of(rev) if rev else None
    sufixo = f" ({ahead} commit(s) à frente)" if ahead else ""
    return f"- relação com o HEAD atual: **{ancestry(rev)}**{sufixo}"


def _provenance_lines(run: dict, stage_rows: list[dict]) -> list[str]:
    """Bloco de proveniência do `run_meta.md` — em prosa, não `repr()` de dict."""
    revs = revisions_in(stage_rows)
    escopo = scope_sentence(
        incremental=run.get("incremental"),
        base_run_id=run.get("base_run_id"),
        stage_rows=stage_rows,
    )
    lines = [_executor_line(revs), f"- {escopo}", _ancestry_line(revs)]
    if mixed_execution(stage_rows):
        lines.append(_MIXED_EXECUTION)
    return lines + [_NO_REPRODUCIBILITY]


def _provenance_context(run: dict, stage_rows: list[dict]) -> dict:
    """Contexto top-level do snapshot — nunca supressor, nunca perna de regressão."""
    revs = revisions_in(stage_rows)
    return {
        "executor_revision": revs[0] if len(revs) == 1 else None,
        "executor_revisions": revs,
        "execucao_mista": mixed_execution(stage_rows),
        "ancestry": ancestry(revs[0] if revs else None),
        "commits_ahead": commits_ahead_of(revs[0]) if revs else None,
        "escopo": {
            "base_run_id": run.get("base_run_id"),
            "incremental": bool(run.get("incremental")),
            "stages_terminais": len({r.get("stage") for r in stage_rows if r.get("stage")}),
        },
    }


def _write_run_meta(
    run_id: str,
    run: dict,
    nr: list[dict],
    cv: list[dict],
    costs: list[dict],
    calls: list[dict],
    out: Path,
    stage_rows: list[dict] | None = None,
) -> None:
    lines = [
        f"# Run meta — report {out.name}",
        f"- run: `{run_id}` · status {run.get('status', '?')} · {run.get('minutes', '?')} min",
        *_provenance_lines(run, stage_rows or []),
        *_telemetry_lines(nr, cv, costs, calls),
    ]
    (out / "run_meta.md").write_text("\n".join(str(x) for x in lines) + "\n")


def _telemetry_lines(
    nr: list[dict], cv: list[dict], costs: list[dict], calls: list[dict]
) -> list[str]:
    fail = [c for c in cv if not c["passed"]]
    return [
        f"- needs_review por tipo: {nr}",
        f"- CV: {len(cv) - len(fail)}/{len(cv)} OK; "
        f"falhas: {[c['check_id'] + ':' + c['details'] for c in fail]}",
        f"- pipeline_run_costs ({len(costs)}): {costs}",
        f"- llm_call_log neste run ({len(calls)}): {calls}",
    ]


async def main() -> None:
    ws, report_id, out_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)
    async with async_session() as db:
        data = await _dump_report_data(db, ws, report_id, out_dir)
        run_id = (
            await db.execute(
                text("SELECT pipeline_run_id FROM reports WHERE id = :r"), {"r": report_id}
            )
        ).scalar()
        parecer = await _dump_parecer(db, ws, run_id, out_dir)
        cv = _dump_cross_validation(data, out_dir)
        run, nr, costs, calls = await _fetch_run_meta(db, ws, run_id)
        stage_rows = await _fetch_stage_logs(db, run_id)
    _write_run_meta(run_id, run, nr, cv, costs, calls, out_dir, stage_rows)
    meta = {"run": run, "needs_review": nr, "costs": costs, "calls": calls}
    snapshot = build_snapshot(
        run_id=str(run_id),
        report_data=data,
        cv_results=cv,
        meta=meta,
        parecer=parecer,
        provenance=_provenance_context(run, stage_rows),
    )
    (out_dir / "review_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2)
    )
    fails = [c["check_id"] for c in cv if not c["passed"]]
    hit = bool((parecer or {}).get("_meta", {}).get("cache_hit")) if parecer else False
    estado = f"ok{' (CACHE HIT)' if hit else ''}" if parecer else "ausente-neste-run"
    print(
        f"OK report_data({len(data)} chaves) parecer={estado} "
        f"CV_falhas={fails} snapshot=review_snapshot.json → {out_dir}"
    )


if __name__ == "__main__":
    asyncio.run(main())

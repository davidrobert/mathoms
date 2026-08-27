"""Resolve uma pausa (`needs_review`) PELA ROTA — conferir e retomar, ou descartar.

Existe porque a A40.l84 fechou a retomada sem decisão registrada: `resume_pipeline_run`
recusa com qualquer `StageReview` sem decisão, em toda entrada. Fechar sem dar a saída
troca um defeito por outro — o operador contorna forjando a decisão no DB, que mente pior:
pula a guarda de run terminal, pula o conflito de review já processada, e some da
telemetria `review_action` (KR1 da A29.l1) que distingue aprovação cega de resolução
construtiva.

Tudo passa pelo `httpx.ASGITransport` contra o app real: mesma autorização, mesmas guardas,
mesma telemetria. Nunca ORM, nunca `UPDATE`.

Rode da RAIZ do repo (carrega ``.env``)::

    .venv/bin/python .claude/skills/pipeline-review/scripts/resolve_pause.py <ws> --list
    .venv/bin/python .claude/skills/pipeline-review/scripts/resolve_pause.py <ws> --approve <id>
    .venv/bin/python .claude/skills/pipeline-review/scripts/resolve_pause.py <ws> --resume
    .venv/bin/python .claude/skills/pipeline-review/scripts/resolve_pause.py <ws> --cancel --reason "..."
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import text

from backend.app.core.database import SyncSessionLocal

_PAUSA = "needs_review"


def _resolve(db, workspace: str) -> dict:
    """Workspace + dono + run pausado. Falha alto: id errado é erro de operador."""
    coluna = "u.email" if "@" in workspace else "w.id"
    row = db.execute(
        text(
            f"SELECT w.id, u.id, u.token_version FROM workspaces w JOIN users u ON u.id = w.owner_id "  # noqa: S608
            f"WHERE {coluna} = :v ORDER BY w.created_at LIMIT 1"
        ),
        {"v": workspace},
    ).first()
    if row is None:
        raise SystemExit(f"workspace {workspace!r} não existe")
    run = (
        db.execute(
            text(
                "SELECT id, paused_at_stage, started_at FROM pipeline_runs "
                "WHERE workspace_id = :w AND status = :s ORDER BY started_at DESC LIMIT 1"
            ),
            {"w": row[0], "s": _PAUSA},
        )
        .mappings()
        .first()
    )
    return {"ws": row[0], "owner": row[1], "tv": row[2] or 0, "run": dict(run) if run else None}


def _custo_em_centavos(db, run_id: str) -> int:
    """Centavos int, nunca float — a coluna é `cost_usd_cents` justamente por isso."""
    valor = db.execute(
        text("SELECT SUM(cost_usd_cents) FROM pipeline_run_costs WHERE pipeline_run_id = :r"),
        {"r": run_id},
    ).scalar()
    return int(valor or 0)


def _token(owner_id: str, token_version: int) -> str:
    """60s, igual a `capture_report_render`. `token_version` omitido = 401 na v0."""
    from backend.app.core.security import create_access_token

    return create_access_token(
        owner_id, expires_delta=timedelta(minutes=1), token_version=token_version
    )


async def _chamar(metodo: str, caminho: str, token: str, corpo: dict | None = None) -> dict:
    import httpx

    from backend.app.main import app

    # `raise_app_exceptions=False`: o operador tem de ver o MESMO 500 que a UI vê, não
    # um traceback do harness. Medido: falha de dispatch no resume sobe
    # `PipelineDispatchError` (RuntimeError), que `resume_run` não traduz.
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://local") as client:
        resp = await client.request(
            metodo, caminho, headers={"Authorization": f"Bearer {token}"}, json=corpo
        )
    return {"status": resp.status_code, "body": _corpo(resp)}


def _corpo(resp) -> object:
    """500 responde `Internal Server Error` em texto puro — `resp.json()` estoura nele."""
    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return resp.text[:500]


def _exigir_pausa(ctx: dict) -> dict:
    if ctx["run"] is None:
        raise SystemExit(f"nenhum run em `{_PAUSA}` neste workspace — nada a resolver")
    return ctx["run"]


def _imprimir(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


async def _listar(ctx: dict, token: str) -> int:
    run = _exigir_pausa(ctx)
    rota = f"/api/workspaces/{ctx['ws']}/pipeline/runs/{run['id']}/reviews"
    r = await _chamar("GET", rota, token)
    # A rota respondendo != 200 é diagnóstico, não crash: indexar o corpo às cegas dava
    # `TypeError: string indices` e escondia o 403/401 que o operador precisa ler.
    if r["status"] != 200:
        _imprimir(r)
        return 1
    pendentes = [x for x in r["body"] if x["status"] == "pending"]
    print(
        json.dumps(
            {
                "run_id": run["id"],
                "paused_at_stage": run["paused_at_stage"],
                "pendentes": [
                    {
                        "review_id": x["id"],
                        "stage": x["stage"],
                        "erros": x.get("validation_errors"),
                        "issues": x.get("validation_issues"),
                    }
                    for x in pendentes
                ],
                "saidas": {
                    "conferir_e_retomar": "--approve <review_id> (cada uma) e depois --resume",
                    "descartar": '--cancel --reason "<por quê>"',
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0


async def _decidir(ctx: dict, token: str, review_id: str, corpo: dict) -> int:
    run = _exigir_pausa(ctx)
    caminho = f"/api/workspaces/{ctx['ws']}/pipeline/runs/{run['id']}/reviews/{review_id}"
    r = await _chamar("POST", caminho, token, corpo)
    _imprimir(r)
    return 0 if r["status"] < 400 else 1


async def _retomar(ctx: dict, token: str) -> int:
    run = _exigir_pausa(ctx)
    r = await _chamar(
        "POST", f"/api/workspaces/{ctx['ws']}/pipeline/runs/{run['id']}/resume", token
    )
    _imprimir(r)
    return 0 if r["status"] < 400 else 1


async def _descartar(ctx: dict, token: str, motivo: str, centavos: int) -> int:
    run = _exigir_pausa(ctx)
    # O custo aparece ANTES do ato: descartar joga fora trabalho pago, e a assimetria
    # entre "aprovar às cegas" e "descartar" só é decidível com o número na frente.
    gasto = Decimal(centavos) / 100
    print(
        f"descartando run {run['id'][:8]} (pausa em {run['paused_at_stage']}, "
        f"US$ {gasto} já gastos) — motivo: {motivo}",
        file=sys.stderr,
    )
    r = await _chamar(
        "POST", f"/api/workspaces/{ctx['ws']}/pipeline/runs/{run['id']}/cancel", token
    )
    _imprimir(r)
    return 0 if r["status"] < 400 else 1


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("workspace", help="email do dono OU uuid do workspace")
    # Sem `--approve-all` de propósito: aprovar em massa sem ler os `validation_issues` é
    # aprovação cega, e quem não vai conferir tem `--cancel`. O id só sai do `--list`.
    g = p.add_mutually_exclusive_group()
    g.add_argument("--list", action="store_true", help="conferências pendentes (default)")
    g.add_argument("--approve", metavar="REVIEW_ID")
    g.add_argument("--edit", metavar="REVIEW_ID")
    g.add_argument("--resume", action="store_true", help="retoma do stage SEGUINTE ao pausado")
    g.add_argument("--cancel", action="store_true", help="descarta o run (irreversível)")
    p.add_argument("--payload", type=Path, help="JSON do output editado (com --edit)")
    p.add_argument("--reason", help="por que descartar (obrigatório com --cancel)")
    return p


def main() -> int:
    args = _parser().parse_args()
    if args.cancel and not args.reason:
        raise SystemExit("--cancel exige --reason: descarte sem motivo registrado é o contorno")
    if args.edit and not args.payload:
        raise SystemExit("--edit exige --payload <arquivo.json>")

    with SyncSessionLocal() as db:
        ctx = _resolve(db, args.workspace)
        centavos = _custo_em_centavos(db, ctx["run"]["id"]) if ctx["run"] else 0
    token = _token(ctx["owner"], ctx["tv"])

    if args.approve:
        return asyncio.run(_decidir(ctx, token, args.approve, {"action": "approve"}))
    if args.edit:
        corpo = {"action": "edit", "edited_output_json": json.loads(args.payload.read_text())}
        return asyncio.run(_decidir(ctx, token, args.edit, corpo))
    if args.resume:
        return asyncio.run(_retomar(ctx, token))
    if args.cancel:
        return asyncio.run(_descartar(ctx, token, args.reason, centavos))
    return asyncio.run(_listar(ctx, token))


if __name__ == "__main__":
    raise SystemExit(main())

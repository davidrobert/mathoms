#!/usr/bin/env python3
"""Captura as superfícies RENDERIZADAS de um relatório real, para a skill `report-review`.

Irmão de ``collect_review_inputs.py``: aquele coleta os **dados**, este coleta as
**superfícies**. Fecha o débito de método da rodada r3 ("ninguém renderizou tela nem
PDF" — toda afirmação de clareza/UX era inferência de código).

Complementar, **não** substituto, do E2E: `frontend/tests/e2e/` renderiza fixtures
sintéticas e é onde moram os **gates**. Este harness renderiza **dado real** e é onde
mora a **observação**. Ferramenta de review não emite veredito.

Artefatos (todos texto linearizado ou imagem — nunca dump de HTML, que é o payload
gigante que a própria skill proíbe subagente de ler):

    screen.txt      inner_text da superfície de tela
    print.txt       inner_text da superfície ?print=1
    report.pdf      PDF via a função de PRODUÇÃO (prova o PDF do cliente)
    report.txt      pdftotext -layout do PDF acima
    screen-1280.png / screen-390.png
    anchors.json    para cada a[href^="#"]: {href, found, height} — observação, sem veredito
    console.json    mensagens de console (Authorization scrubado)
    MANIFEST.md     git SHA, report_id, run_id, elapsed por superfície

Uso:
    .venv/bin/python .claude/skills/pipeline-review/scripts/capture_report_render.py \\
        <workspace-email-ou-uuid> [--report-id <id>] [--out <dir>]

Requisitos: frontend de pé, playwright + chromium, pdftotext (poppler).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT))

# Superfícies: (nome, sufixo de query). A tela e o print DIVERGEM por construção —
# `?print=1` ativa `isPrint` no React e o print CSS força `details[open]` em blocos
# que na tela ficam colapsados. Capturar só uma reproduz o ponto cego.
_SURFACES = (("screen", ""), ("print", "?print=1"))

_VIEWPORTS = {"screen": ((1280, 900), (390, 844))}

_BEARER_RE = re.compile(r"Bearer\s+[\w\-.]+", re.IGNORECASE)

# Chave de auth do cliente (`frontend/src/lib/api/core.ts`). O gate da rota lê daqui,
# não do header — ver comentário em `_capture_surface`.
_TOKEN_KEY = "fin_token"


def _assert_local(base_url: str) -> None:
    """Recusa apontar para não-localhost: o risco não é RAM, é competir com PDF real."""
    host = (urlparse(base_url).hostname or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit(f"ABORTADO: base-url deve ser localhost, recebido {host!r}")


def _scrub(text: str) -> str:
    return _BEARER_RE.sub("Bearer <scrubbed>", text)


def _resolve(db, workspace: str) -> dict:
    from sqlalchemy import text as _t

    ws = workspace
    if "@" in workspace:
        row = db.execute(
            _t(
                "SELECT w.id FROM workspaces w JOIN users u ON u.id = w.owner_id WHERE u.email = :e"
            ),
            {"e": workspace},
        ).first()
        if row is None:
            raise SystemExit(f"workspace não encontrado para {workspace!r}")
        ws = row[0]
    owner = db.execute(
        _t(
            "SELECT u.id, u.token_version FROM workspaces w JOIN users u ON u.id = w.owner_id "
            "WHERE w.id = :i"
        ),
        {"i": ws},
    ).first()
    if owner is None:
        raise SystemExit(f"workspace {ws!r} não existe")
    rep = db.execute(
        _t(
            "SELECT id, pipeline_run_id FROM reports WHERE workspace_id = :w "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"w": ws},
    ).first()
    return {
        "workspace_id": ws,
        "owner_id": owner[0],
        "token_version": owner[1] or 0,
        "report_id": rep[0] if rep else None,
        "run_id": rep[1] if rep else None,
    }


def _mint(owner_id: str, token_version: int) -> str:
    """Token novo por superfície (60s, igual à produção) — nunca um de vida longa.

    `token_version` é obrigatório: omiti-lo produz token da versão 0, rejeitado com
    401 por usuário que já invalidou sessões. Foi assim que este harness descobriu
    o mesmo defeito no caminho de produção.
    """
    from backend.app.core.security import create_access_token

    return create_access_token(
        owner_id, expires_delta=timedelta(minutes=1), token_version=token_version
    )


async def _capture_surface(name: str, url: str, token: str, out: Path) -> dict:
    from playwright.async_api import async_playwright

    from backend.app.services.pdf_renderer import REPORT_READY_PREDICATE

    started = time.monotonic()
    console: list[dict] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            # Header sozinho NÃO basta: o gate client-side de `/reports/[id]` lê o
            # token de localStorage e redireciona para /login sem ele. Semear é o
            # que o mock do E2E já faz (`frontend/tests/e2e/helpers/mock-report.ts`).
            await page.add_init_script(f"localStorage.setItem({_TOKEN_KEY!r}, {token!r});")
            await page.set_extra_http_headers({"Authorization": f"Bearer {token}"})
            page.on(
                "console",
                lambda m: console.append({"type": m.type, "text": _scrub(m.text)[:500]}),
            )
            if name == "print":
                # `useIsPrint` lê `window.matchMedia("print")`, NÃO o `?print=1` —
                # sem emular a mídia, esta superfície seria a tela com um query param
                # decorativo, e a captura viraria evidência falsa.
                await page.emulate_media(media="print")
            await page.goto(url, wait_until="networkidle", timeout=60_000)
            await page.wait_for_function(REPORT_READY_PREDICATE, timeout=45_000)
            await page.wait_for_timeout(2000)

            (out / f"{name}.txt").write_text(await page.inner_text("body"))

            if name == "screen":
                for w, h in _VIEWPORTS["screen"]:
                    await page.set_viewport_size({"width": w, "height": h})
                    await page.wait_for_timeout(400)
                    await page.screenshot(path=str(out / f"screen-{w}.png"), full_page=True)
                await page.set_viewport_size({"width": 1280, "height": 900})
                anchors = await page.evaluate(
                    """() => [...document.querySelectorAll('a[href^="#"]')].map(a => {
                        const el = document.getElementById(a.hash.slice(1));
                        return {href: a.hash, found: !!el,
                                height: el ? Math.round(el.getBoundingClientRect().height) : 0};
                    })"""
                )
                (out / "anchors.json").write_text(json.dumps(anchors, ensure_ascii=False, indent=1))
        finally:
            await browser.close()

    (out / f"console-{name}.json").write_text(json.dumps(console, ensure_ascii=False, indent=1))
    return {"surface": name, "elapsed_s": round(time.monotonic() - started, 1)}


async def _capture_pdf(report_url: str, token: str, out: Path) -> dict:
    """PDF pela função de PRODUÇÃO — se não sair dela, não prova nada sobre o do cliente.

    Falha aqui **é o achado mais forte que esta ferramenta pode produzir**: significa
    que o download de PDF do cliente está quebrado. Registra e segue, em vez de
    derrubar a captura.
    """
    from backend.app.services.pdf_renderer import render_pdf

    started = time.monotonic()
    try:
        pdf = await render_pdf(report_url=report_url, bearer_token=token, timeout_ms=60_000)
    except Exception as exc:
        (out / "report-PRODUCAO-FALHOU.txt").write_text(
            f"{type(exc).__name__}: {_scrub(str(exc))[:800]}\n\n"
            "O caminho de produção (render_pdf) não produziu PDF. Reporte como achado.\n"
        )
        return {
            "surface": "pdf",
            "elapsed_s": round(time.monotonic() - started, 1),
            "erro": type(exc).__name__,
        }
    (out / "report.pdf").write_bytes(pdf)
    try:
        subprocess.run(
            ["pdftotext", "-layout", str(out / "report.pdf"), str(out / "report.txt")],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        (out / "report.txt").write_text(f"pdftotext indisponível: {exc}")
    return {"surface": "pdf", "elapsed_s": round(time.monotonic() - started, 1)}


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "desconhecido"


def build_manifest(ctx: dict, timings: list[dict], base_url: str) -> str:
    """Provenance: sem SHA a captura de uma rodada não é citável na seguinte."""
    linhas = [
        "# Captura de render — provenance",
        "",
        f"- git SHA: `{ctx['sha']}`",
        f"- workspace: `{str(ctx['workspace_id'])[:8]}`",
        f"- report: `{str(ctx['report_id'])[:8]}`",
        f"- run: `{str(ctx['run_id'])[:8] if ctx.get('run_id') else '—'}`",
        f"- base-url: `{base_url}`",
        "",
        "| Superfície | Elapsed (s) |",
        "|---|---|",
    ]
    linhas += [f"| {t['surface']} | {t['elapsed_s']} |" for t in timings]
    linhas += [
        "",
        "> Carga lenta é **achado**, não ruído — se uma superfície estourar, reporte.",
        "> Artefatos contêm PII do workspace: off-git, nunca citáveis no MOC.",
    ]
    return "\n".join(linhas) + "\n"


async def _run(args) -> int:
    _assert_local(args.base_url)
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as db:
        ctx = _resolve(db, args.workspace)
    if args.report_id:
        ctx["report_id"] = args.report_id
    if not ctx["report_id"]:
        raise SystemExit("workspace não tem report — nada a capturar")
    ctx["sha"] = _git_sha()

    out = Path(args.out) if args.out else _ROOT / "_scratch" / f"render-{str(ctx['report_id'])[:8]}"
    out.mkdir(parents=True, exist_ok=True)

    base = f"{args.base_url}/reports/{ctx['report_id']}"
    timings = []
    for name, suffix in _SURFACES:
        timings.append(
            await _capture_surface(
                name, base + suffix, _mint(ctx["owner_id"], ctx["token_version"]), out
            )
        )
    timings.append(
        await _capture_pdf(f"{base}?print=1", _mint(ctx["owner_id"], ctx["token_version"]), out)
    )

    (out / "MANIFEST.md").write_text(build_manifest(ctx, timings, args.base_url))
    print(json.dumps({"out": str(out), "timings": timings}, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", help="email ou uuid")
    ap.add_argument("--report-id", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--base-url", default="http://localhost:3000")
    return asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

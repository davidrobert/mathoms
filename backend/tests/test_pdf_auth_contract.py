"""Contrato de auth do PDF server-side — os dois defeitos que quebravam o download.

Ambos foram achados ao construir o harness de captura da skill `report-review`, com
prova vermelho/verde contra o frontend real:

1. `create_access_token` nasce em `token_version=0`. Usuário que já invalidou sessões
   está em versão >= 1, então o token efêmero era rejeitado (401) e o endpoint
   devolvia HTTP 500.
2. O gate client-side de `/reports/[id]` lê o token de `localStorage`, não do header
   `Authorization`. Sem semear, a página redirecionava para `/login` e o
   `wait_for_function` estourava — mesmo com token válido.

O I/O de browser não é mockado (não vale o custo); o que se testa é o **contrato**
que quebra em silêncio.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from backend.app.services import pdf_renderer

_FRONTEND_CORE = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "api" / "core.ts"
)


class _FakeDB:
    async def get(self, *_args: Any) -> None:
        return None


async def _coro(value: Any) -> Any:
    return value


def _patch_download_pdf(monkeypatch) -> dict:
    """Neutraliza I/O do use case e captura os kwargs do token."""
    from backend.app.application.report import download_pdf as mod

    capturado: dict = {}

    def _token(subject: str, expires_delta=None, token_version: int = 0) -> str:
        capturado.update(subject=subject, token_version=token_version)
        return "tok"

    monkeypatch.setattr(mod, "create_access_token", _token)
    monkeypatch.setattr(mod, "render_pdf", lambda **_k: _coro(b"%PDF-1.4"))
    monkeypatch.setattr(mod, "compose_pdf_filename", lambda *_a: "r.pdf")
    monkeypatch.setattr(
        mod,
        "fetch_report",
        lambda *_a, **_k: _coro(type("R", (), {"period": "2026-01", "created_at": None})()),
    )
    return capturado


def test_chave_de_token_bate_com_o_frontend():
    """Se alguém renomear a chave no cliente, o PDF volta a redirecionar para /login."""
    chaves = set(
        re.findall(r'localStorage\.(?:get|set)Item\(\s*"([^"]+)"', _FRONTEND_CORE.read_text())
    )
    assert pdf_renderer._CLIENT_TOKEN_KEY in chaves, (
        f"{pdf_renderer._CLIENT_TOKEN_KEY!r} não é a chave usada em core.ts ({chaves}) — "
        "o PDF server-side vai redirecionar para /login"
    )


def test_predicado_de_prontidao_e_compartilhado():
    """Sentinela duplicado drifta em silêncio e captura página meio-renderizada."""
    assert 'data-report-ready="true"' in pdf_renderer.REPORT_READY_PREDICATE


@pytest.mark.asyncio
async def test_download_pdf_propaga_token_version(monkeypatch):
    """Sem `token_version`, o token é rejeitado por quem já invalidou sessões."""
    from backend.app.application.report import download_pdf as mod

    capturado = _patch_download_pdf(monkeypatch)
    user = type("U", (), {"id": "user-1", "token_version": 7})()

    await mod.download_report_pdf("ws-1", "rep-1", user=user, db=_FakeDB())

    assert capturado["token_version"] == 7, "token_version não propagou → 401 → PDF 500"
    assert capturado["subject"] == "user-1"


@pytest.mark.asyncio
async def test_download_pdf_tolera_token_version_nulo(monkeypatch):
    from backend.app.application.report import download_pdf as mod

    capturado = _patch_download_pdf(monkeypatch)
    user = type("U", (), {"id": "u", "token_version": None})()

    await mod.download_report_pdf("ws", "rep", user=user, db=_FakeDB())

    assert capturado["token_version"] == 0

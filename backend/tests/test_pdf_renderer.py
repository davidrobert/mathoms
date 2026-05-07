# Regression tests para PDF renderer (W1-T04 · BB-009).
#
# Valida o cap de concorrência via asyncio.Semaphore: 5 chamadas
# simultâneas a `render_pdf` nunca devem exceder 2 ativas em paralelo
# (default `MATHOMS_PDF_CONCURRENCY=2`). Sem o cap, 4+ Playwright
# Chromium concorrentes em CX32 (8GB) garantem OOM.
#
# Mocka todo o módulo `playwright.async_api` — o teste roda em CI sem
# Chromium instalado.
"""Regression tests para PDF renderer (W1-T04 · BB-009)."""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any

import pytest

import backend.app.services.pdf_renderer as pdf_renderer


class _ConcurrencyCounter:
    """Counter compartilhado entre fakes para verificar paralelismo real."""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self.calls = 0
        self._lock = asyncio.Lock()

    async def enter(self) -> None:
        async with self._lock:
            self.active += 1
            self.calls += 1
            if self.active > self.peak:
                self.peak = self.active

    async def exit(self) -> None:
        async with self._lock:
            self.active -= 1


def _build_fake_playwright(counter: _ConcurrencyCounter, hold_seconds: float = 0.05) -> Any:
    """Constrói módulo fake `playwright.async_api` — `pdf()` segura
    hold_seconds dentro da seção crítica para forçar overlap real."""

    class _FakePage:
        async def set_extra_http_headers(self, _headers: dict[str, str]) -> None:
            return None

        async def goto(self, _url: str, **_kwargs: Any) -> None:
            return None

        async def wait_for_function(self, _expr: str, **_kwargs: Any) -> None:
            return None

        async def wait_for_timeout(self, _ms: int) -> None:
            return None

        async def pdf(self, **_kwargs: Any) -> bytes:
            await counter.enter()
            try:
                # hold dentro da seção crítica — semaphore deve impedir >2 simultâneos
                await asyncio.sleep(hold_seconds)
                return b"%PDF-1.4 fake"
            finally:
                await counter.exit()

    class _FakeBrowser:
        async def new_page(self) -> _FakePage:
            return _FakePage()

        async def close(self) -> None:
            return None

    class _FakeChromium:
        async def launch(self, **_kwargs: Any) -> _FakeBrowser:
            return _FakeBrowser()

    class _FakePlaywrightCtx:
        chromium = _FakeChromium()

        async def __aenter__(self) -> "_FakePlaywrightCtx":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

    def async_playwright() -> _FakePlaywrightCtx:
        return _FakePlaywrightCtx()

    fake_async_api = types.ModuleType("playwright.async_api")
    fake_async_api.async_playwright = async_playwright  # type: ignore[attr-defined]

    fake_pw = types.ModuleType("playwright")
    fake_pw.async_api = fake_async_api  # type: ignore[attr-defined]
    return fake_pw, fake_async_api


@pytest.fixture
def fake_playwright(monkeypatch: pytest.MonkeyPatch) -> _ConcurrencyCounter:
    """Substitui `playwright` por fake e retorna counter de concorrência."""
    counter = _ConcurrencyCounter()
    fake_pw, fake_async_api = _build_fake_playwright(counter)
    monkeypatch.setitem(sys.modules, "playwright", fake_pw)
    monkeypatch.setitem(sys.modules, "playwright.async_api", fake_async_api)

    # Reset capability cache + semaphore singleton entre testes
    monkeypatch.setattr(pdf_renderer, "_PLAYWRIGHT_AVAILABLE", None, raising=False)
    monkeypatch.setattr(pdf_renderer, "_pdf_semaphore", None, raising=False)
    return counter


@pytest.mark.asyncio
async def test_render_pdf_caps_concurrent_renders_at_settings_limit(
    fake_playwright: _ConcurrencyCounter,
) -> None:
    """5 chamadas simultâneas → max 2 ativas (MATHOMS_PDF_CONCURRENCY=2)."""
    from backend.app.core.config import settings

    expected_cap = settings.MATHOMS_PDF_CONCURRENCY
    assert expected_cap == 2, "default MATHOMS_PDF_CONCURRENCY mudou — atualize o teste"

    coros = [
        pdf_renderer.render_pdf(
            f"http://frontend/reports/{i}",
            "fake-token",
            timeout_ms=5_000,
        )
        for i in range(5)
    ]
    results = await asyncio.gather(*coros)

    assert len(results) == 5
    assert all(r == b"%PDF-1.4 fake" for r in results)
    assert fake_playwright.calls == 5, "todas as 5 chamadas devem completar"
    assert (
        fake_playwright.peak <= expected_cap
    ), f"semaphore violado: peak concorrência {fake_playwright.peak} > cap {expected_cap}"
    # Sanity: pelo menos 2 rodaram em paralelo (semaphore não está
    # serializando tudo em 1).
    assert fake_playwright.peak >= 2, f"esperava paralelismo até cap, peak={fake_playwright.peak}"


@pytest.mark.asyncio
async def test_render_pdf_singleton_semaphore_reused(
    fake_playwright: _ConcurrencyCounter,
) -> None:
    """Mesmo objeto Semaphore é retornado entre invocações (lazy singleton)."""
    sem1 = pdf_renderer._get_pdf_semaphore()
    sem2 = pdf_renderer._get_pdf_semaphore()
    assert sem1 is sem2

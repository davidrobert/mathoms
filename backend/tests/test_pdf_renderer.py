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


class _FakePage:
    def __init__(self, counter: _ConcurrencyCounter, hold_seconds: float) -> None:
        self._counter = counter
        self._hold_seconds = hold_seconds

    async def add_init_script(self, _script: str) -> None:
        """O gate client-side lê o token de localStorage — ver `_CLIENT_TOKEN_KEY`."""
        return None

    async def set_extra_http_headers(self, _headers: dict[str, str]) -> None:
        return None

    async def goto(self, _url: str, **_kwargs: Any) -> None:
        return None

    async def wait_for_function(self, _expr: str, **_kwargs: Any) -> None:
        return None

    async def wait_for_timeout(self, _ms: int) -> None:
        return None

    async def pdf(self, **_kwargs: Any) -> bytes:
        await self._counter.enter()
        try:
            await asyncio.sleep(self._hold_seconds)
            return b"%PDF-1.4 fake"
        finally:
            await self._counter.exit()


class _FakeBrowser:
    def __init__(self, counter: _ConcurrencyCounter, hold_seconds: float) -> None:
        self._counter = counter
        self._hold_seconds = hold_seconds

    async def new_page(self) -> _FakePage:
        return _FakePage(self._counter, self._hold_seconds)

    async def close(self) -> None:
        return None


class _FakeChromium:
    def __init__(self, counter: _ConcurrencyCounter, hold_seconds: float) -> None:
        self._counter = counter
        self._hold_seconds = hold_seconds

    async def launch(self, **_kwargs: Any) -> _FakeBrowser:
        return _FakeBrowser(self._counter, self._hold_seconds)


class _FakePlaywrightCtx:
    def __init__(self, counter: _ConcurrencyCounter, hold_seconds: float) -> None:
        self.chromium = _FakeChromium(counter, hold_seconds)

    async def __aenter__(self) -> "_FakePlaywrightCtx":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None


def _build_fake_playwright(counter: _ConcurrencyCounter, hold_seconds: float = 0.05) -> Any:
    """Módulo fake `playwright.async_api` — `pdf()` segura hold dentro da
    seção crítica para forçar overlap real com semaphore."""
    fake_async_api = types.ModuleType("playwright.async_api")
    fake_async_api.async_playwright = lambda: _FakePlaywrightCtx(counter, hold_seconds)  # type: ignore[attr-defined]
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
    monkeypatch.setattr(pdf_renderer, "_PLAYWRIGHT_AVAILABLE", None, raising=False)
    monkeypatch.setattr(pdf_renderer, "_pdf_semaphore", None, raising=False)
    return counter


def _assert_semaphore_caps_peak(counter: _ConcurrencyCounter, expected_cap: int) -> None:
    assert counter.calls == 5, "todas as 5 chamadas devem completar"
    assert (
        counter.peak <= expected_cap
    ), f"semaphore violado: peak concorrência {counter.peak} > cap {expected_cap}"
    # Sanity: pelo menos 2 rodaram em paralelo — semaphore não está serializando em 1.
    assert counter.peak >= 2, f"esperava paralelismo até cap, peak={counter.peak}"


@pytest.mark.asyncio
async def test_render_pdf_caps_concurrent_renders_at_settings_limit(
    fake_playwright: _ConcurrencyCounter,
) -> None:
    """5 chamadas simultâneas → max 2 ativas (MATHOMS_PDF_CONCURRENCY=2)."""
    from backend.app.core.config import settings

    expected_cap = settings.MATHOMS_PDF_CONCURRENCY
    assert expected_cap == 2, "default MATHOMS_PDF_CONCURRENCY mudou — atualize o teste"

    coros = [
        pdf_renderer.render_pdf(f"http://frontend/reports/{i}", "fake-token", timeout_ms=5_000)
        for i in range(5)
    ]
    results = await asyncio.gather(*coros)

    assert len(results) == 5
    assert all(r == b"%PDF-1.4 fake" for r in results)
    _assert_semaphore_caps_peak(fake_playwright, expected_cap)


@pytest.mark.asyncio
async def test_render_pdf_singleton_semaphore_reused(
    fake_playwright: _ConcurrencyCounter,
) -> None:
    """Mesmo objeto Semaphore é retornado entre invocações (lazy singleton)."""
    sem1 = pdf_renderer._get_pdf_semaphore()
    sem2 = pdf_renderer._get_pdf_semaphore()
    assert sem1 is sem2

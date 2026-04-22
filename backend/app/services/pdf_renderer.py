"""Server-side PDF rendering via Playwright (F9 · ADR-076 · F4.2).

Renderiza o relatório nativo React como PDF A4 usando headless Chromium.
O frontend serve a rota /reports/{id}?print=1 com print CSS otimizado
(F3.2) — Playwright navega, espera networkidle, e gera o PDF.

Uso:
    pdf_bytes = await render_pdf(report_id, bearer_token)

Requisitos:
    pip install playwright
    playwright install chromium   (ou via Dockerfile)

NOTA: Playwright consome ~200MB de RAM por renderização. Em produção,
limitar concorrência (semaphore ou fila dedicada). Para MVP/beta,
renderização síncrona é aceitável.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import — Playwright pode não estar instalado em ambientes leves (CI unit tests).
_PLAYWRIGHT_AVAILABLE: Optional[bool] = None


def _check_playwright() -> bool:
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is None:
        try:
            import playwright  # noqa: F401

            _PLAYWRIGHT_AVAILABLE = True
        except ImportError:
            _PLAYWRIGHT_AVAILABLE = False
            logger.warning(
                "playwright não instalado — PDF server-side indisponível. "
                "Instale com: pip install playwright && playwright install chromium"
            )
    return _PLAYWRIGHT_AVAILABLE


async def render_pdf(
    report_url: str,
    bearer_token: str,
    *,
    timeout_ms: int = 30_000,
    format: str = "A4",
    print_background: bool = True,
) -> bytes:
    """Renderiza uma URL como PDF via headless Chromium.

    Args:
        report_url: URL completa do relatório (ex: http://frontend:3000/reports/id)
        bearer_token: Token JWT para autenticação via header
        timeout_ms: Timeout total de navegação + render
        format: Formato da página (A4 default)
        print_background: Manter cores de fundo (print-color-adjust)

    Returns:
        bytes do PDF gerado

    Raises:
        RuntimeError: se Playwright não estiver instalado
        Exception: se navegação ou render falharem
    """
    if not _check_playwright():
        raise RuntimeError(
            "Playwright não está instalado. Execute: "
            "pip install playwright && playwright install chromium"
        )

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()

            # Injeta Bearer token no header de todas as requisições da page
            await page.set_extra_http_headers(
                {
                    "Authorization": f"Bearer {bearer_token}",
                }
            )

            # Navega para a rota de relatório com query ?print=1 para ativar
            # o modo print do frontend (se implementado; caso contrário, o
            # print CSS media query faz o trabalho)
            url = report_url if "?" in report_url else f"{report_url}?print=1"
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

            # Estado terminal da rota (sucesso F9+, legado pré-F9, ou erro de metadados).
            ready_timeout = max(5_000, timeout_ms - 3_000)
            await page.wait_for_function(
                """() => !!document.querySelector('[data-report-ready="true"]')"""
                """ || !!document.querySelector('[data-report-pdf-legacy="1"]')"""
                """ || !!document.querySelector('[data-report-pdf-error="1"]')""",
                timeout=ready_timeout,
            )

            # Recharts / layout assíncronos
            await page.wait_for_timeout(2000)

            pdf_bytes = await page.pdf(
                format=format,
                print_background=print_background,
                margin={
                    "top": "15mm",
                    "right": "12mm",
                    "bottom": "15mm",
                    "left": "12mm",
                },
            )
            return pdf_bytes
        finally:
            await browser.close()

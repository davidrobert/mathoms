"""Use cases do agregado ``Report`` (A6e.4 · ADR-101 R15).

Listagem + serve JSON/PDF + fallback de tasks. O PDF é renderizado
server-side via Playwright sobre a rota React (ADR-076 · ADR-129);
não há mais renderer HTML server-side.
"""

from backend.app.application.report.consumo_pontuais import (
    VALID_PERIODS,
    list_consumo_pontuais,
)
from backend.app.application.report.download_pdf import download_report_pdf
from backend.app.application.report.get_report import get_report
from backend.app.application.report.get_report_data import get_report_data
from backend.app.application.report.get_report_tasks import get_report_tasks
from backend.app.application.report.list_reports import list_reports

__all__ = [
    "VALID_PERIODS",
    "download_report_pdf",
    "get_report",
    "get_report_data",
    "get_report_tasks",
    "list_consumo_pontuais",
    "list_reports",
]

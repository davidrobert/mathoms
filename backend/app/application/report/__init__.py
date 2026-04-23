"""Use cases do agregado ``Report`` (A6e.4 · ADR-101 R15).

Listagem + serve HTML/JSON/PDF + fallback de tasks. O PDF é renderizado
server-side via Playwright (ADR-076); HTML standalone vem do E6.
"""

from backend.app.application.report.download_pdf import download_report_pdf
from backend.app.application.report.get_report import get_report
from backend.app.application.report.get_report_data import get_report_data
from backend.app.application.report.get_report_html import (
    download_report_html,
    get_report_html,
)
from backend.app.application.report.get_report_tasks import get_report_tasks
from backend.app.application.report.list_reports import list_reports

__all__ = [
    "download_report_html",
    "download_report_pdf",
    "get_report",
    "get_report_data",
    "get_report_html",
    "get_report_tasks",
    "list_reports",
]

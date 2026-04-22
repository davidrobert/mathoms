"""DocumentTextExtractor — extract text from PDFs and spreadsheets for LLM input.

Supports: PDF (via pdfplumber), XLSX/XLS (via openpyxl), CSV (stdlib).
Images (JPG, JPEG, PNG) are returned as raw bytes via extract_image_bytes().
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

_MEDIA_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class DocumentTextExtractor:
    """Extracts text content from documents for use as LLM prompt input.

    Usage:
        extractor = DocumentTextExtractor(max_chars=50_000)
        text = extractor.extract(Path("extrato.pdf"))
    """

    def __init__(self, max_chars: int = 100_000, max_pages: int = 50):
        self.max_chars = max_chars
        self.max_pages = max_pages

    @staticmethod
    def is_image(path: Path) -> bool:
        return path.suffix.lower() in IMAGE_EXTENSIONS

    def extract_image_bytes(self, path: Path) -> tuple[bytes, str]:
        """Return raw bytes and MIME type for an image file."""
        media_type = _MEDIA_TYPE_MAP.get(path.suffix.lower(), "image/jpeg")
        return path.read_bytes(), media_type

    def extract(self, path: Path) -> str:
        """Extract text from a file. Returns empty string on failure."""
        suffix = path.suffix.lower()

        try:
            if suffix == ".pdf":
                return self._extract_pdf(path)
            elif suffix in (".xlsx", ".xls"):
                return self._extract_excel(path)
            elif suffix == ".csv":
                return self._extract_csv(path)
            elif suffix == ".json":
                return path.read_text(encoding="utf-8")[: self.max_chars]
            elif suffix in (".txt", ".md"):
                return path.read_text(encoding="utf-8")[: self.max_chars]
            elif suffix in IMAGE_EXTENSIONS:
                logger.debug("Image file %s — use extract_image_bytes() instead", path.name)
                return ""
            else:
                logger.warning("Unsupported file type: %s", suffix)
                return ""
        except Exception as exc:
            logger.error("Failed to extract text from %s: %s", path.name, exc)
            return ""

    def _extract_pdf(self, path: Path) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed — cannot extract PDF text")
            return ""

        pages_text: list[str] = []
        total_chars = 0

        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= self.max_pages:
                    pages_text.append(f"\n[... truncated at {self.max_pages} pages ...]")
                    break

                text = page.extract_text() or ""

                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        table_text = self._format_table(table)
                        if table_text and table_text not in text:
                            text += "\n" + table_text

                if total_chars + len(text) > self.max_chars:
                    remaining = self.max_chars - total_chars
                    pages_text.append(text[:remaining])
                    pages_text.append(f"\n[... truncated at {total_chars + remaining} chars ...]")
                    break

                pages_text.append(text)
                total_chars += len(text)

        return "\n\n".join(pages_text)

    def _extract_excel(self, path: Path) -> str:
        """Extract text from XLSX/XLS using openpyxl."""
        try:
            import openpyxl
        except ImportError:
            logger.error("openpyxl not installed — cannot extract Excel text")
            return ""

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheets_text: list[str] = []
        total_chars = 0

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows: list[str] = [f"=== Sheet: {sheet_name} ==="]

            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    row_text = " | ".join(cells)
                    rows.append(row_text)
                    total_chars += len(row_text) + 1

                if total_chars > self.max_chars:
                    rows.append("[... truncated ...]")
                    break

            sheets_text.append("\n".join(rows))
            if total_chars > self.max_chars:
                break

        wb.close()
        return "\n\n".join(sheets_text)

    def _extract_csv(self, path: Path) -> str:
        """Extract text from CSV file."""
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > self.max_chars:
            text = text[: self.max_chars] + "\n[... truncated ...]"
        return text

    @staticmethod
    def _format_table(table: list[list[Optional[str]]]) -> str:
        """Format a pdfplumber table as pipe-delimited text."""
        if not table:
            return ""
        rows = []
        for row in table:
            cells = [str(c).strip() if c else "" for c in row]
            rows.append(" | ".join(cells))
        return "\n".join(rows)

    def extract_multiple(self, paths: list[Path]) -> dict[str, str]:
        """Extract text from multiple files. Returns {filename: text}."""
        results = {}
        for path in paths:
            results[path.name] = self.extract(path)
        return results

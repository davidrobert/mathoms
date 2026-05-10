"""Content-based document classifier — orchestrator.

Classifies financial documents by inspecting their **contents** (not filenames).
Bank-exported filenames are frequently wrong or misleading, so we ignore them
entirely for classification purposes.

Pipeline:
    1. Extract text preview (first pages of PDF, first rows of XLSX/CSV).
    2. Match institution markers (razao social, CNPJ, headers).
    3. Match document-type markers in priority order (IRPF > fatura > extrato
       > investimento > CDB). Each type has REQUIRED and SUPPORTING markers;
       confidence = 1.0 if required + >=1 supporting, 0.7 if only required,
       0.5 if only supporting.
    4. Extract period from content (DD/MM/YYYY ranges, MM/YYYY, YYYY).
    5. Return dict compatible with ``scripts.e0_route.classify_by_name``.

The caller decides what to do with low-confidence results (LLM fallback,
``needs_review`` flag, etc.). This module has no LLM calls and no network.

Internals live in ``backend.app.services.classification.*``:
  - institution_classifier: INSTITUTION_CONTENT_PATTERNS + detect_institution_by_content
  - type_classifier: TYPE_RULES, TypeRule, detect_type_by_content, compute_confidence
  - period_extractor: extract_period_from_content
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from backend.app.services.classification.institution_classifier import (
    INSTITUTION_CONTENT_PATTERNS,
    detect_institution_by_content,
)
from backend.app.services.classification.period_extractor import extract_period_from_content
from backend.app.services.classification.type_classifier import (
    TYPE_RULES,
    TypeRule,
    compute_confidence,
    detect_type_by_content,
)

# Re-export public symbols consumed by tests and external callers.
__all__ = [
    "INSTITUTION_CONTENT_PATTERNS",
    "TYPE_RULES",
    "TypeRule",
    "ContentClassification",
    "classify_file",
    "classify_text",
    "compute_confidence",
    "detect_institution_by_content",
    "detect_type_by_content",
    "extract_period_from_content",
]


@dataclass
class ContentClassification:
    doc_type: str | None
    dest_group: str | None
    institution: str | None
    period: str | None
    confidence: float  # 0.0 to 1.0
    source: str = "content_regex"
    matched_required: int = 0
    matched_supporting: int = 0
    force_review: bool = False

    def to_dict(self) -> dict:
        return {
            "institution": self.institution,
            "doc_type": self.doc_type,
            "dest_group": self.dest_group,
            "period": self.period,
            "member": None,
            "confidence": self.confidence,
            "source": self.source,
            "matched_required": self.matched_required,
            "matched_supporting": self.matched_supporting,
            "force_review": self.force_review,
        }


def _empty_classification(
    institution: str | None = None,
    period: str | None = None,
    *,
    source: str | None = None,
) -> ContentClassification:
    return ContentClassification(
        doc_type=None,
        dest_group=None,
        institution=institution,
        period=period,
        confidence=0.0,
        source=source,
        matched_required=0,
        matched_supporting=0,
    )


_RFB_AUTHORED_RULES = frozenset({"irpfdeclaracao", "irpfrecibo"})


def _resolve_institution(rule: TypeRule, detected: str | None) -> str | None:
    # Apenas declaração e recibo são emitidos PELA RFB. Informes de rendimentos
    # são emitidos pela fonte pagadora (banco, administradora) — preservar o
    # emissor real. Override existe porque a declaração lista bancos em "Bens e
    # Direitos" e o regex de banco bateria primeiro.
    if rule.code in _RFB_AUTHORED_RULES:
        return "receitafederal"
    return detected


def classify_text(text: str) -> ContentClassification:
    """Classify a preview text extracted from a financial document."""
    if not text or len(text.strip()) < 20:
        return _empty_classification(source="content_regex_empty")

    institution = detect_institution_by_content(text)
    rule, req, sup = detect_type_by_content(text)
    period = extract_period_from_content(text)

    if rule is None:
        return _empty_classification(institution=institution, period=period)

    return ContentClassification(
        doc_type=rule.code,
        dest_group=rule.dest_group,
        institution=_resolve_institution(rule, institution),
        period=period,
        confidence=compute_confidence(rule, req, sup),
        matched_required=req,
        matched_supporting=sup,
    )


# Filename-guarded investment override
# ---------------------------------------------------------------------------
# Contexto: exports de corretoras (Rico, XP) vêm nomeados `*_extratoconta_*`
# mas o conteúdo é dashboard de posição de investimentos, não extrato de conta.
# Isso força o parser E2 a rodar e extrair 0 transações (ERROR espúrio).
# Heurística determinística: se o filename sugere extrato, mas o conteúdo
# mostra marcadores de investimento (≥3) e zero marcadores de extrato
# bancário, reclassificamos como ``investimentosposicao`` e marcamos
# ``force_review=True`` para revisão humana.
_INVESTMENT_MARKERS: tuple[re.Pattern, ...] = (
    re.compile(r"Posi[çc][ãa]o\s*(a\s*mercado|consolidada|de\s*carteira)", re.I),
    re.compile(r"Fundos?\s*de\s*Investimentos?", re.I),
    re.compile(r"Renda\s*Vari[aá]vel", re.I),
    re.compile(r"Rentabilidade\s*(L[ií]quida|Bruta|Acumulada)?", re.I),
    re.compile(r"\bproventos?\b", re.I),
    re.compile(r"Aloca[çc][ãa]o(\s+da\s+carteira)?", re.I),
    re.compile(r"Tesouro\s*(Direto|Selic|IPCA|Prefixado|Nacional)", re.I),
    re.compile(r"\bETFs?\b|\bFIIs?\b|\bBDRs?\b"),
    re.compile(r"\b[A-Z]{4}\d{1,2}\b"),  # B3 tickers: PETR4, ITSA4, MGLU3
    re.compile(r"Carteira\s+de\s+(Renda|Investimentos)", re.I),
)

_BANK_STATEMENT_MARKERS: tuple[re.Pattern, ...] = (
    re.compile(r"Saldo\s+anterior", re.I),
    re.compile(r"Lan[çc]amentos\s+(do\s+dia|da\s+conta|do\s+per[ií]odo)", re.I),
    re.compile(r"SALDO\s+(DO\s+DIA|ATUAL|DISPON[IÍ]VEL)", re.I),
    re.compile(r"Ag[êe]ncia\s*[:\-]?\s*\d+.{0,40}Conta\s*[:\-]?\s*[\d-]+", re.I | re.DOTALL),
    re.compile(r"TED\s+(Enviad|Recebid)", re.I),
    re.compile(r"D[ée]bito\s+autom[aá]tico", re.I),
    re.compile(r"PIX\s+(Enviad|Recebid)", re.I),
    re.compile(r"Hist[oó]rico\s+de\s+Lan[çc]amentos", re.I),
)


def _maybe_apply_investment_override(
    result: ContentClassification, filename: str, text: str
) -> ContentClassification:
    if "extratoconta" not in filename.lower():
        return result
    invest_hits = sum(1 for p in _INVESTMENT_MARKERS if p.search(text))
    if invest_hits < 3:
        return result
    bank_hits = sum(1 for p in _BANK_STATEMENT_MARKERS if p.search(text))
    if bank_hits > 0:
        return result
    # Skip LLM (conf >= 0.8) and force human review.
    return ContentClassification(
        doc_type="investimentosposicao",
        dest_group="financial_statements",
        institution=result.institution,
        period=result.period,
        confidence=0.85,
        source="content_regex_investment_override",
        matched_required=invest_hits,
        matched_supporting=0,
        force_review=True,
    )


def classify_file(filepath: Path, preview_extractor) -> ContentClassification:
    """Classify a file by its content.

    ``preview_extractor`` is a callable ``(Path) -> str`` that extracts a text
    preview from the file. We inject it (rather than importing) so tests can
    pass fake text and so we don't pull in pdfplumber/openpyxl at import time.
    """
    try:
        text = preview_extractor(filepath)
    except Exception as exc:  # preview extraction failed — fall through
        return ContentClassification(
            doc_type=None,
            dest_group=None,
            institution=None,
            period=None,
            confidence=0.0,
            source=f"content_regex_preview_error:{type(exc).__name__}",
        )
    result = classify_text(text or "")
    return _maybe_apply_investment_override(result, filepath.name, text or "")

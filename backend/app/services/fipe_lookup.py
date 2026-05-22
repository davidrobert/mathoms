"""FipeLookupClient Protocol + InMemory fake + adapter BrasilAPI (ADR-239 D5; A18 L3 P1)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Optional, Protocol

logger = logging.getLogger("mathoms.fipe.lookup")


# ===========================================================================
# Resultado tipado (ADR-097 D3 value object)
# ===========================================================================


FipeStatus = Literal["fresh", "stale_acceptable", "pending_refresh", "missing"]


@dataclass(frozen=True)
class FipeQuote:
    """Cotação FIPE retornada pelo client. ``value_brl`` sempre Decimal (ADR-090)."""

    fipe_code: str
    value_brl: Decimal
    reference_month: str  # "YYYY-MM"
    source: str  # "brasilapi" | "in_memory" | "cache"


@dataclass(frozen=True)
class FipeLookupError:
    """Resultado de falha — `status` orienta o caller (retry, fallback, ou aceitar pending)."""

    fipe_code: str
    status: FipeStatus  # "pending_refresh" | "missing"
    reason: str


# ===========================================================================
# Protocol (ADR-097 D2 — boundary)
# ===========================================================================


class FipeLookupClient(Protocol):
    """Contrato de lookup FIPE. Implementações: ``BrasilAPIFipeClient`` (HTTP) e
    ``InMemoryFipeLookup`` (testes). Nunca chamado síncrono no upload — sempre
    via Celery task ``refresh_fipe_value`` (ADR-239 D5)."""

    def fetch(self, fipe_code: str, ano_modelo: int) -> FipeQuote | FipeLookupError:
        """Retorna FipeQuote ou FipeLookupError tipado. Não levanta exceção em falha esperada (429/5xx) — retorna pending_refresh."""
        ...


# ===========================================================================
# InMemory fake (testes determinísticos)
# ===========================================================================


class InMemoryFipeLookup:
    """Fake determinístico — popule com `register(code, ano, value)`. Testes ADR-097."""

    def __init__(self) -> None:
        self._db: dict[tuple[str, int], FipeQuote] = {}
        self._next_status: FipeStatus = "fresh"

    def register(
        self,
        fipe_code: str,
        ano_modelo: int,
        value_brl: Decimal,
        reference_month: Optional[str] = None,
    ) -> None:
        """Adiciona quote ao DB; reference_month default = mês corrente."""
        if reference_month is None:
            today = date.today()
            reference_month = f"{today.year:04d}-{today.month:02d}"
        self._db[(fipe_code, ano_modelo)] = FipeQuote(
            fipe_code=fipe_code,
            value_brl=value_brl,
            reference_month=reference_month,
            source="in_memory",
        )

    def force_next_status(self, status: FipeStatus) -> None:
        """Permite testar caminho de erro/pending sem mock HTTP."""
        self._next_status = status

    def fetch(self, fipe_code: str, ano_modelo: int) -> FipeQuote | FipeLookupError:
        if self._next_status != "fresh":
            status = self._next_status
            self._next_status = "fresh"
            return FipeLookupError(fipe_code=fipe_code, status=status, reason="forced_in_test")
        quote = self._db.get((fipe_code, ano_modelo))
        if quote is None:
            return FipeLookupError(
                fipe_code=fipe_code, status="missing", reason="codigo_nao_registrado"
            )
        return quote


# ===========================================================================
# BrasilAPI adapter (HTTP) — implementação real
# ===========================================================================


# Regex permissivo para fipe_code (ADR-239 schema CRLV permite [0-9\-]{4,20}).
_FIPE_CODE_RE = re.compile(r"^[0-9\-]{4,20}$")


def _validate_fipe_code(fipe_code: str) -> Optional[str]:
    """Retorna None se válido; mensagem de erro se inválido."""
    if not _FIPE_CODE_RE.match(fipe_code or ""):
        return f"fipe_code inválido: {fipe_code!r}"
    return None


_MESES_PT = {
    "janeiro": "01",
    "fevereiro": "02",
    "marco": "03",
    "março": "03",
    "abril": "04",
    "maio": "05",
    "junho": "06",
    "julho": "07",
    "agosto": "08",
    "setembro": "09",
    "outubro": "10",
    "novembro": "11",
    "dezembro": "12",
}


def _current_month_str() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def _ref_month_from_iso(iso: Optional[str] = None) -> str:
    """Converte 'dezembro/2025' ou '2025-12' BrasilAPI → 'YYYY-MM'; None → mês corrente."""
    if not iso:
        return _current_month_str()
    if re.match(r"^\d{4}-\d{2}$", iso):
        return iso
    parts = iso.lower().split("/")
    if len(parts) == 2 and parts[0] in _MESES_PT:
        return f"{parts[1]}-{_MESES_PT[parts[0]]}"
    return _current_month_str()


class BrasilAPIFipeClient:
    """Adapter HTTP para BrasilAPI ``/fipe/preco/v1/<code>`` (open-source comunitário)."""

    BASE_URL = "https://brasilapi.com.br/api/fipe/preco/v1"
    DEFAULT_TIMEOUT_S = 8.0

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self._timeout_s = timeout_s

    def fetch(self, fipe_code: str, ano_modelo: int) -> FipeQuote | FipeLookupError:
        """ADR-239 D5: HTTP síncrono **proibido fora de Celery** (caller é a task)."""
        err = _validate_fipe_code(fipe_code)
        if err is not None:
            return FipeLookupError(fipe_code=fipe_code, status="missing", reason=err)
        return self._fetch_safe(fipe_code, ano_modelo)

    def _fetch_safe(self, fipe_code: str, ano_modelo: int) -> FipeQuote | FipeLookupError:
        """Try/except externo — 429/5xx → pending_refresh (não exception)."""
        try:
            return self._fetch_http(fipe_code, ano_modelo)
        except Exception as exc:  # noqa: BLE001 — degradação graceful
            logger.warning(
                "mathoms.fipe.lookup_failed",
                extra={"fipe_code_prefix": fipe_code[:4], "reason": str(exc)[:120]},
            )
            return FipeLookupError(
                fipe_code=fipe_code,
                status="pending_refresh",
                reason=f"http_error: {type(exc).__name__}",
            )

    def _fetch_http(self, fipe_code: str, ano_modelo: int) -> FipeQuote | FipeLookupError:
        """HTTP call — isolado para teste com responses/httpx_mock."""
        import httpx

        url = f"{self.BASE_URL}/{fipe_code}"
        resp = httpx.get(url, timeout=self._timeout_s)
        if resp.status_code in (429, 500, 502, 503, 504):
            return FipeLookupError(
                fipe_code=fipe_code,
                status="pending_refresh",
                reason=f"http_{resp.status_code}",
            )
        if resp.status_code == 404:
            return FipeLookupError(fipe_code=fipe_code, status="missing", reason="brasilapi_404")
        resp.raise_for_status()
        data = resp.json()
        return _parse_brasilapi_response(fipe_code, ano_modelo, data)


def _parse_brasilapi_response(fipe_code: str, ano_modelo: int, data) -> FipeQuote | FipeLookupError:
    """BrasilAPI retorna array de quotes; filtra por ano_modelo (best-effort)."""
    if not isinstance(data, list) or not data:
        return FipeLookupError(fipe_code=fipe_code, status="missing", reason="empty_response")
    entry = _pick_by_ano(data, ano_modelo) or data[0]
    return _quote_from_entry(fipe_code, entry)


def _pick_by_ano(quotes: list, ano_modelo: int) -> Optional[dict]:
    """Match estrito por ano_modelo; None se nenhum bate."""
    for q in quotes:
        if isinstance(q, dict) and q.get("anoModelo") == ano_modelo:
            return q
    return None


def _quote_from_entry(fipe_code: str, entry) -> FipeQuote | FipeLookupError:
    """Materializa quote ou erro a partir de entry BrasilAPI."""
    if not isinstance(entry, dict):
        return FipeLookupError(fipe_code=fipe_code, status="missing", reason="invalid_entry")
    valor_str = entry.get("valor") or ""
    value_brl = _parse_brl_currency(valor_str)
    if value_brl is None:
        return FipeLookupError(
            fipe_code=fipe_code, status="missing", reason=f"unparseable_valor: {valor_str[:40]}"
        )
    return FipeQuote(
        fipe_code=fipe_code,
        value_brl=value_brl,
        reference_month=_ref_month_from_iso(entry.get("mesReferencia")),
        source="brasilapi",
    )


def _parse_brl_currency(raw: str) -> Optional[Decimal]:
    """'R$ 17.500,00' → Decimal('17500.00'); '17500.00' (ISO) também aceito."""
    if not raw:
        return None
    cleaned = raw.replace("R$", "").replace(" ", "").strip()
    if "," in cleaned:
        # Formato BR: ponto=milhar, vírgula=decimal.
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except Exception:  # noqa: BLE001
        return None

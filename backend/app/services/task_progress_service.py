"""Task↔Transaction integration — % executado da tarefa (ADR-074 §F8.3).

Heurística de detecção:
- Task.category ∈ {"Invest", "Orcamento"} + title contém "aporte" → "aporte mensal".
- Target extraído via regex BRL do title (ex: "R$ 20k/mês", "R$ 20.000").
  Se não encontrado, usa `goals.aportes.meta_aporte_mensal` do goals.json
  via adapter (F8.4 trará isso nativo; por ora, target=None se não parseável).
- Keywords de matching vêm de `config/goals.json` →
  `dashboard.aporte_match_keywords.<destino>` (cofrinhos, tesouro, etc.).

Transações são carregadas via `transaction_service.load_transactions`
(filesystem E4). Futuramente (F8.4+) virá do DB direto.

É uma integração best-effort — retorna `is_trackable=False` se heurística
não cobre a task, e a UI esconde o card.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from backend.app.models.task import Task
from backend.app.schemas.task import TaskProgress
from backend.app.services.transaction_service import load_transactions

# Keywords default caso `config/goals.json` não esteja acessível.
_DEFAULT_APORTE_KEYWORDS: list[str] = [
    "aporte",
    "cofrinho",
    "cofrinhos",
    "cdb itau",
    "cdb itaú",
    "tesouro",
    "ipca+",
    "ipca +",
    "ivvb11",
    "ivvb",
    "wise",
    "s&p",
    "sp500",
]


def _load_aporte_keywords_from_config(tenant_root: Optional[str] = None) -> list[str]:
    """Tenta ler config/goals.json do tenant. Se ausente ou malformado,
    volta para default."""
    if not tenant_root:
        return _DEFAULT_APORTE_KEYWORDS
    path = Path(tenant_root) / "config" / "goals.json"
    if not path.exists():
        # tenta caminho do repo (single-tenant legado)
        repo_path = Path(__file__).resolve().parents[3] / "config" / "goals.json"
        if not repo_path.exists():
            return _DEFAULT_APORTE_KEYWORDS
        path = repo_path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        buckets = data.get("dashboard", {}).get("aporte_match_keywords", {}) or {}
        if not buckets:
            return _DEFAULT_APORTE_KEYWORDS
        out: list[str] = []
        for lst in buckets.values():
            if isinstance(lst, list):
                out.extend(str(k).lower() for k in lst)
        return out or _DEFAULT_APORTE_KEYWORDS
    except (json.JSONDecodeError, OSError):
        return _DEFAULT_APORTE_KEYWORDS


# Regex para extrair valor BRL do title. Cobre: R$ 20k, R$20.000, R$ 1.234,56,
# 20k/mês, etc. Retorna o PRIMEIRO match numeric (em reais).
_BRL_RE = re.compile(
    r"R\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?)(k)?",
    re.IGNORECASE,
)
_SHORT_BRL_RE = re.compile(r"(\d+)k(?:\W|$)", re.IGNORECASE)


def _parse_brl_target(title: str) -> Optional[Decimal]:
    """Melhor esforço: extrai primeiro valor em reais do título. Retorna
    Decimal (BRL) ou None. Trata "R$ 20k" como 20.000."""
    m = _BRL_RE.search(title)
    if m:
        raw, k_suffix = m.group(1), m.group(2)
        value = _raw_to_float(raw)
        if value is None:
            return None
        d = Decimal(str(value))
        if k_suffix:
            d *= Decimal("1000")
        return d
    m = _SHORT_BRL_RE.search(title)
    if m:
        try:
            return Decimal(m.group(1)) * Decimal("1000")
        except (ValueError, ArithmeticError):
            return None
    return None


def _normalize_both_separators(raw: str) -> str:
    """Dois separadores: o da direita é o decimal. BRL '20.000,00' → '20000.00'."""
    if raw.rfind(",") > raw.rfind("."):
        return raw.replace(".", "").replace(",", ".")
    return raw.replace(",", "")  # US: '20,000.00'


def _normalize_single_separator(raw: str, sep: str) -> str:
    """Só um tipo de separador. 3 dígitos após último → milhar (remove);
    ≠3 → decimal (padroniza para ponto)."""
    if sep == "." and raw.count(".") > 1:
        return raw.replace(".", "")  # múltiplos pontos → todos milhares
    after = raw[raw.rfind(sep) + 1 :]
    if len(after) == 3 and after.isdigit():
        return raw.replace(sep, "")  # milhar
    return raw.replace(",", ".") if sep == "," else raw  # decimal


def _raw_to_float(raw: str) -> Optional[float]:
    """Normaliza '20.000,00' ou '20,000.00' → 20000.0.

    Heurística: dois separadores → último é decimal; um só → 3 dígitos
    após = milhar, senão = decimal. Empty/inválido → None.
    """
    raw = raw.strip()
    if not raw:
        return None

    has_comma, has_dot = "," in raw, "." in raw
    if has_comma and has_dot:
        raw = _normalize_both_separators(raw)
    elif has_comma:
        raw = _normalize_single_separator(raw, ",")
    elif has_dot:
        raw = _normalize_single_separator(raw, ".")

    try:
        return float(raw)
    except ValueError:
        return None


def _is_tracked_task(task: Task) -> bool:
    """Heurística — só tasks que contêm palavras ligadas a aporte/fluxo."""
    title_lower = task.title.lower()
    if not any(word in title_lower for word in ("aporte", "aportar", "mensal")):
        return False
    if task.category not in ("Invest", "Orcamento"):
        return False
    return True


def _current_month_period() -> tuple[date, date]:
    """Retorna (primeiro-dia, último-dia) do mês corrente."""
    today = date.today()
    start = today.replace(day=1)
    # Último dia do mês
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    from datetime import timedelta

    end = next_month - timedelta(days=1)
    return start, end


def _tx_date_in_period(tx, period_start: date, period_end: date) -> bool:
    """True se a transação tem data válida dentro do período do mês corrente."""
    if not tx.data:
        return False
    try:
        tx_date_obj = date.fromisoformat(tx.data[:10])
    except ValueError:
        return False
    return period_start <= tx_date_obj <= period_end


def _match_transactions_by_keyword(
    workspace_id: str,
    tenant_root: str,
    keywords: list[str],
    period_start: date,
    period_end: date,
) -> tuple[Decimal, int, set[str]]:
    """Soma `abs(valor)` de transações no período cujo `descricao` contém
    uma das keywords. Retorna (executed, count, keywords_matched).

    Best-effort: qualquer erro em `load_transactions` retorna zeros.
    """
    try:
        txs = load_transactions(workspace_id, tenant_root)
    except Exception:  # noqa: BLE001 — best-effort, nunca quebra endpoint
        return Decimal("0"), 0, set()

    executed = Decimal("0")
    matched_count = 0
    matched_keywords: set[str] = set()
    for tx in txs:
        if not _tx_date_in_period(tx, period_start, period_end):
            continue
        desc_lower = (tx.descricao or "").lower()
        matched_kw = next((k for k in keywords if k in desc_lower), None)
        if matched_kw:
            matched_keywords.add(matched_kw)
            executed += abs(tx.valor)
            matched_count += 1
    return executed, matched_count, matched_keywords


def compute_progress(
    task: Task,
    *,
    workspace_id: Optional[str] = None,
    tenant_root: Optional[str] = None,
) -> TaskProgress:
    """Computa progresso da task no mês corrente.

    Se `task` não é "trackable", retorna `TaskProgress(is_trackable=False)`.
    Caso contrário, carrega transações do tenant_root + faz matching por
    keyword no `descricao` e soma `abs(valor)`.

    `tenant_root` é o filesystem root usado pelo pipeline (ex:
    `storage/{workspace_id}`). Pode ser None em testes unitários.
    """
    if not _is_tracked_task(task):
        return TaskProgress(is_trackable=False)

    target = _parse_brl_target(task.title)
    period_start, period_end = _current_month_period()
    keywords = _load_aporte_keywords_from_config(tenant_root)

    executed, matched_count, matched_keywords_set = (
        _match_transactions_by_keyword(
            workspace_id, tenant_root, keywords, period_start, period_end
        )
        if tenant_root and workspace_id
        else (Decimal("0"), 0, set())
    )

    percent: Optional[float] = None
    if target and target > 0:
        percent = round(float(Decimal("100") * executed / target), 1)

    return TaskProgress(
        is_trackable=True,
        period_start=period_start,
        period_end=period_end,
        target_brl=target,
        executed_brl=executed.quantize(Decimal("0.01")),
        percent_executed=percent,
        matched_keywords=sorted(matched_keywords_set),
        matched_transactions_count=matched_count,
    )


__all__ = ["compute_progress"]

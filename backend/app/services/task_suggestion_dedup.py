"""Dedup canônico de TaskSuggestion (ADR-266): sha256(source:normalize(title):normalize(category))[:64] — normalize = lower+strip+colapsar whitespace; description/priority/deadline ficam fora porque LLM varia entre runs."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Final

__all__ = [
    "DISMISS_RESPECT_WINDOW_DAYS",
    "compute_task_suggestion_dedup_key",
    "normalize_llm_draft",
    "normalize_text",
]

# Mesma janela do Suggestion aggregate (ADR-153) — rejeição do usuário
# em <90 dias bloqueia recriação do mesmo dedup_key. Após a janela,
# o run novo pode re-sugerir.
DISMISS_RESPECT_WINDOW_DAYS: Final = 90

_WHITESPACE_RE: Final = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    """Lower + strip + colapsar whitespace (estável entre runs)."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def compute_task_suggestion_dedup_key(source: str, title: str | None, category: str | None) -> str:
    """sha256(source:normalize(title):normalize(category))[:64] — ADR-266; source entra raw (enum curto canônico)."""
    payload = f"{source}:{normalize_text(title)}:{normalize_text(category)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:64]


def normalize_llm_draft(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Mapeia raw JSON E5N (pt/en) → {dedup_key, proposed_payload}; defaults espelham mapping legado pré-ADR-266."""
    title = raw.get("tarefa", raw.get("title", "Sugestão LLM"))
    category = raw.get("categoria", raw.get("category", "Orcamento"))
    proposed_payload = {
        "title": title,
        "category": category,
        "priority": raw.get("prioridade", raw.get("priority", "R")),
        "deadline_kind": raw.get("deadline_kind", "UNSCHEDULED"),
        "deadline_label": raw.get("prazo", raw.get("deadline_label")),
        "description": raw.get("descricao", raw.get("description")),
    }
    return {
        "dedup_key": compute_task_suggestion_dedup_key(source, title, category),
        "proposed_payload": proposed_payload,
    }

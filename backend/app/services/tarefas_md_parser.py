"""Parser determinístico de `config/tarefas.md` → ParsedTask in-memory.

Usado tanto pelo importer one-shot (seed inicial dos workspaces
legados) quanto por testes do contrato `task_service.export_markdown`
(round-trip: parsear, exportar, re-parsear → deve ser idempotente).

Não depende de DB, não tem side-effects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional


# Mapeamento bidirecional entre labels do MD e categorias canônicas do model.
_MD_TO_CATEGORY = {
    "Invest.": "Invest",
    "Invest": "Invest",
    "Orçamento": "Orcamento",
    "Orcamento": "Orcamento",
    "Tributário": "Tributario",
    "Tributario": "Tributario",
    "Trib./EUA": "Tributario",
    "Invest./EUA": "Invest",
    "Seguros": "Seguros",
    "Imóveis": "Imoveis",
    "Imoveis": "Imoveis",
    "Financeiro": "Financeiro",
    "Plan. EUA": "Plan. EUA",
    "Jurídico": "Juridico",
    "Juridico": "Juridico",
    "Sucessório": "Sucessorio",
    "Sucessorio": "Sucessorio",
    "Pipeline": "Pipeline",
}


_MONTH_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


_STATUS_FROM_MD = {
    "pendente": "pending",
    "em andamento": "in_progress",
    "feito": "done",
    "cancelado": "cancelled",
    "bloqueado": "blocked",
}


@dataclass
class ParsedTask:
    number: int
    title: str
    category: str  # canônico (ver VALID_CATEGORIES)
    priority: str  # S | R | O
    status: str  # canônico (pending, done, etc.)
    ref: Optional[str] = None
    deadline_kind: str = "UNSCHEDULED"
    deadline_date: Optional[date] = None
    deadline_label: Optional[str] = None
    # Preenchido no segundo passo (parsing das Notas de dependência)
    parent_number: Optional[int] = None
    completion_detail: Optional[str] = None


def _normalize_category(raw: str) -> str:
    raw = raw.strip()
    return _MD_TO_CATEGORY.get(raw, raw)


def _parse_deadline(raw: str) -> tuple[str, Optional[date], Optional[str]]:
    """Heurística pragmática:
    - DD/MM/YYYY → HARD_DATE
    - Mmm/YYYY (Abr/2026) → MONTH (preserva label, sem date)
    - Tn/YYYY ou Tn/YY (T3/26) → QUARTER
    - 2027, YYYY isolado → MONTH (fim do ano)
    - "Antes EUA", "Após mudança EUA", "Imediato" → CONDITIONAL
    - "—", "-", "" → UNSCHEDULED
    """
    raw = raw.strip()
    if not raw or raw in ("—", "-"):
        return ("UNSCHEDULED", None, None)

    # DD/MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw)
    if m:
        d, mo, y = map(int, m.groups())
        try:
            return ("HARD_DATE", date(y, mo, d), raw)
        except ValueError:
            pass

    # Mmm/YYYY (Abr/2026, abr/26)
    m = re.match(r"^([a-zA-Zç]{3})/(\d{2,4})$", raw)
    if m:
        label_month, y = m.group(1).lower()[:3], int(m.group(2))
        if y < 100:
            y = 2000 + y
        mo = _MONTH_PT.get(label_month)
        if mo:
            # Representa "Abr/2026" como MONTH — guarda label para UI
            return ("MONTH", date(y, mo, 1), raw)

    # Trimestre: T3/26, T4/2026
    m = re.match(r"^T([1-4])/(\d{2,4})$", raw)
    if m:
        return ("QUARTER", None, raw)

    # Ano isolado: 2027
    m = re.match(r"^(\d{4})$", raw)
    if m:
        y = int(m.group(1))
        return ("MONTH", date(y, 12, 31), raw)

    # Palavras-chave condicionais
    lower = raw.lower()
    if any(
        k in lower
        for k in ("antes eua", "após mudança", "apos mudanca", "imediato", "quando")
    ):
        return ("CONDITIONAL", None, raw)

    # Fallback: preserva o texto bruto como label
    return ("CONDITIONAL", None, raw)


_PRIORITY_SECTION_RE = re.compile(
    r"^## (Essenciais|Recomendadas|Opcionais)"
)
_CONCLUIDAS_RE = re.compile(r"^## Concluídas")
_NOTAS_RE = re.compile(r"^## Notas")
_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.*?)\|$"
)
_DONE_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|$"
)
# Casa "#19 depende de #18", "Depende de #18", "(depende de #18)"
_DEP_RE = re.compile(
    r"#?(\d+)\s*(?:depende|dependência)[^0-9]*(\d+)|depende.*?#(\d+)",
    re.IGNORECASE,
)


def parse_tarefas_md(content: str) -> list[ParsedTask]:
    """Parseia o MD e retorna lista ordenada por `number`.

    Duas passes: 1. tabelas por prioridade + Concluídas; 2. Notas para
    inferir `parent_number` (dependências).
    """
    lines = content.splitlines()

    current_priority: Optional[str] = None
    in_concluidas = False
    in_notas = False

    parsed: dict[int, ParsedTask] = {}

    priority_map = {
        "Essenciais": "S",
        "Recomendadas": "R",
        "Opcionais": "O",
    }

    for line in lines:
        m = _PRIORITY_SECTION_RE.match(line)
        if m:
            current_priority = priority_map[m.group(1)]
            in_concluidas = False
            in_notas = False
            continue
        if _CONCLUIDAS_RE.match(line):
            current_priority = None
            in_concluidas = True
            in_notas = False
            continue
        if _NOTAS_RE.match(line):
            current_priority = None
            in_concluidas = False
            in_notas = True
            continue
        # Pula linhas não-tabela
        if not line.startswith("|") or line.startswith("|-") or line.startswith("| #"):
            continue

        if in_concluidas:
            m = _DONE_ROW_RE.match(line)
            if not m:
                continue
            num, title, data_concl, detail = m.groups()
            completed_at = _parse_deadline(data_concl.strip())[1]
            parsed[int(num)] = ParsedTask(
                number=int(num),
                title=title.strip(),
                category="Financeiro",  # default — MD não tem categoria em concluídas
                priority="S",  # default — status=done sobrescreve visibilidade
                status="done",
                deadline_kind="HARD_DATE" if completed_at else "UNSCHEDULED",
                deadline_date=completed_at,
                deadline_label=data_concl.strip() or None,
                completion_detail=detail.strip() or None,
            )
            continue

        if current_priority is not None:
            m = _ROW_RE.match(line)
            if not m:
                continue
            num, title, cat, prazo, status, ref = m.groups()
            num_int = int(num)
            status_key = status.strip().lower()
            canonical_status = _STATUS_FROM_MD.get(status_key, "pending")
            kind, d, label = _parse_deadline(prazo)
            parsed[num_int] = ParsedTask(
                number=num_int,
                title=title.strip(),
                category=_normalize_category(cat),
                priority=current_priority,
                status=canonical_status,
                deadline_kind=kind,
                deadline_date=d,
                deadline_label=label,
                ref=(ref.strip() if ref.strip() not in ("", "—") else None),
            )

    # Segunda passe: varre todas as descrições procurando "#N depende de #M"
    for p in parsed.values():
        m = _DEP_RE.search(p.title)
        if m:
            # Tenta extrair os dois números possíveis (padrões variados)
            nums = [int(g) for g in m.groups() if g]
            # Filtra: primeiro = child (o próprio), segundo = parent
            candidates = [n for n in nums if n != p.number]
            if candidates:
                p.parent_number = candidates[0]

    return sorted(parsed.values(), key=lambda x: x.number)


def parse_file(path: Path) -> list[ParsedTask]:
    return parse_tarefas_md(path.read_text(encoding="utf-8"))

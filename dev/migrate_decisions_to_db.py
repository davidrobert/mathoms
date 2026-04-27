#!/usr/bin/env python3
"""dev/migrate_decisions_to_db.py — migrator one-shot (A7.2a · ADR-136).

Lê ``config/decisions.md`` (markdown table), parseia cada linha ``| Dxx |``
e cria uma row em ``decisions`` + um ``DecisionEvent`` ``Created`` no
workspace alvo. Usado **uma vez** no workspace piloto antes de remover
``config/decisions.md`` do git.

Idempotente: se ``code`` já existe no workspace, skipa com log + segue.

Uso::

    python dev/migrate_decisions_to_db.py --workspace-id <UUID> [--dry-run]

NÃO generalizar — script descartável. Não importar em backend/app.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.application.decisions import create_decision  # noqa: E402
from backend.app.core.database import async_session  # noqa: E402
from backend.app.repositories.decision_repository import (  # noqa: E402
    DecisionRepository,
)
from backend.app.schemas.dto.decision import DecisionCreateCommand  # noqa: E402

DECISIONS_MD = _REPO_ROOT / "config" / "decisions.md"

logger = logging.getLogger("mathoms.migrator.decisions")


@dataclass(frozen=True)
class ParsedDecision:
    """Linha parseada do markdown table (não persistida ainda)."""

    code: str
    title: str
    rationale: Optional[str]
    status: str


_LINE_RE = re.compile(r"^\|\s*(D\d{2})\s*\|", re.MULTILINE)


def _parse_table(markdown: str) -> list[ParsedDecision]:
    """Itera linhas ``| Dxx | ... |`` da seção DECISÕES CONFIRMADAS."""
    parsed: list[ParsedDecision] = []
    for line in markdown.splitlines():
        if not _LINE_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        code, title, _data, detalhes, status_raw = cells[:5]
        parsed.append(
            ParsedDecision(
                code=code,
                title=title,
                rationale=detalhes or None,
                status=_normalize_status(status_raw),
            )
        )
    return parsed


def _normalize_status(raw: str) -> str:
    """Mapeia status humano (markdown) → enum DB.

    Prioridade:
    - "Superseded" → "Superseded"
    - "executado" → "Executado"
    - "decidido" (qualquer posição na string) → "Decidido"
    - "pendente" → "Pendente"
    Default defensivo: "Pendente".
    """
    cleaned = raw.replace("**", "").strip().lower()
    if "superseded" in cleaned:
        return "Superseded"
    if "executado" in cleaned:
        return "Executado"
    if "descartad" in cleaned:
        return "Descartado"
    if "decidido" in cleaned:
        return "Decidido"
    if "pendente" in cleaned:
        return "Pendente"
    return "Pendente"


async def _migrate(workspace_id: str, *, dry_run: bool) -> int:
    """Roda migração. Retorna nº de rows criadas (skipa duplicates)."""
    if not DECISIONS_MD.is_file():
        logger.error("config/decisions.md não encontrado em %s", DECISIONS_MD)
        return 0

    parsed = _parse_table(DECISIONS_MD.read_text(encoding="utf-8"))
    logger.info("parsed %d decisions from markdown", len(parsed))

    created = 0
    async with async_session() as session:
        repo = DecisionRepository(session)
        for item in parsed:
            existing = await repo.get_by_code(workspace_id, item.code)
            if existing is not None:
                logger.info(
                    "skip %s — já existe (id=%s, status=%s)",
                    item.code,
                    existing.id,
                    existing.status,
                )
                continue
            if dry_run:
                logger.info("[dry-run] would create %s: %s", item.code, item.title)
                created += 1
                continue
            cmd = DecisionCreateCommand(
                code=item.code,
                title=item.title,
                rationale=item.rationale,
                status=item.status,
            )
            await create_decision(
                cmd,
                workspace_id=workspace_id,
                repo=repo,
                actor="system:migrator",
            )
            await session.commit()
            created += 1
            logger.info("created %s status=%s", item.code, item.status)

    return created


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="UUID do workspace alvo",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não persiste — apenas loga o que seria criado",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args()
    created = asyncio.run(_migrate(args.workspace_id, dry_run=args.dry_run))
    logger.info("done — %d rows %s", created, "(dry-run)" if args.dry_run else "created")
    return 0


if __name__ == "__main__":
    sys.exit(main())

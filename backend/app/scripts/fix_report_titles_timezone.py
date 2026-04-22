"""Corrige títulos de relatórios gerados com datetime UTC em vez de horário local.

Problema: até o fix do pipeline_task.py, o título era gerado com
    datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
o que embutia UTC no título enquanto o frontend exibe horários locais (BRT = UTC-3).

Solução: regenerar o título a partir de `report.created_at` convertido para o
fuso-horário configurado (padrão: America/Sao_Paulo). Só altera relatórios cujo
título segue exatamente o padrão "Relatório YYYY-MM-DD HH:MM".

Usage:
    .venv/bin/python -m backend.app.scripts.fix_report_titles_timezone --dry-run
    .venv/bin/python -m backend.app.scripts.fix_report_titles_timezone --apply
    .venv/bin/python -m backend.app.scripts.fix_report_titles_timezone --apply --tz America/Sao_Paulo
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.report import Report

TITLE_PATTERN = re.compile(r"^Relatório \d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


async def run(dry_run: bool, tz_name: str) -> None:
    local_tz = ZoneInfo(tz_name)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Report).order_by(Report.created_at))
        reports = result.scalars().all()

        to_fix = [r for r in reports if TITLE_PATTERN.match(r.title)]

        if not to_fix:
            print("Nenhum relatório com título no formato UTC encontrado.")
            return

        print(f"Relatórios a corrigir: {len(to_fix)} de {len(reports)} total\n")

        for report in to_fix:
            created_utc = report.created_at
            if created_utc.tzinfo is None:
                created_utc = created_utc.replace(tzinfo=timezone.utc)
            created_local = created_utc.astimezone(local_tz)
            new_title = f"Relatório {created_local.strftime('%Y-%m-%d %H:%M')}"

            print(f"  [{report.id[:8]}] {report.title!r}  →  {new_title!r}")

            if not dry_run:
                report.title = new_title

        if dry_run:
            print("\n[dry-run] Nenhuma alteração aplicada. Use --apply para salvar.")
        else:
            await db.commit()
            print(f"\n{len(to_fix)} título(s) corrigido(s) e salvos.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corrige títulos de relatórios de UTC → horário local"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Aplica as alterações (padrão: dry-run)"
    )
    parser.add_argument(
        "--tz", default="America/Sao_Paulo", help="Fuso-horário alvo (padrão: America/Sao_Paulo)"
    )
    args = parser.parse_args()

    asyncio.run(run(dry_run=not args.apply, tz_name=args.tz))


if __name__ == "__main__":
    main()

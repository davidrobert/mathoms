"""Blast-radius do off-by-one exercício↔ano-base (ADR-274) — READ-ONLY, só contagens + workspace_id (sem valores/CPF/FERNET_KEY)."""

from __future__ import annotations

import argparse

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.crypto import decrypt_artifact_payload
from pipeline.domain.services.patrimonio_types import _max_value_year

_BASELINE_STAGES = ("E1.5c", "consolidate_baseline")
_BASELINE_KEY = "baseline_patrimonial"


def _summary_year(baseline: dict) -> str | None:
    """Maior ano numérico em ``patrimonio_por_ano`` (chave de resumo)."""
    years = [k for k in (baseline.get("patrimonio_por_ano") or {}) if str(k).isdigit()]
    return max(years, key=int) if years else None


def _is_divergent(baseline: dict) -> bool:
    value_year = _max_value_year(baseline)
    summary_year = _summary_year(baseline)
    return bool(value_year and summary_year and value_year != summary_year)


def _scan() -> tuple[int, list[str]]:
    """Retorna (total inspecionado, workspace_ids divergentes)."""
    total = 0
    divergent_ws: list[str] = []
    with SyncSessionLocal() as session:
        rows = (
            session.query(PipelineArtifact)
            .filter(PipelineArtifact.stage.in_(_BASELINE_STAGES))
            .filter(PipelineArtifact.artifact_key == _BASELINE_KEY)
            .all()
        )
        for row in rows:
            total += 1
            if _is_divergent(decrypt_artifact_payload(row.content_json)):
                divergent_ws.append(str(row.workspace_id))
    return total, divergent_ws


def audit(*, list_ids: bool = False) -> int:
    """Varre baselines E1.5c e conta divergências. Retorna nº de divergentes."""
    total, divergent_ws = _scan()
    divergent = len(divergent_ws)
    print(f"baselines E1.5c inspecionados: {total}")
    print(f"divergentes (ADR-274): {divergent}")
    if list_ids and divergent_ws:
        print("workspace_ids afetados:")
        for ws in sorted(set(divergent_ws)):
            print(f"  - {ws}")
    return divergent


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ADR-274 (read-only).")
    parser.add_argument(
        "--list", action="store_true", help="lista workspace_ids afetados (sem valores)"
    )
    args = parser.parse_args()
    audit(list_ids=args.list)


if __name__ == "__main__":
    main()

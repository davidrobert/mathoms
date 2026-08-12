#!/usr/bin/env python3
"""Backfill one-shot da supersessão de PropertyIdentity órfãs (ADR-324).

Re-roda ``resolve_dedup_winner_by_property_id`` sobre as rows do DB para
descobrir os GRUPOS, mas o vencedor de cada grupo é o pid presente no
baseline consolidado mais recente — grupo sem exatamente 1 âncora é
ABORTADO, nunca eleito por ordem de criação (a ordem de criação elege row
de run falho). Aplica via o MESMO ``reconcile_supersession`` do
forward-path. Dry-run por default; ``--apply`` executa. Idempotente: 2ª
execução com ``--apply`` = zero mudanças.

O baseline é lido DECRIPTADO (envelope Fernet, ADR-231): ler
``content_json`` cru devolvia o envelope, o backfill via ``{}`` e a eleição
degradava em silêncio.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MATHOMS_JWT_SECRET", "x" * 32)


class BaselineUnreadableError(RuntimeError):
    """Baseline consolidado existe mas o payload não tem o shape esperado — o
    backfill não pode eleger vencedor às cegas (ADR-324 · PR0)."""


def _load_identities(session, workspace_id: str):
    from sqlalchemy import select

    from backend.app.models import PropertyIdentity

    stmt = (
        select(PropertyIdentity)
        .where(PropertyIdentity.workspace_id == workspace_id)
        .order_by(PropertyIdentity.created_at.asc())
    )
    return list(session.execute(stmt).scalars().all())


def _baseline_row(session, workspace_id: str):
    from sqlalchemy import select

    from backend.app.models.pipeline_artifact import PipelineArtifact
    from pipeline.artifact_store import stage_aliases

    candidates = set(stage_aliases("consolidate_baseline")) | {"E1.5c", "consolidate_baseline"}
    stmt = (
        select(PipelineArtifact.content_json)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(sorted(candidates)),
            PipelineArtifact.artifact_key == "baseline_patrimonial",
        )
        .order_by(PipelineArtifact.created_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _require_consolidados(payload: object) -> dict:
    """Ausência de baseline é warn; baseline ilegível é erro — não confunda os dois."""
    imoveis = payload.get("imoveis_consolidados") if isinstance(payload, dict) else None
    if isinstance(imoveis, list):
        return payload  # type: ignore[return-value]
    keys = sorted(payload.keys()) if isinstance(payload, dict) else "<não-dict>"
    raise BaselineUnreadableError(
        "baseline consolidado ilegível: esperado dict com 'imoveis_consolidados': list[dict], "
        f"veio {type(payload).__name__} com keys={keys!r} e "
        f"imoveis_consolidados={type(imoveis).__name__}"
    )


def _load_latest_baseline(session, workspace_id: str) -> dict | None:
    """Payload decriptado do baseline consolidado (ADR-231); None se o workspace nunca rodou E1.5c."""
    from backend.app.services.security.crypto import read_artifact_content

    raw = _baseline_row(session, workspace_id)
    if raw is None:
        return None
    return _require_consolidados(read_artifact_content(raw))


def _baseline_pids(baseline: dict | None) -> frozenset[str]:
    entries = (baseline or {}).get("imoveis_consolidados") or []
    return frozenset(str(e.get("property_id")) for e in entries if e.get("property_id"))


# A coluna `endereco_canonical` guarda a forma da ERA em que a row nasceu, e é
# justamente a fragmentação que impede o agrupamento (ADR-375 §Tabela de eras).
# O sweep agrupa pela chave RECOMPUTADA da descrição-fonte — in-memory, nunca
# persistida: gravá-la faria a row mais antiga vencer o match e trocaria o
# conjunto de zumbis em vez de eliminá-lo (ADR-375 §Decisão 7).
def _synthetic_entries(identities, baseline_payload: dict | None) -> list[dict]:
    """Espelha `_dedup_entries` do forward-path, com o canonical recomputado da descrição."""
    from pipeline.domain.services.endereco_canonicalizer import canonicalize

    valores = {
        im.get("property_id"): im.get("valores_31_12") or {}
        for im in (baseline_payload or {}).get("imoveis_consolidados") or []
    }
    return [
        {
            "property_id": ident.id,
            "codigo_rfb": ident.codigo_rfb,
            "endereco_canonical": canonicalize(ident.descricao_sample or "")
            or ident.endereco_canonical,
            "descricao": ident.descricao_sample,
            "valores_31_12": valores.get(ident.id, {}),
        }
        for ident in identities
    ]


def _groups(winner_by_pid: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for pid, winner in winner_by_pid.items():
        grouped[winner].append(pid)
    return {winner: sorted(members) for winner, members in grouped.items()}


def _abort_record(members: list[str], anchored: list[str]) -> dict:
    return {
        "group": [_short(pid) for pid in members],
        "baseline_anchors": [_short(pid) for pid in anchored],
        "reason": (
            f"esperado exatamente 1 pid do grupo no baseline consolidado, veio {len(anchored)}"
        ),
    }


def _elect_by_baseline(
    grouped: dict[str, list[str]], baseline_pids: frozenset[str]
) -> tuple[dict[str, str], list[dict]]:
    """Vencedor = único pid do grupo no baseline; 0 ou 2+ âncoras aborta o grupo inteiro."""
    winners: dict[str, str] = {}
    aborted: list[dict] = []
    for _, members in sorted(grouped.items()):
        if len(members) == 1:
            continue
        anchored = [pid for pid in members if pid in baseline_pids]
        if len(anchored) != 1:
            aborted.append(_abort_record(members, anchored))
            continue
        winners.update({pid: anchored[0] for pid in members})
    return winners, aborted


def _short(pid: str) -> str:
    return str(pid)[:8]


def _canonical_probe(descricao: str | None) -> tuple[str | None, str | None]:
    """Canonical recomputado + complemento — o par que denuncia row envenenada da era-1."""
    from pipeline.domain.services.canonical_fuzzy_match import extract_complemento
    from pipeline.domain.services.endereco_canonicalizer import canonicalize

    return (canonicalize(descricao or ""), extract_complemento(descricao))


def _row_report(ident, baseline_pids: frozenset[str], losers: dict[str, str]) -> dict:
    """Uma linha por identity. Sem `descricao_sample` nem valores — canonical basta pro gate."""
    recomputed, complemento = _canonical_probe(ident.descricao_sample)
    return {
        "pid": _short(ident.id),
        "codigo_rfb": ident.codigo_rfb,
        "canonical_stored": ident.endereco_canonical,
        "canonical_recomputed": recomputed,
        "complemento": complemento,
        "in_baseline": ident.id in baseline_pids,
        "already_superseded": ident.superseded_at is not None,
        "loser_of": _short(losers[ident.id]) if ident.id in losers else None,
    }


def _plan(identities, winner_by_pid: dict[str, str], baseline_pids: frozenset[str]) -> dict:
    known = {ident.id for ident in identities}
    losers = {
        pid: winner
        for pid, winner in winner_by_pid.items()
        if pid != winner and pid in known and winner in known
    }
    already = {ident.id for ident in identities if ident.superseded_at is not None}
    return {
        "rows": len(identities),
        "losers": losers,
        "to_supersede": sorted(set(losers) - already),
        "to_clear": sorted(already - set(losers)),
        "identities": [_row_report(ident, baseline_pids, losers) for ident in identities],
    }


def _session_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    default_db = REPO_ROOT / "mathoms.db"
    db_url = os.environ.get("MATHOMS_DATABASE_URL_SYNC", f"sqlite:///{default_db}")
    return sessionmaker(bind=create_engine(db_url, future=True), future=True)


# O sweep observa a tabela inteira do workspace — é justamente o que o
# forward-path não faz (ADR-376). Sem declarar isso, as rows fora do escopo
# ficariam intocáveis e o sweep não teria efeito algum.
def _apply(session, workspace_id: str, winner_by_pid: dict[str, str], identities) -> dict:
    from backend.app.services.db_property_supersession_writer import (
        DBPropertySupersessionWriter,
    )
    from pipeline.domain.types.property_supersession import SupersessionScope

    scope = SupersessionScope(
        workspace_id=workspace_id,
        winner_by_pid=winner_by_pid,
        observed_pids=frozenset(ident.id for ident in identities),
    )
    outcome = DBPropertySupersessionWriter(session).reconcile_supersession(scope)
    return {
        "superseded": outcome.superseded,
        "cleared": outcome.cleared,
        "overrides_repointed": outcome.overrides_repointed,
        "overrides_merged": outcome.overrides_merged,
    }


def _winner_map(identities, baseline: dict | None) -> tuple[dict[str, str], list[dict]]:
    from pipeline.domain.services.imoveis_dedup import (
        resolve_dedup_winner_by_property_id,
    )

    proposed = resolve_dedup_winner_by_property_id(_synthetic_entries(identities, baseline))
    return _elect_by_baseline(_groups(proposed), _baseline_pids(baseline))


def _process(workspace_id: str, dry_run: bool) -> dict:
    with _session_factory()() as session:
        identities = _load_identities(session, workspace_id)
        baseline = _load_latest_baseline(session, workspace_id)
        if baseline is None:
            print("[WARN] baseline ausente — todo grupo aborta (sem âncora)", file=sys.stderr)
        winner_by_pid, aborted = _winner_map(identities, baseline)
        report = {
            "workspace_id": workspace_id,
            "dry_run": dry_run,
            "baseline_found": baseline is not None,
            "aborted_groups": aborted,
            **_plan(identities, winner_by_pid, _baseline_pids(baseline)),
        }
        if not dry_run:
            report["applied"] = _apply(session, workspace_id, winner_by_pid, identities)
        return report


def _clear_supersession(workspace_id: str, property_id: str) -> dict:
    """Des-supersede uma row: reversão declarada, para não virar SQL manual em prod."""
    with _session_factory()() as session:
        identities = _load_identities(session, workspace_id)
        alvo = next((i for i in identities if i.id == property_id), None)
        if alvo is None:
            raise BaselineUnreadableError(
                f"property_id não encontrado no workspace: esperado um id de "
                f"property_identity de {workspace_id}, veio {property_id!r}"
            )
        antes = alvo.superseded_by_id
        alvo.superseded_at = None
        alvo.superseded_by_id = None
        session.commit()
        return {"cleared": property_id, "era_superseded_by": antes}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_id")
    parser.add_argument("--apply", action="store_true", help="executa (default: dry-run)")
    parser.add_argument(
        "--clear",
        metavar="PROPERTY_ID",
        help="reverte a supersessão de uma row (escape hatch de ops)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.clear:
            report = _clear_supersession(args.workspace_id, args.clear)
        else:
            report = _process(args.workspace_id, dry_run=not args.apply)
    except BaselineUnreadableError as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 2
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

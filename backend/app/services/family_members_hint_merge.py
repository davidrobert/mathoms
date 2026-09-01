"""Funde contas do artefato E1 no `family_members.json` como hint tier 1 ([[ADR-430]] §2)."""

# A tabela `bank_accounts` é CURADA pelo usuário ([[ADR-229]] §1: o clique humano
# promove tier 1 → tier 5) e o pipeline não escreve nela. O defeito da A40.l96 era
# o pipeline publicar a AUSÊNCIA de curadoria como fato sobre a família: com a
# tabela vazia, `banco_membro`/`contas` chegavam vazios ao E4 e o relatório
# afirmava que ~49% da carteira não tinha dono. Aqui o hint entra marcado, sem
# nunca sobrescrever curadoria nem ressuscitar o que o usuário recusou.

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.application.family_member.irpf_hint_policy import (
    build_existing_indexes,
    classificar_hint,
    conta_normalizada,
    dismissed_keys_for_year,
)
from backend.app.models.family_member import WorkspaceIrpfSuggestionDismissal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.security.crypto import read_artifact_content
from pipeline.artifact_store import stage_aliases
from pipeline.domain.services.member_name_resolver import MemberNameResolver

_logger = logging.getLogger("mathoms.family_members_hint_merge")


def _latest_e1_row(workspace_id: str, db: Session) -> Optional[PipelineArtifact]:
    stmt = (
        select(PipelineArtifact)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(stage_aliases("extract_members")),
            PipelineArtifact.artifact_key == "members",
        )
        .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _dismissals(workspace_id: str, db: Session) -> list[Any]:
    stmt = select(WorkspaceIrpfSuggestionDismissal).where(
        WorkspaceIrpfSuggestionDismissal.workspace_id == workspace_id
    )
    return list(db.execute(stmt).scalars().all())


def _chave_canonica(bruto: str, resolver: MemberNameResolver) -> str:
    """Chave curta do E1 → canônica do workspace; PRESERVA o bruto sem match."""
    # Descartar o hint não-resolvível parece limpo e fabrica atribuição FALSA:
    # instituição com 2 hints, um resolvível e outro não, viraria singleton e
    # seria atribuída ao membro errado. Preservado, ela vira `ambiguous` — que é
    # honesto. Limite conhecido: `_MIN_SUBSTRING_LEN` é 5, então chave de ≤4
    # chars cujo `short_name` difira não resolve (A40.l96 §Achados do PR2c).
    canonica = resolver.resolve(bruto).canonical_key
    if canonica:
        return canonica
    _logger.warning(
        "hint_merge.chave_nao_resolvida",
        extra={"event": "hint_merge.chave_nao_resolvida", "chave_curta": bruto},
    )
    return bruto


def _conta_hint(conta: dict[str, Any], member_key: str) -> dict[str, Any]:
    return {
        "member_key": member_key,
        "institution_code": conta.get("institution_code"),
        "account_type": conta.get("account_type") or "",
        "account_number_raw": conta.get("account_number_raw"),
        "agency": conta.get("agency"),
        "is_joint": bool(conta.get("is_joint")),
        "co_titulares": list(conta.get("co_titulares") or ()),
        "origem": "irpf_hint",
    }


def _irpf_year(row: PipelineArtifact) -> int:
    """V0 da [[ADR-229]]: IRPF do ano Y é declarado em Mar-Abr de Y+1."""
    return (row.created_at.year - 1) if row.created_at else 0


def _hints_aceitos(
    contas_hint: list[dict[str, Any]],
    blob: dict[str, Any],
    *,
    ano: int,
    members: list[Any],
    recusadas: set,
) -> list[dict[str, Any]]:
    """Aplica a política e canonicaliza — a REGRA é de `irpf_hint_policy`."""
    by_bank_num, _ = build_existing_indexes(members)
    resolver = MemberNameResolver.from_family_config(blob)
    return [
        _conta_hint(c, _chave_canonica(str(c.get("member_key") or ""), resolver))
        for c in contas_hint
        if classificar_hint(c, irpf_year=ano, by_bank_num=by_bank_num, dismissed_keys=recusadas)
        == "emit"
    ]


def _log_merge(blob: dict[str, Any], candidatas: int, aceitas: int, ano: int) -> None:
    _logger.info(
        "hint_merge.resultado",
        extra={
            "event": "hint_merge.resultado",
            "curadas": len(blob.get("contas") or []),
            "hint_candidatas": candidatas,
            "hint_aceitas": aceitas,
            "irpf_year": ano,
        },
    )


def merge_irpf_hints(
    blob: dict[str, Any], *, workspace_id: str, members: list[Any], db: Session
) -> dict[str, Any]:
    """Acrescenta a `blob["contas"]` os hints que a UI ofereceria — e só eles."""
    row = _latest_e1_row(workspace_id, db)
    if row is None:
        return blob
    contas_hint = (read_artifact_content(row.content_json) or {}).get("contas") or []
    if not contas_hint:
        return blob
    ano = _irpf_year(row)
    recusadas = dismissed_keys_for_year(_dismissals(workspace_id, db), ano)
    novas = _hints_aceitos(contas_hint, blob, ano=ano, members=members, recusadas=recusadas)
    _log_merge(blob, len(contas_hint), len(novas), ano)
    if not novas:
        return blob
    return {**blob, "contas": [*(blob.get("contas") or []), *novas]}

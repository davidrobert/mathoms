"""ADR-229 — use case ``get_irpf_suggestions`` (artifact E1 → cards de pre-fill)."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol

from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.application.family_member.irpf_hint_policy import (
    build_existing_indexes,
    classificar_hint,
    conta_normalizada,
    dismissed_keys_for_year,
    normalize_account_digits,
)
from backend.app.schemas.dto.family_member import (
    IrpfSuggestionItem,
    SuggestionsFromIrpfResponse,
)


@dataclass(frozen=True)
class IrpfArtifactPayload:
    """Snapshot mínimo do artifact E1 consumido pelo use case."""

    irpf_year: int
    processed_at: datetime
    contas: list[dict[str, Any]] = field(default_factory=list)
    membros: dict[str, dict[str, Any]] = field(default_factory=dict)


class IrpfArtifactSourceProtocol(Protocol):
    """Boundary ADR-097: handler injeta leitura de PipelineArtifact."""

    async def get_latest(self, workspace_id: str) -> Optional[IrpfArtifactPayload]: ...


class InstitutionLabelResolverProtocol(Protocol):
    """Mapa ``institution_code → display name`` (institution_catalog)."""

    async def resolve(self, codes: list[str]) -> dict[str, str]: ...


_DIGITS_RE = re.compile(r"\D")

_normalize = normalize_account_digits


def _mask_cpf(cpf: Optional[str] = None) -> Optional[str]:
    if not cpf:
        return None
    digits = _DIGITS_RE.sub("", cpf)
    if len(digits) != 11:
        return None
    return f"***.{digits[3:6]}.{digits[6:9]}-**"


def _empty_response(irpf_year: int = 0) -> SuggestionsFromIrpfResponse:
    return SuggestionsFromIrpfResponse(
        irpf_year=irpf_year,
        processed_at=None,
        suggestions=[],
        total_filtered_exact_match=0,
        total_dismissed=0,
    )


def _detect_collision(
    by_bank_member: dict[tuple[str, str], list[Any]],
    *,
    inst: str,
    member_key: str,
    norm: Optional[str],
) -> tuple[str, Optional[str]]:
    for acc in by_bank_member.get((inst, member_key), []):
        if _normalize(acc.account_number) != norm:
            return "partial_collision", acc.id
    return "new", None


def _member_full_name(member_info: dict[str, Any], fallback: str) -> str:
    return member_info.get("nome_completo") or member_info.get("nome_curto") or fallback


def _conta_field_payload(
    conta: dict[str, Any], norm: Optional[str] = None
) -> dict[str, Optional[str]]:
    return {
        "account_type": conta.get("account_type") or "corrente",
        "agency": conta.get("agency"),
        "account_number_raw": conta.get("account_number_raw"),
        "account_number_norm": norm,
    }


@dataclass
class _SuggestionBuildArgs:
    conta: dict[str, Any]
    payload: IrpfArtifactPayload
    norm: Optional[str]
    inst: str
    member_key: str
    labels: dict[str, str]
    match_kind: str
    collision_id: Optional[str] = None


def _build_suggestion(args: _SuggestionBuildArgs) -> IrpfSuggestionItem:
    info = args.payload.membros.get(args.member_key, {})
    return IrpfSuggestionItem(
        institution_code=args.inst,
        institution_label=args.labels.get(args.inst) or args.inst,
        member_key=args.member_key,
        member_full_name=_member_full_name(info, args.member_key),
        cpf_titular_masked=_mask_cpf(info.get("cpf")),
        irpf_year=args.payload.irpf_year,
        match_kind=args.match_kind,  # type: ignore[arg-type]
        collision_with_account_id=args.collision_id,
        **_conta_field_payload(args.conta, args.norm),
    )


_conta_normalized = conta_normalizada


@dataclass
class _IrpfFilterContext:
    payload: IrpfArtifactPayload
    by_bank_num: dict[tuple[str, str], Any]
    by_bank_member: dict[tuple[str, str], list[Any]]
    dismissed_keys: set[tuple[int, str, Optional[str]]]
    labels: dict[str, str]


def _build_args(
    conta: dict[str, Any],
    ctx: _IrpfFilterContext,
    inst: str,
    member_key: str,
    norm: Optional[str] = None,
) -> _SuggestionBuildArgs:
    match_kind, collision_id = _detect_collision(
        ctx.by_bank_member, inst=inst, member_key=member_key, norm=norm
    )
    return _SuggestionBuildArgs(
        conta=conta,
        payload=ctx.payload,
        norm=norm,
        inst=inst,
        member_key=member_key,
        labels=ctx.labels,
        match_kind=match_kind,
        collision_id=collision_id,
    )


def _classify_conta(
    conta: dict[str, Any], ctx: _IrpfFilterContext
) -> tuple[Optional[IrpfSuggestionItem], str]:
    """Devolve (sugestão|None, motivo). A REGRA é de `irpf_hint_policy` (A40.l96)."""
    decisao = classificar_hint(
        conta,
        irpf_year=ctx.payload.irpf_year,
        by_bank_num=ctx.by_bank_num,
        dismissed_keys=ctx.dismissed_keys,
    )
    if decisao != "emit":
        return None, decisao
    inst = str(conta.get("institution_code"))
    member_key = str(conta.get("member_key"))
    args = _build_args(conta, ctx, inst, member_key, _conta_normalized(conta))
    return _build_suggestion(args), "emit"


def _institution_codes(contas: list[dict[str, Any]]) -> list[str]:
    return sorted({c.get("institution_code", "") for c in contas if c.get("institution_code")})


async def _load_filter_context(
    payload: IrpfArtifactPayload,
    *,
    repo: FamilyMemberRepositoryProtocol,
    institution_labels: InstitutionLabelResolverProtocol,
    workspace_id: str,
) -> _IrpfFilterContext:
    members = await repo.list_by_workspace(workspace_id)
    dismissals = await repo.list_irpf_dismissals(workspace_id)
    by_bank_num, by_bank_member = build_existing_indexes(members)
    return _IrpfFilterContext(
        payload=payload,
        by_bank_num=by_bank_num,
        by_bank_member=by_bank_member,
        dismissed_keys=dismissed_keys_for_year(dismissals, payload.irpf_year),
        labels=await institution_labels.resolve(_institution_codes(payload.contas)),
    )


def _apply_filters(
    contas: list[dict[str, Any]], ctx: _IrpfFilterContext
) -> tuple[list[IrpfSuggestionItem], int, int]:
    suggestions: list[IrpfSuggestionItem] = []
    counts = {"exact": 0, "dismissed": 0}
    for conta in contas:
        item, reason = _classify_conta(conta, ctx)
        if reason in counts:
            counts[reason] += 1
        if item is not None:
            suggestions.append(item)
    return suggestions, counts["exact"], counts["dismissed"]


def _build_response(
    payload: IrpfArtifactPayload,
    items: list[IrpfSuggestionItem],
    n_exact: int,
    n_dismissed: int,
) -> SuggestionsFromIrpfResponse:
    return SuggestionsFromIrpfResponse(
        irpf_year=payload.irpf_year,
        processed_at=payload.processed_at,
        suggestions=items,
        total_filtered_exact_match=n_exact,
        total_dismissed=n_dismissed,
    )


async def get_irpf_suggestions(
    workspace_id: str,
    *,
    repo: FamilyMemberRepositoryProtocol,
    irpf_source: IrpfArtifactSourceProtocol,
    institution_labels: InstitutionLabelResolverProtocol,
) -> SuggestionsFromIrpfResponse:
    """Sugestões de contas a partir do IRPF mais recente do workspace (ADR-229 §4)."""
    payload = await irpf_source.get_latest(workspace_id)
    if payload is None or not payload.contas:
        return _empty_response(payload.irpf_year if payload else 0)
    ctx = await _load_filter_context(
        payload, repo=repo, institution_labels=institution_labels, workspace_id=workspace_id
    )
    items, n_exact, n_dismissed = _apply_filters(payload.contas, ctx)
    return _build_response(payload, items, n_exact, n_dismissed)

"""Application service do card Exposição Cambial V2 (ADR-224 §5; read-time: E5 artifact + catalog + overrides; agregação não materializada em E5 — pattern jurisprudência ADR-215 §6)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import PipelineArtifact
from backend.app.models.asset_catalog import AssetCatalog, WorkspaceAssetOverride
from backend.app.schemas.dto.exposicao_cambial import (
    AssetOverrideCommand,
    AssetOverrideResponse,
    ExposicaoCambialAtivoDTO,
    ExposicaoCambialPorMoedaDTO,
    ExposicaoCambialResponse,
)
from backend.app.services.crypto import read_artifact_content
from backend.app.services.lastro_resolver import (
    AssetQuery,
    CatalogEntry,
    OverrideEntry,
    resolve_lastro_with_source,
)

THRESHOLD_VERDE_PCT = 10.0
THRESHOLD_AMARELO_PCT = 5.0


def _tier_from_pct(pct: float, has_data: bool) -> str:
    if not has_data:
        return "empty"
    if pct >= THRESHOLD_VERDE_PCT:
        return "verde"
    if pct >= THRESHOLD_AMARELO_PCT:
        return "amarelo"
    return "vermelho"


def _to_decimal(v: Any) -> Decimal:
    if v is None or isinstance(v, bool):
        return Decimal(0)
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (ValueError, TypeError):
        return Decimal(0)


async def _load_catalog(db: AsyncSession, version: int = 1) -> list[CatalogEntry]:
    stmt = select(AssetCatalog).where(AssetCatalog.catalog_version == version)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        CatalogEntry(
            ticker=r.ticker,
            cnpj=r.cnpj,
            match_keyword=r.match_keyword,
            asset_class=r.asset_class,
            lastro_moeda=r.lastro_moeda,
        )
        for r in rows
    ]


async def _load_overrides(db: AsyncSession, workspace_id: str) -> list[OverrideEntry]:
    stmt = select(WorkspaceAssetOverride).where(WorkspaceAssetOverride.workspace_id == workspace_id)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        OverrideEntry(
            match_kind=r.match_kind,
            asset_match_key=r.asset_match_key,
            lastro_moeda=r.lastro_moeda,
        )
        for r in rows
    ]


async def _load_latest_e5_artifact(
    db: AsyncSession, workspace_id: str
) -> Optional[PipelineArtifact]:
    stmt = (
        select(PipelineArtifact)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage == "analyze_finances",
        )
        .order_by(PipelineArtifact.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _build_asset_query(pos: dict) -> AssetQuery:
    ticker = pos.get("ticker") or pos.get("codigo")
    cnpj = pos.get("cnpj")
    descricao = pos.get("descricao") or pos.get("nome") or pos.get("tipo")
    asset_class = pos.get("classe") or pos.get("tipo") or "Outros"
    return AssetQuery(
        ticker=str(ticker) if ticker else None,
        cnpj=str(cnpj) if cnpj else None,
        descricao=str(descricao) if descricao else None,
        asset_class_fallback=str(asset_class),
    )


def _resolve_with_source(
    pos: dict, catalog: list[CatalogEntry], overrides: list[OverrideEntry]
) -> tuple[str, str]:
    """Resolve lastro e retorna (lastro_moeda, source)."""
    return resolve_lastro_with_source(_build_asset_query(pos), catalog=catalog, overrides=overrides)


def _ativo_dto(pos: dict, valor_brl: Decimal, moeda: str, source: str) -> ExposicaoCambialAtivoDTO:
    nome = str(pos.get("descricao") or pos.get("nome") or pos.get("tipo") or "")
    return ExposicaoCambialAtivoDTO(
        nome=nome,
        moeda=moeda,
        valor_brl=round(valor_brl, 2),
        tipo="ativo",
        lastro_source=source,
    )


def _caixa_to_dto(d: dict) -> ExposicaoCambialAtivoDTO:
    return ExposicaoCambialAtivoDTO(
        nome=str(d.get("conta") or "caixa"),
        moeda=str(d.get("moeda") or "").upper(),
        valor_brl=round(_to_decimal(d.get("valor_brl")), 2),
        tipo="caixa",
        lastro_source="catalog",
    )


def _aggregate_positions(
    posicoes: list[dict],
    catalog: list[CatalogEntry],
    overrides: list[OverrideEntry],
) -> tuple[dict[str, Decimal], list[ExposicaoCambialAtivoDTO]]:
    por_moeda: dict[str, Decimal] = {}
    contribuintes: list[ExposicaoCambialAtivoDTO] = []
    for pos in posicoes:
        if not isinstance(pos, dict):
            continue
        valor = _to_decimal(pos.get("valor") or pos.get("valor_31_12_ano_base"))
        if valor <= Decimal(0):
            continue
        moeda, source = _resolve_with_source(pos, catalog, overrides)
        if moeda == "BRL":
            continue
        por_moeda[moeda] = por_moeda.get(moeda, Decimal(0)) + valor
        contribuintes.append(_ativo_dto(pos, valor, moeda, source))
    return por_moeda, contribuintes


def _aggregate_caixa(
    caixa_detalhes: list[dict],
) -> tuple[dict[str, Decimal], list[ExposicaoCambialAtivoDTO]]:
    por_moeda: dict[str, Decimal] = {}
    contribuintes: list[ExposicaoCambialAtivoDTO] = []
    for d in caixa_detalhes or []:
        moeda = str(d.get("moeda") or "").upper()
        if not moeda or moeda == "BRL":
            continue
        valor = _to_decimal(d.get("valor_brl"))
        if valor <= Decimal(0):
            continue
        por_moeda[moeda] = por_moeda.get(moeda, Decimal(0)) + valor
        contribuintes.append(_caixa_to_dto(d))
    return por_moeda, contribuintes


def _build_por_moeda_dtos(
    por_moeda: dict[str, Decimal], total: Decimal
) -> list[ExposicaoCambialPorMoedaDTO]:
    return [
        ExposicaoCambialPorMoedaDTO(
            moeda=m,
            valor_brl=round(v, 2),
            share_pct=float(round(v / total * 100, 2)) if total > Decimal(0) else 0.0,
        )
        for m, v in sorted(por_moeda.items(), key=lambda x: -x[1])
        if v > Decimal(0)
    ]


def _empty_response(workspace_id: str) -> ExposicaoCambialResponse:
    return ExposicaoCambialResponse(
        workspace_id=workspace_id,
        total_brl=Decimal("0.00"),
        pct_investivel_financeiro=0.0,
        por_moeda=[],
        tier="empty",
        ativos_contribuintes=[],
        source_run_id=None,
        computed_at=datetime.now(timezone.utc),
    )


def _extract_e5_inputs(artifact: PipelineArtifact) -> tuple[list[dict], list[dict], Decimal]:
    payload = read_artifact_content(artifact.content_json) or {}
    patrimonio_full = payload.get("patrimonio_full") or {}
    investimentos = payload.get("investimentos_atuais") or {}
    posicoes = investimentos.get("dados") if isinstance(investimentos, dict) else []
    return (
        posicoes if isinstance(posicoes, list) else [],
        patrimonio_full.get("caixa_detalhes") or [],
        _to_decimal(
            patrimonio_full.get("investivel_financeiro") or patrimonio_full.get("investivel")
        ),
    )


def _merge_por_moeda(*maps: dict[str, Decimal]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for m in maps:
        for moeda, v in m.items():
            out[moeda] = out.get(moeda, Decimal(0)) + v
    return out


def _build_response(
    *,
    workspace_id: str,
    por_moeda: dict[str, Decimal],
    investivel_denom: Decimal,
    ativos: list[ExposicaoCambialAtivoDTO],
    artifact: PipelineArtifact,
) -> ExposicaoCambialResponse:
    total = sum(por_moeda.values(), Decimal(0))
    pct = float(total / investivel_denom * 100) if investivel_denom > Decimal(0) else 0.0
    return ExposicaoCambialResponse(
        workspace_id=workspace_id,
        total_brl=round(total, 2),
        pct_investivel_financeiro=round(pct, 2),
        por_moeda=_build_por_moeda_dtos(por_moeda, total),
        tier=_tier_from_pct(pct, has_data=total > Decimal(0)),
        ativos_contribuintes=ativos,
        source_run_id=str(artifact.pipeline_run_id) if artifact.pipeline_run_id else None,
        computed_at=datetime.now(timezone.utc),
    )


async def _aggregate_all(
    artifact: PipelineArtifact, db: AsyncSession, workspace_id: str
) -> tuple[dict[str, Decimal], list[ExposicaoCambialAtivoDTO], Decimal]:
    posicoes, caixa_detalhes, investivel_denom = _extract_e5_inputs(artifact)
    catalog = await _load_catalog(db, version=1)
    overrides = await _load_overrides(db, workspace_id)
    por_caixa, caixa_dtos = _aggregate_caixa(caixa_detalhes)
    por_ativos, ativo_dtos = _aggregate_positions(posicoes, catalog, overrides)
    return _merge_por_moeda(por_caixa, por_ativos), caixa_dtos + ativo_dtos, investivel_denom


def _to_override_response(row: WorkspaceAssetOverride) -> AssetOverrideResponse:
    return AssetOverrideResponse(
        id=row.id,
        workspace_id=row.workspace_id,
        match_kind=row.match_kind,
        asset_match_key=row.asset_match_key,
        lastro_moeda=row.lastro_moeda,
        override_source=row.override_source,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by_user_id=row.created_by_user_id,
    )


async def _find_override(
    db: AsyncSession, workspace_id: str, match_kind: str, asset_match_key: str
) -> Optional[WorkspaceAssetOverride]:
    stmt = select(WorkspaceAssetOverride).where(
        WorkspaceAssetOverride.workspace_id == workspace_id,
        WorkspaceAssetOverride.match_kind == match_kind,
        WorkspaceAssetOverride.asset_match_key == asset_match_key,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _new_override_row(
    workspace_id: str, command: AssetOverrideCommand, user_id: Optional[str] = None
) -> WorkspaceAssetOverride:
    now = datetime.now(timezone.utc)
    return WorkspaceAssetOverride(
        workspace_id=workspace_id,
        match_kind=command.match_kind,
        asset_match_key=command.asset_match_key,
        lastro_moeda=command.lastro_moeda,
        override_source="user_manual",
        created_by_user_id=user_id,
        created_at=now,
        updated_at=now,
    )


async def _create_override(
    db: AsyncSession,
    workspace_id: str,
    command: AssetOverrideCommand,
    user_id: Optional[str] = None,
) -> WorkspaceAssetOverride:
    row = _new_override_row(workspace_id, command, user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _update_override(
    db: AsyncSession,
    existing: WorkspaceAssetOverride,
    lastro_moeda: str,
    user_id: Optional[str] = None,
) -> WorkspaceAssetOverride:
    existing.lastro_moeda = lastro_moeda
    existing.updated_at = datetime.now(timezone.utc)
    if user_id is not None:
        existing.created_by_user_id = user_id
    await db.commit()
    await db.refresh(existing)
    return existing


async def upsert_asset_override(
    workspace_id: str,
    command: AssetOverrideCommand,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> AssetOverrideResponse:
    """Upsert sticky pattern ADR-215 — mesma `(ws, kind, key)` atualiza in-place."""
    existing = await _find_override(db, workspace_id, command.match_kind, command.asset_match_key)
    if existing is None:
        row = await _create_override(db, workspace_id, command, user_id)
    else:
        row = await _update_override(db, existing, command.lastro_moeda, user_id)
    return _to_override_response(row)


async def delete_asset_override(
    workspace_id: str, match_kind: str, asset_match_key: str, db: AsyncSession
) -> bool:
    """Remove override per-workspace. Retorna True se removeu, False se não existia."""
    existing = await _find_override(db, workspace_id, match_kind, asset_match_key)
    if existing is None:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def list_asset_overrides(workspace_id: str, db: AsyncSession) -> list[AssetOverrideResponse]:
    stmt = select(WorkspaceAssetOverride).where(WorkspaceAssetOverride.workspace_id == workspace_id)
    result = await db.execute(stmt)
    return [_to_override_response(r) for r in result.scalars().all()]


async def compute_exposicao_cambial_v2(
    workspace_id: str, db: AsyncSession
) -> ExposicaoCambialResponse:
    """Recomputa exposição cambial em read-time usando catalog + overrides correntes."""
    artifact = await _load_latest_e5_artifact(db, workspace_id)
    if artifact is None:
        return _empty_response(workspace_id)
    por_moeda, ativos, investivel_denom = await _aggregate_all(artifact, db, workspace_id)
    return _build_response(
        workspace_id=workspace_id,
        por_moeda=por_moeda,
        investivel_denom=investivel_denom,
        ativos=ativos,
        artifact=artifact,
    )

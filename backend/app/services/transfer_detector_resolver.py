"""Resolve ``InternalTransferDetector`` (DB-first → defaults globais) — ADR-133."""

from __future__ import annotations

from typing import Any

from backend.app.models.config_blob import TransferConfig
from backend.app.repositories.config_blob_repository import ConfigBlobRepository
from backend.app.services.config_defaults import ConfigDefaultsLoader
from pipeline.domain.services import InternalTransferConfig, InternalTransferDetector


def _global_transfer_block(defaults: ConfigDefaultsLoader) -> dict[str, Any]:
    family = defaults.load_json("family_members.json") or {}
    return family.get("transferencias_internas") or {}


def _global_pattern_list(defaults: ConfigDefaultsLoader) -> list[str]:
    categorization = defaults.load_json("categorization.json") or {}
    return list(categorization.get("internal_transfer_patterns") or [])


def _merge(transfer_block: dict[str, Any], extra_patterns: list[str]) -> dict[str, Any]:
    patterns = list(extra_patterns)
    patterns += list(transfer_block.get("patterns_pix") or [])
    return {
        "internal_transfer_patterns": patterns,
        "internal_transfer_recipients": list(transfer_block.get("recipients") or []),
        "bank_specific_transfer_patterns": transfer_block.get("patterns_bank_specific") or {},
        "global_transfer_patterns": list(transfer_block.get("patterns_global") or []),
    }


async def resolve_internal_transfer_detector(
    workspace_id: str,
    *,
    repo: ConfigBlobRepository,
    defaults: ConfigDefaultsLoader,
) -> InternalTransferDetector:
    """Constrói o detector com config DB-first; fallback para defaults globais."""
    blob = await repo.get_config_json(workspace_id, TransferConfig)
    transfer_block = blob if blob is not None else _global_transfer_block(defaults)
    merged = _merge(transfer_block, _global_pattern_list(defaults))
    return InternalTransferDetector(InternalTransferConfig.from_categorization(merged))

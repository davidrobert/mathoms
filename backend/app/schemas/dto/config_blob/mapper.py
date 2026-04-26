"""Mapper dict → DTO + helper de deep-merge para os 3 blobs de config.

Responsabilidades:

1. Converter ``dict[str, Any]`` (do DB ou do disco) em DTO de resposta
   tipado. Aplica ``model_validate`` — útil para pegar shape inválido
   cedo (ex.: ``pipeline.json`` corrompido retorna erro 500 explícito em
   vez de ``KeyError`` embaixo da stack).

2. ``deep_merge``: merge recursivo usado pelo ``PUT /config/pipeline``.
   É pura (não muda ``base`` nem ``override``) e fica fora do router para
   ser testável sem FastAPI.

Mapper **não** recebe ``AsyncSession`` nem toca disco. Recebe dicts e
devolve DTOs.
"""

from __future__ import annotations

from typing import Any

from backend.app.schemas.dto.config_blob.response import (
    InstitutionConfigResponse,
    PipelineConfigResponse,
    ReportLayoutResponse,
    TransferConfigResponse,
)


def pipeline_blob_to_response(
    config_json: dict[str, Any],
) -> PipelineConfigResponse:
    """Converte dict (DB row ou ``pipeline.json`` do disco) → DTO tipado.

    Usa ``model_validate`` (Pydantic v2) que é equivalente a espalhar o
    dict via ``**cfg`` mas preserva a origem do erro se o shape for
    inválido.
    """
    return PipelineConfigResponse.model_validate(config_json)


def institution_blob_to_response(
    config_json: dict[str, Any],
) -> InstitutionConfigResponse:
    """Converte dict → DTO (wrap opaco).

    O dict pode vir de ``institution_configs.config_json`` (DB) ou de
    ``institutions.json`` (disco, fallback). Ambos têm a mesma shape de
    cima: chave por banco + estrutura interna livre.
    """
    return InstitutionConfigResponse(config_json=config_json)


def report_layout_to_response(
    config_json: dict[str, Any],
) -> ReportLayoutResponse:
    """Converte dict → DTO (wrap opaco).

    Dict vem de ``report_layouts.config_json`` (DB) ou de
    ``report_layout.yaml`` convertido via ``yaml.safe_load`` (disco).
    """
    return ReportLayoutResponse(config_json=config_json)


def transfer_blob_to_response(config_json: dict[str, Any]) -> TransferConfigResponse:
    """Converte dict → DTO tipado para ``transferencias_internas`` (ADR-133)."""
    return TransferConfigResponse.model_validate(_strip_transfer_comments(config_json))


def _strip_transfer_comments(config_json: dict[str, Any]) -> dict[str, Any]:
    """Filtra chaves ``_comment`` em ``patterns_bank_specific`` (legado JSON)."""
    bank_raw = config_json.get("patterns_bank_specific") or {}
    bank_clean = {k: v for k, v in bank_raw.items() if not str(k).startswith("_")}
    return {**config_json, "patterns_bank_specific": bank_clean}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge recursivo: ``override`` vence no leaf, dicts aninhados são
    mergeados recursivamente. Não muta ``base`` nem ``override``.

    Regras:

    - Chaves só em ``base`` → preservadas.
    - Chaves só em ``override`` → adicionadas.
    - Chaves em ambos, ambos dict → merge recursivo.
    - Chaves em ambos, pelo menos um não-dict → valor de ``override``
      substitui (listas NÃO são concatenadas — substituição completa).

    Usado no ``PUT /config/pipeline``.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

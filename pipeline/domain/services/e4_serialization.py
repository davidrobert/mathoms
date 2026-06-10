"""Serialização para os 7 artefatos E4 legados (Sessão A4b).

Converte :class:`CategorizationResult` em mapping ``{artifact_key: payload}``
aderente ao schema ``config/schemas/e4_unified.schema.json``. Artifact keys
correspondem aos nomes de arquivo (sem sufixo) esperados pelo
``DiskArtifactStore`` (stage ``E4``, sufixo ``-4_unified.json``).

Os 7 artefatos:

- ``receitas`` — output de ``CashFlowBuilder.build_receitas_unified``
- ``despesas`` — output de ``CashFlowBuilder.build_despesas_unified``
- ``fluxo_mensal_detalhado`` — output de ``CashFlowBuilder.build_fluxo_mensal``
- ``patrimonio`` — baseline normalizado (:class:`NormalizedBaseline`); chave
  **omitida** quando o baseline está ausente/vazio (ADR-132). O caller deve
  escrever só as chaves presentes; o ``read()`` do store resolve a ausência
  via fallback workspace-scoped para o E1.5c persistente do run anterior.
- ``investimentos`` — output de ``InvestmentsConsolidator.consolidate``
- ``seguros`` — placeholder ``{"dados": []}`` (legado sempre regenera)
- ``pontos_milhas`` — placeholder ``{"dados": []}`` (legado sempre regenera)

Funções puras, sem I/O. O caller escreve os payloads via ``ArtifactStore``.
"""

from __future__ import annotations

from typing import Mapping

from pipeline.domain.services.e4_categorizer_adapter import CategorizationResult
from pipeline.domain.services.lineage_fields import LINEAGE_VERSION

# Chaves de artifact aceitas pelo ``DiskArtifactStore`` para o stage ``E4``
# (o store anexa ``-4_unified.json`` via ``stage_suffix``).
ARTIFACT_KEYS: tuple[str, ...] = (
    "receitas",
    "despesas",
    "fluxo_mensal_detalhado",
    "patrimonio",
    "investimentos",
    "seguros",
    "pontos_milhas",
)


def empty_placeholder() -> dict:
    """Payload para ``seguros-4_unified.json`` e ``pontos_milhas-4_unified.json``.

    Paridade com ``e4_categorize.main`` linhas 1030-1033.
    """
    return {"dados": []}


def build_patrimonio_artifact(baseline) -> dict | None:
    """Payload para ``patrimonio-4_unified.json``.

    Quando ``baseline`` tem ``data`` não-vazio (baseline E1.5c carregado),
    usa o próprio dict normalizado. Quando ausente/vazio devolve ``None`` —
    sinal para :func:`serialize_e4_artifacts` **omitir** a chave (ADR-132).
    Antes devolvia ``{"dados": []}``, que sobrescrevia o E4-patrimônio bom
    em re-runs sem reprocessar IRPF.
    """
    if baseline is None or not getattr(baseline, "data", None):
        return None
    return dict(baseline.data)


def conferencia_signals(result: CategorizationResult) -> dict[str, str]:
    """Sinais de conferência do dedup K4 (ADR-279 · A25.l5 N2): ``tx_total`` =
    lançamentos classificados ANTES do dedup; ``dedup_collapsed``/``dedup_review``
    vêm do :class:`DedupReport` (até A24, só telemetria de log). Strings int
    (zero float no lineage); transporte via artefato ``despesas`` é o único
    canal E4→E5 que sobrevive ao modo incremental."""
    report = result.cash_flow.dedup_report
    return {
        "tx_total": str(len(result.classified)),
        "dedup_collapsed": str(report.collapsed_count),
        "dedup_review": str(report.review_count),
    }


def _despesas_with_conferencia(result: CategorizationResult) -> dict:
    """``despesas`` + bloco ``_lineage`` (metadata ADR-279, não contrato E4)."""
    despesas = result.cash_flow.despesas.to_legacy_dict()
    despesas["_lineage"] = {
        "lineage_version": LINEAGE_VERSION,
        "signals": conferencia_signals(result),
    }
    return despesas


def serialize_e4_artifacts(result: CategorizationResult) -> dict[str, dict]:
    """Produz os payloads E4 a partir de um :class:`CategorizationResult`.

    A ordem das chaves no dict retornado segue ``ARTIFACT_KEYS`` quando
    todos presentes; ``patrimonio`` é **omitido** se o baseline está vazio
    (ADR-132 T2: preservar o artefato do run anterior é mais correto que
    sobrescrever com placeholder).
    """
    patrimonio = build_patrimonio_artifact(result.baseline)
    payloads: dict[str, dict] = {
        "receitas": result.cash_flow.receitas.to_legacy_dict(),
        "despesas": _despesas_with_conferencia(result),
        "fluxo_mensal_detalhado": result.cash_flow.fluxo_mensal.to_legacy_dict(),
    }
    if patrimonio is not None:
        payloads["patrimonio"] = patrimonio
    payloads["investimentos"] = result.investments.to_legacy_dict()
    payloads["seguros"] = empty_placeholder()
    payloads["pontos_milhas"] = empty_placeholder()
    return payloads


def filename_for(artifact_key: str) -> str:
    """Retorna o filename legado (``{key}-4_unified.json``).

    Usado no retorno de ``main_with_store`` para gerar a lista ``files_created``
    que o worker exibe na UI.
    """
    if artifact_key not in ARTIFACT_KEYS:
        raise KeyError(f"Artifact key inválida: {artifact_key!r}")
    return f"{artifact_key}-4_unified.json"


def all_filenames() -> list[str]:
    """Lista de todos os 7 filenames na ordem canônica."""
    return [filename_for(k) for k in ARTIFACT_KEYS]


def payloads_to_files(payloads: Mapping[str, dict]) -> dict[str, dict]:
    """Alias de conveniência — converte ``{key: payload}`` para
    ``{filename: payload}`` (útil em testes que escrevem em disco direto).
    """
    return {filename_for(k): v for k, v in payloads.items()}

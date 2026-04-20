"""Serialização para os 7 artefatos E4 legados (Sessão A4b).

Converte :class:`CategorizationResult` em mapping ``{artifact_key: payload}``
aderente ao schema ``config/schemas/e4_unified.schema.json``. Artifact keys
correspondem aos nomes de arquivo (sem sufixo) esperados pelo
``DiskArtifactStore`` (stage ``E4``, sufixo ``-4_unified.json``).

Os 7 artefatos:

- ``receitas`` — output de ``CashFlowBuilder.build_receitas_unified``
- ``despesas`` — output de ``CashFlowBuilder.build_despesas_unified``
- ``fluxo_mensal_detalhado`` — output de ``CashFlowBuilder.build_fluxo_mensal``
- ``patrimonio`` — baseline normalizado (:class:`NormalizedBaseline`) OU
  ``{"dados": []}`` quando ausente (paridade com ``load_patrimonio`` retornando
  ``{}``).
- ``investimentos`` — output de ``InvestmentsConsolidator.consolidate``
- ``seguros`` — placeholder ``{"dados": []}`` (legado sempre regenera)
- ``pontos_milhas`` — placeholder ``{"dados": []}`` (legado sempre regenera)

Funções puras, sem I/O. O caller escreve os payloads via ``ArtifactStore``.
"""

from __future__ import annotations

from typing import Mapping

from pipeline.domain.services.e4_categorizer_adapter import CategorizationResult


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


def build_patrimonio_artifact(baseline) -> dict:
    """Payload para ``patrimonio-4_unified.json``.

    Quando ``baseline`` tem ``data`` não-vazio (baseline E1.5c carregado),
    usa o próprio dict normalizado. Caso contrário, placeholder
    ``{"dados": []}`` — paridade com ``load_patrimonio`` retornando ``{}``.
    """
    if baseline is None or not getattr(baseline, "data", None):
        return empty_placeholder()
    return dict(baseline.data)


def serialize_e4_artifacts(result: CategorizationResult) -> dict[str, dict]:
    """Produz os 7 payloads E4 a partir de um :class:`CategorizationResult`.

    A ordem das chaves no dict retornado é estável (``ARTIFACT_KEYS``), o que
    ajuda a reproduzir o mesmo order de escrita do legado em testes de paridade.
    """
    return {
        "receitas": result.cash_flow.receitas.to_legacy_dict(),
        "despesas": result.cash_flow.despesas.to_legacy_dict(),
        "fluxo_mensal_detalhado": result.cash_flow.fluxo_mensal.to_legacy_dict(),
        "patrimonio": build_patrimonio_artifact(result.baseline),
        "investimentos": result.investments.to_legacy_dict(),
        "seguros": empty_placeholder(),
        "pontos_milhas": empty_placeholder(),
    }


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

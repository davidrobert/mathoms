"""Leitura do corpus IRPF pela S8 — ano-base eleito e âncora de declarante.

Separado de ``tributario_input_builder`` porque é a superfície que a [[A40.l65]]
faz crescer: eleição de ano (§Escopo 1), âncora de titular (§Escopo 2) e o gate de
coerência com o Card B (§Escopo 4) moram todos aqui.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session as SyncSession

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.security.crypto import read_artifact_content
from pipeline.domain.services.tributario.irpf_titular_anchor import (
    AncoraTitular,
    escolher_declaracao_do_titular,
)

logger = logging.getLogger("mathoms.tributario.irpf_reader")

#: Payload de `extract_irpf_full` + o `created_at` que desempata o dedup.
_Declaracao = tuple[dict, str]


# Uma row por `artifact_key`, a mais recente — o MESMO corpus que o E5 enxerga.
# `extract_irpf_full` está em `_WORKSPACE_SCOPED_STAGES`, então o `DBArtifactStore`
# resolve cada key por `_get_latest_in_workspace` (`created_at desc, id desc`).
# A unicidade é `(pipeline_run_id, stage, artifact_key)`: cada run repete as
# mesmas keys, e o E1.6 churna (285 versões de 4 documentos medidas no dogfood em
# 2026-08-21), então ler todas as rows custaria um decrypt Fernet por versão.
#
# Medido: isto é paridade de corpus e custo, NÃO um guarda de correção — o dedup
# de `IRPFAnalyzer.from_payloads` já colapsa a duplicata semântica, e remover
# este filtro não muda o valor publicado em nenhum caso que soubemos construir.
# Não há teste aqui porque um teste que passa com e sem o filtro nomearia um
# mecanismo que não exercita.
def _read_workspace_artifacts(
    workspace_id: str, stages: tuple[str, ...], *, db: SyncSession
) -> list[_Declaracao]:
    """Versão corrente de cada ``artifact_key`` do workspace, mais recente primeiro."""
    return _primeira_por_key(_rows_de_artefato(workspace_id, stages, db=db))


def _rows_de_artefato(workspace_id: str, stages: tuple[str, ...], *, db: SyncSession) -> list:
    return (
        db.query(
            PipelineArtifact.artifact_key,
            PipelineArtifact.content_json,
            PipelineArtifact.created_at,
        )
        .filter(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(stages),
        )
        .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
        .all()
    )


def _primeira_por_key(rows: list) -> list[_Declaracao]:
    """Decripta só a row vencedora de cada key — o E1.6 churna e o resto é custo."""
    vistos: set[str] = set()
    correntes: list[_Declaracao] = []
    for artifact_key, content_json, created_at in rows:
        if artifact_key not in vistos:
            vistos.add(artifact_key)
            correntes.append((read_artifact_content(content_json), str(created_at)))
    return correntes


# A40.l65 §Escopo 1: o ano-base sai do MESMO resolvedor que o E5 e o Card B usam
# (ADR-305 D1/D2), não do `created_at` mais recente. Antes disto a S8 podia
# publicar sobre o ano X enquanto o Card B publicava sobre o Y — dois resolvedores
# do mesmo corpus no mesmo documento, a classe que nomeia a ADR-375.
def _irpf_do_ano_base(
    workspace_id: str, declaracoes: list[_Declaracao], cpf_titular: Optional[str] = None
) -> Optional[dict]:
    """Declaração do TITULAR no ano-base fiscal eleito (A40.l65 §Escopo 1+2)."""
    if not declaracoes:
        return None
    ano = _resolve_ano_base_das(declaracoes)
    if ano is None:
        _warn_ano_base_nao_resolvido(workspace_id, declaracoes)
        # Sem ano eleito não há o que resolver (payloads que não parseiam). Manter
        # o comportamento anterior é degradação declarada — publicar AUSÊNCIA aqui
        # é decisão do §Escopo 2, que é dono da semântica de base ausente.
        return declaracoes[0][0]
    do_ano = [payload for payload, _ in declaracoes if _ano_base_de(payload) == ano]
    if not do_ano:
        # Só ocorre com payload sem `contribuinte.ano_base` legível — o schema
        # exige o campo, então é artefato malformado, não família sem declaração.
        _warn_ano_base_nao_resolvido(workspace_id, declaracoes, eleito=ano)
        return declaracoes[0][0]
    escolhida, ancora = escolher_declaracao_do_titular(do_ano, cpf_titular)
    if ancora is not AncoraTitular.resolvida:
        # A base de OUTRO CPF é pior que base nenhuma: o teto de 12% é por
        # declaração, e publicar a do cônjuge sobre o nome do titular é erro de
        # identidade, não de aritmética (A40.l65 §Problema 2).
        _warn_titular_nao_ancorado(workspace_id, ano, ancora, len(do_ano))
        return None
    return escolhida


# Os dois ramos de degradação eram MUDOS: a S8 voltava a publicar o ano da ordem
# de processamento sem deixar rastro, e nenhum gate podia ver. O VO publica o ano
# que somou (proveniência), e este log nomeia por que ele divergiu do eleito.
def _warn_titular_nao_ancorado(
    workspace_id: str, ano: int, ancora: AncoraTitular, candidatas: int
) -> None:
    logger.warning(
        "tributario_irpf_titular_nao_ancorado",
        extra={
            "workspace_id": workspace_id,
            "ano_base": ano,
            "ancora": ancora.value,
            "declaracoes_no_ano": candidatas,
        },
    )


def _warn_ano_base_nao_resolvido(
    workspace_id: str, declaracoes: list[_Declaracao], eleito: Optional[int] = None
) -> None:
    logger.warning(
        "tributario_irpf_ano_base_nao_resolvido",
        extra={
            "workspace_id": workspace_id,
            "ano_eleito": eleito,
            "declaracoes": len(declaracoes),
            "ano_publicado": _ano_base_de(declaracoes[0][0]) if declaracoes else None,
        },
    )


# `partition_irpf_payloads` é a mesma partição que o E5 aplica: PJ (ADR-268) e
# schema-inválido saem, para 1 artifact ruim não derrubar a resolução do workspace
# inteiro — sem ela um payload malformado devolvia a S8 em silêncio para a leitura
# por `created_at`. `from_payloads` dedupa, e o tie-break por `created_at` é o "e
# dedup" do §Escopo 1: sem ele o vencedor sairia por índice de lista.
def _resolve_ano_base_das(declaracoes: list[_Declaracao]) -> Optional[int]:
    from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer, partition_irpf_payloads
    from pipeline.domain.services.irpf_completude import resolve_ano_base_fiscal

    validos, chaves, _skipped = partition_irpf_payloads(
        [payload for payload, _ in declaracoes],
        [created_at for _, created_at in declaracoes],
    )
    if not validos:
        return None
    try:
        analyzer = IRPFAnalyzer.from_payloads(validos, tie_break_keys=chaves)
    except Exception:
        return None
    resolvido = resolve_ano_base_fiscal(analyzer.estados_completude())
    return resolvido.ano if resolvido else None


def _ano_base_de(payload: dict) -> Optional[int]:
    contribuinte = payload.get("contribuinte") if isinstance(payload, dict) else None
    return (contribuinte or {}).get("ano_base")

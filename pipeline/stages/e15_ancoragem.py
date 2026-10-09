"""Âncora da ficha no stage E1.5a: a razão de revisão e a re-âncora do incremental ([[ADR-440]])."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Callable

from pipeline.stages.ficha_imovel_parser import Ancoragem, aplicar_ancoras, assinatura_de_ancoras


# [[ADR-440]] D2 — WARN-first como as demais razões do E1.5a ([[ADR-357]]): o item sem
# âncora não some, só cai na chave da descrição. Uma razão por documento, só contagens.
def razao_de_ancoragem(ancoragem: Ancoragem, *, artifact_key: str) -> dict | None:
    """Ficha de imóvel que não casou com um único item vira review_reason do documento."""
    from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

    if not ancoragem.ambiguas and not ancoragem.sem_ficha:
        return None
    return ReviewReason(
        code=ReviewReasonCode.extract_ancora_imovel_ambigua
        if ancoragem.ambiguas
        else ReviewReasonCode.extract_ancora_imovel_sem_ficha,
        stage="extract_baseline",
        artifact_key=artifact_key,
        document_id=None,
        offending_value=f"fichas={ancoragem.fichas} ancoradas={len(ancoragem.ancoras)} "
        f"ambiguas={ancoragem.ambiguas} sem_ficha={ancoragem.sem_ficha}",
        expected="toda ficha de imovel com rotulo casa com um unico item pelo valor",
        message="ficha de imovel sem ancora — a identidade do item cai na chave da descricao",
    ).to_dict()


# [[ADR-440]] D4: o incremental não reenvia ao LLM o IRPF já extraído, mas a âncora vem de
# parser — re-ler o texto cura o artefato antigo sem re-extração. Texto vazio não toca o
# artefato: uma falha de leitura apagaria a âncora boa que ele já tem.
def reancorar_fora_do_lote(
    store, docs: list[Path], extractor, artifact_key_for: Callable[[Path], str]
) -> tuple[int, list[dict]]:
    """Re-âncora os E1.5a que este run não reextrai; devolve (regravados, razões)."""
    regravados, razoes = 0, []
    for doc in docs:
        key = artifact_key_for(doc)
        atual = store.read("E1.5a", key)
        texto = extractor.extract(doc) if isinstance(atual, dict) else ""
        if ((atual or {}).get("payload_version") or 0) < 2 or not texto.strip():
            continue
        novo = copy.deepcopy(atual)
        ancoragem = aplicar_ancoras(novo, texto)
        if assinatura_de_ancoras(novo) != assinatura_de_ancoras(atual):
            store.write("E1.5a", key, novo)
            regravados += 1
            razoes += [r for r in [razao_de_ancoragem(ancoragem, artifact_key=key)] if r]
    return regravados, razoes


__all__ = ["razao_de_ancoragem", "reancorar_fora_do_lote"]

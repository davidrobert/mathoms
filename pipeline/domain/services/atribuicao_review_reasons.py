"""Eixo de ATRIBUIÇÃO da carteira financeira ([[ADR-412]] §D5 · §Emenda E1).

Ortogonal a `cobertura_investimentos`, que particiona **pessoas** ("este membro
foi medido?"). Este particiona **dinheiro**: quanto da carteira tem titular
identificado. No corpus que motivou a lane as duas linhas de cobertura estavam
`apurado`/`motivo: null` **e** a maior parte da base não tinha dono — uma tabela
por-pessoa não consegue dizer isso.

A razão nasce **advisory**, não de retenção (§Emenda E1): no E5
`valid = not reasons`, e reter faria o run não produzir relatório algum — nem
`reports`, nem parecer, nem cross-validation. Publicar com o diagnóstico
declarado é estritamente mais informativo que ausência de relatório.
"""

from __future__ import annotations

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

# Herdado da [[ADR-406]] §D1, mesma base (carteira financeira): abaixo disto a
# fatia é ignorada em silêncio; a partir daqui ela é NOMEADA. Suprimir veredito
# é outro degrau, com teste de sensibilidade — não é este piso (§Emenda E4).
PISO_AGREGADO_PCT = 1.0


def _pct(nao_atribuidos: float, base: float) -> float:
    return round(nao_atribuidos / base * 100.0, 2) if base > 0 else 0.0


def _status(nao_atribuidos: float, base: float, titular_identificado: float) -> str:
    """Vocabulário de `componente_exposicao_cambial` ([[ADR-403]]), não um terceiro."""
    if base <= 0 or titular_identificado <= 0:
        return "indeterminado"
    return "apurado" if nao_atribuidos <= 0 else "parcial"


# Valores crus, nunca o dict publicado — mesma razão de `publicar_bases`.
# `pct_inferido` divide pela MESMA base de `pct_carteira_financeira` ([[ADR-430]]
# §3): duas porcentagens do mesmo bloco sobre denominadores diferentes é o
# defeito que a A40.l96 já pagou ao comparar o `pct_carteira` do Top 15 com os
# 49% de titularidade. Ele mede a fatia COM dono cuja atribuição veio de
# inferência (banco de dono único), não de declaração nem de conta casada —
# fato ≠ hint ([[ADR-394]]).
def atribuicao_investimentos(
    *, orfa: float, cheia: float, identificada: float, inferida: float = 0.0
) -> dict:
    """Bloco `atribuicao_investimentos`: quanto da carteira tem dono conhecido."""
    pct = _pct(orfa, cheia)
    acima = pct >= PISO_AGREGADO_PCT
    return {
        "status": _status(orfa, cheia, identificada),
        "pct_carteira_financeira": pct,
        "piso_pct": PISO_AGREGADO_PCT,
        "motivo": _motivo(pct) if acima else None,
        "pct_inferido": _pct(inferida, cheia),
    }


def review_reasons_da_atribuicao(patrimonio: dict, *, stage: str, artifact_key: str) -> list[dict]:
    """Razão ADVISORY quando a fatia sem dono cruza o piso; nunca retém."""
    bloco = (patrimonio or {}).get("atribuicao_investimentos") or {}
    if not bloco.get("motivo"):
        return []
    reason = ReviewReason(
        code=ReviewReasonCode.domain_investimento_sem_titularidade,
        stage=stage,
        artifact_key=artifact_key,
        document_id=None,
        offending_value=f"pct_carteira_financeira={bloco.get('pct_carteira_financeira')}",
        expected=f"< {bloco.get('piso_pct')}% da carteira financeira",
        message=bloco["motivo"],
    )
    return [reason.to_dict()]


def _motivo(pct: float) -> str:
    return (
        f"{pct}% da carteira financeira está em posições cujo titular não foi "
        "identificado — reconciliar a titularidade"
    )

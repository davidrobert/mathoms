"""Gate por ITEM da catch-all de classes de ativo ([[ADR-405]] · DE-2 / RV7-04).

Migração entre baldes preserva Σ por construção, então os 16 checks de
conservação são cegos a ela por desenho: no §r7 a perda de um balde igualou o
ganho do outro com resíduo 0,0000%. O sensor que existia era de **nível**
(`OUTROS_EXCESSIVO_THRESHOLD_PCT`, 5%) contra participação observada de 0,84% —
~6× abaixo. Este módulo troca o nível pelo item, e o warning pela retenção.

Projeta do **artefato publicado**, como `investimentos_cobertura`: a razão fica
auditável contra o que foi entregue ao cliente, não contra estado em voo.
"""

from __future__ import annotations

import os
from typing import Any, Iterable

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

GATE_ENV = "MATHOMS_E5_CLASSIFICACAO_GATE"

# Base = carteira financeira (`total - imóveis físicos`), a mesma de
# `pct_carteira_financeira` e de `nao_classificado_pct` (A37.l9). Imóvel é
# classificado pela origem e nunca depende de keyword; incluí-lo no denominador
# diluiria a incerteza — no corpus do §r7 o divisor mudaria em 1,5×.
ITEM_MIN_PCT = 0.5
AGREGADO_MIN_PCT = 1.0

# Cap por code ([[ADR-272]] §Cap de cardinalidade). 5 e não 50 porque estas
# razões também viram string em `validation.errors`: acima de ~5 itens materiais
# a lista deixa de informar e a linha agregada já é o recado. Medido: 3
# razões/run no corpus real do §r7.
MAX_RAZOES_POR_CODE = 5

_AUTORIDADE_SEM_HAYSTACK = "sem_haystack"


def classificacao_gate_ligado() -> bool:
    """Kill-switch de 1 env var; `0` desliga a retenção, não os campos do artefato."""
    return os.environ.get(GATE_ENV, "1") != "0"


# Separador DECIMAL PONTO, não vírgula: `redact_pii._MONEY_RE` casa `\d+,\d{2}`
# e mascarava "1,30%" como "R$ ***%" — percentual em pt-BR é indistinguível de
# BRL para o redator. O valor em reais fica de fora por decisão ([[ADR-405]]);
# o peso na carteira é o número que decide o limiar.
def _pct_str(pct: float) -> str:
    """Percentual da carteira financeira, imune à redação monetária."""
    return f"{pct:.2f}%"


def _cap(reasons: list[ReviewReason]) -> list[ReviewReason]:
    """Mantém as `MAX_RAZOES_POR_CODE` maiores; o excedente vira contagem na última."""
    if len(reasons) <= MAX_RAZOES_POR_CODE:
        return reasons
    from dataclasses import replace

    mantidas = reasons[:MAX_RAZOES_POR_CODE]
    excedente = len(reasons) - MAX_RAZOES_POR_CODE
    ultima = mantidas[-1]
    mantidas[-1] = replace(ultima, occurrence_count=ultima.occurrence_count + excedente)
    return mantidas


def _reason(
    code: ReviewReasonCode, offending: str, expected: str, message: str, **kw
) -> ReviewReason:
    return ReviewReason(
        code=code,
        stage=kw["stage"],
        artifact_key=kw["artifact_key"],
        document_id=None,
        offending_value=offending,
        expected=expected,
        message=message,
    )


# `sem_haystack` NUNCA escala por limiar: item sem `tipo` e sem `descricao` é
# violação de contrato do produtor, não incerteza de taxonomia — e o produtor
# não fica menos quebrado porque o item é pequeno. Medido 0/28 no §r7.
def _razoes_sem_haystack(itens: list[dict], **kw) -> list[ReviewReason]:
    return _cap(
        [
            _reason(
                ReviewReasonCode.domain_ativo_sem_haystack,
                f"investment_id={i['locator']} pct={_pct_str(i['pct'])}",
                "item com `tipo` ou `descricao` preenchidos",
                "Ativo sem sinal algum: o produtor a montante nao informou tipo nem descricao",
                **kw,
            )
            for i in itens
            if i["autoridade"] == _AUTORIDADE_SEM_HAYSTACK
        ]
    )


def _razoes_item_nao_classificado(itens: list[dict], **kw) -> list[ReviewReason]:
    materiais = [
        i for i in itens if i["autoridade"] != _AUTORIDADE_SEM_HAYSTACK and i["pct"] >= ITEM_MIN_PCT
    ]
    return _cap(
        [
            _reason(
                ReviewReasonCode.domain_ativo_nao_classificado,
                f"investment_id={i['locator']} pct={_pct_str(i['pct'])}",
                f"classe decidida por algum degrau, ou peso < {_pct_str(ITEM_MIN_PCT)}",
                "Ativo material caiu na catch-all: nenhum degrau decidiu a classe",
                **kw,
            )
            for i in materiais
        ]
    )


# Segundo braço, e não redundância do primeiro: mil cortes pequenos somam sem
# que nenhum item cruze `ITEM_MIN_PCT`. É também a faixa 1–2%, que hoje fica
# abaixo do primeiro degrau da supressão graduada e não produz sinal algum.
def _razao_agregado(pct_carteira: float, **kw) -> list[ReviewReason]:
    if pct_carteira <= AGREGADO_MIN_PCT:
        return []
    return [
        _reason(
            ReviewReasonCode.domain_ativo_nao_classificado,
            f"carteira nao_classificado_pct={_pct_str(pct_carteira)}",
            f"nao_classificado_pct <= {_pct_str(AGREGADO_MIN_PCT)}",
            "Fracao nao classificada da carteira acima do piso agregado",
            **kw,
        )
    ]


# Braço disjunto do anterior, medido: no §r7 a interseção entre `sem_match` e
# `sem instituição` foi ZERO, e o maior órfão (2,81% da carteira) classificava
# num balde nomeado — invisível a `nao_classificado_pct`.
def _razoes_instituicao_ausente(
    por_membro: Iterable[dict], denominador: float, **kw
) -> list[ReviewReason]:
    materiais = _posicoes_orfas_materiais(por_membro, denominador)
    return _cap(
        [
            _reason(
                ReviewReasonCode.domain_instituicao_ausente,
                f"investment_id={loc} pct={_pct_str(pct)}",
                "posicao com valor atribuida a uma instituicao",
                "Posicao material sem identidade de instituicao: sai da cobertura por membro",
                **kw,
            )
            for loc, pct in materiais
        ]
    )


def _orfas_declaradas(por_membro: Iterable[dict]) -> list[dict]:
    return [
        pos
        for linha in por_membro
        if isinstance(linha, dict)
        for pos in linha.get("posicoes_sem_identidade") or []
        if isinstance(pos, dict)
    ]


def _posicoes_orfas_materiais(
    por_membro: Iterable[dict], denominador: float
) -> list[tuple[str, float]]:
    if denominador <= 0:
        return []
    pesos = [
        (str(p.get("locator") or "?"), float(p.get("valor") or 0) / denominador * 100)
        for p in _orfas_declaradas(por_membro)
    ]
    return sorted([p for p in pesos if p[1] >= ITEM_MIN_PCT], key=lambda p: -p[1])


def _itens_normalizados(investimentos: dict) -> list[dict]:
    brutos = investimentos.get("nao_classificado_itens") or []
    itens = [
        {
            "locator": str(i.get("locator") or "?"),
            "pct": float(i.get("pct_carteira_financeira") or 0),
            "autoridade": str(i.get("autoridade") or ""),
        }
        for i in brutos
        if isinstance(i, dict)
    ]
    return sorted(itens, key=lambda i: -i["pct"])


def review_reasons_da_classificacao(
    investimentos: dict[str, Any] | None, *, stage: str, artifact_key: str
) -> list[dict]:
    """Projeta o gate por item do artefato E5 para ``review_reason`` ([[ADR-405]])."""
    if not classificacao_gate_ligado():
        return []
    inv = investimentos or {}
    kw = {"stage": stage, "artifact_key": artifact_key}
    itens = _itens_normalizados(inv)
    reasons = _razoes_sem_haystack(itens, **kw)
    reasons += _razoes_item_nao_classificado(itens, **kw)
    reasons += _razao_agregado(float(inv.get("nao_classificado_pct") or 0), **kw)
    reasons += _razoes_instituicao_ausente(
        inv.get("instituicoes_por_membro") or [], float(inv.get("total_financeiro") or 0), **kw
    )
    return [r.to_dict() for r in reasons]


__all__ = [
    "AGREGADO_MIN_PCT",
    "GATE_ENV",
    "ITEM_MIN_PCT",
    "MAX_RAZOES_POR_CODE",
    "classificacao_gate_ligado",
    "review_reasons_da_classificacao",
]

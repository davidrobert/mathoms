"""Veredito de publicação dos baldes de imóvel ([[ADR-439]]): zero só com evidência de zero.

`residencia` e `imoveis_geradores` publicavam `0,00` para *"não sei qual é"* — o `else`
dos splitters não distingue o imóvel que não é residência do imóvel cuja identidade se
perdeu no run. A partição monetária continua a dos splitters ([[ADR-433]] §D3); o que
muda aqui é a AFIRMAÇÃO publicada sobre cada balde.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.investimentos_cobertura import CoberturaStatus
from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_DESCONHECIDO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATIONS_GERADORAS,
    CoberturaClassificacaoImovel,
    classificacao_do_imovel,
    cobertura_classificacao_imovel,
)
from pipeline.domain.services.patrimonio_types import imovel_property_id, imovel_valor
from pipeline.domain.services.valor_nao_apurado import item_nao_apurado

# Espelho de `backend/app/models/property_identity.py` ([[ADR-215]]): o pipeline não
# importa o backend, e a paridade dos três valores é teste, não disciplina.
RESIDENCIA_ALUGADA = "rented"
RESIDENCIA_PROPRIA = "owned"
RESIDENCIA_NAO_DECLARADA = "undeclared"


class MotivoBaldeImovel(str, Enum):
    """Por que o balde saiu `null` — cada motivo pede uma ação diferente da família."""

    nao_localizada = "nao_localizada"
    sem_valor = "sem_valor"
    nao_classificada = "nao_classificada"
    nao_declarada = "nao_declarada"
    vinculo_perdido = "vinculo_perdido"
    nao_classificados = "nao_classificados"


@dataclass(frozen=True)
class VereditoBalde:
    """`piso` diz que o número publicado é o mínimo — só a residência o usa ([[ADR-439]] D2)."""

    status: CoberturaStatus
    motivo: MotivoBaldeImovel | None = None
    piso: bool = False

    @property
    def publicavel(self) -> bool:
        """`False` quando não apurado: o balde sai `null` — zero é afirmação ([[ADR-431]])."""
        return self.status is not CoberturaStatus.nao_apurado

    def to_dict(self) -> dict:
        motivo = self.motivo.value if self.motivo is not None else None
        return {"status": self.status.value, "motivo": motivo, "piso": self.piso}


@dataclass(frozen=True)
class EvidenciaDeImovel:
    """O que o run viu dos imóveis, antes de qualquer veredito."""

    pids_no_run: frozenset[str]
    n_desconhecido_em_aberto: int
    gerador_sem_valor: bool


# "Em aberto" é o desconhecido que PODE valer algo. Zero declarado em 31/12 é venda no
# ano e não conta; valor não apurado ([[ADR-431]]) conta, porque ninguém mediu.
def _em_aberto(imovel: dict) -> bool:
    return imovel_valor(imovel) > 0 or item_nao_apurado(imovel)


def evidencia_de_imoveis(imoveis: list[dict], overrides: Mapping[str, str]) -> EvidenciaDeImovel:
    """Uma passada sobre os itens do run, com o mesmo classificador dos splitters."""
    classes = [(im, classificacao_do_imovel(im, dict(overrides))) for im in imoveis]
    return EvidenciaDeImovel(
        pids_no_run=frozenset(filter(None, (imovel_property_id(im) for im in imoveis))),
        n_desconhecido_em_aberto=sum(
            1 for im, cls in classes if cls == CLASSIFICATION_DESCONHECIDO and _em_aberto(im)
        ),
        gerador_sem_valor=any(
            cls in CLASSIFICATIONS_GERADORAS and item_nao_apurado(im) for im, cls in classes
        ),
    )


def _orfaos(evidencia: EvidenciaDeImovel, overrides: Mapping[str, str], classes) -> set[str]:
    """Overrides de `classes` cujo imóvel não aparece neste run."""
    return {pid for pid, cls in overrides.items() if cls in classes} - evidencia.pids_no_run


# Zero numérico de residência só com a palavra da família (`rented`, [[ADR-215]]): IRPF
# sem imóvel não prova ausência de casa — holding, bem comum declarado só no IRPF do
# cônjuge que não chegou, usufruto. Com a residência identificada o número é PISO: sem
# `property_id` o dedup da [[ADR-246]] não roda, e a cota do cônjuge pode estar no balde
# desconhecido.
def veredito_residencia(
    residencia: Decimal,
    evidencia: EvidenciaDeImovel,
    overrides: Mapping[str, str],
    status: str | None,
) -> VereditoBalde:
    """Número se > 0; zero só alugando; senão `null` com o motivo que orienta a ação."""
    if residencia > 0:
        return VereditoBalde(CoberturaStatus.apurado, piso=evidencia.n_desconhecido_em_aberto > 0)
    if status == RESIDENCIA_ALUGADA:
        return VereditoBalde(CoberturaStatus.zero_apurado)
    return VereditoBalde(
        CoberturaStatus.nao_apurado, _motivo_da_residencia(evidencia, overrides, status)
    )


def _motivo_da_residencia(
    evidencia: EvidenciaDeImovel, overrides: Mapping[str, str], status: str | None
) -> MotivoBaldeImovel:
    marcadas = {pid for pid, cls in overrides.items() if cls == CLASSIFICATION_RESIDENCIA_PRINCIPAL}
    if _orfaos(evidencia, overrides, {CLASSIFICATION_RESIDENCIA_PRINCIPAL}):
        return MotivoBaldeImovel.nao_localizada
    if marcadas:
        return MotivoBaldeImovel.sem_valor
    if status == RESIDENCIA_PROPRIA:
        return MotivoBaldeImovel.nao_classificada
    return MotivoBaldeImovel.nao_declarada


# [[ADR-444]] D2: a carteira de investimentos lê o veredito PUBLICADO, nunca um quarto
# splitter — os quatro motivos de `nao_apurado`, inclusive `sem_valor`: zero em 31/12 é venda,
# e quem vendeu a casa marcada tem a casa nova no desconhecido.
def residencia_pode_estar_no_desconhecido(bloco: Mapping[str, Any] | None) -> bool:
    """`True` com a residência não apurada; payload legado sem o bloco segue o anterior."""
    residencia = (bloco or {}).get("residencia") or {}
    return residencia.get("status") == CoberturaStatus.nao_apurado.value


# O discriminador é o imóvel em aberto, não o override: quem trocou o imóvel de renda por
# FII deixa o `locado` órfão gravado, e esse zero é verdadeiro. O órfão só escolhe o
# MOTIVO — vínculo perdido não tem CTA de classificar, porque o override já existe.
# Com imóvel em aberto o par sai `null` mesmo havendo gerador identificado: campo que às
# vezes é valor e às vezes é piso não tem leitor correto, e o piso já sai com nome
# próprio (`geradores_identificados`).
def veredito_geradores(
    geradores: Decimal, evidencia: EvidenciaDeImovel, overrides: Mapping[str, str]
) -> VereditoBalde:
    """Número só com todo imóvel identificado e com valor; senão `null` com o motivo."""
    if evidencia.gerador_sem_valor:
        return VereditoBalde(CoberturaStatus.nao_apurado, MotivoBaldeImovel.sem_valor)
    if evidencia.n_desconhecido_em_aberto == 0:
        status = CoberturaStatus.apurado if geradores > 0 else CoberturaStatus.zero_apurado
        return VereditoBalde(status)
    orfao = _orfaos(evidencia, overrides, CLASSIFICATIONS_GERADORAS)
    motivo = MotivoBaldeImovel.vinculo_perdido if orfao else MotivoBaldeImovel.nao_classificados
    return VereditoBalde(CoberturaStatus.nao_apurado, motivo)


@dataclass(frozen=True)
class VereditosDeImovel:
    """Os dois vereditos do run + a contagem de overrides sem imóvel, para o motivo."""

    residencia: VereditoBalde
    geradores: VereditoBalde
    evidencia: EvidenciaDeImovel
    orfaos_residencia: int
    orfaos_geradores: int

    def to_dict(self) -> dict:
        return {
            "residencia": self.residencia.to_dict(),
            "imoveis_geradores": self.geradores.to_dict(),
            "n_desconhecido_em_aberto": self.evidencia.n_desconhecido_em_aberto,
            "overrides_sem_imovel": {
                "residencia_principal": self.orfaos_residencia,
                "geradores": self.orfaos_geradores,
            },
        }


def vereditos_de_imovel(
    *,
    imoveis: list[dict],
    overrides: Mapping[str, str],
    residencia_status: str | None,
    residencia: Decimal,
    geradores: Decimal,
) -> VereditosDeImovel:
    """Produtor único dos vereditos que o calculator publica ([[ADR-439]] D1)."""
    ev = evidencia_de_imoveis(imoveis, overrides)
    return VereditosDeImovel(
        residencia=veredito_residencia(residencia, ev, overrides, residencia_status),
        geradores=veredito_geradores(geradores, ev, overrides),
        evidencia=ev,
        orfaos_residencia=len(_orfaos(ev, overrides, {CLASSIFICATION_RESIDENCIA_PRINCIPAL})),
        orfaos_geradores=len(_orfaos(ev, overrides, CLASSIFICATIONS_GERADORAS)),
    )


@dataclass(frozen=True)
class ImoveisDoRun:
    """Cobertura + vereditos do run: o que o calculator publica sobre imóveis."""

    cobertura: CoberturaClassificacaoImovel
    vereditos: VereditosDeImovel
    residencia_status: str

    def bloco(self) -> dict:
        """`patrimonio.cobertura_classificacao_imovel` ([[ADR-439]] D1)."""
        return {
            **self.cobertura.to_dict(),
            **self.vereditos.to_dict(),
            "residencia_status": self.residencia_status,
        }


# Fronteira float→Decimal do `PatrimonioCalculator`, no molde de
# `aplicar_guarda_aos_componentes`: os splitters ainda somam em float.
def classificar_imoveis_do_run(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides: Mapping[str, str],
    residencia_status: str | None,
    residencia: float,
    geradores: float,
) -> ImoveisDoRun:
    """Cobertura e vereditos sobre os MESMOS itens que os splitters somaram."""
    bens = {"titular_bens": titular_bens, "conjuge_bens": conjuge_bens}
    status = residencia_status or RESIDENCIA_NAO_DECLARADA
    imoveis = (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or [])
    return ImoveisDoRun(
        cobertura=cobertura_classificacao_imovel(**bens, overrides_by_property_id=dict(overrides)),
        vereditos=_vereditos_em_decimal(imoveis, overrides, status, residencia, geradores),
        residencia_status=status,
    )


def _vereditos_em_decimal(
    imoveis: list[dict], overrides: Mapping[str, str], status: str, *baldes: float
) -> VereditosDeImovel:
    residencia, geradores = (Decimal(str(b)) for b in baldes)
    return vereditos_de_imovel(
        imoveis=imoveis,
        overrides=overrides,
        residencia_status=status,
        residencia=residencia,
        geradores=geradores,
    )


# Só a evidência CONTRÁRIA vira razão: a família classificou e o run perdeu o vínculo.
# "Nunca classificou" é estado do produto, e o CTA do relatório já cuida dele. O override
# órfão sozinho também não vira razão — imóvel vendido o deixa gravado ([[ADR-439]] D7).
_MOTIVO_DE_VINCULO_PERDIDO = {
    "residencia": MotivoBaldeImovel.nao_localizada,
    "imoveis_geradores": MotivoBaldeImovel.vinculo_perdido,
}


def review_reasons_da_classificacao_imovel(
    patrimonio: dict, *, stage: str, artifact_key: str
) -> list[dict]:
    """Razão ADVISORY: override gravado que o run não alcançou; nunca retém."""
    bloco = (patrimonio or {}).get("cobertura_classificacao_imovel") or {}
    return [
        _razao_de_vinculo_perdido(balde, stage=stage, artifact_key=artifact_key)
        for balde, motivo in _MOTIVO_DE_VINCULO_PERDIDO.items()
        if (bloco.get(balde) or {}).get("motivo") == motivo.value
    ]


def _razao_de_vinculo_perdido(balde: str, *, stage: str, artifact_key: str) -> dict:
    """Sem descrição nem endereço: o nome do balde basta, e endereço é PII."""
    return ReviewReason(
        code=ReviewReasonCode.domain_classificacao_imovel_nao_apurada,
        stage=stage,
        artifact_key=artifact_key,
        document_id=None,
        offending_value=f"balde={balde}",
        expected="override de classificação alcançado por um imóvel do run",
        message="Imovel classificado pela familia nao foi localizado neste run",
    ).to_dict()


__all__ = [
    "EvidenciaDeImovel",
    "ImoveisDoRun",
    "MotivoBaldeImovel",
    "RESIDENCIA_ALUGADA",
    "RESIDENCIA_NAO_DECLARADA",
    "RESIDENCIA_PROPRIA",
    "VereditoBalde",
    "VereditosDeImovel",
    "classificar_imoveis_do_run",
    "evidencia_de_imoveis",
    "residencia_pode_estar_no_desconhecido",
    "review_reasons_da_classificacao_imovel",
    "veredito_geradores",
    "veredito_residencia",
    "vereditos_de_imovel",
]

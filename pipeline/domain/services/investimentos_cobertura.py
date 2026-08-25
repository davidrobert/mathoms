"""Cobertura de investimentos por membro ([[ADR-394]] §Emenda 2026-08-18 (b), D7).

`fonte_investimentos` é uma string do **domicílio**: descreve o caminho que o
cálculo tomou, não se cada pessoa foi medida. Com o titular vindo de posições
atuais e o cônjuge de lugar nenhum, ela diz `"posicoes_atuais"` para os dois.
Quem responde "este membro foi medido?" é o campo desta módulo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

COBERTURA_ENV = "MATHOMS_E5_COBERTURA_MEMBRO"

FONTE_POSICOES = "posicoes_atuais"
FONTE_IRPF = "irpf"


class CoberturaStatus(str, Enum):
    """`zero_apurado` é a saída da ressalva; `nao_apurado` nunca publica 0,00."""

    apurado = "apurado"
    zero_apurado = "zero_apurado"
    nao_apurado = "nao_apurado"


def cobertura_enforcement_ligado() -> bool:
    """Kill-switch de 1 env var; `0` desliga a ressalva e a supressão, não o campo."""
    return os.environ.get(COBERTURA_ENV, "1") != "0"


@dataclass(frozen=True)
class MembroObservado:
    """O que o calculator viu para um membro, antes de qualquer decisão."""

    membro: str
    valor_brl: Decimal
    posicoes_atribuidas: bool
    fallback_irpf: bool
    ano_base: str | None = None


@dataclass(frozen=True)
class CoberturaMembro:
    """Veredito de cobertura de um membro — enum fechado, nunca string livre."""

    membro: str
    status: CoberturaStatus
    fonte: str | None
    # `frescor` responde "de QUANDO", que `fonte` não responde: a §Escopo da
    # [[A40.l69]] pediu os dois e a implementação inicial só shipou `fonte`.
    # Defasagem não é estado — `status` diz se mediu, `frescor` diz quando.
    frescor: str | None = None
    motivo: str | None = None

    @property
    def apurado(self) -> bool:
        return self.status is not CoberturaStatus.nao_apurado

    def to_dict(self) -> dict:
        return {
            "membro": self.membro,
            "status": self.status.value,
            "fonte": self.fonte,
            "frescor": self.frescor,
            "motivo": self.motivo,
        }

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Só `nao_apurado` vira razão — zero medido é resposta, não pendência."""
        if self.apurado:
            return None
        return ReviewReason(
            code=ReviewReasonCode.domain_membro_nao_apurado,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value=f"membro={self.membro}",
            expected="fonte de investimentos atribuida ao membro",
            message="Membro sem fonte de investimentos: balde nao apurado",
        )


# A ordem dos ramos é a hierarquia de autoridade: fonte observada primeiro
# (posições atuais > IRPF), e "não medido" só quando nenhuma delas respondeu.
#
# Não existe ramo "tem bens no baseline ⇒ zero_apurado". Ele existiu e media o
# CONTÊINER: `build_members_from_consolidated` materializa `bens` com 4 chaves
# sempre, então o predicado era constante `True` e `nao_apurado` era inalcançável
# — 0/114 instâncias-membro do corpus. Presença de linha não é evidência de
# medição; só valor é. Com o valor lido, o ramo 2 já capturou; sem ele, é
# `nao_apurado` ([[ADR-394]] §Emenda (c)).
def classificar_cobertura(obs: MembroObservado) -> CoberturaMembro:
    """Traduz o observado nos 3 estados ([[ADR-394]] §Emenda (b) D7)."""
    if obs.posicoes_atribuidas:
        status = CoberturaStatus.apurado if obs.valor_brl != 0 else CoberturaStatus.zero_apurado
        return CoberturaMembro(
            membro=obs.membro, status=status, fonte=FONTE_POSICOES, frescor=obs.ano_base
        )
    if obs.fallback_irpf:
        return CoberturaMembro(
            membro=obs.membro,
            status=CoberturaStatus.apurado,
            fonte=FONTE_IRPF,
            frescor=obs.ano_base,
        )
    return CoberturaMembro(
        membro=obs.membro,
        status=CoberturaStatus.nao_apurado,
        fonte=None,
        motivo="nenhuma fonte devolveu valor para o membro",
    )


# `None` e não `0,0`: um zero publicado é uma afirmação sobre o patrimônio da
# pessoa, e o sistema não a mediu ([[ADR-394]] §Emenda (b) D7).
def valor_publicavel(valor: float, cobertura: tuple, papel: str) -> float | None:
    """Valor do balde, ou ``None`` quando o membro não foi apurado."""
    apurado = next((c.apurado for c in cobertura if c.membro == papel), True)
    return round(valor, 2) if apurado else None


def motivo_supressao_por_cobertura(coberturas: tuple[CoberturaMembro, ...]) -> str | None:
    """Prescrição exige cobertura: um membro não apurado já a suprime."""
    if not cobertura_enforcement_ligado():
        return None
    pendentes = [c.membro for c in coberturas if not c.apurado]
    return f"cobertura_incompleta: {', '.join(pendentes)}" if pendentes else None


def motivo_supressao_da_cobertura(patrimonio: dict) -> str | None:
    """Motivo derivado do artefato E5; `None` em payload legado sem o campo."""
    linhas = (patrimonio or {}).get("cobertura_investimentos") or []
    coberturas = tuple(
        CoberturaMembro(
            membro=str(linha.get("membro") or ""),
            status=CoberturaStatus(linha.get("status") or CoberturaStatus.nao_apurado.value),
            fonte=linha.get("fonte"),
        )
        for linha in linhas
        if isinstance(linha, dict)
    )
    return motivo_supressao_por_cobertura(coberturas)


def motivo_supressao_e5(patrimonio: dict) -> str | None:
    """Prescrição cai se a guarda de sinal OU a cobertura por membro falarem."""
    from pipeline.domain.services.patrimonio_sign_guard import motivo_supressao_do_patrimonio

    return motivo_supressao_do_patrimonio(patrimonio) or motivo_supressao_da_cobertura(patrimonio)


# Família de 1 titular: `tem_conjuge=False` significa que não há pessoa a cobrir,
# e uma linha `nao_apurado` seria ressalva sobre alguém que não existe.
def cobertura_de_membros(
    *, tem_conjuge: bool, titular: tuple, conjuge: tuple
) -> tuple[CoberturaMembro, ...]:
    """Veredito por papel a partir do observado `(valor, atribuido, fallback, ano_base)`."""
    papeis = [("titular", titular)]
    if tem_conjuge:
        papeis.append(("conjuge", conjuge))
    return tuple(
        classificar_cobertura(
            MembroObservado(
                membro=papel,
                valor_brl=Decimal(str(valor)),
                posicoes_atribuidas=atribuido,
                fallback_irpf=fallback,
                ano_base=ano_base,
            )
        )
        for papel, (valor, atribuido, fallback, ano_base) in papeis
    )


def review_reasons_da_cobertura(patrimonio: dict, *, stage: str, artifact_key: str) -> list[dict]:
    """Projeta os membros `nao_apurado` do artefato E5 para ``review_reason``."""
    if not cobertura_enforcement_ligado():
        return []
    linhas = (patrimonio or {}).get("cobertura_investimentos") or []
    reasons = [
        CoberturaMembro(
            membro=str(linha.get("membro") or ""),
            status=CoberturaStatus(linha.get("status") or CoberturaStatus.nao_apurado.value),
            fonte=linha.get("fonte"),
        ).to_review_reason(stage=stage, artifact_key=artifact_key, document_id=None)
        for linha in linhas
        if isinstance(linha, dict)
    ]
    return [r.to_dict() for r in reasons if r is not None]


__all__ = [
    "COBERTURA_ENV",
    "CoberturaMembro",
    "CoberturaStatus",
    "MembroObservado",
    "classificar_cobertura",
    "cobertura_de_membros",
    "cobertura_enforcement_ligado",
    "motivo_supressao_da_cobertura",
    "motivo_supressao_e5",
    "motivo_supressao_por_cobertura",
    "review_reasons_da_cobertura",
    "valor_publicavel",
]

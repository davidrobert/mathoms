"""Guarda de sinal dos baldes patrimoniais publicados ([[ADR-394]] §Emenda 2026-08-18).

Roda **a montante** de ``_compute_bruto`` e ``_build_composicao`` — que são duas
somas independentes sobre os mesmos seis componentes. Corrigir a linha da
``composicao`` dessincronizaria os dois agregados; corrigir o componente preserva
``composicao ≡ bruto`` e mantém ``patrimonio_liquido`` intacto.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

SIGN_GUARD_ENV = "MATHOMS_E5_SIGN_GUARD"

# Negativo aqui é saldo devedor legítimo — cheque especial na conta corrente,
# conta margem na corretora. Vira dívida de curto prazo e o relatório publica
# normalmente ([[ADR-394]] §Emenda D6).
BALDES_RECLASSIFICAVEIS: tuple[str, ...] = (
    "caixa_total_brl",
    "investimentos_titular",
    "investimentos_conjuge",
)

# Imóvel e veículo não valem menos que nada: negativo aqui é defeito de dado, não
# passivo. Mover o montante para `total_dividas` inventaria um passivo; zerá-lo
# sem mover inventaria patrimônio. Publica com ressalva e sem mutação — que
# também é o que preserva `imoveis_investimento ≡ geradores + não-geradores`.
BALDES_FISICOS: tuple[str, ...] = (
    "residencia",
    "imoveis_investimento",
    "veiculos",
    "imoveis_geradores",
    "imoveis_nao_geradores",
)


class SignGuardMode(str, Enum):
    """`off` restaura o status quo ante literal, incluindo o clamp de caixa."""

    enforce = "enforce"
    warn = "warn"
    off = "off"


def sign_guard_mode() -> SignGuardMode:
    """Modo declarado no ambiente; valor desconhecido cai em `enforce` (fail-closed)."""
    raw = (os.environ.get(SIGN_GUARD_ENV) or "").strip().lower()
    try:
        return SignGuardMode(raw)
    except ValueError:
        return SignGuardMode.enforce


@dataclass(frozen=True)
class BaldesPatrimoniais:
    """Os 6 componentes da composição + o split derivado de cat_2, em Decimal (ADR-090)."""

    residencia: Decimal
    imoveis_investimento: Decimal
    veiculos: Decimal
    investimentos_titular: Decimal
    investimentos_conjuge: Decimal
    caixa_total_brl: Decimal
    imoveis_geradores: Decimal
    imoveis_nao_geradores: Decimal

    def valor(self, balde: str) -> Decimal:
        return getattr(self, balde)


@dataclass(frozen=True)
class ReclassificadoParaDividaCurtoPrazo:
    """Warning tipado ([[ADR-097]] D1): saldo devedor saiu do ativo e entrou no passivo."""

    balde: str
    montante_brl: Decimal

    def format(self) -> str:
        return (
            f"{self.balde} estava negativo em R$ {self.montante_brl:.2f}; "
            "reclassificado para dívida de curto prazo (patrimônio líquido inalterado)"
        )

    def to_dict(self) -> dict:
        return {"balde": self.balde, "montante_brl": float(self.montante_brl)}


@dataclass(frozen=True)
class BaldeNegativoSobrevivente:
    """Warning tipado: negativo em balde físico — publica com ressalva, sem mutar."""

    balde: str
    valor_brl: Decimal

    def format(self) -> str:
        return (
            f"{self.balde} publicou valor negativo (R$ {self.valor_brl:.2f}) e não é "
            "reclassificável: imóvel e veículo não têm saldo devedor próprio"
        )

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason:
        """Projeta para ReviewReason ([[ADR-272]]); o nome do balde não é PII."""
        return ReviewReason(
            code=ReviewReasonCode.domain_balde_patrimonial_negativo,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value=f"balde={self.balde}",
            expected=f"{self.balde} >= 0",
            message="Balde patrimonial fisico publicou valor negativo",
        )

    def to_dict(self) -> dict:
        return {"balde": self.balde, "valor_brl": float(self.valor_brl)}


# Um grão ABAIXO do balde ([[ADR-430]]). A D6 opera no agregado e é cega ao item:
# o balde segue positivo enquanto o negativo for menor que a soma dos irmãos. Aqui
# o item já chega com o valor removido pelo produtor — a guarda não muta nada, só
# conta o que chegou sem valor para decidir a supressão.
@dataclass(frozen=True)
class ItemFisicoSemValor:
    """Ativo físico publicado sem valor apurado — o item fica, a Σ o exclui."""

    colecao: str
    descricao: str
    ano: str

    def format(self) -> str:
        return (
            f"{self.colecao}: item sem valor apurado em {self.ano}; fora da soma "
            "e das prescrições que dependem dele"
        )

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason:
        """Projeta para ReviewReason ([[ADR-272]]); sem `descricao` — endereço é PII."""
        return ReviewReason(
            code=ReviewReasonCode.domain_valor_nao_apurado,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value=f"colecao={self.colecao} ano={self.ano}",
            expected=f"{self.colecao}[].valor_31_12_ano_base apurado",
            message="Ativo fisico publicado sem valor apurado",
        )

    def to_dict(self) -> dict:
        return {"colecao": self.colecao, "descricao": self.descricao, "ano": self.ano}


@dataclass(frozen=True)
class GuardaDeSinalResult:
    baldes: BaldesPatrimoniais
    dividas_curto_prazo_brl: Decimal
    reclassificados: tuple[ReclassificadoParaDividaCurtoPrazo, ...]
    sobreviventes: tuple[BaldeNegativoSobrevivente, ...]
    modo: SignGuardMode
    itens_sem_valor: tuple[ItemFisicoSemValor, ...] = ()

    @property
    def cobertura_completa(self) -> bool:
        """Sem sobrevivente e sem item sem valor, a prescrição pode ser publicada."""
        return not self.sobreviventes and not self.itens_sem_valor

    # Composto: os dois eixos suprimem a MESMA família de prescrição (as que
    # dependem de cat_2), e o consumidor decide por `is not None`. Concatenar em
    # vez de eleger um preserva o diagnóstico quando ambos ocorrem no mesmo run.
    @property
    def motivo_supressao(self) -> str | None:
        motivos = []
        if self.sobreviventes:
            motivos.append("balde_negativo: " + ", ".join(s.balde for s in self.sobreviventes))
        if self.itens_sem_valor:
            motivos.append(f"valor_nao_apurado: {len(self.itens_sem_valor)} item(ns)")
        return "; ".join(motivos) or None

    def to_dict(self) -> dict:
        return {
            "modo": self.modo.value,
            "cobertura_completa": self.cobertura_completa,
            "motivo_supressao": self.motivo_supressao,
            "dividas_curto_prazo_brl": float(self.dividas_curto_prazo_brl),
            "reclassificados": [r.to_dict() for r in self.reclassificados],
            "baldes_negativos": [s.to_dict() for s in self.sobreviventes],
            "itens_sem_valor": [i.to_dict() for i in self.itens_sem_valor],
        }


def _reclassificar(
    baldes: BaldesPatrimoniais,
) -> tuple[BaldesPatrimoniais, Decimal, tuple[ReclassificadoParaDividaCurtoPrazo, ...]]:
    movidos: list[ReclassificadoParaDividaCurtoPrazo] = []
    total = Decimal("0")
    for balde in BALDES_RECLASSIFICAVEIS:
        valor = baldes.valor(balde)
        if valor >= 0:
            continue
        movidos.append(ReclassificadoParaDividaCurtoPrazo(balde=balde, montante_brl=-valor))
        total += -valor
        baldes = replace(baldes, **{balde: Decimal("0")})
    return baldes, total, tuple(movidos)


def _sobreviventes(baldes: BaldesPatrimoniais) -> tuple[BaldeNegativoSobrevivente, ...]:
    return tuple(
        BaldeNegativoSobrevivente(balde=b, valor_brl=baldes.valor(b))
        for b in BALDES_FISICOS
        if baldes.valor(b) < 0
    )


def _status_quo_ante(baldes: BaldesPatrimoniais) -> BaldesPatrimoniais:
    if baldes.caixa_total_brl >= 0:
        return baldes
    return replace(baldes, caixa_total_brl=Decimal("0"))


def motivo_supressao_do_patrimonio(patrimonio: dict | None) -> str | None:
    guarda = (patrimonio or {}).get("guarda_de_sinal")
    return guarda.get("motivo_supressao") if isinstance(guarda, dict) else None


# Só `enforce` projeta razão: em `warn` o artefato carrega a evidência e a
# prescrição já sai suprimida, mas o run não pausa. É aqui que o kill-switch
# separa "rebaixa e declara" de "para e espera humano".
def _razoes_dos_baldes(guarda: dict, **destino) -> list[dict]:
    return [
        BaldeNegativoSobrevivente(
            balde=str(b.get("balde") or ""),
            valor_brl=Decimal(str(b.get("valor_brl") or 0)),
        )
        .to_review_reason(**destino)
        .to_dict()
        for b in guarda.get("baldes_negativos") or []
    ]


# O produtor (E1.5c) já emite a razão no baseline; esta é a do artefato E5, que é
# o que o relatório lê. Cada stage declara o que CARREGA ([[ADR-411]] D2).
def _razoes_dos_itens(guarda: dict, **destino) -> list[dict]:
    return [
        ItemFisicoSemValor(
            colecao=str(i.get("colecao") or ""), descricao="", ano=str(i.get("ano") or "")
        )
        .to_review_reason(**destino)
        .to_dict()
        for i in guarda.get("itens_sem_valor") or []
    ]


def review_reasons_do_artefato(patrimonio: dict, *, stage: str, artifact_key: str) -> list[dict]:
    """Projeta os dois graus de negativo do artefato E5 para ``review_reason`` ([[ADR-272]])."""
    guarda = (patrimonio or {}).get("guarda_de_sinal") or {}
    if guarda.get("modo") != SignGuardMode.enforce.value:
        return []
    destino = {"stage": stage, "artifact_key": artifact_key, "document_id": None}
    return _razoes_dos_baldes(guarda, **destino) + _razoes_dos_itens(guarda, **destino)


def aplicar_guarda_de_sinal(
    baldes: BaldesPatrimoniais,
    *,
    modo: SignGuardMode | None = None,
    itens_sem_valor: tuple[ItemFisicoSemValor, ...] = (),
) -> GuardaDeSinalResult:
    """Reclassifica o negativo financeiro e ressalva o físico ([[ADR-394]] §Emenda D5/D6)."""
    modo = modo if modo is not None else sign_guard_mode()
    if modo is SignGuardMode.off:
        return _resultado_off(baldes)
    corrigidos, dividas, movidos = _reclassificar(baldes)
    return GuardaDeSinalResult(
        baldes=corrigidos,
        dividas_curto_prazo_brl=dividas,
        reclassificados=movidos,
        sobreviventes=_sobreviventes(corrigidos),
        modo=modo,
        itens_sem_valor=itens_sem_valor,
    )


def _resultado_off(baldes: BaldesPatrimoniais) -> GuardaDeSinalResult:
    return GuardaDeSinalResult(
        baldes=_status_quo_ante(baldes),
        dividas_curto_prazo_brl=Decimal("0"),
        reclassificados=(),
        sobreviventes=(),
        modo=SignGuardMode.off,
    )


def aplicar_guarda_aos_componentes(
    *,
    itens_sem_valor: tuple[ItemFisicoSemValor, ...] = (),
    **baldes: float,
) -> tuple[GuardaDeSinalResult, float, float, float]:
    """Boundary float→Decimal do ``PatrimonioCalculator``; devolve financeiros reclassificados."""
    guarda = aplicar_guarda_de_sinal(
        BaldesPatrimoniais(**{k: Decimal(str(v)) for k, v in baldes.items()}),
        itens_sem_valor=itens_sem_valor,
    )
    return (
        guarda,
        float(guarda.baldes.investimentos_titular),
        float(guarda.baldes.investimentos_conjuge),
        float(guarda.baldes.caixa_total_brl),
    )


__all__ = [
    "BALDES_FISICOS",
    "BALDES_RECLASSIFICAVEIS",
    "BaldeNegativoSobrevivente",
    "BaldesPatrimoniais",
    "GuardaDeSinalResult",
    "ItemFisicoSemValor",
    "ReclassificadoParaDividaCurtoPrazo",
    "SIGN_GUARD_ENV",
    "SignGuardMode",
    "aplicar_guarda_aos_componentes",
    "aplicar_guarda_de_sinal",
    "motivo_supressao_do_patrimonio",
    "review_reasons_do_artefato",
    "sign_guard_mode",
]

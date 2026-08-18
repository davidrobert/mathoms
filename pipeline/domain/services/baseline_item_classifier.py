"""Roteamento ativo × passivo de item de baseline patrimonial ([[ADR-394]]).

O eixo é decidido pelo **fato** — a ficha da declaração de onde o item foi lido —
e nunca pelo rótulo que o LLM escreveu. Medido em 7 runs do dogfood: o rótulo
flipa em 5/7 e o código sozinho é ambíguo (`'11'` rotula imóvel E dívida).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional

SECAO_ATIVO = "bens_direitos"
SECAO_PASSIVO = "dividas_onus"


class BaselineAxis(str, Enum):
    ATIVO = "ativo"
    PASSIVO = "passivo"


class ClassificationAuthority(str, Enum):
    """Qual degrau decidiu — vai no artefato, para o leitor saber a força da decisão."""

    SECAO = "secao"
    CATALOGO = "catalogo"
    SINAL = "sinal"
    HINT = "hint"


# `codigo` sozinho não é chave: o mesmo dígito vive nas duas fichas ('11' rotula
# apartamento E dívida). Sem `secao`, nada aqui é consultado.
@dataclass(frozen=True)
class BaselineCatalog:
    """Catálogo RFB por ano-base, indexado por `(secao, codigo)` ([[ADR-394]] D2)."""

    ano_base: int
    subtipo_por_secao_codigo: Mapping[tuple[str, str], str] = field(default_factory=dict)
    ano_base_solicitado: Optional[int] = None

    def subtipo(self, secao: Optional[str] = None, codigo: str = "") -> Optional[str]:
        if not secao:
            return None
        return self.subtipo_por_secao_codigo.get((secao, codigo.strip()))

    @property
    def is_fallback(self) -> bool:
        """O ano pedido não existia e caiu no mais recente — decisão enfraquecida."""
        return self.ano_base_solicitado is not None and self.ano_base_solicitado != self.ano_base


@dataclass(frozen=True)
class DivergenciaFatoHint:
    """Warning tipado ([[ADR-097]] D1): o hint discorda de quem decidiu."""

    autoridade: ClassificationAuthority
    eixo: BaselineAxis
    categoria_hint: str

    def format(self) -> str:
        return (
            f"fato ({self.autoridade.value}) roteou para {self.eixo.value}; "
            f"categoria_hint dizia {self.categoria_hint!r}"
        )


@dataclass(frozen=True)
class EixoDecididoPeloHint:
    """Warning tipado: nenhum fato estava disponível — decidiu o rótulo do LLM."""

    categoria_hint: str
    eixo: BaselineAxis

    def format(self) -> str:
        return (
            f"sem secao, sem catalogo e sem sinal: eixo {self.eixo.value} veio do "
            f"categoria_hint {self.categoria_hint!r}"
        )


@dataclass(frozen=True)
class BaselineClassification:
    eixo: BaselineAxis
    autoridade: ClassificationAuthority
    subtipo: Optional[str] = None
    warnings: tuple[object, ...] = ()


_HINT_PASSIVO = {"divida", "dividas", "financiamento", "emprestimo", "passivo"}


def _eixo_por_secao(secao: Optional[str] = None) -> Optional[BaselineAxis]:
    if secao == SECAO_PASSIVO:
        return BaselineAxis.PASSIVO
    if secao == SECAO_ATIVO:
        return BaselineAxis.ATIVO
    return None


def classify_baseline_item(
    *,
    codigo: str,
    valor_cents: int,
    secao: Optional[str] = None,
    categoria_hint: str = "",
    catalogo: Optional[BaselineCatalog] = None,
) -> BaselineClassification:
    """Decide o eixo pelo fato disponível mais forte; o hint é o último recurso."""
    hint = (categoria_hint or "").strip().lower()
    subtipo = catalogo.subtipo(secao, codigo) if catalogo else None
    eixo, autoridade = _decide_eixo(secao, valor_cents, hint)
    return BaselineClassification(
        eixo=eixo,
        autoridade=autoridade,
        subtipo=subtipo,
        warnings=tuple(_warnings_for(eixo, autoridade, hint)),
    )


# Ordem ([[ADR-394]] D1): `secao` → sinal (veto suficiente, nunca necessário) →
# `categoria_hint`. O sinal não promove a ativo: o IRPF declara saldo devedor
# POSITIVO na ficha de dívidas, então "positivo" não prova patrimônio.
def _decide_eixo(
    secao: Optional[str] = None, valor_cents: int = 0, hint: str = ""
) -> tuple[BaselineAxis, ClassificationAuthority]:
    """Degrau mais forte disponível → (eixo, quem decidiu)."""
    eixo = _eixo_por_secao(secao)
    if eixo is not None:
        return eixo, ClassificationAuthority.SECAO
    if valor_cents < 0:
        return BaselineAxis.PASSIVO, ClassificationAuthority.SINAL
    if hint in _HINT_PASSIVO:
        return BaselineAxis.PASSIVO, ClassificationAuthority.HINT
    return BaselineAxis.ATIVO, ClassificationAuthority.HINT


def _warnings_for(
    eixo: BaselineAxis, autoridade: ClassificationAuthority, hint: str
) -> list[object]:
    if autoridade is ClassificationAuthority.HINT:
        return [EixoDecididoPeloHint(categoria_hint=hint, eixo=eixo)]
    hint_diz_passivo = hint in _HINT_PASSIVO or hint == "outros"
    if eixo is BaselineAxis.PASSIVO and not hint_diz_passivo:
        return [DivergenciaFatoHint(autoridade=autoridade, eixo=eixo, categoria_hint=hint)]
    return []

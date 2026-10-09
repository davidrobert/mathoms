"""Contrato do veredito da métrica do parecer — estampado no finalize ([[A40.l92]]).

Extraído de ``parecer_planejador`` (teto de 500 linhas do CLAUDE.md §Code style). O front
desenhava a trilha re-derivando os números por regex sobre ``target``, a regex comia o
glifo, e a barra de um teto ENCHIA conforme a métrica piorava. O veredito agora viaja como
dado, e quem desenha não julga.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

# `<` segue no vocabulário do CONSUMIDOR: o parecer pode ser regenerado sobre E5 anterior
# à doutrina do limiar ([[ADR-399]] §Emenda 2026-10-08), e o E5 daquela era diz `<`.
OperadorComparador = Literal["<", "<=", ">="]
# Tiers da [[ADR-353]] D1, publicados pelo produtor em `diagnostico_confianca.nivel`.
NivelConfianca = Literal["alta", "parcial", "insuficiente"]


class Comparador(BaseModel):
    """Veredito do comparador da métrica, estampado no finalize — o front desenha, não julga."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # `operador` cru, não uma polaridade derivada: um 2º vocabulário teria de ficar em
    # sincronia com `KpiTarget`, `RiskTrigger` e o schema E5 (co-design data-engineer).
    operador: OperadorComparador
    conforme: bool
    # Só no piso — teto não tem progresso ([[A40.l92]]); 100 se e só se conforme.
    progresso_pct: Optional[int] = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _ck_progresso(self) -> "Comparador":
        erro = erro_de_forma(self.operador, self.conforme, self.progresso_pct)
        if erro:
            raise ValueError(erro)
        return self


# `progresso_pct` None é a forma do teto (sem progresso), não um valor desconhecido.
def erro_de_forma(operador: str, conforme: bool, progresso_pct: Optional[int]) -> Optional[str]:
    """Mensagem se a forma é incoerente — só piso tem progresso, e 100 é o conforme."""
    if progresso_pct is None:
        return None
    if operador != ">=" or (progresso_pct == 100) != conforme:
        return (
            f"progresso_pct={progresso_pct} incoerente com operador={operador!r} "
            f"conforme={conforme}: só piso tem progresso, e 100 é exatamente o conforme"
        )
    return None


# `SkipJsonSchema` só esconde o campo do contrato enviado ao modelo: o que ele mandar chega
# ao parse, e valor inválido levantaria `ValidationError` — reask, o padrão do incidente que
# a [[ADR-294]] fechou com coerce. O finalize estampa os dois campos de todo jeito; aqui o
# válido passa (é o que o round-trip do cache precisa) e o resto vira `None`.
def coerce_estampado(campo: str, valor: Any) -> Any:
    """Valor de campo estampado vindo de fora: o válido passa, o inválido vira ``None``."""
    if valor is None or isinstance(valor, Comparador):
        return valor
    if campo == "nivel_confianca":
        return valor if isinstance(valor, str) and valor in get_args(NivelConfianca) else None
    try:
        return Comparador.model_validate(valor)
    except ValidationError:
        return None


__all__ = [
    "Comparador",
    "NivelConfianca",
    "OperadorComparador",
    "coerce_estampado",
    "erro_de_forma",
]

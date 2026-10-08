"""Contrato do veredito da métrica do parecer — estampado no finalize ([[A40.l92]]).

Extraído de ``parecer_planejador`` (teto de 500 linhas do CLAUDE.md §Code style). O front
desenhava a trilha re-derivando os números por regex sobre ``target``, a regex comia o
glifo, e a barra de um teto ENCHIA conforme a métrica piorava. O veredito agora viaja como
dado, e quem desenha não julga.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
        teto = self.operador != ">="
        if self.progresso_pct is None:
            return self
        if teto or (self.progresso_pct == 100) != self.conforme:
            raise ValueError(
                f"progresso_pct={self.progresso_pct} incoerente com operador="
                f"{self.operador!r} conforme={self.conforme}: só piso tem progresso, "
                "e 100 é exatamente o conforme"
            )
        return self


__all__ = ["Comparador", "NivelConfianca", "OperadorComparador"]

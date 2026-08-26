"""Predicado ÚNICO de supressão por atribuição incompleta ([[ADR-412]] §D7 · §Emenda E4).

Morre a **prescrição dimensionada** — o *quanto mover* —, nunca a descrição. É o
precedente `alocacao_alvo_deviation.suprimir_prescricao`, e a distinção é
medida: suprimir o rótulo `avaliacao_liquidity` faz `HeroKpiGrid.reservaQuality`
re-derivar "excelente" por conta própria e desarma `neutralize_autocontradicao`,
libertando o LLM a elogiar a reserva.

**Não chama `cobertura_enforcement_ligado()`.** Aquele kill-switch governa
ressalva e retenção ([[ADR-412]] §D8); herdá-lo aqui entregaria supressão de
prescrição desligável por env var, e prescrição errada não é ruído — é conselho.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pipeline.domain.services.bases_financeiras import BaseFinanceira, publicavel_sozinha

# Degraus em MESES/ANOS da quantidade acionável, nunca em razão. O erro medido na
# A40.l80 foi 1,73x na cobertura e 3,50x no excedente sobre o alvo — subtrair o
# alvo amplifica. Mas `meses_alvo` é comum aos dois extremos do intervalo, então o
# spread do excedente É o spread da cobertura: a razão motiva o degrau, e nunca
# entra no `if`. Os valores reusam o que o relatório já publica em `niveis_meses`.
DEGRAU_EXCEDENTE_MESES = 6.0
DEGRAU_DEFICIT_MESES = 1.0
DEGRAU_PRAZO_ANOS = 1.0


@dataclass(frozen=True)
class SupressaoPorAtribuicao:
    """Decidida UMA vez por run e injetada; produtor não a resolve por dentro."""

    acima_do_piso: bool
    pct_sem_titular: float
    base_medida: BaseFinanceira
    base_piso: BaseFinanceira

    def __post_init__(self) -> None:
        if not publicavel_sozinha(self.base_medida):
            raise ValueError(f"base da medida não é publicável sozinha: {self.base_medida.value}")
        if publicavel_sozinha(self.base_piso):
            raise ValueError(f"base do piso não é extremo de intervalo: {self.base_piso.value}")

    @classmethod
    def do_patrimonio(
        cls,
        patrimonio: Mapping[str, Any],
        *,
        base_medida: BaseFinanceira = BaseFinanceira.carteira_financeira_familia,
        base_piso: BaseFinanceira = BaseFinanceira.carteira_com_titular_identificado,
    ) -> "SupressaoPorAtribuicao":
        """Lê o eixo já publicado pelo PR3a — não recomputa a atribuição."""
        bloco = (patrimonio or {}).get("atribuicao_investimentos") or {}
        return cls(
            acima_do_piso=bool(bloco.get("motivo")),
            pct_sem_titular=float(bloco.get("pct_carteira_financeira") or 0.0),
            base_medida=base_medida,
            base_piso=base_piso,
        )

    def de_reserva(
        self, *, medida_meses: float, piso_meses: float, meses_alvo: float
    ) -> str | None:
        """Suprime *quanto realocar*; o rótulo da reserva sobrevive."""
        if self._cruza(medida_meses, piso_meses, meses_alvo):
            return self._motivo("o intervalo cruza o alvo da reserva")
        degrau = DEGRAU_EXCEDENTE_MESES if piso_meses >= meses_alvo else DEGRAU_DEFICIT_MESES
        return (
            self._motivo("excedente da reserva")
            if self._spread(medida_meses, piso_meses, degrau)
            else None
        )

    def de_autonomia(self, *, medida_meses: float, piso_meses: float) -> str | None:
        """Autonomia autoriza gastar o fôlego — conservador é o extremo inferior."""
        if self._spread(medida_meses, piso_meses, DEGRAU_DEFICIT_MESES):
            return self._motivo("meses de autonomia")
        return None

    def de_prazo(self, *, medida_anos: float | None, teto_anos: float | None) -> str | None:
        """Prazo de IF: conservador é o MAIS LONGO — errar para 'demora mais' faz poupar mais."""
        if medida_anos is None or teto_anos is None:
            return None
        if self._spread(teto_anos, medida_anos, DEGRAU_PRAZO_ANOS):
            return self._motivo("anos até a independência")
        return None

    def _spread(self, maior: float, menor: float, degrau: float) -> bool:
        return self.acima_do_piso and (maior - menor) >= degrau

    # Materialidade automática: se um extremo diz "acima do alvo" e o outro diz
    # "abaixo", nenhum degrau de tamanho salva a prescrição — ela inverte de sinal.
    def _cruza(self, medida: float, piso: float, alvo: float) -> bool:
        return self.acima_do_piso and piso < alvo <= medida

    def _motivo(self, grandeza: str) -> str:
        return (
            f"atribuicao_incompleta: {self.pct_sem_titular:.1f}% da carteira financeira "
            f"sem titular identificado — {grandeza} depende de quem é o dono"
        )


__all__ = [
    "DEGRAU_DEFICIT_MESES",
    "DEGRAU_EXCEDENTE_MESES",
    "DEGRAU_PRAZO_ANOS",
    "SupressaoPorAtribuicao",
]

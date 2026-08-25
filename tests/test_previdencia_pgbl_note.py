"""Regressão RV2-03 + FP-5A: a nota PGBL ramifica por motivo, não por ``restante``.

Antes de RV2-03, ``modelo_simplificado`` (dedução desabilitada pelo modelo) e
``no_teto`` (teto de 12% consumido) colapsavam ambos em "teto atingido" —
factualmente falso no simplificado e invertendo o conselho.

Pós-ADR-402 o teste atravessa o ANALYZER, não o helper de nota: nota e campos
derivam do mesmo VO, então exercitar só a função de texto deixaria de medir a
coocorrência que é o contrato.
"""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.irpf_analyzer import CapacidadePgbl, PgblStatus
from pipeline.domain.services.previdencia_analyzer import (
    CapacidadePgblIRPF,
    PrevidenciaAnalyzer,
)

_RENDA = Decimal("100000")
_TETO = _RENDA * Decimal("0.12")


def _nota(status: PgblStatus, restante: str = "0") -> str:
    tem_teto = status not in (PgblStatus.modelo_simplificado, PgblStatus.sem_renda_tributavel)
    cap = CapacidadePgblIRPF(
        capacidade=CapacidadePgbl(
            teto=_TETO if tem_teto else None,
            aportado=Decimal("0"),
            restante=Decimal(restante) if tem_teto else None,
            status=status,
            excedente_nao_dedutivel=Decimal("0"),
        ),
        renda_tributavel_anual=_RENDA,
        base_calculo_anual=_RENDA,
        ano_base=2024,
        fonte="irpf_pgbl_capacidade",
    )
    return PrevidenciaAnalyzer().analyze({}, capacidade_irpf=cap).nota


def test_simplificado_nao_afirma_teto_atingido():
    nota = _nota(PgblStatus.modelo_simplificado)
    assert "atingido" not in nota.lower()  # o bug afirmava teto atingido
    assert "não foi consumido" in nota
    assert "modelo completo" in nota
    assert "simplificado" in nota.lower()


def test_no_teto_afirma_teto():
    nota = _nota(PgblStatus.no_teto)
    assert "teto de 12%" in nota.lower()
    assert "atingido" in nota.lower()


def test_sem_renda_atribui_ausencia_a_base():
    nota = _nota(PgblStatus.sem_renda_tributavel)
    assert "sem base de cálculo" in nota.lower()
    assert "atingido" not in nota.lower()


def test_capacidade_disponivel_mostra_restante_e_diferimento():
    nota = _nota(PgblStatus.capacidade_disponivel, "5000")
    assert "Capacidade PGBL restante" in nota
    assert "difere o IR" in nota


def test_simplificado_difere_de_no_teto():
    """O bug RV2-03 fazia os dois colapsarem no mesmo texto."""
    assert _nota(PgblStatus.modelo_simplificado) != _nota(PgblStatus.no_teto)

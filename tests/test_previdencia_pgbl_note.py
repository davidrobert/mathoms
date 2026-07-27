"""Regressão RV2-03: a nota PGBL ramifica por PgblStatus (modelo_simplificado ≠ teto).

Antes do fix, `_nota_capacidade_irpf` ramificava só em `restante > 0` — modelo_simplificado
(dedução desabilitada pelo modelo) e no_teto (teto de 12% consumido) colapsavam ambos em
"teto atingido", factualmente falso no simplificado e invertendo o conselho.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.irpf_analyzer import PgblStatus
from pipeline.domain.services.previdencia_analyzer import (
    CapacidadePgblIRPF,
    _nota_capacidade_irpf,
)


def _cap(status: PgblStatus | None, restante: str = "0") -> CapacidadePgblIRPF:
    return CapacidadePgblIRPF(
        restante_anual=Decimal(restante),
        renda_tributavel_anual=Decimal("100000"),
        ano_base=2024,
        fonte="irpf_pgbl_capacidade",
        pgbl_status=status,
    )


def test_simplificado_nao_afirma_teto_atingido():
    nota = _nota_capacidade_irpf(_cap(PgblStatus.modelo_simplificado), 0.0)
    assert "atingido" not in nota.lower()  # o bug afirmava teto atingido
    assert "não foi consumido" in nota
    assert "modelo completo" in nota
    assert "simplificado" in nota.lower()


def test_no_teto_afirma_teto():
    nota = _nota_capacidade_irpf(_cap(PgblStatus.no_teto), 0.0)
    assert "teto de 12%" in nota.lower()
    assert "atingido" in nota.lower()


def test_sem_renda_atribui_ausencia_a_base():
    nota = _nota_capacidade_irpf(_cap(PgblStatus.sem_renda_tributavel), 0.0)
    assert "sem base de cálculo" in nota.lower()
    assert "atingido" not in nota.lower()


def test_capacidade_disponivel_mostra_restante_e_diferimento():
    nota = _nota_capacidade_irpf(_cap(PgblStatus.capacidade_disponivel, "5000"), 5000.0)
    assert "Capacidade PGBL restante" in nota
    assert "difere o IR" in nota


def test_simplificado_difere_de_no_teto():
    """O bug RV2-03 fazia os dois colapsarem no mesmo texto."""
    n_simpl = _nota_capacidade_irpf(_cap(PgblStatus.modelo_simplificado), 0.0)
    n_teto = _nota_capacidade_irpf(_cap(PgblStatus.no_teto), 0.0)
    assert n_simpl != n_teto


def test_fallback_sem_status_preserva_comportamento_legado():
    """pgbl_status=None (path proxy antigo) mantém a ramificação por restante."""
    com_saldo = _nota_capacidade_irpf(_cap(None, "3000"), 3000.0)
    sem_saldo = _nota_capacidade_irpf(_cap(None, "0"), 0.0)
    assert "Capacidade PGBL restante" in com_saldo
    assert "atingido" in sem_saldo.lower()

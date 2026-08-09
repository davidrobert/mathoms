"""ADR-373 — S7 e o Apêndice C resolvem o prazo IF pela MESMA fórmula.

`CenariosConjugeAnalyzer._compute_prazo` era uma segunda cópia de
`IFProjector._solve_prazo`, com o mesmo guard `r > 0 and aporte > 0`. Preencher
um ramo só de um lado faria a projeção principal dizer "N anos" e o cenário de
estresse dizer "não projetável" para a mesma família, com as mesmas premissas.
"""

from __future__ import annotations

from datetime import date

import pytest

from pipeline.domain.services.cenarios_conjuge_analyzer import (
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
)
from pipeline.domain.services.if_projector import solve_prazo_anos

_REF = date(2026, 4, 19)
_DOB = date(1985, 6, 15)

# (investivel, meta, r_mensal, aporte)
_CASOS = [
    (1_000_000.0, 5_000_000.0, 0.0048675, 10_000.0),  # ramo composto
    (100_000.0, 1_000_000.0, 0.0, 10_000.0),  # ramo linear (retorno zero)
    (13_000_000.0, 100_000_000.0, 0.0048675, 0.0),  # aporte não declarado
    (0.0, 1_000_000.0, 0.0, 0.0),  # sem trajetória
    (2_000_000.0, 1_000_000.0, 0.0048675, 5_000.0),  # meta já atingida
]


@pytest.mark.parametrize("investivel,meta,r,aporte", _CASOS)
def test_os_dois_call_sites_devolvem_o_mesmo_prazo(investivel, meta, r, aporte) -> None:
    """Mutação que mata: reintroduzir a fórmula em `_compute_prazo`."""
    do_cenario = CenariosConjugeAnalyzer._compute_prazo(investivel, meta, r, aporte)
    do_projetor = solve_prazo_anos(investivel=investivel, if_meta=meta, r=r, aporte_mensal=aporte)

    assert do_cenario == do_projetor


def test_cenario_de_estresse_com_retorno_zero_projeta_em_vez_de_calar() -> None:
    """O ramo novo tem de aparecer no resumo do Apêndice C, não só na função."""
    cfg = CenariosConjugeConfig(
        titular_dob=_DOB,
        retorno_real_anual_pct=0.0,
        aporte_base=100_000.0,
        fator_reduzido=0.5,
        reference_date=_REF,
    )

    resultado = CenariosConjugeAnalyzer(cfg).analyze(
        patrimonio={"investivel_efetivo": 40_000_000.0},
        goals={"if_meta": 100_000_000.0},
        fluxo={},
    )

    cenario = resultado.cenarios[0]
    # (100M − 40M) / 50k = 1200 meses = 100 anos.
    assert cenario.prazo_if_anos == pytest.approx(100.0)
    assert "não projetável" not in cenario.resumo

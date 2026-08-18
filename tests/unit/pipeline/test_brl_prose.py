"""A40.l51 C2 — BRL em prosa usa milhar pt-BR."""

from __future__ import annotations

from pipeline.domain.services.brl_prose import fmt_brl_prosa


def test_milhar_ptbr_sem_virgula_americana():
    assert fmt_brl_prosa(2000) == "R$ 2.000"
    assert fmt_brl_prosa(36000) == "R$ 36.000"


def test_centavos_ptbr():
    assert fmt_brl_prosa(250000, decimals=2) == "R$ 250.000,00"

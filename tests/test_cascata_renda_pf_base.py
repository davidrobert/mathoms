"""Base de renda PF da cascata fiscal — pró-labore não entra duas vezes (A40.l36)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.domain.models.transaction import Money  # noqa: E402
from pipeline.domain.services.tributario.cascata_calculator import (  # noqa: E402
    CascataInput,
    compute,
)

# ---------------------------------------------------------------------------
# A40.l36 — pró-labore entra DUAS vezes na base de renda PF da cascata.
#
# Cadeia medida em 2026-08-16:
#   `_compute_layers` faz renda_pf = cargas.bruto_anual + outras_rendas  (:369)
#   `_assemble_input` preenche outras_rendas com irpf_total              (:264)
#   `extract_renda_tributavel_pf` soma rendimentos_pj[] + rendimentos_pf[]
#
# Pró-labore É declarado no IRPF como `rendimentos_pj` — a própria empresa do
# titular é fonte pagadora PJ. Logo, sempre que o contribuinte declara a própria
# PJ (que é o caso normal, não a exceção), o pró-labore está nos dois termos.
#
# A base de renda PF governa o limite PGBL publicado (ADR-375 fez a S8 dona
# única dele), então inflá-la publica um teto de dedução maior que o real.
# ---------------------------------------------------------------------------


def _input_pro_labore_tambem_no_irpf() -> CascataInput:
    """Titular com pró-labore de R$ 12k/mês, declarado no IRPF pela própria PJ."""
    return CascataInput(
        regime="simples",
        anexo_simples="III",
        iss_aliquota_pct=None,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("12000"),
        lucros_distribuidos_mensal=Money.brl("20000"),
        folha_pj_mensal=Money.brl("6000"),
        # O que `extract_renda_tributavel_pf` devolveria: os R$ 144k de
        # pró-labore que a PJ do titular informou, mais R$ 30k de um aluguel.
        renda_tributavel_pf_irpf_anual=Money.brl("174000"),
    )


def test_pro_labore_nao_pode_entrar_duas_vezes_na_renda_pf():
    """Base correta = 144k (pró-labore) + 30k (aluguel) = 174k, não 318k."""
    out = compute(_input_pro_labore_tambem_no_irpf())
    assert out.renda_pf_tributavel_total == Money.brl("174000"), (
        "pró-labore contado duas vezes: uma via `cargas.bruto_anual`, outra "
        "dentro do `irpf_total` que já o inclui como rendimento de PJ"
    )


def test_o_limite_pgbl_publicado_herda_a_inflacao():
    """Por que isto importa: a base governa o teto de dedução que o produto publica."""
    out = compute(_input_pro_labore_tambem_no_irpf())
    assert out.pgbl_limite_anual == Money.brl("20880"), "12% de 174k"


# ---------------------------------------------------------------------------
# Guardas contra o "fix óbvio" que o co-design recusou (A40.l36).
#
# `rendimentos_pj` é heterogêneo: cabem ali salário CLT de OUTRO empregador (o
# ICP é PJ/CLT alta renda), aluguel pago por inquilino PJ com IR retido,
# aposentadoria, RPA, pró-labore de segunda empresa e lucro excedente
# tributável. Qualquer regra que subtraia "a parte da própria PJ" apaga renda
# legítima — e a ficha da própria PJ nem é só pró-labore.
# ---------------------------------------------------------------------------


def test_duas_fontes_pj_somam_nada_e_subtraido():
    """Própria PJ (R$ 144k) + segundo empregador (R$ 90k) → base 234k."""
    inp = CascataInput(
        regime="simples",
        anexo_simples="III",
        iss_aliquota_pct=None,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("12000"),
        lucros_distribuidos_mensal=Money.brl("20000"),
        folha_pj_mensal=Money.brl("6000"),
        renda_tributavel_pf_irpf_anual=Money.brl("234000"),
    )
    assert compute(inp).renda_pf_tributavel_total == Money.brl("234000")


def test_aluguel_em_ficha_de_pj_nao_muda_a_base():
    """Inquilino PJ declara aluguel em `rendimentos_pj` — nenhuma regra por ficha."""
    inp = CascataInput(
        regime="simples",
        anexo_simples="III",
        iss_aliquota_pct=None,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("12000"),
        lucros_distribuidos_mensal=Money.brl("20000"),
        folha_pj_mensal=Money.brl("6000"),
        renda_tributavel_pf_irpf_anual=Money.brl("174000"),
    )
    assert compute(inp).renda_pf_tributavel_total == Money.brl("174000")


def test_sem_irpf_a_base_nao_existe_e_o_fluxo_nao_a_inventa():
    """Ausência de IRPF com pró-labore no fluxo: base ausente, não 144k."""
    inp = CascataInput(
        regime="simples",
        anexo_simples="III",
        iss_aliquota_pct=None,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("12000"),
        lucros_distribuidos_mensal=Money.brl("20000"),
        folha_pj_mensal=Money.brl("6000"),
        renda_tributavel_pf_irpf_anual=Money.zero("BRL"),
    )
    out = compute(inp)
    assert out.renda_pf_tributavel_total == Money.zero("BRL")
    assert out.pgbl_aplicavel is False
    assert out.pgbl_motivo_inaplicavel == "renda_tributavel_pf_zerada"

"""A17 L1 P4 (ADR-238 D5) — FiscalSource polimórfico + política de precedência D4."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.fiscal_source import (
    FiscalSource,
    InformePrevidenciaSummary,
)


def _make_informe_pgbl(
    *,
    ano: int = 2024,
    cnpj: str = "16404287000167",
    contribuicoes: str = "12000.00",
    saldo: str = "85420.00",
) -> dict:
    """Cria payload InformeRendimentosBase válido para previdência PGBL."""
    return {
        "ano_base": ano,
        "tipo_informe": "previdencia_privada",
        "fonte_pagadora_cnpj": cnpj,
        "fonte_pagadora_nome": "BrasilPrev",
        "confidence": 0.95,
        "source_priority": 1,
        "prompt_version": "informe-prev-v1.0.0",
        "needs_review": False,
        "previdencia": {
            "plano_tipo": "pgbl",
            "regime_tributacao": "regressivo",
            "data_adesao": "2018-06",
            "contribuicoes_anuais": contribuicoes,
            "saldo_31_12": saldo,
        },
    }


def _make_informe_vgbl() -> dict:
    return {
        "ano_base": 2024,
        "tipo_informe": "previdencia_privada",
        "fonte_pagadora_cnpj": "47960950000121",
        "fonte_pagadora_nome": "Icatu Seguros",
        "confidence": 0.92,
        "source_priority": 1,
        "prompt_version": "informe-prev-v1.0.0",
        "needs_review": False,
        "previdencia": {
            "plano_tipo": "vgbl",
            "regime_tributacao": "progressivo",
            "contribuicoes_anuais": "5000.00",
            "saldo_31_12": "32000.00",
        },
    }


# ─────────────────────── Gate P4 (a): só informe → PGBL > 0 ──────────────────


def test_fiscal_source_so_informe_pgbl_tem_dados():
    """Workspace SEM E1.6 + com informe PGBL → FiscalSource oferece dado de capacidade."""
    fs = FiscalSource.from_informes([_make_informe_pgbl()])
    assert fs.has_pgbl_data() is True
    assert fs.pgbl_contribuicoes_total() == Decimal("12000.00")


def test_fiscal_source_vazia_sem_dados():
    """Workspace SEM E1.6 e SEM informe → has_pgbl_data False."""
    fs = FiscalSource()
    assert fs.has_pgbl_data() is False
    assert fs.pgbl_contribuicoes_total() == Decimal("0")


# ─────────────────────── Gate P4 (c): VGBL nunca conta PGBL ───────────────────


def test_vgbl_nao_conta_como_capacidade_pgbl():
    """ADR-238 D8 + §Não-objetivos: VGBL sempre filtrado."""
    fs = FiscalSource.from_informes([_make_informe_vgbl()])
    assert fs.has_pgbl_data() is False
    assert fs.pgbl_contribuicoes_total() == Decimal("0")


def test_pgbl_e_vgbl_coexistem_so_pgbl_soma():
    """Workspace com PGBL + VGBL: total considera apenas PGBL."""
    fs = FiscalSource.from_informes([_make_informe_pgbl(), _make_informe_vgbl()])
    assert fs.has_pgbl_data() is True
    assert fs.pgbl_contribuicoes_total() == Decimal("12000.00")  # só PGBL


# ─────────────────────── Sumários ─────────────────────────────────────────────


def test_previdencia_summaries_lista_todos_planos():
    """Lista ambos PGBL e VGBL — consumer (UI) filtra por plano_tipo."""
    fs = FiscalSource.from_informes([_make_informe_pgbl(), _make_informe_vgbl()])
    summaries = fs.previdencia_summaries()
    assert len(summaries) == 2
    planos = {s.plano_tipo for s in summaries}
    assert planos == {"pgbl", "vgbl"}
    pgbl = next(s for s in summaries if s.plano_tipo == "pgbl")
    assert pgbl.contribuicoes_anuais == Decimal("12000.00")
    assert pgbl.saldo_31_12 == Decimal("85420.00")
    assert isinstance(pgbl, InformePrevidenciaSummary)


# ─────────────────────── Política D4: declaração vence ────────────────────────


class _FakePagamentoPGBL:
    def __init__(self, valor: Decimal, cnpj: str) -> None:
        self.codigo = "36"  # CodigoPagamentoDedutivel.pgbl
        self.valor_pago = valor
        self.cnpj_beneficiario = cnpj


class _FakeContribuinte:
    def __init__(self, ano: int) -> None:
        self.ano_base = ano


class _FakeIRPF:
    """Stub mínimo de IRPFFullOutput — só pagamentos_efetuados + contribuinte."""

    def __init__(self, ano: int, pagamentos: list) -> None:
        self.contribuinte = _FakeContribuinte(ano)
        self.pagamentos_efetuados = pagamentos


def test_declaracao_vence_quando_cobre_mesmo_cnpj_ano():
    """ADR-238 D4: dedupe por (ano, CNPJ) — declaração vence, informe não soma."""
    cnpj = "16404287000167"
    irpf = _FakeIRPF(2024, [_FakePagamentoPGBL(Decimal("15000.00"), cnpj)])
    informe = _make_informe_pgbl(ano=2024, cnpj=cnpj, contribuicoes="12000.00")
    fs = FiscalSource.from_both(irpf, [informe])
    # Total = declaração apenas (informe é descartado por overlap).
    assert fs.pgbl_contribuicoes_total() == Decimal("15000.00")


def test_informe_preenche_gaps_de_cnpj_nao_coberto_pela_declaracao():
    """ADR-238 D4: informe complementa quando declaração não tem aquele CNPJ."""
    irpf = _FakeIRPF(2024, [_FakePagamentoPGBL(Decimal("15000.00"), "11111111000111")])
    # Informe é de outro CNPJ — soma.
    informe_outro = _make_informe_pgbl(ano=2024, cnpj="22222222000122", contribuicoes="8000.00")
    fs = FiscalSource.from_both(irpf, [informe_outro])
    assert fs.pgbl_contribuicoes_total() == Decimal("23000.00")  # 15000 + 8000


# ─────────────────────── Gate P4 (b): divergência → warning ───────────────────


def test_divergencia_pgbl_gera_warning_estruturado():
    """ADR-238 D4: divergência entre informe e IRPF mesmo (ano, CNPJ) emite warning efêmero."""
    cnpj = "16404287000167"
    irpf = _FakeIRPF(2024, [_FakePagamentoPGBL(Decimal("15000.00"), cnpj)])
    informe = _make_informe_pgbl(ano=2024, cnpj=cnpj, contribuicoes="12000.00")
    fs = FiscalSource.from_both(irpf, [informe])
    divs = fs.divergencias_pgbl()
    assert len(divs) == 1
    d = divs[0]
    assert d.ano_base == 2024
    assert d.fonte_pagadora_cnpj == cnpj
    assert d.irpf_valor == Decimal("15000.00")
    assert d.informe_valor == Decimal("12000.00")
    assert d.campo == "pgbl_contribuicoes"


def test_divergencia_ignora_diferenca_centavos():
    """Ruído de arredondamento (< R$ 1,00) não gera warning."""
    cnpj = "16404287000167"
    irpf = _FakeIRPF(2024, [_FakePagamentoPGBL(Decimal("12000.50"), cnpj)])
    informe = _make_informe_pgbl(ano=2024, cnpj=cnpj, contribuicoes="12000.00")
    fs = FiscalSource.from_both(irpf, [informe])
    assert fs.divergencias_pgbl() == []


def test_divergencia_sem_overlap_nao_gera_warning():
    """Informe e IRPF cobrem CNPJs distintos → não há divergência (cada um é fonte primária)."""
    irpf = _FakeIRPF(2024, [_FakePagamentoPGBL(Decimal("15000.00"), "11111111000111")])
    informe = _make_informe_pgbl(ano=2024, cnpj="22222222000122")
    fs = FiscalSource.from_both(irpf, [informe])
    assert fs.divergencias_pgbl() == []


# ─────────────────────── FiscalAnalyzer alias (compat) ────────────────────────


def test_fiscal_analyzer_eh_alias_de_irpf_analyzer():
    """ADR-238 D5: rename IRPFAnalyzer → FiscalAnalyzer com alias retrocompat 1 sprint."""
    from pipeline.domain.services.irpf_analyzer import FiscalAnalyzer, IRPFAnalyzer

    assert FiscalAnalyzer is IRPFAnalyzer

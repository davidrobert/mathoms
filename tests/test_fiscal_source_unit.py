"""A17 L1 P4 (ADR-238 D5) — FiscalSource polimórfico + política de precedência D4."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.fiscal_source import (
    FiscalSource,
    InformeFinanceiroPJSummary,
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


def _pj_payload(ano, cnpj_pagador, regime, receita, irrf, csll):
    return {
        "regime_tributario": regime,
        "cnpj_pagador": cnpj_pagador,
        "nome_pagador": "Stone Pagamentos S.A.",
        "cnpj_beneficiario": "12345678000190",
        "periodo_inicio": f"{ano}-01",
        "periodo_fim": f"{ano}-12",
        "receita_bruta_anual": receita,
        "irrf_anual": irrf,
        "csll_anual": csll,
    }


def _make_informe_financeiro_pj(
    *,
    ano: int = 2024,
    cnpj_pagador: str = "16501555000157",
    regime: str = "lucro_presumido",
    receita: str = "240000.00",
    irrf: str = "3600.00",
    csll: str = "2400.00",
) -> dict:
    return {
        "ano_base": ano,
        "tipo_informe": "financeiro_pj",
        "fonte_pagadora_cnpj": cnpj_pagador,
        "fonte_pagadora_nome": "Stone Pagamentos S.A.",
        "confidence": 0.95,
        "source_priority": 1,
        "prompt_version": "informe-pj-v1.0.0",
        "financeiro_pj": _pj_payload(ano, cnpj_pagador, regime, receita, irrf, csll),
    }


def test_financeiro_pj_summaries_extrai_payload_completo():
    """A17 L2 P3: financeiro_pj_summaries retorna InformeFinanceiroPJSummary dataclass."""
    fs = FiscalSource.from_informes([_make_informe_financeiro_pj()])
    summaries = fs.financeiro_pj_summaries()
    assert len(summaries) == 1
    s = summaries[0]
    assert isinstance(s, InformeFinanceiroPJSummary)
    assert s.regime_tributario == "lucro_presumido"
    assert s.cnpj_pagador == "16501555000157"
    assert s.cnpj_beneficiario == "12345678000190"
    assert s.ano_base == 2024
    assert s.receita_bruta_anual == Decimal("240000.00")
    # IRRF 3600 + CSLL 2400 + (PIS/COFINS/INSS/ISS default 0) = 6000
    assert s.retencoes_totais_anuais == Decimal("6000.00")


def test_financeiro_pj_summaries_filtra_outros_tipos():
    """Mistura tipos: financeiro_pj_summaries retorna apenas financeiro_pj."""
    fs = FiscalSource.from_informes(
        [_make_informe_pgbl(), _make_informe_financeiro_pj(), _make_informe_vgbl()]
    )
    summaries = fs.financeiro_pj_summaries()
    assert len(summaries) == 1
    assert summaries[0].regime_tributario == "lucro_presumido"


def test_financeiro_pj_summaries_vazio_se_so_previdencia():
    fs = FiscalSource.from_informes([_make_informe_pgbl()])
    assert fs.financeiro_pj_summaries() == []


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


# ─────────────────────── Proventos summaries (A17 L4) ────────────────────────


def _make_informe_proventos(*, ano: int = 2024, proventos=None, posicao=None) -> dict:
    return {
        "tipo_informe": "proventos_acoes",
        "ano_base": ano,
        "proventos": {
            "cnpj_emissor": "02332886000104",
            "nome_emissor": "XP Investimentos CCTVM S.A.",
            "proventos": proventos or [],
            "posicao_31_12": posicao or [],
        },
    }


def _evento(ticker: str, tipo: str, valor: str, ir: str = "0") -> dict:
    return {
        "ticker": ticker,
        "cnpj_pagador": "02332886000104",
        "tipo": tipo,
        "valor_brl": valor,
        "data_pagamento": "2024-06-15",
        "ir_retido_brl": ir,
    }


def test_proventos_agrega_por_ticker_e_ano():
    informe = _make_informe_proventos(
        proventos=[
            _evento("WEGE3", "dividendo", "100.00"),
            _evento("WEGE3", "jcp", "50.00", ir="7.50"),
            _evento("MXRF11", "rend_fii", "30.00"),
        ]
    )
    summaries = FiscalSource.from_informes([informe]).proventos_summaries()
    by_ticker = {s.ticker: s for s in summaries}
    assert by_ticker["WEGE3"].total_proventos_brl == Decimal("150.00")
    assert by_ticker["WEGE3"].ir_retido_brl == Decimal("7.50")
    assert by_ticker["MXRF11"].total_proventos_brl == Decimal("30.00")
    assert by_ticker["WEGE3"].ano_base == 2024


def test_proventos_bonificacao_nao_vira_renda():
    """Bonificação é ajuste de custo médio, não fluxo (critério de aceite A17.L4)."""
    informe = _make_informe_proventos(
        proventos=[
            _evento("ITSA4", "dividendo", "80.00"),
            _evento("ITSA4", "bonificacao", "500.00"),
        ]
    )
    (s,) = FiscalSource.from_informes([informe]).proventos_summaries()
    assert s.total_proventos_brl == Decimal("80.00")


def test_proventos_yield_on_cost_com_posicao_31_12():
    """quantidade × custo_medio → yield-on-cost 2 casas (Perini viver de renda)."""
    informe = _make_informe_proventos(
        proventos=[_evento("ITSA4", "dividendo", "60.00")],
        posicao=[{"ticker": "ITSA4", "quantidade": "100", "custo_medio_brl": "10.00"}],
    )
    (s,) = FiscalSource.from_informes([informe]).proventos_summaries()
    assert s.custo_total_brl == Decimal("1000.00")
    assert s.yield_on_cost_pct == Decimal("6.00")


def test_proventos_sem_custo_medio_yoc_none():
    informe = _make_informe_proventos(
        proventos=[_evento("PETR4", "dividendo", "10.00")],
        posicao=[{"ticker": "PETR4", "quantidade": "50", "custo_medio_brl": None}],
    )
    (s,) = FiscalSource.from_informes([informe]).proventos_summaries()
    assert s.custo_total_brl is None
    assert s.yield_on_cost_pct is None


def test_proventos_ticker_so_custodia_aparece_sem_renda():
    informe = _make_informe_proventos(
        posicao=[{"ticker": "BOVA11", "quantidade": "10", "custo_medio_brl": "120.00"}]
    )
    (s,) = FiscalSource.from_informes([informe]).proventos_summaries()
    assert s.ticker == "BOVA11"
    assert s.total_proventos_brl == Decimal("0")
    assert s.yield_on_cost_pct == Decimal("0.00")


def test_proventos_ignora_outros_tipos_de_informe():
    informe = {"tipo_informe": "previdencia_privada", "ano_base": 2024, "previdencia": {}}
    assert FiscalSource.from_informes([informe]).proventos_summaries() == []

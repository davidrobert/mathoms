"""Plumbing E5 (A17 L2 P3): tributario_input_builder consome informes financeiro_pj via InformeQuery."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from pipeline.domain.models.transaction import Money
from pipeline.domain.services.tributario.cascata_calculator import (
    CascataInput,
    FinanceiroPJSnapshot,
    compute,
)


def _pj_payload(ano, cnpj_pagador, cnpj_beneficiario, regime, receita, irrf, csll, pis, cofins):
    return {
        "regime_tributario": regime,
        "cnpj_pagador": cnpj_pagador,
        "nome_pagador": "Stone Pagamentos S.A.",
        "cnpj_beneficiario": cnpj_beneficiario,
        "periodo_inicio": f"{ano}-01",
        "periodo_fim": f"{ano}-12",
        "receita_bruta_anual": receita,
        "irrf_anual": irrf,
        "csll_anual": csll,
        "pis_anual": pis,
        "cofins_anual": cofins,
    }


def _informe_envelope(ano, cnpj_pagador, payload):
    return {
        "ano_base": ano,
        "tipo_informe": "financeiro_pj",
        "fonte_pagadora_cnpj": cnpj_pagador,
        "fonte_pagadora_nome": "Stone Pagamentos S.A.",
        "confidence": 0.95,
        "source_priority": 1,
        "prompt_version": "informe-pj-v1.0.0",
        "financeiro_pj": payload,
    }


def _make_informe_pj(
    *,
    ano: int = 2024,
    cnpj_pagador: str = "16501555000157",
    cnpj_beneficiario: str = "12345678000190",
    regime: str = "lucro_presumido",
    receita: str = "240000.00",
    irrf: str = "3600.00",
    csll: str = "2400.00",
    pis: str = "1560.00",
    cofins: str = "7200.00",
) -> dict:
    payload = _pj_payload(
        ano, cnpj_pagador, cnpj_beneficiario, regime, receita, irrf, csll, pis, cofins
    )
    return _informe_envelope(ano, cnpj_pagador, payload)


def _run_with_informes(informes: list[dict]):
    from backend.app.services.tributario_input_builder import _load_financeiro_pj_snapshot

    fake_q = MagicMock()
    fake_q.list_for_workspace.return_value = informes
    with patch("backend.app.services.tributario_input_builder.InformeQuery", return_value=fake_q):
        return _load_financeiro_pj_snapshot("ws-1", db=MagicMock())


# ─────────────────────── _load_financeiro_pj_snapshot ──────────────────────


def test_workspace_sem_informe_pj_retorna_none() -> None:
    """Workspace sem informes financeiro_pj → snapshot None (default no Input)."""
    snap = _run_with_informes([])
    assert snap is None


def test_workspace_com_um_informe_pj_agrega_corretamente() -> None:
    """1 informe LP com retenções típicas → soma correta + regime LP."""
    snap = _run_with_informes([_make_informe_pj()])
    assert snap is not None
    assert snap.informes_count == 1
    assert snap.receita_bruta_total_anual == Money.brl(Decimal("240000.00"))
    # IRRF 3600 + CSLL 2400 + PIS 1560 + COFINS 7200 + INSS 0 + ISS 0 = 14760
    assert snap.retencoes_totais_anuais == Money.brl(Decimal("14760.00"))
    assert snap.regime_declarado == "lucro_presumido"
    assert snap.ano_base_coberto == 2024


def test_multiplos_informes_soma_receita_e_retencoes() -> None:
    """2 informes do mesmo workspace → soma agregada."""
    snap = _run_with_informes(
        [
            _make_informe_pj(receita="100000.00", irrf="1500.00"),
            _make_informe_pj(cnpj_pagador="60746948000112", receita="50000.00", irrf="750.00"),
        ]
    )
    assert snap is not None
    assert snap.informes_count == 2
    assert snap.receita_bruta_total_anual == Money.brl(Decimal("150000.00"))
    # 2250 IRRF total + (2x outras retenções) = 2250 + 2*(2400+1560+7200) = 2250 + 22320 = 24570
    assert snap.retencoes_totais_anuais == Money.brl(Decimal("24570.00"))


def test_snapshot_regime_dominante_sn_vence_lp_em_empate() -> None:
    """3 informes (2 SN + 1 LP) → regime_declarado=SN (mais frequente)."""
    snap = _run_with_informes(
        [
            _make_informe_pj(regime="simples_nacional", csll="0", pis="0", cofins="0", irrf="0"),
            _make_informe_pj(regime="simples_nacional", csll="0", pis="0", cofins="0", irrf="0"),
            _make_informe_pj(regime="lucro_presumido"),
        ]
    )
    assert snap is not None
    assert snap.regime_declarado == "simples_nacional"


def test_snapshot_ano_mais_recente() -> None:
    """Múltiplos anos → ano_base_coberto = max(anos)."""
    snap = _run_with_informes(
        [
            _make_informe_pj(ano=2022),
            _make_informe_pj(ano=2024),
            _make_informe_pj(ano=2023),
        ]
    )
    assert snap is not None
    assert snap.ano_base_coberto == 2024


# ─────────────────────── Passthrough Input → Output ────────────────────────


def test_cascata_output_passthrough_financeiro_pj_snapshot() -> None:
    """CascataOutput preserva o snapshot do Input (passthrough — não recalcula)."""
    snap = FinanceiroPJSnapshot(
        informes_count=2,
        receita_bruta_total_anual=Money.brl(Decimal("150000")),
        retencoes_totais_anuais=Money.brl(Decimal("12000")),
        regime_declarado="lucro_presumido",
        ano_base_coberto=2024,
    )
    inp = CascataInput(
        regime="lucro_presumido",
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl(Decimal("120000")),
        pro_labore_mensal=Money.brl(Decimal("5000")),
        financeiro_pj_snapshot=snap,
    )
    out = compute(inp)
    assert out.financeiro_pj_snapshot is snap


def test_cascata_output_sem_snapshot_quando_input_none() -> None:
    """Workspace sem informes PJ → output.financeiro_pj_snapshot is None."""
    inp = CascataInput(
        regime="lucro_presumido",
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl(Decimal("120000")),
        pro_labore_mensal=Money.brl(Decimal("5000")),
    )
    out = compute(inp)
    assert out.financeiro_pj_snapshot is None


def test_cascata_output_fallback_preserva_snapshot_pj() -> None:
    """Mesmo no fallback (regime ausente), snapshot é preservado para UI consumir."""
    snap = FinanceiroPJSnapshot(
        informes_count=1,
        receita_bruta_total_anual=Money.brl(Decimal("100000")),
        regime_declarado="simples_nacional",
        ano_base_coberto=2024,
    )
    inp = CascataInput(financeiro_pj_snapshot=snap)
    out = compute(inp)
    assert out.regime_nao_suportado is True
    assert out.financeiro_pj_snapshot is snap


def _pj_snap_basico() -> FinanceiroPJSnapshot:
    return FinanceiroPJSnapshot(
        informes_count=1,
        receita_bruta_total_anual=Money.brl(Decimal("100000")),
        regime_declarado="lucro_presumido",
        ano_base_coberto=2024,
    )


def _prev_snap_basico():
    from pipeline.domain.services.tributario.cascata_calculator import PrevidenciaSnapshot

    return PrevidenciaSnapshot(
        planos_pgbl_count=1,
        aporte_pgbl_realizado_anual=Money.brl(Decimal("12000")),
        saldo_total_31_12=Money.brl(Decimal("85420")),
    )


def test_snapshot_e_previdencia_coexistem_em_input_e_output() -> None:
    """Workspace com PJ + previdência → ambos snapshots independentes."""
    pj_snap, prev_snap = _pj_snap_basico(), _prev_snap_basico()
    inp = CascataInput(
        regime="lucro_presumido",
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl(Decimal("120000")),
        pro_labore_mensal=Money.brl(Decimal("5000")),
        previdencia_snapshot=prev_snap,
        financeiro_pj_snapshot=pj_snap,
    )
    out = compute(inp)
    assert out.financeiro_pj_snapshot is pj_snap
    assert out.previdencia_snapshot is prev_snap

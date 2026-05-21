"""Plumbing E5 (débito A17 L1): tributario_input_builder consome informes previdência via InformeQuery."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from pipeline.domain.models.transaction import Money
from pipeline.domain.services.tributario.cascata_calculator import (
    CascataInput,
    PrevidenciaSnapshot,
    compute,
)


def _make_informe_pgbl(
    *,
    ano: int = 2024,
    cnpj: str = "16404287000167",
    contrib: str = "12000.00",
    saldo: str = "85420.00",
) -> dict:
    base = _informe_base(ano, cnpj, "BrasilPrev")
    base["previdencia"] = {
        "plano_tipo": "pgbl",
        "regime_tributacao": "regressivo",
        "data_adesao": "2018-06",
        "contribuicoes_anuais": contrib,
        "saldo_31_12": saldo,
    }
    return base


def _informe_base(ano: int, cnpj: str, nome: str) -> dict:
    return {
        "ano_base": ano,
        "tipo_informe": "previdencia_privada",
        "fonte_pagadora_cnpj": cnpj,
        "fonte_pagadora_nome": nome,
        "confidence": 0.95,
        "source_priority": 1,
        "prompt_version": "informe-prev-v1.0.0",
    }


def _make_informe_vgbl() -> dict:
    base = _informe_base(2024, "47960950000121", "Icatu")
    base["previdencia"] = {
        "plano_tipo": "vgbl",
        "regime_tributacao": "progressivo",
        "contribuicoes_anuais": "5000.00",
        "saldo_31_12": "32000.00",
    }
    return base


# ─────────────────────── _load_previdencia_snapshot ────────────────────────


def test_workspace_sem_informe_retorna_none() -> None:
    """Workspace sem extract_informes_anuais → snapshot None (default no Input)."""
    from backend.app.services.tributario_input_builder import _load_previdencia_snapshot

    fake_q = MagicMock()
    fake_q.list_previdencia.return_value = []
    with patch(
        "backend.app.services.tributario_input_builder.InformeQuery",
        return_value=fake_q,
    ):
        snap = _load_previdencia_snapshot("ws-1", db=MagicMock())
    assert snap is None


def test_workspace_com_pgbl_so_agrega_pgbl_nao_vgbl() -> None:
    """ADR-238 D8: VGBL filtrado out de aporte; conta no saldo + planos_vgbl_count."""
    snap = _run_with_informes(
        [_make_informe_pgbl(contrib="12000.00", saldo="85420.00"), _make_informe_vgbl()]
    )
    assert snap is not None
    assert snap.planos_pgbl_count == 1
    assert snap.planos_vgbl_count == 1
    # Aporte conta APENAS PGBL.
    assert snap.aporte_pgbl_realizado_anual == Money.brl(Decimal("12000.00"))
    # Saldo total agrega ambos (snapshot patrimonial — visão global).
    assert snap.saldo_total_31_12 == Money.brl(Decimal("117420.00"))


def _run_with_informes(informes: list[dict]):
    from backend.app.services.tributario_input_builder import _load_previdencia_snapshot

    fake_q = MagicMock()
    fake_q.list_previdencia.return_value = informes
    with patch("backend.app.services.tributario_input_builder.InformeQuery", return_value=fake_q):
        return _load_previdencia_snapshot("ws-1", db=MagicMock())


def test_multiplos_pgbl_soma_aportes() -> None:
    """2 planos PGBL → aporte é soma; planos_pgbl_count é 2."""
    from backend.app.services.tributario_input_builder import _load_previdencia_snapshot

    fake_q = MagicMock()
    fake_q.list_previdencia.return_value = [
        _make_informe_pgbl(cnpj="16404287000167", contrib="12000.00", saldo="85420.00"),
        _make_informe_pgbl(cnpj="33010851000174", contrib="8000.00", saldo="50000.00"),
    ]
    with patch(
        "backend.app.services.tributario_input_builder.InformeQuery",
        return_value=fake_q,
    ):
        snap = _load_previdencia_snapshot("ws-1", db=MagicMock())
    assert snap is not None
    assert snap.planos_pgbl_count == 2
    assert snap.aporte_pgbl_realizado_anual == Money.brl(Decimal("20000.00"))
    assert snap.saldo_total_31_12 == Money.brl(Decimal("135420.00"))


# ─────────────────────── Passthrough Input → Output ────────────────────────


def test_cascata_output_passthrough_previdencia_snapshot() -> None:
    """CascataOutput preserva o snapshot do Input (passthrough — não recalcula)."""
    snap = PrevidenciaSnapshot(
        planos_pgbl_count=1,
        planos_vgbl_count=0,
        aporte_pgbl_realizado_anual=Money.brl(Decimal("12000")),
        saldo_total_31_12=Money.brl(Decimal("85420")),
    )
    inp = CascataInput(
        regime="lucro_presumido",
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl(Decimal("120000")),
        pro_labore_mensal=Money.brl(Decimal("5000")),
        previdencia_snapshot=snap,
    )
    out = compute(inp)
    assert out.previdencia_snapshot is snap


def test_cascata_output_sem_snapshot_quando_input_none() -> None:
    """Workspace sem informes → output.previdencia_snapshot is None."""
    inp = CascataInput(
        regime="lucro_presumido",
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl(Decimal("120000")),
        pro_labore_mensal=Money.brl(Decimal("5000")),
    )
    out = compute(inp)
    assert out.previdencia_snapshot is None


def test_cascata_output_fallback_preserva_snapshot() -> None:
    """Mesmo no fallback (regime ausente), snapshot é preservado para UI consumir."""
    snap = PrevidenciaSnapshot(
        planos_pgbl_count=1,
        aporte_pgbl_realizado_anual=Money.brl(Decimal("12000")),
        saldo_total_31_12=Money.brl(Decimal("85420")),
    )
    inp = CascataInput(previdencia_snapshot=snap)  # sem regime → fallback
    out = compute(inp)
    assert out.regime_nao_suportado is True
    assert out.previdencia_snapshot is snap

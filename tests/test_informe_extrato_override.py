"""Unit tests A33.l2 — regra "informe 31/12 vence extrato D+1" (ADR-238 D5)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.informe_extrato_override import (
    ExtratoPosicao,
    InformeExtratoDivergencia,
    apply_informe_override,
)
from pipeline.domain.services.patrimonio_types import CaixaDetalhe


def _detalhe(**overrides) -> CaixaDetalhe:
    base = dict(
        conta="wise (contacorrente)",
        moeda="USD",
        saldo_original=5200.00,
        valor_brl=32200.00,
        tipo="moeda_estrangeira",
    )
    base.update(overrides)
    return CaixaDetalhe(**base)


def _posicao(period_end: str = "2025-01-31", banco: str = "wise", **overrides) -> ExtratoPosicao:
    return ExtratoPosicao(detalhe=_detalhe(**overrides), banco=banco, period_end=period_end)


def _entry(**overrides) -> dict:
    base = {
        "ano_base": 2024,
        "tipo": "conta_exterior",
        "descricao": "Wise Multi-Currency Account — USD",
        "moeda": "USD",
        "saldo_original": "5210.55",
        "saldo_brl": "32262.16",
        "ptax_status": "applied",
        "fonte": "informe_31_12",
    }
    base.update(overrides)
    return base


def test_informe_vence_extrato_na_janela_d1():
    entry = _entry()
    result = apply_informe_override([_posicao()], [entry])
    detalhe = result.detalhes[0]
    assert detalhe.fonte == "informe_31_12"
    assert detalhe.valor_brl == 32262.16
    assert entry["informe_venceu_extrato"] is True
    # Ajuste no total = informe − extrato (Decimal, ADR-090).
    assert result.ajuste_total_brl == Decimal("62.16")


def test_divergencia_acima_da_tolerancia_gera_warning_tipado():
    """diff 62,16 > max(1,00; 0,01% × 32262,16 = 3,23) → warning com .format()."""
    result = apply_informe_override([_posicao()], [_entry()])
    assert len(result.divergencias) == 1
    d = result.divergencias[0]
    assert isinstance(d, InformeExtratoDivergencia)
    assert d.diff_brl == Decimal("62.16")
    assert "adotado o informe como fonte fiscal" in d.format()


def test_divergencia_dentro_da_tolerancia_silenciosa():
    """diff R$ 0,50 ≤ max(1,00; 3,23) → usa informe sem warning."""
    entry = _entry(saldo_brl="32200.50")
    result = apply_informe_override([_posicao()], [entry])
    assert result.detalhes[0].valor_brl == 32200.50
    assert result.divergencias == []
    assert entry["divergencia_relevante"] is False


def test_extrato_fora_da_janela_d1_nao_sofre_override():
    """Extrato de junho não é a virada de ano — informe 31/12 não substitui saldo corrente."""
    entry = _entry()
    result = apply_informe_override([_posicao(period_end="2025-06-30")], [entry])
    assert result.detalhes[0].fonte == "extrato"
    assert result.ajuste_total_brl == Decimal("0")
    assert "informe_venceu_extrato" not in entry


def test_janela_dezembro_do_ano_base_tambem_vale():
    result = apply_informe_override([_posicao(period_end="2024-12-31")], [_entry()])
    assert result.detalhes[0].fonte == "informe_31_12"


def test_moeda_diferente_nao_matcheia():
    result = apply_informe_override([_posicao(moeda="EUR")], [_entry()])
    assert result.detalhes[0].fonte == "extrato"


def test_banco_sem_token_na_descricao_nao_matcheia():
    result = apply_informe_override([_posicao(banco="itau")], [_entry()])
    assert result.detalhes[0].fonte == "extrato"


def test_informe_sem_saldo_brl_nao_e_elegivel():
    """PTAX missing (saldo_brl None) → não há valor para vencer o extrato."""
    entry = _entry(saldo_brl=None, ptax_status="missing")
    result = apply_informe_override([_posicao()], [entry])
    assert result.detalhes[0].fonte == "extrato"


def test_tipo_cdb_nao_substitui_conta_corrente():
    """Saldo de CDB no informe não é caixa — nunca sobrepõe conta corrente."""
    entry = _entry(tipo="cdb")
    result = apply_informe_override([_posicao()], [entry])
    assert result.detalhes[0].fonte == "extrato"


def test_um_informe_matcheia_no_maximo_uma_posicao():
    entry = _entry()
    posicoes = [_posicao(), _posicao(period_end="2024-12-31")]
    result = apply_informe_override(posicoes, [entry])
    fontes = [d.fonte for d in result.detalhes]
    assert fontes.count("informe_31_12") == 1


def test_brl_conta_corrente_tambem_sofre_override():
    pos = _posicao(
        banco="bancosintetico",
        moeda="BRL",
        conta="bancosintetico (contacorrente)",
        saldo_original=8250.00,
        valor_brl=8250.00,
        tipo="caixa",
    )
    entry = _entry(
        tipo="conta_corrente",
        descricao="Banco Sintético conta corrente",
        moeda="BRL",
        saldo_original="8300.00",
        saldo_brl="8300.00",
    )
    result = apply_informe_override([pos], [entry])
    assert result.detalhes[0].fonte == "informe_31_12"
    assert result.detalhes[0].valor_brl == 8300.00
    assert result.ajuste_total_brl == Decimal("50.00")


def test_sem_informes_passthrough():
    result = apply_informe_override([_posicao()], [])
    assert result.detalhes[0].fonte == "extrato"
    assert result.ajuste_total_brl == Decimal("0")
    assert result.divergencias == []

"""Unit tests A33.l2 — regra "informe 31/12 vence extrato D+1" (ADR-238 D5)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.conversao_me import FxQuote, convert_me_brl
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
        # ADR-390 §Emenda 2026-08-24 — o carimbo deixou de ser opcional.
        conversao=convert_me_brl(
            "5200.00", "USD", FxQuote(rate=Decimal("6.1923"), fonte="market_rate_corrente")
        ),
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
        "taxa_ptax_aplicada": "6.1917",
        "ptax_data": "2024-12-31",
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
    assert detalhe.conversao is not None
    assert detalhe.conversao.taxa_fonte == "ptax_31_12"
    assert detalhe.conversao.status == "converted"
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


# =============================================================================
# ADR-384 (A40.l40) — cascata de identidade: CNPJ-raiz → token de nome
# =============================================================================


def test_cnpj_raiz_casa_descricao_sem_nome_do_banco():
    """A representação que quebra hoje: 'Conta Corrente - Ag 9652...' não
    contém 'itau', mas o cnpj_emissor resolve para o code do catálogo."""
    entry = _entry(
        tipo="conta_corrente",
        moeda="BRL",
        descricao="Conta Corrente - Ag 9652 Conta 0004397-8",
        cnpj_emissor="60701190000104",
        saldo_brl="0.00",
        saldo_original="0.00",
    )
    pos = _posicao(banco="itau", moeda="BRL", valor_brl=5156.06, saldo_original=5156.06)
    result = apply_informe_override([pos], [entry], cnpj_raiz_to_code={"60701190": ("itau",)})
    assert result.detalhes[0].fonte == "informe_31_12"
    assert entry["informe_venceu_extrato"] is True


def test_cnpj_raiz_de_outro_banco_veta_match_mesmo_com_token_na_descricao():
    """CNPJ conhecido tem precedência TOTAL: se aponta para outra instituição,
    o token de nome não ressuscita o match (cascata, não união)."""
    entry = _entry(
        tipo="conta_corrente",
        moeda="BRL",
        descricao="Conta wise de terceiros",
        cnpj_emissor="60701190000104",
        saldo_brl="10.00",
    )
    pos = _posicao(banco="wise", moeda="BRL", valor_brl=10.0)
    result = apply_informe_override([pos], [entry], cnpj_raiz_to_code={"60701190": ("itau",)})
    assert result.detalhes[0].fonte == "extrato"


def test_sem_cnpj_no_entry_cai_no_token_de_nome():
    entry = _entry(descricao="Wise Multi-Currency Account — USD")
    pos = _posicao(banco="wise")
    result = apply_informe_override([pos], [entry], cnpj_raiz_to_code={"60701190": ("itau",)})
    assert result.detalhes[0].fonte == "informe_31_12"


def test_slug_do_code_normaliza_espaco_e_acento():
    """'btg pactual' (com espaço) e 'Itaú' (acento) resolvem para o code ASCII."""
    entry = _entry(
        tipo="conta_corrente",
        moeda="BRL",
        descricao="Aplicação automática",
        cnpj_emissor="30306294000145",
        saldo_brl="1.00",
    )
    pos = _posicao(banco="btg pactual", moeda="BRL", valor_brl=1.0)
    result = apply_informe_override([pos], [entry], cnpj_raiz_to_code={"30306294": ("btgpactual",)})
    assert result.detalhes[0].fonte == "informe_31_12"

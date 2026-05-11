"""Tests — :mod:`asset_classifier` (ADR-193).

Cobre os 10 buckets canônicos, ordem de avaliação (especialização → fallback),
normalização de separadores (`_`/`-` → espaço — o bug que motivou ADR-193),
ticker FII XXXX11 e o `OutrosExcessivoWarning`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.asset_classifier import (  # noqa: E402
    BUCKETS,
    EVALUATION_ORDER,
    OUTROS_EXCESSIVO_THRESHOLD_PCT,
    OutrosExcessivoWarning,
    classify_asset,
    default_keywords,
)


class TestTaxonomy:
    def test_buckets_has_10_canonical_classes(self):
        assert len(BUCKETS) == 10
        assert "Imóveis Investimento" in BUCKETS
        assert "Outros" in BUCKETS

    def test_evaluation_order_is_8_financial(self):
        assert len(EVALUATION_ORDER) == 8
        assert "Imóveis Investimento" not in EVALUATION_ORDER
        assert "Outros" not in EVALUATION_ORDER

    def test_evaluation_order_starts_with_specializations(self):
        # Cripto e Previdência antes de Renda Fixa e Caixa.
        idx_cripto = EVALUATION_ORDER.index("Cripto")
        idx_prev = EVALUATION_ORDER.index("Previdência")
        idx_rf = EVALUATION_ORDER.index("Renda Fixa")
        idx_caixa = EVALUATION_ORDER.index("Caixa")
        idx_acoes = EVALUATION_ORDER.index("Ações BR")
        assert idx_cripto < idx_rf
        assert idx_prev < idx_rf
        assert idx_rf < idx_caixa
        # Renda Fixa antes de Ações BR: LCI/CDB/RDB vencem participacao_societaria.
        assert idx_rf < idx_acoes


class TestNormalizationBug:
    """O bug raiz do ADR-193: `tipo='renda_fixa'` não casava com `'renda fixa'`."""

    def test_underscore_in_tipo_normalized(self):
        # Esse era o exato bug em produção (tipo IRPF vem com underscore).
        assert classify_asset("renda_fixa", "", "") == "Renda Fixa"

    def test_hyphen_in_tipo_normalized(self):
        assert classify_asset("conta-corrente", "", "") == "Caixa"

    def test_descricao_dominates_when_tipo_is_generic(self):
        # `tipo='investimento'` é o aggregate genérico do E1.5 — o sinal
        # real fica na descricao.
        c = classify_asset("investimento", "ACOES - ITSA4 - QUANTIDADE 693", "Itausa S.A.")
        assert c == "Ações BR"


class TestBucketSpecific:
    def test_cripto_via_descricao(self):
        assert (
            classify_asset(
                "investimento",
                "RICO - HASHDEX 20 NASDAQ CRYPTO INDEX FIC FIM",
                "XP INVESTIMENTOS",
            )
            == "Cripto"
        )

    def test_cripto_btc(self):
        assert classify_asset("", "BTC cold wallet", "") == "Cripto"

    def test_previdencia_pgbl(self):
        assert classify_asset("previdencia", "PGBL Itaú", "Itau") == "Previdência"

    def test_previdencia_vgbl(self):
        assert classify_asset("investimento", "VGBL Brasilprev", "Brasilprev") == "Previdência"

    def test_fii_via_ticker_xxxx11(self):
        # Sinal forte: ticker XXXX11.
        assert classify_asset("fundo_investimento", "HGLG11 quotas", "BTG") == "FIIs"

    def test_fii_via_keyword(self):
        assert classify_asset("fundo_investimento", "Fundo Imobiliário XP Log", "XP") == "FIIs"

    def test_internacional_usd(self):
        assert classify_asset("conta_bancaria", "Conta em USD na Wise", "Wise") == "Internacional"

    def test_internacional_moeda_estrangeira(self):
        assert (
            classify_asset("outros", "DEPOSITO EM MOEDA ESTRANGEIRA - U$ 6524,00", "")
            == "Internacional"
        )

    def test_acoes_br_via_tipo(self):
        assert classify_asset("acao", "ITSA4", "Itausa") == "Ações BR"

    def test_acoes_br_via_participacao_societaria(self):
        assert classify_asset("participacao_societaria", "PETR4 - 300 acoes", "") == "Ações BR"

    def test_renda_fixa_cdb(self):
        assert classify_asset("investimento", "CDB BTG Pactual", "BTG") == "Renda Fixa"

    def test_renda_fixa_lci(self):
        assert (
            classify_asset("participacao_societaria", "LCI OPEA SECURITIZADORA - BTG", "BTG")
            == "Renda Fixa"
        )

    def test_renda_fixa_poupanca(self):
        assert classify_asset("poupanca", "SALDO POUPANCA CAIXA", "Caixa Econômica") == "Renda Fixa"

    def test_renda_fixa_tesouro(self):
        assert classify_asset("renda_fixa", "Tesouro IPCA+ 2030", "Itau") == "Renda Fixa"

    def test_fundos_fic_fim(self):
        # `tipo='fundo_investimento'` + descricao com FIC FIM (mas não FII).
        assert (
            classify_asset("fundo_investimento", "DNA ENERGY FIC FIM CP", "XP INVESTIMENTOS")
            == "Fundos"
        )

    def test_fundos_fia_alaska(self):
        assert (
            classify_asset("fundo_investimento", "ALASKA BLACK FIC FIA", "XP INVESTIMENTOS")
            == "Fundos"
        )

    def test_caixa_conta_corrente(self):
        assert (
            classify_asset("conta_bancaria", "CONTA CORRENTE AG 1218", "Caixa Econômica") == "Caixa"
        )

    def test_caixa_picpay(self):
        assert classify_asset("conta_bancaria", "Saldo Picpay", "Picpay Bank") == "Caixa"

    def test_outros_fallback(self):
        assert classify_asset("outros", "ativo exotico XYZ", "") == "Outros"

    def test_outros_when_empty(self):
        assert classify_asset("", "", "") == "Outros"


class TestSpecializationWins:
    """FII deve ganhar de Fundos; Internacional deve ganhar de Caixa; etc."""

    def test_fii_wins_over_fundos(self):
        # "FIC" também é keyword de Fundos, mas FII é mais específico.
        assert classify_asset("fundo_investimento", "FII XPLG11", "XP") == "FIIs"

    def test_internacional_wins_over_caixa(self):
        # Conta corrente em USD → Internacional, não Caixa.
        assert (
            classify_asset("conta_bancaria", "Conta corrente USD - Wise", "Wise") == "Internacional"
        )

    def test_previdencia_wins_over_renda_fixa(self):
        # PGBL atuarialmente é RF; semanticamente é Previdência.
        assert classify_asset("renda_fixa", "PGBL Bradesco IPCA+", "Bradesco") == "Previdência"

    def test_cripto_wins_over_fundos(self):
        # Hashdex é fundo, mas categoria semântica é Cripto.
        assert (
            classify_asset("fundo_investimento", "HASHDEX 20 NASDAQ CRYPTO FIC FIM", "XP")
            == "Cripto"
        )


class TestCustomKeywords:
    def test_override_uses_only_provided_keywords(self):
        custom = {"Cripto": ("solana",)}
        assert classify_asset("solana wallet", "", "", keywords=custom) == "Cripto"
        # Bitcoin não está no override custom (sem fallback default) → Outros.
        assert classify_asset("bitcoin", "", "", keywords=custom) == "Outros"

    def test_default_keywords_has_8_buckets(self):
        kws = default_keywords()
        assert set(kws.keys()) == set(EVALUATION_ORDER)


class TestOutrosExcessivoWarning:
    def test_format_message_contains_pct_and_threshold(self):
        w = OutrosExcessivoWarning(pct_outros=23.1)
        msg = w.format()
        assert "23.1%" in msg
        assert "5%" in msg or "5.0%" in msg or f"{OUTROS_EXCESSIVO_THRESHOLD_PCT:.0f}%" in msg

    def test_threshold_default(self):
        w = OutrosExcessivoWarning(pct_outros=10.0)
        assert w.threshold_pct == 5.0

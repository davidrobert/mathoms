"""Tests — :class:`InvestimentosClassesAnalyzer` (Sessão A5b + ADR-193)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.asset_classifier import (  # noqa: E402
    OutrosExcessivoWarning,
)
from pipeline.domain.services.investimentos_classes_analyzer import (  # noqa: E402
    ClasseAtivo,
    InvestimentosClassesAnalysis,
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)


def _bens(**kwargs) -> dict:
    return kwargs


class TestConfig:
    def test_defaults_have_eight_financial_classes(self):
        # ADR-193 — 8 buckets financeiros (Cripto, Previdência, FIIs,
        # Internacional, Ações BR, Renda Fixa, Fundos, Caixa).
        cfg = InvestimentosClassesConfig.from_configs()
        for cls in (
            "Cripto",
            "Previdência",
            "FIIs",
            "Internacional",
            "Ações BR",
            "Renda Fixa",
            "Fundos",
            "Caixa",
        ):
            assert cls in cfg.keywords_por_classe

    def test_override_replaces_defaults(self):
        cfg = InvestimentosClassesConfig.from_configs(
            scoring={"asset_class_keywords": {"Ações BR": ["custom"]}},
        )
        assert cfg.keywords_por_classe["Ações BR"] == ("custom",)

    def test_residencia_property_ids_passthrough(self):
        cfg = InvestimentosClassesConfig.from_configs(
            residencia_property_ids=frozenset({"prop-residencia"})
        )
        assert cfg.residencia_property_ids == frozenset({"prop-residencia"})

    def test_scoring_can_introduce_new_class(self):
        # Forward-compat: classe nova em scoring.json não precisa estar em defaults.
        cfg = InvestimentosClassesConfig.from_configs(
            scoring={"asset_class_keywords": {"Alternativos": ["arte", "vinho"]}},
        )
        assert cfg.keywords_por_classe.get("Alternativos") == ("arte", "vinho")


class TestClassificacaoBasica:
    def test_acoes_br_matched_by_keyword(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "Ações ITSA4", "valor": 10_000}])]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Ações BR" in cats

    def test_renda_fixa_matched_by_keyword(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "CDB Banco X", "valor": 50_000}])]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Renda Fixa" in cats

    def test_cripto_matched_by_keyword(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "Bitcoin cold wallet", "valor": 20_000}])]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Cripto" in cats

    def test_renda_fixa_with_underscore_separator(self):
        # ADR-193 bug raiz: `tipo='renda_fixa'` precisa casar com `'renda fixa'`.
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "renda_fixa", "valor": 50_000}])]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Renda Fixa" in cats

    def test_classifica_via_descricao_quando_tipo_e_generico(self):
        # `tipo='investimento'` é o aggregate genérico do E1.5; sinal real
        # mora na descricao.
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {
                            "tipo": "investimento",
                            "descricao": "ACOES - ITSA4 - QUANTIDADE 693",
                            "valor": 100_000,
                        },
                    ]
                ),
            ]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Ações BR" in cats

    def test_previdencia_classe_propria(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "previdencia", "descricao": "PGBL Itaú", "valor": 80_000}
                    ]
                )
            ]
        )
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Previdência") == 80_000.0

    def test_internacional_via_descricao(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {
                            "tipo": "conta_bancaria",
                            "descricao": "Conta em USD na Wise",
                            "valor": 50_000,
                        }
                    ]
                )
            ]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Internacional" in cats

    def test_fii_via_ticker_xxxx11(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "fundo_investimento", "descricao": "HGLG11", "valor": 30_000}
                    ]
                )
            ]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "FIIs" in cats

    def test_outros_when_no_keyword_match(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "Investimento exotico XYZ", "valor": 5_000}])]
        )
        cats = {c.categoria for c in r.tabela_classes}
        assert "Outros" in cats

    def test_zero_valor_skipped(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "CDB", "valor": 0}])]
        )
        assert r.total == 0.0

    def test_fallback_valor_31_12_ano_base(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "CDB", "valor_31_12_ano_base": 1000}])]
        )
        rf = next(c for c in r.tabela_classes if c.categoria == "Renda Fixa")
        assert rf.valor == 1000.0


class TestTopLevelCripto:
    def test_criptos_escalar_soma_em_cripto(self):
        r = InvestimentosClassesAnalyzer().analyze([_bens(criptos=5_000)])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Cripto") == 5_000.0


class TestCaixa:
    def test_contas_escalar_soma_em_caixa(self):
        # ADR-193 — bucket renomeado de "Contas Bancárias" para "Caixa".
        r = InvestimentosClassesAnalyzer().analyze([_bens(contas_bancarias=10_000)])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Caixa") == 10_000.0

    def test_contas_lista_nao_entra_via_escalar(self):
        # Quando ``contas_bancarias`` é lista, não é somado pelo escalar-handler.
        r = InvestimentosClassesAnalyzer().analyze([_bens(contas_bancarias=[{"valor": 1000}])])
        cats = {c.categoria for c in r.tabela_classes}
        assert "Caixa" not in cats


class TestImoveisInvestimento:
    def test_imoveis_nao_residencia_entram_como_investimento(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    imoveis=[{"descricao": "Sala comercial", "valor_irpf": 300_000}],
                ),
            ]
        )
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Imóveis Investimento") == 300_000.0

    def test_residencia_excluida_por_property_id_override(self):
        """ADR-215 §1 sunset: filtro por property_id ∈ residencia_property_ids."""
        cfg = InvestimentosClassesConfig.from_configs(residencia_property_ids=frozenset({"p-vm"}))
        imoveis = [
            {"property_id": "p-vm", "valor_irpf": 800_000},
            {"descricao": "Sala", "valor_irpf": 300_000},
        ]
        r = InvestimentosClassesAnalyzer(cfg).analyze([_bens(imoveis=imoveis)])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Imóveis Investimento") == 300_000.0


class TestPercentuais:
    def test_pct_soma_100_quando_ha_valores(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "CDB", "valor": 50_000},
                        {"tipo": "Ações ITSA", "valor": 30_000},
                        {"tipo": "Bitcoin", "valor": 20_000},
                    ]
                ),
            ]
        )
        total_pct = sum(c.pct for c in r.tabela_classes)
        assert total_pct == pytest.approx(100.0)
        assert r.total == 100_000.0


class TestTabelaOrder:
    def test_ordered_by_valor_desc(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "CDB", "valor": 10_000},
                        {"tipo": "Ações ITSA", "valor": 50_000},
                        {"tipo": "Bitcoin", "valor": 30_000},
                    ]
                ),
            ]
        )
        cats = [c.categoria for c in r.tabela_classes]
        assert cats == ["Ações BR", "Cripto", "Renda Fixa"]


class TestMultiMember:
    def test_aggregates_across_members(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(investimentos=[{"tipo": "CDB", "valor": 50_000}]),
                _bens(investimentos=[{"tipo": "CDB Banco Y", "valor": 30_000}]),
            ]
        )
        rf = next(c for c in r.tabela_classes if c.categoria == "Renda Fixa")
        assert rf.valor == 80_000.0


class TestResult:
    def test_empty_input_returns_empty_analysis(self):
        r = InvestimentosClassesAnalyzer().analyze([])
        assert r.total == 0.0
        assert r.tabela_classes == ()
        assert r.warnings == ()

    def test_result_is_analysis_type(self):
        r = InvestimentosClassesAnalyzer().analyze([])
        assert isinstance(r, InvestimentosClassesAnalysis)

    def test_legacy_dict_shape(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(investimentos=[{"tipo": "CDB", "valor": 1000}])]
        )
        d = r.to_legacy_dict()
        assert "tabela_classes" in d
        assert "total" in d
        # `warnings` é Python-side, não vaza para o dict legacy.
        assert "warnings" not in d
        assert isinstance(d["tabela_classes"], list)
        assert d["tabela_classes"][0]["pct"] == 100.0


class TestDecomposicaoCarteiraFinanceira:
    """A37.l9 — decomposição total = financeiro + imóveis físicos + pct por base."""

    def _mixed(self) -> InvestimentosClassesAnalysis:
        return InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "CDB", "valor": 60_000},
                        {
                            "tipo": "conta_bancaria",
                            "descricao": "Conta em USD na Wise",
                            "valor": 20_000,
                        },
                    ],
                    imoveis=[{"valor_31_12_ano_base": 120_000}],
                )
            ]
        )

    def test_total_decomposto_por_construcao(self):
        r = self._mixed()
        assert r.total == pytest.approx(200_000.0)
        assert r.total_financeiro == pytest.approx(80_000.0)
        assert r.total_imoveis_investimento == pytest.approx(120_000.0)
        assert r.total == pytest.approx(r.total_financeiro + r.total_imoveis_investimento)

    def test_pct_carteira_financeira_exclui_imoveis_do_denominador(self):
        r = self._mixed()
        por_cat = {c.categoria: c for c in r.tabela_classes}
        # Internacional: 20k/200k = 10% do total investido; 20k/80k = 25% da financeira.
        assert por_cat["Internacional"].pct == pytest.approx(10.0)
        assert por_cat["Internacional"].pct_carteira_financeira == pytest.approx(25.0)
        assert por_cat["Renda Fixa"].pct_carteira_financeira == pytest.approx(75.0)

    def test_imoveis_investimento_sem_pct_carteira_financeira(self):
        r = self._mixed()
        imoveis = next(c for c in r.tabela_classes if c.categoria == "Imóveis Investimento")
        assert imoveis.pct_carteira_financeira is None
        assert imoveis.to_dict()["pct_carteira_financeira"] is None

    def test_legacy_dict_emite_decomposicao(self):
        d = self._mixed().to_legacy_dict()
        assert d["total_financeiro"] == pytest.approx(80_000.0)
        assert d["total_imoveis_investimento"] == pytest.approx(120_000.0)
        rf = next(c for c in d["tabela_classes"] if c["categoria"] == "Renda Fixa")
        assert rf["pct_carteira_financeira"] == pytest.approx(75.0)

    def test_empty_input_zera_decomposicao(self):
        r = InvestimentosClassesAnalyzer().analyze([])
        assert r.total_financeiro == 0.0
        assert r.total_imoveis_investimento == 0.0

    def test_carteira_100pct_imoveis_nao_divide_por_zero(self):
        r = InvestimentosClassesAnalyzer().analyze(
            [_bens(imoveis=[{"valor_31_12_ano_base": 100_000}])]
        )
        assert r.total_financeiro == 0.0
        imoveis = r.tabela_classes[0]
        assert imoveis.pct == pytest.approx(100.0)
        assert imoveis.pct_carteira_financeira is None


class TestOutrosExcessivoWarning:
    def test_warning_emitted_when_outros_above_threshold(self):
        # 90% em Outros (1 ativo classificado, 9 outros sem keyword) > 5% threshold.
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "CDB", "valor": 10_000},
                        {"tipo": "xyz exotico", "valor": 90_000},
                    ]
                )
            ]
        )
        assert len(r.warnings) == 1
        assert isinstance(r.warnings[0], OutrosExcessivoWarning)
        assert r.warnings[0].pct_outros == pytest.approx(90.0)

    def test_no_warning_when_outros_below_threshold(self):
        # 4% em Outros < 5% threshold → no warning.
        r = InvestimentosClassesAnalyzer().analyze(
            [
                _bens(
                    investimentos=[
                        {"tipo": "CDB", "valor": 96_000},
                        {"tipo": "xyz exotico", "valor": 4_000},
                    ]
                )
            ]
        )
        assert r.warnings == ()

    def test_no_warning_when_total_zero(self):
        r = InvestimentosClassesAnalyzer().analyze([_bens(investimentos=[])])
        assert r.warnings == ()

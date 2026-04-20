"""Tests — ``InvestimentosClassesAnalyzer`` (Sessão A5b)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.investimentos_classes_analyzer import (  # noqa: E402
    ClasseAtivo,
    InvestimentosClassesAnalyzer,
    InvestimentosClassesAnalysis,
    InvestimentosClassesConfig,
)


def _bens(**kwargs) -> dict:
    return kwargs


class TestConfig:
    def test_defaults_have_four_classes(self):
        cfg = InvestimentosClassesConfig.from_configs()

        for cls in ("Ações", "Renda Fixa", "Cripto", "Contas Bancárias"):
            assert cls in cfg.keywords_por_classe

    def test_override_replaces_defaults(self):
        cfg = InvestimentosClassesConfig.from_configs(
            scoring={"asset_class_keywords": {"Ações": ["custom"]}},
        )
        assert cfg.keywords_por_classe["Ações"] == ("custom",)

    def test_residencia_keyword_lowered_and_stripped(self):
        cfg = InvestimentosClassesConfig.from_configs(residencia_keyword="  VILA madalena  ")
        assert cfg.residencia_keyword == "vila madalena"


class TestClassificacaoBasica:
    def test_acoes_matched_by_keyword(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "Ações ITSA4", "valor": 10_000}]),
        ])
        cats = {c.categoria for c in r.tabela_classes}
        assert "Ações" in cats

    def test_renda_fixa_matched_by_keyword(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "CDB Banco X", "valor": 50_000}]),
        ])
        cats = {c.categoria for c in r.tabela_classes}
        assert "Renda Fixa" in cats

    def test_cripto_matched_by_keyword(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "Bitcoin cold wallet", "valor": 20_000}]),
        ])
        cats = {c.categoria for c in r.tabela_classes}
        assert "Cripto" in cats

    def test_outros_when_no_keyword_match(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "Investimento exotico XYZ", "valor": 5_000}]),
        ])
        cats = {c.categoria for c in r.tabela_classes}
        assert "Outros" in cats

    def test_zero_valor_skipped(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "CDB", "valor": 0}]),
        ])
        assert r.total == 0.0

    def test_fallback_valor_31_12_ano_base(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "CDB", "valor_31_12_ano_base": 1000}]),
        ])
        rf = next(c for c in r.tabela_classes if c.categoria == "Renda Fixa")
        assert rf.valor == 1000.0


class TestTopLevelCripto:
    def test_criptos_escalar_soma_em_cripto(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(criptos=5_000),
        ])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Cripto") == 5_000.0


class TestContasBancarias:
    def test_contas_escalar_soma_em_contas(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(contas_bancarias=10_000),
        ])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Contas Bancárias") == 10_000.0

    def test_contas_lista_nao_entra_via_escalar(self):
        """Quando ``contas_bancarias`` é lista, não é somado pelo
        escalar-handler (paridade com legado linha 1570-1575)."""
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(contas_bancarias=[{"valor": 1000}]),
        ])
        cats = {c.categoria for c in r.tabela_classes}
        # Não entra em "Contas Bancárias" via escalar — se houvesse investimentos
        # com keyword "conta" entraria. Aqui: nada.
        assert "Contas Bancárias" not in cats


class TestImoveisInvestimento:
    def test_imoveis_nao_residencia_entram_como_investimento(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(imoveis=[
                {"descricao": "Sala comercial", "valor_irpf": 300_000},
            ]),
        ])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Imóveis Investimento") == 300_000.0

    def test_residencia_matching_keyword_eh_excluida(self):
        cfg = InvestimentosClassesConfig.from_configs(residencia_keyword="vila madalena")
        r = InvestimentosClassesAnalyzer(cfg).analyze([
            _bens(imoveis=[
                {"descricao": "Casa Vila Madalena", "valor_irpf": 800_000},
                {"descricao": "Sala", "valor_irpf": 300_000},
            ]),
        ])
        cats = {c.categoria: c.valor for c in r.tabela_classes}
        assert cats.get("Imóveis Investimento") == 300_000.0


class TestPercentuais:
    def test_pct_soma_100_quando_ha_valores(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[
                {"tipo": "CDB", "valor": 50_000},
                {"tipo": "Ações ITSA", "valor": 30_000},
                {"tipo": "Bitcoin", "valor": 20_000},
            ]),
        ])
        # 100k total, split 50/30/20.
        total_pct = sum(c.pct for c in r.tabela_classes)
        assert total_pct == pytest.approx(100.0)
        assert r.total == 100_000.0


class TestTabelaOrder:
    def test_ordered_by_valor_desc(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[
                {"tipo": "CDB", "valor": 10_000},
                {"tipo": "Ações ITSA", "valor": 50_000},
                {"tipo": "Bitcoin", "valor": 30_000},
            ]),
        ])
        cats = [c.categoria for c in r.tabela_classes]
        # Ações 50k, Cripto 30k, Renda Fixa 10k.
        assert cats == ["Ações", "Cripto", "Renda Fixa"]


class TestMultiMember:
    def test_aggregates_across_members(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "CDB", "valor": 50_000}]),
            _bens(investimentos=[{"tipo": "CDB Banco Y", "valor": 30_000}]),
        ])
        rf = next(c for c in r.tabela_classes if c.categoria == "Renda Fixa")
        assert rf.valor == 80_000.0


class TestResult:
    def test_empty_input_returns_empty_analysis(self):
        r = InvestimentosClassesAnalyzer().analyze([])
        assert r.total == 0.0
        assert r.tabela_classes == ()

    def test_result_is_analysis_type(self):
        r = InvestimentosClassesAnalyzer().analyze([])
        assert isinstance(r, InvestimentosClassesAnalysis)

    def test_legacy_dict_shape(self):
        r = InvestimentosClassesAnalyzer().analyze([
            _bens(investimentos=[{"tipo": "CDB", "valor": 1000}]),
        ])
        d = r.to_legacy_dict()

        assert "tabela_classes" in d
        assert "total" in d
        assert isinstance(d["tabela_classes"], list)
        assert d["tabela_classes"][0]["pct"] == 100.0

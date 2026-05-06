"""Tests — :class:`TopAtivosAnalyzer` (companion de A5b)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.top_ativos_analyzer import (  # noqa: E402
    TopAtivo,
    TopAtivosAnalyzer,
    TopAtivosConfig,
    TopAtivosResult,
)


def _bens(**kwargs) -> dict:
    return kwargs


def _entries(*pairs):
    return list(pairs)


class TestEmpty:
    def test_no_members_returns_empty_result(self):
        r = TopAtivosAnalyzer().analyze([])
        assert isinstance(r, TopAtivosResult)
        assert r.top_ativos == ()
        assert r.total_carteira == 0.0

    def test_none_input_returns_empty(self):
        r = TopAtivosAnalyzer().analyze(None)
        assert r.top_ativos == ()
        assert r.total_carteira == 0.0


class TestRanking:
    def test_orders_desc_by_value(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"tipo": "CDB", "valor": 50_000, "nome": "CDB BTG"},
                            {"tipo": "Ações ITSA", "valor": 200_000, "nome": "ITSA4"},
                            {"tipo": "Bitcoin", "valor": 30_000, "nome": "BTC"},
                        ]
                    ),
                )
            )
        )
        assert [a.nome for a in r.top_ativos] == ["ITSA4", "CDB BTG", "BTC"]
        assert [a.posicao for a in r.top_ativos] == [1, 2, 3]

    def test_aggregates_across_members(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(investimentos=[{"tipo": "CDB", "valor": 100_000, "nome": "A"}]),
                ),
                (
                    "mariana",
                    _bens(investimentos=[{"tipo": "CDB", "valor": 200_000, "nome": "B"}]),
                ),
            )
        )
        assert r.top_ativos[0].nome == "B"
        assert r.top_ativos[0].membro == "mariana"
        assert r.top_ativos[1].membro == "david"

    def test_limit_applied(self):
        cfg = TopAtivosConfig.from_configs(limit=3)
        invs = [{"tipo": "CDB", "valor": 1000 + i, "nome": f"A{i}"} for i in range(10)]
        r = TopAtivosAnalyzer(cfg).analyze(_entries(("david", _bens(investimentos=invs))))
        assert len(r.top_ativos) == 3


class TestPercentual:
    def test_pct_relative_to_total_individual(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"tipo": "CDB", "valor": 50_000, "nome": "A"},
                            {"tipo": "Ações", "valor": 50_000, "nome": "B"},
                        ]
                    ),
                )
            )
        )
        assert r.total_carteira == 100_000.0
        assert all(a.pct_carteira == 50.0 for a in r.top_ativos)


class TestNomeFallback:
    def test_uses_tipo_and_instituicao_when_nome_empty(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"tipo": "Tesouro IPCA+", "valor": 50_000, "instituicao": "btg"}
                        ]
                    ),
                )
            )
        )
        assert r.top_ativos[0].nome == "Tesouro IPCA+ (Btg)"
        assert r.top_ativos[0].instituicao == "Btg"

    def test_uses_tipo_only_when_no_instituicao(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(investimentos=[{"tipo": "Tesouro", "valor": 1000}])))
        )
        assert r.top_ativos[0].nome == "Tesouro"


class TestImoveisInvestimento:
    def test_imoveis_nao_residencia_entram(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        imoveis=[
                            {"descricao": "Sala comercial", "valor_irpf": 300_000},
                        ]
                    ),
                )
            )
        )
        assert r.top_ativos[0].nome == "Sala comercial"
        assert r.top_ativos[0].classe == "Imóveis Investimento"
        assert r.top_ativos[0].tipo_origem == "imovel"

    def test_residencia_filtrada_por_keyword(self):
        cfg = TopAtivosConfig.from_configs(residencia_keyword="vila madalena")
        r = TopAtivosAnalyzer(cfg).analyze(
            _entries(
                (
                    "david",
                    _bens(
                        imoveis=[
                            {"descricao": "Casa Vila Madalena", "valor_irpf": 800_000},
                            {"descricao": "Sala", "valor_irpf": 300_000},
                        ]
                    ),
                )
            )
        )
        assert len(r.top_ativos) == 1
        assert r.top_ativos[0].nome == "Sala"


class TestExclusaoEscalares:
    def test_criptos_escalar_nao_entra(self):
        # Criptos sem nome individual ficam só em tabela_classes (agregado).
        r = TopAtivosAnalyzer().analyze(_entries(("david", _bens(criptos=50_000))))
        assert r.top_ativos == ()

    def test_contas_escalar_nao_entra(self):
        r = TopAtivosAnalyzer().analyze(_entries(("david", _bens(contas_bancarias=20_000))))
        assert r.top_ativos == ()


class TestZeroValores:
    def test_valor_zero_skipado(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(investimentos=[{"tipo": "CDB", "valor": 0, "nome": "A"}]),
                )
            )
        )
        assert r.top_ativos == ()


_CLASSIFICATION_INVS = [
    {"tipo": "Ações ITSA4", "valor": 1000, "nome": "X"},
    {"tipo": "CDB", "valor": 1000, "nome": "Y"},
    {"tipo": "Bitcoin", "valor": 1000, "nome": "Z"},
    {"tipo": "Algo exotico", "valor": 1000, "nome": "W"},
]


class TestClassificacao:
    def test_classifies_using_inv_classes_keywords(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(investimentos=_CLASSIFICATION_INVS)))
        )
        by_nome = {a.nome: a.classe for a in r.top_ativos}
        assert by_nome["X"] == "Ações"
        assert by_nome["Y"] == "Renda Fixa"
        assert by_nome["Z"] == "Cripto"
        assert by_nome["W"] == "Outros"


class TestSerialization:
    def test_to_dict_roundtrip(self):
        a = TopAtivo(
            posicao=1,
            nome="A",
            classe="Renda Fixa",
            membro="david",
            instituicao="Btg",
            valor=12345.678,
            pct_carteira=33.3333,
            tipo_origem="investimento",
        )
        d = a.to_dict()
        assert d["valor"] == 12345.68
        assert d["pct_carteira"] == 33.33

    def test_legacy_dict_shape(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(investimentos=[{"tipo": "CDB", "valor": 1000, "nome": "A"}])))
        )
        d = r.to_legacy_dict()
        assert "top_ativos" in d
        assert isinstance(d["top_ativos"], list)
        assert d["top_ativos"][0]["posicao"] == 1


class TestTipoOrigem:
    def test_investimento_tag(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(investimentos=[{"tipo": "CDB", "valor": 100, "nome": "A"}])))
        )
        assert r.top_ativos[0].tipo_origem == "investimento"

    def test_imovel_tag(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(imoveis=[{"descricao": "X", "valor_irpf": 100}])))
        )
        assert r.top_ativos[0].tipo_origem == "imovel"

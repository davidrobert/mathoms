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
        # ADR-337: rótulo classe-only na fonte (não lê a descrição cartorial).
        assert r.top_ativos[0].nome == "Imóvel de investimento"
        assert r.top_ativos[0].classe == "Imóveis Investimento"
        assert r.top_ativos[0].tipo_origem == "imovel"

    def test_residencia_filtrada_por_property_id_override(self):
        """ADR-215 §1 sunset: filtro por property_id ∈ residencia_property_ids."""
        cfg = TopAtivosConfig.from_configs(residencia_property_ids=frozenset({"p-vm"}))
        imoveis = [
            {"property_id": "p-vm", "valor_irpf": 800_000},
            {"descricao": "Sala", "valor_irpf": 300_000},
        ]
        r = TopAtivosAnalyzer(cfg).analyze(_entries(("david", _bens(imoveis=imoveis))))
        assert len(r.top_ativos) == 1
        assert r.top_ativos[0].nome == "Imóvel de investimento"

    def test_imovel_nome_e_classe_only_sem_pii(self):
        """ADR-337/PD-02/H1: a descrição cartorial (matrícula/IPTU/CNPJ/endereço)
        NUNCA entra em top_ativos[].nome — vazaria à UI e ao prompt do parecer."""
        # Fixture sintética (ADR-319): só palavras-marcador, sem PII real.
        registral = (
            "APARTAMENTO CONDOMINIO EXEMPLO. Matrícula sintética. IPTU informado. "
            "CNPJ da incorporadora. AV das Amostras, sem numero."
        )
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(imoveis=[{"descricao": registral, "valor_irpf": 500_000}])))
        )
        nome = r.top_ativos[0].nome
        assert nome == "Imóvel de investimento"
        for marker in ("Matríc", "IPTU", "CNPJ", "AV ", "APARTAMENTO", "Amostras"):
            assert marker not in nome, f"vazou marcador registral em top_ativos[].nome: {marker!r}"


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
        # ADR-193 — usa taxonomia canônica de 10 buckets unificada com
        # InvestimentosClassesAnalyzer via asset_classifier.classify_asset.
        r = TopAtivosAnalyzer().analyze(
            _entries(("david", _bens(investimentos=_CLASSIFICATION_INVS)))
        )
        by_nome = {a.nome: a.classe for a in r.top_ativos}
        assert by_nome["X"] == "Ações BR"
        assert by_nome["Y"] == "Renda Fixa"
        assert by_nome["Z"] == "Cripto"
        assert by_nome["W"] == "Outros"

    def test_classifies_using_descricao_when_tipo_generic(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {
                                "tipo": "investimento",
                                "descricao": "ACOES - ITSA4",
                                "valor": 10_000,
                                "nome": "ITSA4",
                            }
                        ]
                    ),
                )
            )
        )
        assert r.top_ativos[0].classe == "Ações BR"

    def test_handles_underscored_tipo(self):
        # Bug ADR-193 — `tipo='renda_fixa'` precisa virar Renda Fixa.
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(investimentos=[{"tipo": "renda_fixa", "valor": 50_000, "nome": "RF"}]),
                )
            )
        )
        assert r.top_ativos[0].classe == "Renda Fixa"


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


def _imovel(descricao: str, valor_irpf, **kw) -> dict:
    out: dict = {"descricao": descricao, "valor_irpf": valor_irpf}
    out.update(kw)
    return out


class TestDedupByPropertyId:
    """ADR-246: defesa em profundidade — Top 15 dedup por property_id (maior vence)."""

    def test_same_property_id_in_two_members_collapses(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                ("david", _bens(imoveis=[_imovel("APT", 477436.58, property_id="uuid-x")])),
                ("mariana", _bens(imoveis=[_imovel("APT", 530000.0, property_id="uuid-x")])),
            )
        )
        assert len(r.top_ativos) == 1
        assert float(r.top_ativos[0].valor) == 530000.0

    def test_distinct_property_ids_preserved(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        imoveis=[
                            _imovel("A", 100, property_id="uuid-a"),
                            _imovel("B", 200, property_id="uuid-b"),
                        ]
                    ),
                )
            )
        )
        assert len(r.top_ativos) == 2

    def test_no_property_id_no_dedup(self):
        # Investimentos sem property_id passam direto (não há chave de dedup)
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"tipo": "CDB", "valor": 100, "nome": "A"},
                            {"tipo": "CDB", "valor": 100, "nome": "A"},
                        ]
                    ),
                )
            )
        )
        assert len(r.top_ativos) == 2

    def test_casal_label_when_proprietario_is_casal(self):
        r = TopAtivosAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        imoveis=[_imovel("APT", 500000, property_id="uuid-c", proprietario="casal")]
                    ),
                ),
            )
        )
        assert r.top_ativos[0].membro == "Casal"

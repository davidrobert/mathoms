"""Tests — :class:`InstituicoesPorMembroAnalyzer` (companion de A5b)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.instituicoes_por_membro_analyzer import (  # noqa: E402
    InstituicoesPorMembroAnalyzer,
    InstituicoesPorMembroConfig,
    InstituicoesPorMembroResult,
    MembroInstituicoes,
)


def _bens(**kwargs) -> dict:
    return kwargs


def _entries(*pairs):
    return list(pairs)


class TestEmpty:
    def test_no_input_returns_empty_result(self):
        r = InstituicoesPorMembroAnalyzer().analyze([])
        assert isinstance(r, InstituicoesPorMembroResult)
        assert r.por_membro == ()
        assert r.n_imoveis_total == 0

    def test_none_input_returns_empty(self):
        r = InstituicoesPorMembroAnalyzer().analyze(None)
        assert r.por_membro == ()
        assert r.n_imoveis_total == 0


class TestAggregation:
    def test_groups_instituicoes_per_membro(self):
        david_invs = [
            {"tipo": "CDB", "valor": 100, "instituicao": "btg"},
            {"tipo": "Ações", "valor": 50, "instituicao": "xp"},
        ]
        mariana_invs = [{"tipo": "CDB", "valor": 30, "instituicao": "itau"}]
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                ("david", _bens(investimentos=david_invs)),
                ("mariana", _bens(investimentos=mariana_invs)),
            )
        )
        names = {m.membro: m.instituicoes for m in r.por_membro}
        assert names["david"] == ("Btg", "Xp")
        assert names["mariana"] == ("Itau",)

    def test_dedupes_repeated_institution(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"tipo": "CDB", "valor": 1, "instituicao": "BTG"},
                            {"tipo": "CDB 2", "valor": 1, "instituicao": "btg"},
                        ]
                    ),
                )
            )
        )
        assert r.por_membro[0].instituicoes == ("Btg",)

    def test_skips_empty_instituicao(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"tipo": "X", "valor": 1, "instituicao": "  "},
                            {"tipo": "Y", "valor": 1},
                        ]
                    ),
                )
            )
        )
        assert r.por_membro[0].instituicoes == ()

    def test_sorts_membros_alphabetically(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                ("zoe", _bens(investimentos=[{"valor": 1, "instituicao": "A"}])),
                ("alice", _bens(investimentos=[{"valor": 1, "instituicao": "B"}])),
            )
        )
        assert [m.membro for m in r.por_membro] == ["alice", "zoe"]

    def test_sorts_instituicoes_alphabetically(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[
                            {"valor": 1, "instituicao": "z banco"},
                            {"valor": 1, "instituicao": "a banco"},
                        ]
                    ),
                )
            )
        )
        # Note: capitalize lowercases tudo após primeira letra → "A banco", "Z banco"
        assert r.por_membro[0].instituicoes == ("A banco", "Z banco")


class TestNImoveis:
    def test_counts_all_imoveis_residencia_e_investimento(self):
        # Paridade com legado: conta TUDO (residência + investimento), não só investimento.
        cfg = InstituicoesPorMembroConfig.from_configs(residencia_property_ids=frozenset({"p-vm"}))
        imoveis = [
            {"property_id": "p-vm", "valor": 800_000},  # residência
            {"descricao": "Sala", "valor": 300_000},  # investimento
        ]
        r = InstituicoesPorMembroAnalyzer(cfg).analyze(_entries(("david", _bens(imoveis=imoveis))))
        assert r.n_imoveis_total == 2

    def test_aggregates_imoveis_across_members(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(imoveis=[{"descricao": "A", "valor": 1}, {"descricao": "B", "valor": 1}]),
                ),
                ("mariana", _bens(imoveis=[{"descricao": "C", "valor": 1}])),
            )
        )
        assert r.n_imoveis_total == 3

    def test_zero_imoveis(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(("david", _bens(investimentos=[{"valor": 1, "instituicao": "X"}])))
        )
        assert r.n_imoveis_total == 0

    def test_empty_member_key_ignored_but_imoveis_counted(self):
        # Workspace sem cônjuge → conjuge_key="". Schema exige membro non-empty,
        # mas a contagem de imóveis precisa preservar paridade.
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                ("david", _bens(investimentos=[{"valor": 1, "instituicao": "btg"}])),
                ("", _bens(imoveis=[{"descricao": "X", "valor": 1}])),
            )
        )
        assert [m.membro for m in r.por_membro] == ["david"]
        assert r.n_imoveis_total == 1


class TestSerialization:
    def test_to_dict_shape(self):
        m = MembroInstituicoes(membro="david", instituicoes=("Btg", "Xp"))
        assert m.to_dict() == {"membro": "david", "instituicoes": ["Btg", "Xp"]}

    def test_legacy_dict_shape(self):
        r = InstituicoesPorMembroAnalyzer().analyze(
            _entries(
                (
                    "david",
                    _bens(
                        investimentos=[{"valor": 1, "instituicao": "btg"}], imoveis=[{"valor": 1}]
                    ),
                )
            )
        )
        d = r.to_legacy_dict()
        assert "instituicoes_por_membro" in d
        assert "n_imoveis_total" in d
        assert d["instituicoes_por_membro"][0]["membro"] == "david"
        assert d["n_imoveis_total"] == 1

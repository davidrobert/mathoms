"""Tests — ``E5MemberResolver`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.e5_member_resolver import (  # noqa: E402
    E5MemberResolver,
    MemberResolverConfig,
    ResolvedMembers,
)


_DAVID_MARIANA = MemberResolverConfig(titular_key="david", conjuge_key="mariana")


class TestConfig:
    def test_from_family_extracts_conjuge(self):
        cfg = MemberResolverConfig.from_family({
            "titular": "david",
            "membros": {
                "david": {"papel": "titular"},
                "mariana": {"papel": "conjuge"},
            },
        })
        assert cfg.titular_key == "david"
        assert cfg.conjuge_key == "mariana"

    def test_from_family_no_conjuge(self):
        cfg = MemberResolverConfig.from_family({
            "titular": "ana",
            "membros": {"ana": {"papel": "titular"}},
        })
        assert cfg.conjuge_key == ""


class TestFormat1DictMembers:
    def test_members_as_dict_with_titular_conjuge(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "members": {
                "david": {"total_bens": 500_000},
                "mariana": {"total_bens": 300_000},
            }
        })
        assert r.source_format == "dict"
        assert r.titular_data["total_bens"] == 500_000
        assert r.conjuge_data["total_bens"] == 300_000

    def test_membros_alias_also_works(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "membros": {"david": {"total_bens": 100}, "mariana": {}}
        })
        assert r.titular_data["total_bens"] == 100

    def test_missing_member_returns_empty(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "members": {"david": {"total_bens": 100}}
        })
        assert r.conjuge_data == {}


class TestFormat2ListOfDicts:
    def test_list_of_dicts_matched_by_nome(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "membros": [
                {"nome": "David Silva", "total_bens": 400_000},
                {"nome": "Mariana Souza", "total_bens": 200_000},
            ]
        })
        assert r.source_format == "list_dicts"
        assert r.titular_data["total_bens"] == 400_000
        assert r.conjuge_data["total_bens"] == 200_000


class TestFormat3Declarations:
    def test_classifies_bens_direitos_by_irpf_grupo(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "membros": ["david", "mariana"],
            "declarations": [
                {
                    "membro": "david",
                    "ano_base": 2024,
                    "bens_direitos": [
                        {"grupo": "G01", "descricao": "Imóvel", "situacao_atual": 800_000},
                        {"grupo": "G02", "descricao": "Carro", "situacao_atual": 50_000},
                        {"grupo": "G04", "descricao": "CDB", "situacao_atual": 100_000},
                        {"grupo": "G06", "descricao": "Conta", "situacao_atual": 20_000},
                    ],
                    "total_bens": 970_000,
                },
            ],
        })
        assert r.source_format == "declarations"
        bens = r.titular_data["bens"]
        assert len(bens["imoveis"]) == 1
        assert len(bens["veiculos"]) == 1
        assert len(bens["investimentos"]) == 1
        assert len(bens["contas_bancarias"]) == 1
        assert r.titular_data["total_bens"] == 970_000

    def test_uses_most_recent_ano_base(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "membros": ["david"],
            "declarations": [
                {
                    "membro": "david",
                    "ano_base": 2022,
                    "bens_direitos": [{"grupo": "G01", "situacao_atual": 100}],
                    "total_bens": 100,
                },
                {
                    "membro": "david",
                    "ano_base": 2024,
                    "bens_direitos": [{"grupo": "G01", "situacao_atual": 999}],
                    "total_bens": 999,
                },
            ],
        })
        assert r.titular_data["total_bens"] == 999

    def test_dividas_from_baseline_attributed_to_member(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "membros": ["david", "mariana"],
            "declarations": [
                {
                    "membro": "david",
                    "ano_base": 2024,
                    "bens_direitos": [],
                    "total_bens": 0,
                },
            ],
            "dividas": [
                {"proprietario": "David Silva", "saldo_31_12": 100_000},
                {"proprietario": "Mariana", "saldo_31_12": 50_000},  # cônjuge
            ],
        })
        assert r.titular_data["total_dividas"] == 100_000


class TestFormat4Consolidated:
    def test_patrimonio_por_ano_resolves_ano_ref(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "patrimonio_por_ano": {
                "2023": {"total_bens": 500_000, "total_dividas": 50_000},
                "2024": {"total_bens": 800_000, "total_dividas": 100_000},
            },
            "imoveis_consolidados": [
                {"descricao": "Casa", "valores_31_12": {"2024": 600_000}},
            ],
            "investimentos_consolidados": [
                {"descricao": "CDB", "valores_31_12": {"2024": 200_000}},
            ],
        })
        assert r.source_format == "consolidated"
        assert r.reference_year == "2024"
        assert r.titular_data["total_bens"] == 800_000

    def test_conjuge_exclusive_item_goes_to_conjuge(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "patrimonio_por_ano": {"2024": {"total_bens": 0, "total_dividas": 0}},
            "imoveis_consolidados": [
                {
                    "descricao": "Apto da Mariana",
                    "proprietario": "Mariana Souza",
                    "valores_31_12": {"2024": 500_000},
                },
            ],
        })
        assert len(r.conjuge_data["bens"]["imoveis"]) == 1
        assert len(r.titular_data["bens"]["imoveis"]) == 0

    def test_investimentos_dict_v2_format(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "patrimonio_por_ano": {"2024": {"total_bens": 200_000, "total_dividas": 0}},
            "investimentos_financeiros_consolidados": {
                "david_2024": {"tesouro": 100_000, "cdb": 50_000, "total": 150_000},
                "mariana_2024": {"lci": 30_000, "total": 30_000},
            },
        })
        # total skipped, 2 entries david, 1 entry mariana.
        assert len(r.titular_data["bens"]["investimentos"]) == 2
        assert len(r.conjuge_data["bens"]["investimentos"]) == 1

    def test_dividas_split_by_proprietario(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "patrimonio_por_ano": {"2024": {"total_bens": 0, "total_dividas": 150_000}},
            "dividas": [
                {"proprietario": "david", "saldo_31_12": {"2024": 100_000}},
                {"proprietario": "mariana", "saldo_31_12": {"2024": 50_000}},
            ],
        })
        assert r.titular_data["total_dividas"] == 100_000
        assert r.conjuge_data["total_dividas"] == 50_000


class TestDefensivos:
    def test_none_baseline_returns_empty(self):
        r = E5MemberResolver().resolve(None)
        assert r.titular_data == {}
        assert r.conjuge_data == {}

    def test_non_dict_baseline_returns_empty(self):
        r = E5MemberResolver().resolve("not a dict")  # type: ignore[arg-type]
        assert r.titular_data == {}

    def test_as_tuple_format_compatible_with_legacy(self):
        r = E5MemberResolver(_DAVID_MARIANA).resolve({
            "members": {"david": {"total_bens": 100}, "mariana": {"total_bens": 50}}
        })
        t, c = r.as_tuple()
        assert t["total_bens"] == 100
        assert c["total_bens"] == 50

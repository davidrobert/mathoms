"""Unit tests for titular_key_normalizer (ADR-215 fix-B3)."""

from __future__ import annotations

from pipeline.domain.services.titular_key_normalizer import normalize_titular_key
from pipeline.domain.types.config import FamilyMemberRecord, FamilyMembersConfig


def _make_config(*members: FamilyMemberRecord) -> FamilyMembersConfig:
    return FamilyMembersConfig(members=tuple(members))


class TestNormalizeTitularKey:
    def test_no_family_members_returns_raw(self):
        assert normalize_titular_key("mariana_x", None) == "mariana_x"

    def test_exact_key_match_returns_canonical(self):
        config = _make_config(
            FamilyMemberRecord(
                key="mariana_andrade_silva",
                full_name="Mariana Andrade Silva",
                short_name="Mariana",
                role="conjuge",
            )
        )
        assert normalize_titular_key("mariana_andrade_silva", config) == "mariana_andrade_silva"

    def test_real_case_mariana_alias_with_birth_name_token(self):
        """Caso real dogfood: LLM extraiu `mariana_ribeiro_andrade`
        (nome de nascimento) em IRPF antigo, `mariana_andrade_silva`
        (nome casada) em IRPF novo. Workspace canônico = nome casada."""
        config = _make_config(
            FamilyMemberRecord(
                key="mariana_andrade_silva",
                full_name="Mariana Andrade Silva",
                short_name="Mariana",
                role="conjuge",
                extra={"nome_nascimento": "Mariana Ribeiro Andrade"},
            )
        )
        # `andrade` é token comum entre raw e canonical
        result = normalize_titular_key("mariana_ribeiro_andrade", config)
        assert result == "mariana_andrade_silva"

    def test_real_case_david_full_name_vs_short_key(self):
        """Caso real dogfood: LLM extraiu `david_robert_martins_de_silva`
        (nome completo) em IRPF antigo, `david_robert` em IRPF novo."""
        config = _make_config(
            FamilyMemberRecord(
                key="david_robert_martins_andrade_silva",
                full_name="David Robert Martins Andrade Silva",
                short_name="David",
                role="titular",
            )
        )
        # 4 tokens em comum (david, robert, martins, silva)
        result = normalize_titular_key("david_robert_martins_de_silva", config)
        assert result == "david_robert_martins_andrade_silva"

    def test_short_key_to_long_canonical(self):
        config = _make_config(
            FamilyMemberRecord(
                key="david_robert_martins_andrade_silva",
                full_name="David Robert Martins Andrade Silva",
                short_name="David",
                role="titular",
            )
        )
        assert normalize_titular_key("david_robert", config) == "david_robert_martins_andrade_silva"

    def test_no_common_tokens_returns_raw(self):
        config = _make_config(
            FamilyMemberRecord(
                key="mariana_souza",
                full_name="Mariana Souza",
                short_name="Mariana",
                role="conjuge",
            )
        )
        # `pedro` não casa com nenhum token de mariana
        assert normalize_titular_key("pedro_x", config) == "pedro_x"

    def test_explicit_aliases_in_extra(self):
        config = _make_config(
            FamilyMemberRecord(
                key="mariana",
                full_name="Mariana Souza",
                short_name="Mariana",
                role="conjuge",
                extra={"titular_key_aliases": ["mariana_ribeiro"]},
            )
        )
        # Match via alias declarado
        assert normalize_titular_key("mariana_ribeiro", config) == "mariana"

    def test_picks_best_score_when_multiple_members_partial_match(self):
        config = _make_config(
            FamilyMemberRecord(
                key="david_robert",
                full_name="David Robert Silva",
                short_name="David",
                role="titular",
            ),
            FamilyMemberRecord(
                key="mariana_souza",
                full_name="Mariana Souza",
                short_name="Mariana",
                role="conjuge",
            ),
        )
        # Apenas "david" casa
        assert normalize_titular_key("david_martins", config) == "david_robert"
        # Apenas "mariana" casa
        assert normalize_titular_key("mariana_ribeiro_andrade", config) == "mariana_souza"

    def test_empty_raw_returns_empty(self):
        assert normalize_titular_key("", _make_config()) == ""

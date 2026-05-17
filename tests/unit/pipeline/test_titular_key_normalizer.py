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
                key="mariana_ferreira_campos",
                full_name="Mariana Ferreira Campos",
                short_name="Mariana",
                role="conjuge",
            )
        )
        assert normalize_titular_key("mariana_ferreira_campos", config) == "mariana_ferreira_campos"

    def test_real_case_mariana_alias_with_birth_name_token(self):
        """Caso real dogfood: LLM extraiu `mariana_teixeira_ferreira`
        (nome de nascimento) em IRPF antigo, `mariana_ferreira_campos`
        (nome casada) em IRPF novo. Workspace canônico = nome casada."""
        config = _make_config(
            FamilyMemberRecord(
                key="mariana_ferreira_campos",
                full_name="Mariana Ferreira Campos",
                short_name="Mariana",
                role="conjuge",
                extra={"nome_nascimento": "Mariana Teixeira Ferreira"},
            )
        )
        # `ferreira` é token comum entre raw e canonical
        result = normalize_titular_key("mariana_teixeira_ferreira", config)
        assert result == "mariana_ferreira_campos"

    def test_real_case_david_full_name_vs_short_key(self):
        """Caso real dogfood: LLM extraiu `david_robert_camargo_de_campos`
        (nome completo) em IRPF antigo, `david_robert` em IRPF novo."""
        config = _make_config(
            FamilyMemberRecord(
                key="david_robert_camargo_ferreira_campos",
                full_name="David Robert Camargo Ferreira Campos",
                short_name="David",
                role="titular",
            )
        )
        # 4 tokens em comum (david, robert, camargo, campos)
        result = normalize_titular_key("david_robert_camargo_de_campos", config)
        assert result == "david_robert_camargo_ferreira_campos"

    def test_short_key_to_long_canonical(self):
        config = _make_config(
            FamilyMemberRecord(
                key="david_robert_camargo_ferreira_campos",
                full_name="David Robert Camargo Ferreira Campos",
                short_name="David",
                role="titular",
            )
        )
        assert (
            normalize_titular_key("david_robert", config) == "david_robert_camargo_ferreira_campos"
        )

    def test_no_common_tokens_returns_raw(self):
        config = _make_config(
            FamilyMemberRecord(
                key="mariana_ferreira",
                full_name="Mariana Ferreira",
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
                full_name="Mariana Ferreira",
                short_name="Mariana",
                role="conjuge",
                extra={"titular_key_aliases": ["mariana_teixeira"]},
            )
        )
        # Match via alias declarado
        assert normalize_titular_key("mariana_teixeira", config) == "mariana"

    def test_picks_best_score_when_multiple_members_partial_match(self):
        config = _make_config(
            FamilyMemberRecord(
                key="david_robert",
                full_name="David Robert Silva",
                short_name="David",
                role="titular",
            ),
            FamilyMemberRecord(
                key="mariana_ferreira",
                full_name="Mariana Ferreira",
                short_name="Mariana",
                role="conjuge",
            ),
        )
        # Apenas "david" casa
        assert normalize_titular_key("david_camargo", config) == "david_robert"
        # Apenas "ferreira" casa
        assert normalize_titular_key("mariana_teixeira_ferreira", config) == "mariana_ferreira"

    def test_empty_raw_returns_empty(self):
        assert normalize_titular_key("", _make_config()) == ""

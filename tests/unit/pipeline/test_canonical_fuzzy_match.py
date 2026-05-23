"""Unit tests do helper canonical_fuzzy_match (ADR-265)."""

from __future__ import annotations

from pipeline.domain.services.canonical_fuzzy_match import (
    extract_complemento,
    matches_fuzzy,
)


class TestExactAndZeroDiff:
    def test_exact_equal_matches(self):
        assert matches_fuzzy("benedito calixto 190", "benedito calixto 190") is True

    def test_delta_zero_matches(self):
        # mesma via+numero string-equal
        assert matches_fuzzy("paulista 1500", "paulista 1500") is True


class TestNumberProximity:
    def test_caso_real_founder_delta_4_matches(self):
        """Praça Benedito Calixto 190 (IRPF) vs 186 (comprovante) — Δ=4."""
        assert matches_fuzzy("benedito calixto 190", "benedito calixto 186") is True

    def test_delta_4_matches_default_k(self):
        assert matches_fuzzy("tasso silveira 61", "tasso silveira 65") is True

    def test_delta_5_does_not_match_without_complemento(self):
        # Δ=5 > K=4 default e sem complemento → rejeita
        assert matches_fuzzy("paulista 1500", "paulista 1505") is False

    def test_delta_10_does_not_match_in_dense_avenue(self):
        # Av Paulista densa: 1500 vs 1490 são imóveis distintos
        assert matches_fuzzy("paulista 1500", "paulista 1490") is False


class TestComplementoGuards:
    def test_complemento_identico_extends_tolerance_to_k8(self):
        # Δ=8 + complemento idêntico → casa
        assert (
            matches_fuzzy(
                "benedito calixto 190",
                "benedito calixto 198",
                complemento_a="34",
                complemento_b="34",
            )
            is True
        )

    def test_complemento_identico_does_not_extend_beyond_k8(self):
        # Δ=12 mesmo com complemento idêntico → rejeita
        assert (
            matches_fuzzy(
                "benedito calixto 190",
                "benedito calixto 202",
                complemento_a="34",
                complemento_b="34",
            )
            is False
        )

    def test_complemento_divergente_blocks_match_inside_k4(self):
        # Mesmo Δ=2 (dentro de K=4), se complementos divergem → NÃO funde
        # (sinal forte: imóveis distintos no mesmo prédio/condomínio).
        assert (
            matches_fuzzy(
                "paulista 100",
                "paulista 102",
                complemento_a="51",
                complemento_b="34",
            )
            is False
        )

    def test_complemento_em_apenas_um_lado_nao_bloqueia(self):
        # Se só uma fonte tem complemento, não pode bloquear — guard só dispara
        # quando AMBOS estão presentes e divergem.
        assert (
            matches_fuzzy(
                "benedito calixto 190",
                "benedito calixto 186",
                complemento_a="34",
                complemento_b=None,
            )
            is True
        )


class TestViaIsolation:
    def test_via_diferente_no_match_zero_delta(self):
        # Vias divergentes — mesmo Δ=0 não pode casar
        assert matches_fuzzy("paulista 100", "berrini 100") is False

    def test_via_diferente_no_match_any_delta(self):
        assert matches_fuzzy("benedito calixto 190", "leonardo da vinci 190") is False


class TestStrongPrefixesReject:
    def test_canonical_mat_does_not_fuzzy_with_via_numero(self):
        # Canonical com prefixo `mat:` é identificador forte — só strict-equal
        assert matches_fuzzy("mat:453527", "benedito calixto 190") is False

    def test_canonical_qa_does_not_fuzzy(self):
        assert matches_fuzzy("qa:894064293", "qa:894064294") is False

    def test_canonical_iptu_does_not_fuzzy(self):
        assert matches_fuzzy("iptu:0870060478", "iptu:0870060479") is False

    def test_both_strong_prefixes_no_match_even_close(self):
        assert matches_fuzzy("mat:1234", "mat:1235") is False


class TestMalformedCanonicalsReject:
    def test_canonical_without_number_no_match(self):
        # Canonical sem número no fim — formato inesperado
        assert matches_fuzzy("benedito calixto", "benedito calixto 190") is False

    def test_empty_string_no_match(self):
        assert matches_fuzzy("", "benedito calixto 190") is False
        assert matches_fuzzy("benedito calixto 190", "") is False

    def test_none_no_match(self):
        assert matches_fuzzy(None, "benedito calixto 190") is False
        assert matches_fuzzy("benedito calixto 190", None) is False
        assert matches_fuzzy(None, None) is False


class TestExtractComplemento:
    def test_extracts_apto(self):
        assert extract_complemento("APARTAMENTO - APTO 34 - PRACA BENEDITO CALIXTO 190") == "34"

    def test_extracts_ap_abreviado(self):
        assert extract_complemento("Apartamento - Praça X, 186 - Ap 34, São Paulo - SP") == "34"

    def test_extracts_unidade(self):
        assert extract_complemento("Conjunto comercial - UNIDADE 1502 - Av Paulista") == "1502"

    def test_extracts_bloco(self):
        assert extract_complemento("Bloco B - Apto X - Rua Y, 100") == "b"

    def test_extracts_torre(self):
        assert extract_complemento("Torre 2 - Av Joao Dias 2192") == "2"

    def test_returns_none_when_no_complemento(self):
        assert extract_complemento("Casa - Rua X, 100") is None

    def test_returns_none_for_empty(self):
        assert extract_complemento("") is None
        assert extract_complemento(None) is None


class TestSymmetry:
    def test_matches_is_symmetric(self):
        # matches_fuzzy(a, b) == matches_fuzzy(b, a) sempre
        assert matches_fuzzy("benedito calixto 190", "benedito calixto 186") == matches_fuzzy(
            "benedito calixto 186", "benedito calixto 190"
        )
        assert matches_fuzzy(
            "paulista 100", "paulista 102", complemento_a="51", complemento_b="34"
        ) == matches_fuzzy("paulista 102", "paulista 100", complemento_a="34", complemento_b="51")

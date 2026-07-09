"""Unit tests for endereco_canonicalizer (ADR-215 P2, ADR-225 §1)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.endereco_canonicalizer import (
    _extract_iptu,
    _extract_matricula,
    _extract_quintoandar,
    canonicalize,
    extract_via_numero,
    normalize,
)


class TestNormalize:
    def test_lowercase_and_strip_accents(self):
        assert normalize("São Paulo") == "sao paulo"

    def test_expands_av_abbreviation(self):
        assert normalize("Av. Paulista") == "avenida paulista"
        assert normalize("AV PAULISTA") == "avenida paulista"

    def test_expands_rua_abbreviation(self):
        assert normalize("R. Exemplo") == "rua exemplo"
        assert normalize("R EXEMPLO") == "rua exemplo"

    def test_removes_apto(self):
        assert "apto" not in normalize("Apto 42 Rua X")
        assert "ap" not in normalize("Ap 42 Rua X").split()

    def test_collapses_whitespace(self):
        assert normalize("rua    A   ") == "rua a"

    def test_returns_empty_for_empty(self):
        assert normalize("") == ""


class TestExtractViaNumero:
    def test_real_case_rua_exemplo(self):
        """Caso real do workspace dogfood 5@5.com (IRPF david_robert)."""
        result = extract_via_numero("CASA - RUA EXEMPLO, 100 - SAO PAULO - SP")
        assert result == ("exemplo", "100")

    def test_real_case_av_exemplo(self):
        result = extract_via_numero("APARTAMENTO NO COND. EXEMPLO A. AV EXEMPLO 320 APTO 812")
        assert result == ("exemplo", "320")

    def test_real_case_avenida_exemplo(self):
        result = extract_via_numero("APARTAMENTO COND EXEMPLO B. AV EXEMPLO 2192 TORRE 2 APT 163")
        assert result == ("exemplo", "2192")

    def test_with_comma_separator(self):
        assert extract_via_numero("Rua Exemplo, 100, SP") == ("exemplo", "100")

    def test_returns_none_without_address(self):
        assert extract_via_numero("APARTAMENTO COND EXEMPLO C APTO 34") is None

    def test_returns_none_for_empty(self):
        assert extract_via_numero("") is None

    def test_handles_accents(self):
        assert extract_via_numero("RUA SÃO PAULO, 500") == ("sao paulo", "500")


class TestCanonicalize:
    def test_canonical_form_combines_via_and_numero(self):
        assert canonicalize("Rua Exemplo, 100") == "exemplo 100"

    def test_returns_none_without_address(self):
        assert canonicalize("APARTAMENTO CYRELA SEM ENDERECO") is None

    def test_idempotent_across_format_variants(self):
        """Mesmo imóvel descrito de 2 jeitos diferentes → mesmo canonical."""
        a = canonicalize("CASA - RUA EXEMPLO, 100 - SP")
        b = canonicalize("Rua Exemplo 100")
        assert a == b == "exemplo 100"

    def test_av_vs_avenida_same_canonical(self):
        assert canonicalize("AV PAULISTA, 1500") == canonicalize("Avenida Paulista 1500")


class TestRegressionB1RealDescriptions:
    """Fixtures reais do workspace 5@5.com — ADR-215 fix-B1."""

    # Antes do fix, "R$ 80.000,00" virava "rua 80 000 00" (porque \br\b
    # matchava o "r" solto) e o regex extraía (via="8", numero="0") /
    # ("4", "77"), gerando endereco_canonical falso.

    def test_casa_modelo_falls_back_to_matricula(self):
        """Pós ADR-225: descrição sem via+numero mas com matrícula → fallback cascade."""
        descricao = (
            "CASA - MODELO 2707, QUADRA 33 LOTE 27, JABAQUARA, "
            "SAO PAULO/SP - Adquirido de CPF 000.000.000-00 em 12/01/2023 - "
            "Valor R$ 80.000,00 - Matrícula 20462"
        )
        assert canonicalize(descricao) == "mat:20462"

    def test_cond_exemplo_b_logradouro_after_currency_blob(self):
        """Descrição com R$ + Logradouro: explícito → canonical da via real."""
        descricao = (
            "APARTAMENTO NO COND. EXEMPLO B. COMPRADO NA PLANTA DA EMPRESA "
            "MAGIKLZ CYRELA ASTURIAS EMPREENDIMENTOS IMOBILIARIOS LTDA CNPJ/MF "
            "SOB O NUMERO 17.102.653/0001-84 COM 88,91 M2. VALOR PAGO: "
            "R$ 477.436,58. Inscrição Municipal (IPTU): 087.006.0478-1. "
            "Logradouro: AVENIDA EXEMPLO Nº 2192, TORRE 2 APT 163, "
            "SANTO AMARO, SÃO PAULO/SP, CEP 04000-000."
        )
        assert canonicalize(descricao) == "exemplo 2192"

    def test_dollar_amount_also_stripped(self):
        """U$$ / U$ em descrição IRPF (moeda estrangeira) também é currency."""
        descricao = "CONTA NO EXTERIOR - U$$ 6524,00 - Banco XYZ"
        assert canonicalize(descricao) is None


class TestCrossIRPFStability:
    """Goldens de paridade: descrição varia ano-a-ano, canonical é estável."""

    @pytest.mark.parametrize(
        "ano_2023,ano_2024",
        [
            (
                "APARTAMENTO COND EXEMPLO A AV EXEMPLO 320 APTO 812",
                "Apartamento Cond. Exemplo A - Av. Exemplo, 320, Apto 812",
            ),
            (
                "CASA RUA EXEMPLO 100",
                "Casa - Rua Exemplo, 100 - São Paulo",
            ),
        ],
    )
    def test_same_property_across_years(self, ano_2023, ano_2024):
        assert canonicalize(ano_2023) == canonicalize(ano_2024)


# =============================================================================
# ADR-225 §1 — cascade signal extractors + cascata ordenada
# =============================================================================


class TestExtractMatricula:
    """Matrícula RFB: ≥4 dígitos pós-normalização (anti-OCR ruim)."""

    def test_extracts_4_digit_matricula(self):
        assert _extract_matricula("Matrícula 3421") == "3421"

    def test_extracts_long_matricula(self):
        assert _extract_matricula("Matrícula 488435") == "488435"

    def test_strips_pontos(self):
        """Matrícula com pontuação ('488.435' ou '12.644') normaliza para dígitos."""
        assert _extract_matricula("Matrícula 12.644") == "12644"

    def test_rejects_short_matricula(self):
        """OCR ruim ('matrícula 12' = página/parágrafo) é rejeitado."""
        assert _extract_matricula("matrícula 12 do livro") is None

    def test_rejects_three_digit(self):
        assert _extract_matricula("Matrícula 999") is None

    def test_no_matricula_returns_none(self):
        assert _extract_matricula("Apartamento sem matrícula identificável") is None

    def test_real_case_5at5_jabaquara(self):
        """Caso real 5@5.com: CASA - MODELO, Matrícula 20462."""
        descricao = (
            "CASA - MODELO 2707, QUADRA 33 LOTE 27, JABAQUARA, "
            "SAO PAULO/SP - Adquirido de CPF 000.000.000-00 em 12/01/2023 - "
            "Valor R$ 80.000,00 - Matrícula 20462"
        )
        assert _extract_matricula(descricao) == "20462"

    def test_case_insensitive(self):
        assert _extract_matricula("MATRICULA 12345") == "12345"
        assert _extract_matricula("matricula 12345") == "12345"


class TestExtractQuintoAndar:
    def test_extracts_qa_code(self):
        descricao = "Apartamento via QuintoAndar: 894064293, Pinheiros"
        assert _extract_quintoandar(descricao) == "894064293"

    def test_extracts_with_cod_prefix(self):
        """Real case: '(Cód. Imóvel QuintoAndar: 893592092)'."""
        descricao = "Apartamento - Rua X, 100 (Cód. Imóvel QuintoAndar: 893592092)"
        assert _extract_quintoandar(descricao) == "893592092"

    def test_no_qa_returns_none(self):
        assert _extract_quintoandar("Apartamento sem código de plataforma") is None


class TestExtractIPTU:
    def test_extracts_iptu_with_pontuation(self):
        """IPTU '087.006.0478-1' → '08700604781' (sem pontos)."""
        assert _extract_iptu("Inscrição Municipal (IPTU): 087.006.0478-1") == "08700604781"

    def test_extracts_iptu_inline(self):
        assert _extract_iptu("IPTU 30105434946") == "30105434946"

    def test_rejects_too_short(self):
        """IPTU com <6 dígitos é provavelmente erro/lixo."""
        assert _extract_iptu("IPTU 12345") is None

    def test_no_iptu_returns_none(self):
        assert _extract_iptu("Apartamento sem inscrição registrada") is None


class TestCanonicalizeCascade:
    """Cascade order: via+numero > matrícula > QA > IPTU (ADR-225 §1)."""

    def test_via_numero_wins_when_present(self):
        """Mesmo com matrícula, via+numero precede (backward-compat)."""
        descricao = "Rua Exemplo, 100 - Matrícula 12345"
        assert canonicalize(descricao) == "exemplo 100"

    def test_matricula_fallback_when_no_via_numero(self):
        """CASE A do problema 5@5.com: descrição sem via+numero mas com matrícula."""
        descricao = (
            "CASA - MODELO 2707, QUADRA 33 LOTE 27, JABAQUARA, " "SAO PAULO/SP - Matrícula 20462"
        )
        assert canonicalize(descricao) == "mat:20462"

    def test_matricula_plain(self):
        """Matrícula sem outras informações → namespace puro."""
        descricao = "Imóvel com Matrícula 99887 - Cartório XXIII"
        assert canonicalize(descricao) == "mat:99887"

    def test_qa_fallback_when_no_via_numero_no_matricula(self):
        descricao = "Imóvel locado via QuintoAndar: 894064293 - sem outras infos"
        assert canonicalize(descricao) == "qa:894064293"

    def test_iptu_fallback(self):
        descricao = "Imóvel - Inscrição Municipal (IPTU): 087.006.0478-1"
        assert canonicalize(descricao) == "iptu:08700604781"

    def test_low_confidence_when_all_fail(self):
        """Sem nenhum sinal extraível: continua None (low_confidence preservado)."""
        descricao = "Apartamento sem nenhuma referência identificável"
        assert canonicalize(descricao) is None

    def test_empty_string_returns_none(self):
        assert canonicalize("") is None

    def test_idempotent_across_years_matricula(self):
        """Mesmo imóvel descrito 2× em IRPFs distintos sem via+numero, com matrícula → mesmo canonical."""
        a = canonicalize("CASA Jabaquara - SAO PAULO/SP - Matrícula 20462")
        b = canonicalize("Casa - Modelo 2707, JABAQUARA, SP - Matrícula 20.462")
        assert a == b == "mat:20462"

    def test_real_case_5at5_cond_exemplo_b_via_wins(self):
        """Quando descrição rica tem AVENIDA + matrícula + IPTU, via+numero vence."""
        descricao = (
            "APARTAMENTO NO COND. EXEMPLO B. "
            "Inscrição Municipal (IPTU): 087.006.0478-1. "
            "Logradouro: AVENIDA EXEMPLO Nº 2192, TORRE 2 APT 163, "
            "SANTO AMARO, SÃO PAULO/SP. Matrícula 453527"
        )
        # via+numero ganha primeiro: "exemplo 2192"
        assert canonicalize(descricao) == "exemplo 2192"

"""Tests — ``MemberNameResolver`` (ADR-243).

Cobre as 6 estratégias de matching + casos de borda (vazio, fora do roster,
substring curta, ambíguo entre 2 membros).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest  # noqa: E402

from pipeline.domain.services.member_name_resolver import (  # noqa: E402
    MemberNameResolution,
    MemberNameResolver,
    MemberRecord,
)

# =============================================================================
# Helpers / fixtures
# =============================================================================


def _family_campos() -> dict:
    """Family config real do workspace observado no bug (ADR-241/242/243)."""
    return {
        "membros": {
            "david_robert_camargo_ferreira_campos": {
                "nome": "David Robert Camargo Ferreira Campos",
                "nome_curto": "David Robert",
                "nome_nascimento": "David Robert Camargo de Campos",
                "papel": "titular",
            },
            "mariana_ferreira_campos": {
                "nome": "Mariana Ferreira Campos",
                "nome_curto": "Mariana",
                "nome_nascimento": "Mariana Teixeira Ferreira",
                "papel": "conjuge",
            },
        },
        "titular": "david_robert_camargo_ferreira_campos",
    }


# =============================================================================
# Strategy: exact match
# =============================================================================


class TestExactMatch:
    def test_exact_key_canonical(self):
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve("david_robert_camargo_ferreira_campos")
        assert result.canonical_key == "david_robert_camargo_ferreira_campos"
        assert result.confidence == "exact"
        assert result.matched_via == "key"

    def test_exact_via_full_name(self):
        """Full name match — quando full_name slugified != key.

        Para o titular, key e full_name slugificam para a mesma string
        (key foi gerada do full_name), então o match é via `key` (mais cedo
        na ordem). Caso interessante: cônjuge tem key=mariana_ferreira_campos
        mas full_name="Mariana Ferreira Campos" — slug bate em ambos via key.
        Para forçar full_name match isolado, usamos um roster sintético.
        """
        resolver = MemberNameResolver(
            [
                MemberRecord(
                    key="cwriter",
                    full_name="Carlos Alberto Esperto",
                    short_name="Carlos",
                ),
            ]
        )
        result = resolver.resolve("Carlos Alberto Esperto")
        assert result.canonical_key == "cwriter"
        assert result.confidence == "full_name"
        assert result.matched_via == "full_name"

    def test_exact_via_short_name(self):
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve("Mariana")
        assert result.canonical_key == "mariana_ferreira_campos"
        assert result.confidence == "short_name"

    def test_exact_via_nome_nascimento(self):
        """Caso real: LLM extrai do informe IR com 'David Robert Camargo de Campos'
        (nome de nascimento), mas a chave canônica usa 'Ferreira Campos'."""
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve("David Robert Camargo de Campos")
        assert result.canonical_key == "david_robert_camargo_ferreira_campos"
        assert result.confidence == "nome_nascimento"


# =============================================================================
# Strategy: substring
# =============================================================================


class TestSubstring:
    def test_short_form_via_short_name(self):
        """LLM emitiu 'david_robert' → match exato via `short_name` ('David Robert')."""
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve("david_robert")
        assert result.canonical_key == "david_robert_camargo_ferreira_campos"
        assert result.confidence == "short_name"

    def test_genuine_substring_match(self):
        """Slug emitido pelo LLM não bate em nenhum campo, mas é substring de uma key."""
        resolver = MemberNameResolver(
            [
                MemberRecord(
                    key="filhote_da_familia_silva",
                    full_name="Filhote da Familia Silva",
                    short_name="Filhote",
                ),
            ]
        )
        # 'filhote_da_familia' é substring de key='filhote_da_familia_silva'.
        result = resolver.resolve("filhote da familia")
        assert result.canonical_key == "filhote_da_familia_silva"
        assert result.confidence == "substring"

    def test_substring_ignores_too_short(self):
        """Substrings curtas (<5 chars) NÃO disparam match para evitar falso positivo."""
        resolver = MemberNameResolver(
            [MemberRecord(key="ana_paula_silva", full_name="Ana Paula Silva")]
        )
        # 'ana' (3 chars) está em 'ana_paula_silva' mas é curto demais.
        result = resolver.resolve("ana")
        assert result.confidence == "unknown"
        assert result.canonical_key is None


# =============================================================================
# Strategy: ambiguous / unknown
# =============================================================================


class TestAmbiguous:
    def test_ambiguous_substring_match(self):
        """'campos' bate em ambos membros via full_name → ambiguous."""
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve("campos")
        # 'campos' tem 6 chars, > MIN_SUBSTRING_LEN, e é substring de ambos.
        assert result.confidence == "ambiguous"
        assert result.canonical_key is None
        assert "david_robert_camargo_ferreira_campos" in result.matched_via
        assert "mariana_ferreira_campos" in result.matched_via


class TestUnknown:
    def test_unknown_name_returns_none(self):
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve("João da Silva Outsider")
        assert result.canonical_key is None
        assert result.confidence == "unknown"

    def test_empty_input_returns_none(self):
        resolver = MemberNameResolver.from_family_config(_family_campos())
        assert resolver.resolve(None).canonical_key is None
        assert resolver.resolve("").canonical_key is None
        assert resolver.resolve("   ").canonical_key is None

    def test_empty_roster(self):
        resolver = MemberNameResolver([])
        result = resolver.resolve("David Robert")
        assert result.canonical_key is None
        assert result.confidence == "unknown"


# =============================================================================
# Construção / from_family_config
# =============================================================================


class TestFromFamilyConfig:
    def test_none_input(self):
        resolver = MemberNameResolver.from_family_config(None)
        assert resolver.resolve("anything").canonical_key is None

    def test_extra_nome_nascimento_via_extra_field(self):
        """Schema futuro pode usar `extra.nome_nascimento` ao invés de top-level."""
        fam = {
            "membros": {
                "k1": {
                    "nome": "K Um",
                    "extra": {"nome_nascimento": "K Original"},
                }
            }
        }
        resolver = MemberNameResolver.from_family_config(fam)
        result = resolver.resolve("K Original")
        assert result.canonical_key == "k1"
        assert result.confidence == "nome_nascimento"


# =============================================================================
# Telemetria
# =============================================================================


def test_resolver_emits_structured_log(caplog):
    import logging

    resolver = MemberNameResolver.from_family_config(_family_campos())
    with caplog.at_level(logging.INFO, logger="mathoms.pipeline.member_name_resolver"):
        resolver.resolve("david_robert")

    records = [
        r for r in caplog.records if r.message == "mathoms.pipeline.member_name_resolver.resolved"
    ]
    assert len(records) == 1
    rec = records[0]
    # 'david_robert' bate exato em short_name='David Robert' do titular.
    assert getattr(rec, "confidence", None) == "short_name"
    assert getattr(rec, "canonical_key", None) == "david_robert_camargo_ferreira_campos"


@pytest.mark.parametrize(
    "raw,expected_key",
    [
        ("david_robert", "david_robert_camargo_ferreira_campos"),
        ("David Robert", "david_robert_camargo_ferreira_campos"),
        ("David Robert Camargo de Campos", "david_robert_camargo_ferreira_campos"),
        ("Mariana Teixeira Ferreira", "mariana_ferreira_campos"),
        ("MARIANA", "mariana_ferreira_campos"),
    ],
)
def test_real_world_llm_variations(raw, expected_key):
    """Variações observadas em artifacts E2-llm reais (workspace Campos)."""
    resolver = MemberNameResolver.from_family_config(_family_campos())
    assert resolver.resolve(raw).canonical_key == expected_key


# =============================================================================
# ADR-267 — Strategy 0: CPF (identidade primária)
# =============================================================================

# CPFs gerados por `tests.utils.cpf.cpf_formatted(seed)` — determinísticos,
# mod-11 válidos, LGPD-safe. Anotamos com `# noqa: PII-ok` por convenção
# do lint anti-PII (F6.5D.7).
from tests.utils.cpf import cpf_formatted  # noqa: E402, I001

_CPF_DAVID = cpf_formatted(seed=42)  # noqa: PII-ok
_CPF_MARIANA = cpf_formatted(seed=84)  # noqa: PII-ok
_CPF_OUTSIDER = cpf_formatted(seed=999)  # noqa: PII-ok


def _family_campos_with_cpf() -> dict:
    """Family config com CPF — base para testes ADR-267 (CPFs sintéticos)."""
    return {
        "membros": {
            "david_robert_camargo_ferreira_campos": {
                "nome": "David Robert Camargo Ferreira Campos",
                "nome_curto": "David Robert",
                "cpf": _CPF_DAVID,  # mascarado (cpf_formatted retorna com pontos)
                "papel": "titular",
            },
            "mariana_ferreira_campos": {
                "nome": "Mariana Ferreira Campos",
                "nome_curto": "Mariana",
                "nome_nascimento": "Mariana Teixeira Ferreira",
                "cpf": _CPF_MARIANA.replace(".", "").replace("-", ""),  # sem máscara
                "papel": "conjuge",
            },
        },
        "titular": "david_robert_camargo_ferreira_campos",
    }


class TestResolveByCpf:
    def test_cpf_match_masked(self):
        """ADR-267 — CPF mascarado bate via normalização."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        result = resolver.resolve_by_cpf(_CPF_DAVID)
        assert result.canonical_key == "david_robert_camargo_ferreira_campos"
        assert result.confidence == "cpf"
        assert result.matched_via == "cpf"

    def test_cpf_match_unmasked(self):
        """CPF sem máscara bate igualmente — normalize_cpf strippa não-dígitos."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        unmasked = _CPF_DAVID.replace(".", "").replace("-", "")
        result = resolver.resolve_by_cpf(unmasked)
        assert result.canonical_key == "david_robert_camargo_ferreira_campos"
        assert result.confidence == "cpf"

    def test_cpf_match_cross_surname(self):
        """CRÍTICO ADR-267 §Bug — IRPF antigo da Mariana traz CPF + sobrenome solteira.
        CPF resolve corretamente independente do nome variante.
        Workspace 1b9f2cf5 (founder dogfood) — bug R$ 811k.
        """
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        # IRPF antigo emite contribuinte.cpf=<CPF Mariana> mas
        # contribuinte.nome="MARIANA TEIXEIRA FERREIRA" (solteira).
        # Resolver por nome cairia em nome_nascimento (estratégia 4) por sorte,
        # mas resolver por CPF é determinístico e imutável.
        result = resolver.resolve_by_cpf(_CPF_MARIANA)
        assert result.canonical_key == "mariana_ferreira_campos"
        assert result.confidence == "cpf"

    def test_cpf_invalid_short(self):
        """CPF com <11 dígitos é inválido — retorna unknown (não match)."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        result = resolver.resolve_by_cpf("12345")
        assert result.canonical_key is None
        assert result.confidence == "unknown"
        assert result.matched_via == "cpf:invalid"

    def test_cnpj_14_digits_rejected(self):
        """CNPJ (14 dígitos) é rejeitado pelo normalize_cpf — não vira CPF parcial."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        result = resolver.resolve_by_cpf("12.345.678/0001-99")
        assert result.canonical_key is None
        assert result.confidence == "unknown"
        assert result.matched_via == "cpf:invalid"

    def test_cpf_not_in_roster(self):
        """CPF válido mas não no family_members → unknown com matched_via='cpf:miss'."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        result = resolver.resolve_by_cpf(_CPF_OUTSIDER)
        assert result.canonical_key is None
        assert result.confidence == "unknown"
        assert result.matched_via == "cpf:miss"

    def test_cpf_empty(self):
        """CPF vazio/None → unknown."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        assert resolver.resolve_by_cpf("").confidence == "unknown"
        assert resolver.resolve_by_cpf(None).confidence == "unknown"

    def test_family_without_cpf_falls_back(self):
        """Workspace sem CPF em family_members → resolve_by_cpf retorna unknown,
        caller cai no resolve(nome) fallback. Backwards compat preservada."""
        # _family_campos() não tem CPF — usa o fixture original sem cpf field.
        resolver = MemberNameResolver.from_family_config(_family_campos())
        result = resolver.resolve_by_cpf(_CPF_DAVID)
        assert result.canonical_key is None
        assert result.confidence == "unknown"
        assert result.matched_via == "cpf:miss"
        # Mas resolve(nome) ainda funciona — fallback.
        assert (
            resolver.resolve("David Robert").canonical_key == "david_robert_camargo_ferreira_campos"
        )

    def test_cpf_confidence_emits_telemetry(self, caplog):
        """ADR-267 — matched_via='cpf' no log estruturado para drift detection."""
        import logging

        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())
        with caplog.at_level(logging.INFO, logger="mathoms.pipeline.member_name_resolver"):
            resolver.resolve_by_cpf(_CPF_DAVID)

        records = [
            r
            for r in caplog.records
            if r.message == "mathoms.pipeline.member_name_resolver.resolved"
        ]
        assert len(records) == 1
        assert getattr(records[0], "confidence", None) == "cpf"
        assert getattr(records[0], "matched_via", None) == "cpf"


class TestCpfStrategyPrioritization:
    """Garante que CPF é estratégia 0 (mais forte que name strategies) na cascata
    de uso pelo caller — embora `resolve_by_cpf` e `resolve` sejam métodos
    separados, a confidence enum `'cpf'` está no topo da hierarquia."""

    def test_cpf_confidence_in_enum(self):
        """Confidence literal aceita 'cpf' (validado por type checking)."""
        # MemberNameResolution(canonical_key=..., confidence="cpf") deve construir sem erro.
        res = MemberNameResolution(canonical_key="x", confidence="cpf", matched_via="cpf")
        assert res.confidence == "cpf"

    def test_caller_cascade_cpf_then_name(self):
        """Pattern recomendado de uso pelo consumer (consolidate_from_itens etc.)."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())

        # Item do IRPF tem CPF + nome — resolver tenta CPF primeiro.
        cpf = _CPF_MARIANA
        nome = "MARIANA TEIXEIRA FERREIRA"

        resolution = resolver.resolve_by_cpf(cpf)
        if resolution.canonical_key is None:
            resolution = resolver.resolve(nome)
        assert resolution.canonical_key == "mariana_ferreira_campos"
        assert resolution.confidence == "cpf"  # CPF venceu, fallback não disparou.

    def test_caller_cascade_no_cpf_falls_to_name(self):
        """Item sem CPF (extratos antigos, baseline manual) → cai no name resolver."""
        resolver = MemberNameResolver.from_family_config(_family_campos_with_cpf())

        cpf = None
        nome = "MARIANA TEIXEIRA FERREIRA"

        resolution = resolver.resolve_by_cpf(cpf) if cpf else None
        if not resolution or resolution.canonical_key is None:
            resolution = resolver.resolve(nome)
        # nome_nascimento bate "Mariana Teixeira Ferreira" → canonical_key correto.
        assert resolution.canonical_key == "mariana_ferreira_campos"
        assert resolution.confidence == "nome_nascimento"  # fallback disparou.

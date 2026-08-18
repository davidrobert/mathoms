"""Testes unitários — regras dormentes Onda 8 (W1-T02 · FP-001/2/3) + carry-trade (W1-T07 · FP-009)."""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

import pipeline.domain.services.suggestion_rules as suggestion_rules_module
from pipeline.domain.services.suggestion_config import SuggestionGeneratorConfig
from pipeline.domain.services.suggestion_generator import SuggestionGenerator
from pipeline.domain.services.suggestion_rules import (
    ALL_RULES,
    CARRY_TRADE_MARGIN_PP,
    rule_endividamento_perigoso,
    rule_renda_passiva_real_baixa,
)
from pipeline.domain.types.suggestion import (
    KIND_TO_CATEGORY,
    VALID_KINDS,
    VALID_SECTION_IDS,
    SuggestionDraft,
)

_REPO = Path(__file__).resolve().parents[3]
_LAYOUT_YAML = _REPO / "config" / "report_layout.yaml"
_PARECER_SCHEMA = _REPO / "config" / "schemas" / "parecer_planejador.schema.json"


@pytest.fixture
def gen() -> SuggestionGenerator:
    return SuggestionGenerator(SuggestionGeneratorConfig())


@pytest.fixture
def cfg() -> SuggestionGeneratorConfig:
    return SuggestionGeneratorConfig()


# =============================================================================
# FP-001 — rule_renda_passiva_real_baixa alias defensivo
# =============================================================================


class TestRendaPassivaAlias:
    def test_dispara_com_if_pct_alias(self, cfg):
        """Real snapshot expõe `if_pct` (não `progresso_if_pct`)."""
        snapshot = {
            "goals": {"if_pct": 55.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 4_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        draft = rule_renda_passiva_real_baixa(snapshot, cfg)
        assert draft is not None
        assert draft.kind == "renda_passiva_real_baixa"
        assert draft.section_id == "S7"
        assert ", mas a renda" in draft.rationale
        assert "R$ 4.000" in draft.rationale

    def test_dispara_com_progresso_if_pct_legado(self, cfg):
        """Backwards-compat: snapshot com `progresso_if_pct` ainda funciona."""
        snapshot = {
            "goals": {"progresso_if_pct": 55.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 4_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        draft = rule_renda_passiva_real_baixa(snapshot, cfg)
        assert draft is not None

    def test_renda_passiva_alias_observada_brl(self, cfg):
        """Snapshot real expõe `goals.renda_passiva_mensal_observada_brl`."""
        snapshot = {
            "goals": {
                "if_pct": 55.0,
                "renda_passiva_mensal_observada_brl": 4_000.0,
            },
            "fluxo_caixa": {
                "despesa_mensal_media": 20_000.0,
                # Sem renda_passiva_mensal_atual — só observada_brl em goals.
            },
        }
        draft = rule_renda_passiva_real_baixa(snapshot, cfg)
        assert draft is not None

    def test_silencia_com_if_pct_baixo(self, cfg):
        snapshot = {
            "goals": {"if_pct": 30.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 1_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        assert rule_renda_passiva_real_baixa(snapshot, cfg) is None

    def test_silencia_quando_nada_disponivel(self, cfg):
        assert rule_renda_passiva_real_baixa({}, cfg) is None


# =============================================================================
# FP-003 — rule_dolarizacao_atrasada removida
# =============================================================================


class TestDolarizacaoAtrasadaRemovida:
    def test_funcao_nao_existe(self):
        rule_names = {r.__name__ for r in ALL_RULES}
        assert "rule_dolarizacao_atrasada" not in rule_names

    def test_kind_nao_em_kind_to_category(self):
        assert "dolarizacao_atrasada" not in KIND_TO_CATEGORY

    def test_kind_nao_em_valid_kinds(self):
        assert "dolarizacao_atrasada" not in VALID_KINDS

    def test_snapshot_com_dolarizacao_silencia(self, gen):
        snapshot = {"dolarizacao": {"cobertura_pct": 0.0, "meta_pct": 50.0}}
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "dolarizacao_atrasada" not in kinds


# =============================================================================
# FP-009 — carry-trade endividamento
# =============================================================================


class TestCarryTradeEndividamento:
    def test_dispara_quando_custo_supera_retorno_mais_margem(self, cfg):
        """Cerbasi — dívida 25%a.a. + retorno 12%a.a. → carry-trade dispara."""
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,  # baixo (não dispara por %)
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 25.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        draft = rule_endividamento_perigoso(snapshot, cfg)
        assert draft is not None
        assert draft.severity == "danger"
        assert draft.kind == "endividamento_perigoso"
        # Rationale menciona o conceito de carry-trade ou retorno esperado.
        assert "retorno esperado" in draft.rationale.lower()

    def test_silencia_quando_retorno_supera_custo(self, cfg):
        """Inverso: dívida 8%a.a. + retorno 12%a.a. → carry-trade NÃO dispara."""
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 8.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        assert rule_endividamento_perigoso(snapshot, cfg) is None

    def test_silencia_dentro_da_margem(self, cfg):
        """Custo dentro da margem (retorno + 1pp) não dispara."""
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,
                "total_dividas": 30_000.0,
                # 12.5 < 12 + 1 = 13.0 → dentro da margem, não dispara.
                "custo_medio_pct_aa": 12.5,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        assert rule_endividamento_perigoso(snapshot, cfg) is None

    def test_carry_margin_constant_documentada(self):
        """Constante nomeada com valor explícito (Cerbasi · Equilíbrio)."""
        assert CARRY_TRADE_MARGIN_PP == 1.0


# =============================================================================
# E2E (smoke) — todos os 4 cenários do prompt em sequência
# =============================================================================


class TestE2ECenariosFundamentais:
    """4 cenários cobertos: renda passiva alta, IF crescendo,
    dívida cara (carry-trade) e dívida barata (não dispara)."""

    def test_cenario_renda_passiva_alta_dispara(self, gen):
        snapshot = {
            "goals": {"if_pct": 55.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 4_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "renda_passiva_real_baixa" in kinds

    def test_cenario_if_crescendo_pontos_fortes_via_adapter(self):
        """Pontos fortes acessível via PontosFortesAnalyzer com goals.if_pct."""
        from pipeline.domain.services.pontos_fortes_analyzer import PontosFortesAnalyzer

        analyzer = PontosFortesAnalyzer()
        out = analyzer.analyze(
            score={"valor": 7.0, "classificacao": "Bom"},
            ratios={},
            patrimonio={},
            fluxo={},
            reserva={},
            goals={"if_pct": 25.0},
        )
        titulos = {p.titulo for p in out}
        assert "Caminho para Independência Financeira" in titulos

    def test_cenario_divida_cara_carry_trade(self, gen):
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 25.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "endividamento_perigoso" in kinds

    def test_cenario_divida_barata_nao_dispara_por_carry(self, gen):
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 10.0,  # também baixo
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 8.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "endividamento_perigoso" not in kinds


# =============================================================================
# Gate de vocabulário de `section_id` — 3 camadas, uma asserção cada
#
# Caso de origem: `rule_seguros_insuficientes` emitia "S6", ID queimado por
# design (report_layout.yaml §NOTA, pós-ADR-168 que removeu o modo USA que os
# ocupava). Efeito medido: âncora morta em `SuggestionCallout` ("Ver em
# contexto · §S6") e no backlink `/reports/{id}#S6` de `/acao`.
#
# O que cada camada cobre:
#   1. `SuggestionDraft.__post_init__` (runtime) — todo produtor executado,
#      presente e futuro. Impede em vez de detectar.
#   2. varredura AST desta suíte — regra nova cujo happy-path nenhum teste
#      exercita (o construtor não roda, logo a camada 1 fica cega).
#   3. drift `VALID_SECTION_IDS` ↔ layout ↔ enum do parecer — a cópia à mão
#      no domínio (que existe porque domínio não faz I/O, ADR-089).
#
# Limite honesto: seção `enabled: true` ainda pode curto-circuitar em
# <EmptyState/> (a S9 tem `summary_suppressed_by`, ADR-356 §D6). Verde aqui
# significa "âncora existe", não "âncora é informativa".
# =============================================================================


def _enabled_layout_section_ids() -> frozenset[str]:
    """Seções habilitadas de §estrategico.sections (apêndices são outra lista)."""
    layout = yaml.safe_load(_LAYOUT_YAML.read_text(encoding="utf-8"))
    return frozenset(s["id"] for s in layout["estrategico"]["sections"] if s.get("enabled"))


def _parecer_schema_section_enum() -> frozenset[str]:
    schema = json.loads(_PARECER_SCHEMA.read_text(encoding="utf-8"))
    return frozenset(schema["$defs"]["section_id"]["enum"])


def _section_id_keywords(source: str) -> Iterator[ast.keyword]:
    calls = (n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call))
    for call in calls:
        yield from (kw for kw in call.keywords if kw.arg == "section_id")


def _emitted_section_id_literals() -> list[str]:
    source = Path(suggestion_rules_module.__file__).read_text(encoding="utf-8")
    literals: list[str] = []
    for kw in _section_id_keywords(source):
        if not (isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)):
            pytest.fail(
                f"section_id não-literal na linha {kw.value.lineno} de "
                "suggestion_rules.py — o gate de vocabulário exige literal string"
            )
        literals.append(kw.value.value)
    return literals


class TestSectionIdVocabulary:
    def test_construtor_rejeita_secao_fora_do_vocabulario(self):
        with pytest.raises(ValueError, match="section_id inválido"):
            SuggestionDraft(
                section_id="S6",
                kind="seguros_insuficientes",
                severity="danger",
                title="t",
                rationale="r",
                dedup_key="abcd1234",
            )

    def test_toda_regra_emite_section_id_do_vocabulario(self):
        literals = _emitted_section_id_literals()
        # Anti-vacuidade: cada regra emite exatamente 1 draft com section_id
        # keyword-literal. Divergência = emissão positional/dinâmica que este
        # gate não enxerga — falhe alto em vez de passar vazio.
        assert len(literals) == len(ALL_RULES), (
            f"esperava {len(ALL_RULES)} emissões literais de section_id "
            f"(1 por regra em ALL_RULES), encontrei {len(literals)}"
        )
        orfaos = sorted(set(literals) - VALID_SECTION_IDS)
        assert not orfaos, f"section_id fora do vocabulário: {orfaos}"

    def test_vocabulario_do_dominio_nao_deriva_do_layout(self):
        """Cópia à mão em `types/suggestion.py` ↔ seções habilitadas do YAML."""
        assert VALID_SECTION_IDS == _enabled_layout_section_ids()

    def test_vocabulario_do_dominio_bate_com_enum_do_parecer(self):
        """Mesmo vocabulário na superfície LLM (ADR-200) — âncora é a mesma."""
        assert VALID_SECTION_IDS == _parecer_schema_section_enum()

    def test_ids_queimados_nunca_voltam(self):
        """S5/S6 reservados por design — reciclar quebra âncora histórica."""
        assert not VALID_SECTION_IDS & {"S5", "S6"}

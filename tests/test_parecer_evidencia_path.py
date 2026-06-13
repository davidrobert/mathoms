"""Golden estrutural da citação verificada E5→E6 — evidencia_path F4 (ADR-279 §E).

Estende o harness de tests/test_parecer_planejador_golden.py (LLM mockado);
vive em módulo próprio para respeitar o limite de 500 linhas por arquivo.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from pipeline.llm.schemas.parecer_planejador import Risco
from tests.test_parecer_planejador_golden import (
    make_canned_output,
    make_run_stage_with_mocks,
    make_workspace_e5,
)

_REPO = Path(__file__).resolve().parents[1]
_OUTPUT_SCHEMA = _REPO / "config" / "schemas" / "parecer_planejador.schema.json"

# Baseline do SYSTEM_PROMPT_TEMPLATE (chars; aproximação tokens = len//4).
# 4664 pré-F4 (ADR-279) → 5411 em 1.4.0 (regras 12-13, ADR-290 F2) → 5846 em
# 1.5.0 (limites de concisão na regra 4, incidente string_too_long 2026-06-12).
_PROMPT_BASELINE_CHARS = 5846


def _risco(descricao: str, path: str | None) -> Risco:
    return Risco(
        severidade="Alta",
        titulo="Risco sintético para verificação de citação",
        descricao=descricao,
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        section_id="S1",
        confianca="alta",
        evidencia_path=path,
    )


def _run_with_risco(descricao: str, path: str | None, workspace_id: str = "ws-evid"):
    canned = make_canned_output().model_copy(update={"riscos": [_risco(descricao, path)]})
    return make_run_stage_with_mocks(make_workspace_e5(), canned, workspace_id=workspace_id)


def _risco_entries(store) -> list[dict]:
    artifact = store.read("E6-parecer", "parecer_planejador")
    entries = artifact["_meta"]["evidencia_verification"]
    return [e for e in entries if e["item_type"] == "risco"]


# -----------------------------------------------------------------------
# Negative cases — modo strict → needs_review
# -----------------------------------------------------------------------


class TestStrictModeNegatives:
    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PARECER_EVIDENCIA_MODE", "strict")

    def test_path_fora_da_whitelist_whitelist_miss(self):
        result, store = _run_with_risco(
            "Reserva líquida de R$ 84.000 é insuficiente.", "$.secao_inexistente.campo"
        )
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified: risco:0:whitelist_miss"
        assert _risco_entries(store)[0]["outcome"] == "whitelist_miss"

    def test_path_nao_resolve_resolve_null(self):
        result, store = _run_with_risco(
            "Reserva líquida de R$ 84.000 é insuficiente.",
            "$.reserva_emergencia.campo_inexistente",
        )
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified: risco:0:resolve_null"
        assert _risco_entries(store)[0]["outcome"] == "resolve_null"

    def test_numero_diferente_do_valor_value_mismatch(self):
        result, store = _run_with_risco(
            "Reserva líquida de R$ 99.999,99 é insuficiente.",
            "$.reserva_emergencia.total_liquida",
        )
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified: risco:0:value_mismatch"
        assert _risco_entries(store)[0]["outcome"] == "value_mismatch"

    def test_prosa_monetaria_sem_path_missing_path(self):
        result, store = _run_with_risco("Reserva líquida de R$ 84.000 é insuficiente.", None)
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified: risco:0:missing_path"
        assert _risco_entries(store)[0]["outcome"] == "missing_path"

    def test_path_resolve_para_valor_errado_value_mismatch(self):
        result, store = _run_with_risco(
            "Reserva líquida de R$ 84.000 é insuficiente.", "$.patrimonio.bruto"
        )
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified: risco:0:value_mismatch"
        assert _risco_entries(store)[0]["outcome"] == "value_mismatch"

    def test_needs_review_telemetry_aggregate(self):
        result, _ = _run_with_risco("Reserva líquida de R$ 84.000 é insuficiente.", None)
        agg = result["evidencia_verification"]
        assert agg["evidencia_failed"] == 1
        assert agg["failures_by_layer"]["missing_path"] == 1
        assert agg["needs_review_triggered"] is True


# -----------------------------------------------------------------------
# Modo warn (default) — violação loga + telemetria, status normal
# -----------------------------------------------------------------------


class TestWarnModeDefault:
    def test_violation_does_not_block_in_warn(self, monkeypatch):
        monkeypatch.delenv("MATHOMS_PARECER_EVIDENCIA_MODE", raising=False)
        result, store = _run_with_risco("Reserva líquida de R$ 84.000 é insuficiente.", None)
        assert result["success"] is True
        agg = result["evidencia_verification"]
        assert agg["evidencia_failed"] == 1
        assert agg["failures_by_layer"]["missing_path"] == 1
        assert agg["needs_review_triggered"] is False
        assert _risco_entries(store)[0]["outcome"] == "missing_path"

    def test_artifact_with_meta_block_validates_against_json_schema(self, monkeypatch):
        monkeypatch.delenv("MATHOMS_PARECER_EVIDENCIA_MODE", raising=False)
        _, store = _run_with_risco("Reserva líquida de R$ 84.000 é insuficiente.", None)
        artifact = store.read("E6-parecer", "parecer_planejador")
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(_OUTPUT_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(artifact, schema)


# -----------------------------------------------------------------------
# Positive cases — modo strict não produz falso positivo
# -----------------------------------------------------------------------


class TestStrictModePositives:
    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PARECER_EVIDENCIA_MODE", "strict")

    def test_match_exato_em_cents(self):
        result, store = _run_with_risco(
            "Reserva total líquida de R$ 84.000 cobre poucos meses.",
            "$.reserva_emergencia.total_liquida",
        )
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"

    def test_match_abreviado_meia_casa_significativa(self):
        result, store = _run_with_risco(
            "Residência avaliada em R$ 1,8 mi concentra o patrimônio.",
            "$.patrimonio.composicao.imoveis_residencia",
        )
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"

    def test_neutro_sem_token_monetario_sem_path_passa(self):
        result, store = _run_with_risco(
            "Cobertura de 2,1 meses está abaixo do alvo de 6 meses (25× despesas).", None
        )
        assert result["success"] is True
        assert _risco_entries(store) == []

    def test_dois_numeros_um_casa_passa(self):
        result, store = _run_with_risco(
            "Reserva entre R$ 10.000 e R$ 84.000 fica aquém do necessário.",
            "$.reserva_emergencia.total_liquida",
        )
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"


# -----------------------------------------------------------------------
# Valor determinístico (ADR-290 F2) — faixa inventada em campo escalar
# bloqueia; faixa legítima (Monte Carlo/cenários/projeções) é suprimida.
# Eval golden determinístico do KR2; o ≥98% de match é gate operacional
# medido em runs reais via telemetria (money_tokens_total / value_mismatch).
# -----------------------------------------------------------------------


class TestValorDeterministicoF2:
    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PARECER_EVIDENCIA_MODE", "strict")

    def test_faixa_inventada_em_campo_escalar_bloqueia(self):
        result, store = _run_with_risco(
            "Recomendamos reserva entre R$ 250-300 mil para a família.",
            "$.reserva_emergencia.total_liquida",
        )
        assert result["status"] == "needs_review"
        assert _risco_entries(store)[0]["outcome"] == "value_mismatch"
        agg = result["evidencia_verification"]
        assert agg["range_in_scalar_count"] == 1

    def test_faixa_legitima_monte_carlo_suprimida(self):
        result, store = _run_with_risco(
            "Projeção indica patrimônio entre R$ 4,0 mi a R$ 6,5 mi no percentil 90.",
            "$.if_monte_carlo.prazo_p50",
        )
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"
        assert result["evidencia_verification"]["range_in_scalar_count"] == 0

    def test_match_exato_conta_tokens_na_telemetria(self):
        result, _ = _run_with_risco(
            "Reserva total líquida de R$ 84.000 cobre poucos meses.",
            "$.reserva_emergencia.total_liquida",
        )
        assert result["success"] is True
        agg = result["evidencia_verification"]
        assert agg["money_tokens_total"] >= 1
        assert agg["range_in_scalar_count"] == 0
        assert agg["prompt_version"] == "1.5.0"


# -----------------------------------------------------------------------
# Extração de tokens monetários — regex ancorada em R$
# -----------------------------------------------------------------------


class TestMoneyTokenExtraction:
    def test_non_monetary_numbers_are_ignored(self):
        from backend.app.services.parecer_evidencia import _extract_money_tokens

        prose = "Cobertura de 2,1 meses, 44,7% da renda, meta 25× até 2030 em 6 meses."
        assert _extract_money_tokens([prose]) == []

    def test_abbreviated_interval_semantics(self):
        from backend.app.services.parecer_evidencia import _extract_money_tokens, _token_matches

        token = _extract_money_tokens(["R$ 1,2 mi"])[0]
        assert _token_matches(token, 115_000_000)  # R$ 1.150.000,00 inclusivo
        assert _token_matches(token, 124_999_999)
        assert not _token_matches(token, 125_000_000)  # limite superior exclusivo

    def test_mil_multiplier_half_step(self):
        from backend.app.services.parecer_evidencia import _extract_money_tokens, _token_matches

        token = _extract_money_tokens(["R$ 800 mil"])[0]
        assert _token_matches(token, 80_000_000)
        assert _token_matches(token, 79_950_000)
        assert not _token_matches(token, 80_050_000)

    def test_exact_cents_precision(self):
        from backend.app.services.parecer_evidencia import _extract_money_tokens

        token = _extract_money_tokens(["R$ 1.234,56"])[0]
        assert token.cents == 123_456
        assert token.half_step_cents == 0


# -----------------------------------------------------------------------
# Paridade dos regex JSONPath (drill-down / Pydantic / $defs do JSON Schema)
# -----------------------------------------------------------------------

_PARITY_PATHS = [
    ("$.a", True),
    ("$.reserva_emergencia.total_liquida", True),
    ("$.investimentos.tabela_classes[*]", True),
    ("$.investimentos.tabela_classes[0].valor", True),
    ("$.a_b.c1", True),
    ("$", False),
    ("$.", False),
    ("a.b", False),
    ("$.1abc", False),
    ("$.a[?(@.x)]", False),
    ("$.a b", False),
]


class TestJsonPathRegexParity:
    def test_python_regexes_identical(self):
        from pipeline.llm.schemas.parecer_planejador import _JSONPATH_RE as schema_re
        from pipeline.llm.tools.planner_drill_down import _JSONPATH_RE as drill_re

        assert drill_re.pattern == schema_re.pattern
        for path, expected in _PARITY_PATHS:
            assert bool(drill_re.match(path)) == expected, f"drill regex divergiu em {path!r}"
            assert bool(schema_re.match(path)) == expected, f"schema regex divergiu em {path!r}"

    def test_json_schema_defs_is_coarse_superset(self):
        """$defs/evidencia_path é sanidade grosseira: aceita tudo que os regex
        Python aceitam (superset), mas não rejeita tudo que eles rejeitam
        (ex.: '$..a') — a paridade exata fica nos dois regex Python."""
        schema = json.loads(_OUTPUT_SCHEMA.read_text(encoding="utf-8"))
        defs_re = re.compile(schema["$defs"]["evidencia_path"]["pattern"])
        for path, expected in _PARITY_PATHS:
            if expected:
                assert defs_re.match(path), f"$defs rejeitou path válido {path!r}"


# -----------------------------------------------------------------------
# Cache key — bump de verification_version invalida caches pré-F4
# -----------------------------------------------------------------------


class TestCacheKeyBump:
    def test_post_bump_key_differs_from_pre_f4_key(self):
        from backend.app.services.parecer_orchestrator import compute_cache_key

        e5 = make_workspace_e5()
        kwargs = dict(
            e5_data=e5,
            manifest_version="1.3",
            schema_version="1.0",
            model_id="anthropic/claude-sonnet-4-20250514",
            workspace_id="ws-cache",
        )
        new_key = compute_cache_key(**kwargs)
        e5_raw = json.dumps(e5, sort_keys=True, ensure_ascii=False, default=str)
        e5_hash = hashlib.sha256(e5_raw.encode("utf-8")).hexdigest()[:16]
        pre_f4_composite = "ws-cache:{}:1.3:1.0:anthropic/claude-sonnet-4-20250514".format(e5_hash)
        pre_f4_digest = hashlib.sha256(pre_f4_composite.encode("utf-8")).hexdigest()
        pre_f4_key = f"mathoms:llm:parecer_planejador:{pre_f4_digest}"
        assert new_key != pre_f4_key


# -----------------------------------------------------------------------
# Prompt — instrução additive cabe no budget de tokens
# -----------------------------------------------------------------------


class TestPromptTokenBudget:
    def test_system_prompt_token_delta_under_5_percent(self):
        from pipeline.llm.prompts.parecer_planejador import PROMPT_VERSION, SYSTEM_PROMPT_TEMPLATE

        baseline_tokens = _PROMPT_BASELINE_CHARS // 4
        current_tokens = len(SYSTEM_PROMPT_TEMPLATE) // 4
        delta = abs(current_tokens - baseline_tokens) / baseline_tokens
        assert delta < 0.05, f"delta de tokens {delta:.2%} excede 5% (F4)"
        assert PROMPT_VERSION == "1.5.0"

    def test_regras_valor_deterministico_presentes(self):
        """ADR-290 F2 — regras 12 (passthrough escalar) e 13 (cap de geração)."""
        from pipeline.llm.prompts.parecer_planejador import SYSTEM_PROMPT_TEMPLATE

        assert "Valor escalar é passthrough" in SYSTEM_PROMPT_TEMPLATE
        assert "Priorize, não preencha" in SYSTEM_PROMPT_TEMPLATE
        assert "máximo 3 sugestões" in SYSTEM_PROMPT_TEMPLATE

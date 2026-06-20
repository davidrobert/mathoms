"""Golden estrutural da citação determinística E5→E6 — ancoras (ADR-296, supersede F4).

Estende o harness de tests/test_parecer_planejador_golden.py (LLM mockado);
vive em módulo próprio para respeitar o limite de 500 linhas por arquivo.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from pipeline.llm.schemas.parecer_planejador import Ancora, Risco
from tests.test_parecer_planejador_golden import (
    make_canned_output,
    make_run_stage_with_mocks,
    make_workspace_e5,
)

_REPO = Path(__file__).resolve().parents[1]
_OUTPUT_SCHEMA = _REPO / "config" / "schemas" / "parecer_planejador.schema.json"

# Baseline do SYSTEM_PROMPT_TEMPLATE (chars; aproximação tokens = len//4). O template
# wrapper não carrega as regras (vêm do manifest YAML); ADR-296 mudou as regras no
# YAML, não o template — delta ~0. Bump só de PROMPT_VERSION (1.9.0 → 2.0.0).
_PROMPT_BASELINE_CHARS = 8571


def _risco(ancoras: list[tuple[str | None, str | None]], severidade: str = "Alta") -> Risco:
    """Risco sintético com âncoras (path, rotulo); prosa SEM R$ (ADR-296)."""
    return Risco(
        severidade=severidade,
        titulo="Risco sintético para verificação de citação",
        descricao="Reserva insuficiente para cobrir as despesas essenciais da família.",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        section_id="S1",
        confianca="alta",
        ancoras=[Ancora(path=p, rotulo=r) for p, r in ancoras],
    )


def _run(
    ancoras: list[tuple[str | None, str | None]],
    workspace_id: str = "ws-evid",
    severidade: str = "Alta",
):
    canned = make_canned_output().model_copy(update={"riscos": [_risco(ancoras, severidade)]})
    return make_run_stage_with_mocks(make_workspace_e5(), canned, workspace_id=workspace_id)


def _risco_entries(store) -> list[dict]:
    artifact = store.read("E6-parecer", "parecer_planejador")
    entries = artifact["_meta"]["evidencia_verification"]
    return [e for e in entries if e["item_type"] == "risco"]


# Paths/rótulos canônicos do E5 sintético (root == 1º segmento do path).
_RESERVA = ("$.reserva_emergencia.total_liquida", "reserva_emergencia")
_IMOVEL = ("$.patrimonio.composicao.imoveis_residencia", "patrimonio")


# -----------------------------------------------------------------------
# Strict — item SEVERIDADE ALTA com citação hard inválida → needs_review (ADR-295)
# -----------------------------------------------------------------------


class TestStrictModeNegatives:
    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PARECER_EVIDENCIA_MODE", "strict")

    def test_path_fora_da_whitelist_whitelist_miss(self):
        result, store = _run([("$.secao_inexistente.campo", "secao_inexistente")])
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified (severidade alta): risco:0"
        assert _risco_entries(store)[0]["outcome"] == "whitelist_miss"

    def test_path_nao_resolve_resolve_null(self):
        result, store = _run([("$.reserva_emergencia.campo_inexistente", "reserva_emergencia")])
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified (severidade alta): risco:0"
        assert _risco_entries(store)[0]["outcome"] == "resolve_null"

    def test_rotulo_incoerente_com_root_pairing_mismatch(self):
        """ADR-296: path resolve mas rotulo aponta seção errada → pairing_mismatch."""
        result, store = _run([("$.reserva_emergencia.total_liquida", "patrimonio")])
        assert result["status"] == "needs_review"
        assert result["reason"] == "evidencia unverified (severidade alta): risco:0"
        assert _risco_entries(store)[0]["outcome"] == "pairing_mismatch"

    def test_rotulo_none_com_path_valido_pairing_mismatch(self):
        """rotulo coercido a None (forma inválida) com path válido → pairing_mismatch."""
        result, store = _run([("$.reserva_emergencia.total_liquida", "tem espaço")])
        assert result["status"] == "needs_review"
        assert _risco_entries(store)[0]["outcome"] == "pairing_mismatch"

    def test_needs_review_telemetry_aggregate(self):
        result, _ = _run([("$.reserva_emergencia.total_liquida", "patrimonio")])
        agg = result["evidencia_verification"]
        assert agg["evidencia_failed"] == 1
        assert agg["failures_by_layer"]["pairing_mismatch"] == 1
        assert agg["needs_review_triggered"] is True


# -----------------------------------------------------------------------
# Strict — enforcement per-item (ADR-295): item baixo/médio cai, parecer segue;
# missing_path é cobertura (fail-open); item alto → needs_review (acima)
# -----------------------------------------------------------------------


class TestStrictPerItemEnforcement:
    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PARECER_EVIDENCIA_MODE", "strict")

    def test_item_baixa_severidade_pairing_mismatch_e_descartado(self):
        result, _ = _run([("$.reserva_emergencia.total_liquida", "patrimonio")], severidade="Baixa")
        assert result["success"] is True  # parecer publicado, item removido
        agg = result["evidencia_verification"]
        assert agg["items_dropped"] == 1
        assert agg["failures_by_layer"]["pairing_mismatch"] == 1

    def test_pareamento_errado_baixa_severidade_nao_falsifica(self):
        """Adversarial: rotulo errado → item cai, citação NÃO é auto-corrigida."""
        result, store = _run([("$.patrimonio.bruto", "reserva_emergencia")], severidade="Média")
        assert result["success"] is True
        assert result["evidencia_verification"]["items_dropped"] == 1
        artifact = store.read("E6-parecer", "parecer_planejador")
        assert artifact.get("riscos", []) == []  # risco ofensor saiu do publicado

    def test_missing_path_e_cobertura_fail_open(self):
        """path None (coerce ADR-292) é cobertura, não derruba item nem parecer."""
        result, store = _run([(None, "reserva_emergencia")])
        assert result["success"] is True
        agg = result["evidencia_verification"]
        assert agg["failures_by_layer"]["missing_path"] == 1
        assert agg["items_dropped"] == 0
        assert agg["needs_review_triggered"] is False
        assert _risco_entries(store)[0]["outcome"] == "missing_path"


# -----------------------------------------------------------------------
# A26.l6 — KPI cobertura (missing_path) vs. correção (pairing_mismatch + …)
# -----------------------------------------------------------------------


class TestCoverageVsCorrectnessKpi:
    def test_missing_path_conta_como_cobertura_nao_correcao(self):
        result, _ = _run([(None, "reserva_emergencia")])
        agg = result["evidencia_verification"]
        assert agg["coverage_failed"] == 1
        assert agg["correctness_failed"] == 0
        assert agg["by_section"]["risco"]["missing_path"] == 1

    def test_pairing_mismatch_conta_como_correcao_nao_cobertura(self):
        result, _ = _run([("$.reserva_emergencia.total_liquida", "patrimonio")])
        agg = result["evidencia_verification"]
        assert agg["coverage_failed"] == 0
        assert agg["correctness_failed"] == 1
        assert agg["by_section"]["risco"]["pairing_mismatch"] == 1

    def test_verificado_nao_conta_em_nenhuma_falha(self):
        result, _ = _run([_RESERVA])
        agg = result["evidencia_verification"]
        assert agg["coverage_failed"] == 0
        assert agg["correctness_failed"] == 0

    def test_by_section_unit_agrega_por_item_type(self):
        from backend.app.services.parecer_evidencia import EvidenciaVerification

        v = EvidenciaVerification(
            entries=[
                {"item_type": "risco", "item_index": 0, "path": None, "outcome": "missing_path"},
                {"item_type": "risco", "item_index": 1, "path": "$.x", "outcome": "verified"},
                {
                    "item_type": "sugestoes_taticas",
                    "item_index": 0,
                    "path": "$.y",
                    "outcome": "pairing_mismatch",
                },
            ]
        )
        by_section = v.by_section()
        assert by_section["risco"] == {"missing_path": 1, "verified": 1}
        assert by_section["sugestoes_taticas"] == {"pairing_mismatch": 1}


# -----------------------------------------------------------------------
# Modo warn (default) — violação loga + telemetria, status normal
# -----------------------------------------------------------------------


class TestWarnModeDefault:
    def test_violation_does_not_block_in_warn(self, monkeypatch):
        monkeypatch.delenv("MATHOMS_PARECER_EVIDENCIA_MODE", raising=False)
        result, store = _run([(None, "reserva_emergencia")])
        assert result["success"] is True
        agg = result["evidencia_verification"]
        assert agg["evidencia_failed"] == 1
        assert agg["failures_by_layer"]["missing_path"] == 1
        assert agg["needs_review_triggered"] is False
        assert _risco_entries(store)[0]["outcome"] == "missing_path"

    def test_artifact_with_meta_block_validates_against_json_schema(self, monkeypatch):
        monkeypatch.delenv("MATHOMS_PARECER_EVIDENCIA_MODE", raising=False)
        _, store = _run([_RESERVA])
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

    def test_pareamento_correto_verifica(self):
        result, store = _run([_RESERVA])
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"

    def test_segunda_secao_pareada_verifica(self):
        result, store = _run([_IMOVEL])
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"

    def test_item_sem_ancora_nao_gera_entrada(self):
        result, store = _run([])
        assert result["success"] is True
        assert _risco_entries(store) == []

    def test_duas_ancoras_ambas_corretas_verificam(self):
        result, store = _run([_RESERVA, _IMOVEL])
        assert result["success"] is True
        outcomes = [e["outcome"] for e in _risco_entries(store)]
        assert outcomes == ["verified", "verified"]

    def test_valor_renderizado_gravado_pelo_finalize(self):
        """ADR-296: o finalize resolve path→valor_renderizado (snapshot, R$ formatado)."""
        _, store = _run([_RESERVA])
        artifact = store.read("E6-parecer", "parecer_planejador")
        ancora = artifact["riscos"][0]["ancoras"][0]
        assert ancora["path"] == _RESERVA[0]
        assert ancora["valor_renderizado"].startswith("R$ ")

    def test_ancoras_total_conta_densidade(self):
        """ADR-296: ancoras_total é a densidade de citação (substitui money_tokens no eval)."""
        result, _ = _run([_RESERVA, _IMOVEL])
        assert result["evidencia_verification"]["ancoras_total"] == 2


# -----------------------------------------------------------------------
# Extração de tokens monetários — telemetria number_in_prose (ADR-296: deve ser 0)
# -----------------------------------------------------------------------


class TestMoneyTokenExtraction:
    def test_non_monetary_numbers_are_ignored(self):
        from backend.app.services.parecer_evidencia import _extract_money_tokens

        prose = "Cobertura de 2,1 meses, 44,7% da renda, meta 25× até 2030 em 6 meses."
        assert _extract_money_tokens([prose]) == []

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
# Prompt — bump de versão + budget de tokens
# -----------------------------------------------------------------------


class TestPromptTokenBudget:
    def test_system_prompt_token_delta_under_5_percent(self):
        from pipeline.llm.prompts.parecer_planejador import PROMPT_VERSION, SYSTEM_PROMPT_TEMPLATE

        baseline_tokens = _PROMPT_BASELINE_CHARS // 4
        current_tokens = len(SYSTEM_PROMPT_TEMPLATE) // 4
        delta = abs(current_tokens - baseline_tokens) / baseline_tokens
        assert delta < 0.05, f"delta de tokens {delta:.2%} excede 5% (F4)"
        assert PROMPT_VERSION == "2.0.0"

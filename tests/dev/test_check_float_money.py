"""A33.l1 · ADR-090 — testes do gate ``dev/check_float_money.py --scan-schemas``."""

# Estratégia: importa o módulo do gate via importlib (padrão de
# test_check_prompt_version_bumped) e exercita o scan estrutural sobre
# arquivos sintéticos + o diretório real pipeline/llm/schemas.

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _REPO_ROOT / "dev" / "check_float_money.py"
_SPEC = importlib.util.spec_from_file_location("check_float_money", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def _offender_fields(tmp_path: Path, source: str) -> list[str]:
    (tmp_path / "schema_sintetico.py").write_text(source, encoding="utf-8")
    return [field for _, _, field in gate.scan_llm_schemas_float_fields(str(tmp_path))]


class TestScanSchemasDetection:
    def test_plain_float_field_is_offender(self, tmp_path):
        assert _offender_fields(tmp_path, "    amount: float = Field(...)\n") == ["amount"]

    def test_optional_float_is_offender(self, tmp_path):
        # Prova do furo fechado: o alvo real da lane (`balance_after`) era
        # Optional[float] e o lookahead antigo do FIELD_FLOAT o deixava passar.
        src = "    balance_after: Optional[float] = Field(None)\n"
        assert _offender_fields(tmp_path, src) == ["balance_after"]

    def test_union_none_is_offender(self, tmp_path):
        assert _offender_fields(tmp_path, "    saldo: float | None = None\n") == ["saldo"]

    def test_list_float_is_offender(self, tmp_path):
        assert _offender_fields(tmp_path, "    valores: list[float] = Field(...)\n") == ["valores"]

    def test_non_money_name_without_field_also_flagged(self, tmp_path):
        # Política invertida: nome desconhecido (nem money nem non-money) é
        # ofensor — em schema de boundary LLM o default é Decimal.
        assert _offender_fields(tmp_path, "    foo: float = 0.0\n") == ["foo"]


class TestScanSchemasSkips:
    def test_confidence_skipped_by_name(self, tmp_path):
        src = "    confidence: float = Field(..., ge=0.0, le=1.0)\n"
        assert _offender_fields(tmp_path, src) == []

    def test_rate_and_score_skipped_by_name(self, tmp_path):
        src = "    taxa_juros: float = 0.0\n    score: float = Field(...)\n"
        assert _offender_fields(tmp_path, src) == []

    def test_comment_on_line_does_not_forgive(self, tmp_path):
        # Comentário com token 'rate' não perdoa — só nome ou allowlist.
        src = "    valor_x: float = Field(...)  # rate from LLM output\n"
        assert _offender_fields(tmp_path, src) == ["valor_x"]

    def test_function_param_lines_ignored(self, tmp_path):
        src = "def f(\n    c: float,\n) -> None:\n    pass\n"
        assert _offender_fields(tmp_path, src) == []

    def test_decimal_field_ignored(self, tmp_path):
        src = "    amount: Decimal = Field(...)\n"
        assert _offender_fields(tmp_path, src) == []


class TestRealSchemasDir:
    def test_real_dir_is_clean(self):
        # Pós-migração A33.l1: zero ofensor fora da allowlist nominal.
        offenders = gate.scan_llm_schemas_float_fields(str(_REPO_ROOT / "pipeline/llm/schemas"))
        assert offenders == [], f"float monetário fora da allowlist: {offenders}"

    def test_parecer_exception_is_nominal_not_structural(self, monkeypatch):
        # Sem a allowlist, exatamente a exceção documentada (ADR-090 WHY no
        # parecer_planejador) aparece — prova que o gate a vê e que a isenção
        # é nominal, não furo do regex.
        monkeypatch.setattr(gate, "LLM_SCHEMAS_FLOAT_ALLOWLIST", {})
        offenders = gate.scan_llm_schemas_float_fields(str(_REPO_ROOT / "pipeline/llm/schemas"))
        assert [(Path(rel).name, field) for rel, _, field in offenders] == [
            ("parecer_planejador.py", "valor_estimado_brl")
        ]

    def test_allowlist_keys_still_exist_in_code(self):
        # Entrada morta na allowlist = exceção fantasma; falha se o campo sumiu.
        for (rel, field), why in gate.LLM_SCHEMAS_FLOAT_ALLOWLIST.items():
            source = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            assert f"{field}: float" in source, f"allowlist órfã: ({rel}, {field})"
            assert why.strip(), f"allowlist sem WHY: ({rel}, {field})"


class TestStagedDiffRegex:
    @pytest.mark.parametrize(
        "line",
        [
            "    amount: float = Field(...)",
            "    balance_after: Optional[float] = Field(None)",
            "    saldo: float | None = None",
            "    total_brl: list[float] = []",
        ],
    )
    def test_field_float_matches_float_bearing(self, line):
        assert gate.FIELD_FLOAT.match(line) is not None

    def test_field_float_ignores_decimal(self):
        assert gate.FIELD_FLOAT.match("    amount: Decimal = Field(...)") is None

    def test_money_tokens_cover_balance(self):
        assert gate.MONEY_TOKENS.search("balance_after") is not None

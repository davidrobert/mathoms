"""A33.l1 · ADR-090 — testes dos full-scans de ``dev/check_float_money.py``."""

# Estratégia: importa o módulo do gate via importlib (padrão de
# test_check_prompt_version_bumped) e exercita o scan estrutural sobre
# arquivos sintéticos + os diretórios reais pipeline/llm/schemas
# (--scan-schemas) e backend/app/models (--scan-models).

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


# cwds exercitados: a raiz (onde o pre-commit roda), dois subdiretórios do
# repo e um diretório fora dele. O veredito do gate não pode depender de
# nenhum deles.
_CWD_CASES = ["repo_root", "tests", "dev", "fora_do_repo"]


def _chdir_case(case: str, tmp_path: Path, monkeypatch) -> None:
    target = {
        "repo_root": _REPO_ROOT,
        "tests": _REPO_ROOT / "tests",
        "dev": _REPO_ROOT / "dev",
        "fora_do_repo": tmp_path,
    }[case]
    monkeypatch.chdir(target)


# Regressão medida em 2026-08-30: ``_repo_rel`` ancorava em ``Path.cwd()``. O
# hook passava por acidente — o pre-commit roda na raiz e passa dir RELATIVO,
# então ``relative_to`` levantava ``ValueError`` e o fallback devolvia justamente
# o path repo-relativo. O mesmo scan sobre o dir ABSOLUTO com ``cwd`` em
# ``tests/`` produzia chave absoluta, a allowlist errava, e a exceção nominal do
# ``parecer_planejador`` — que o hook isenta — reaparecia como ofensor.
class TestAllowlistKeyIsCwdInvariant:
    """A chave da allowlist nomeia um arquivo do REPO, não do ``cwd``."""

    @pytest.mark.parametrize("cwd_case", _CWD_CASES)
    def test_schemas_scan_clean_from_any_cwd(self, cwd_case, tmp_path, monkeypatch):
        _chdir_case(cwd_case, tmp_path, monkeypatch)
        schemas = str(_REPO_ROOT / "pipeline/llm/schemas")
        assert gate.scan_llm_schemas_float_fields(schemas) == []

    @pytest.mark.parametrize("cwd_case", _CWD_CASES)
    def test_models_scan_clean_from_any_cwd(self, cwd_case, tmp_path, monkeypatch):
        # MODELS_FLOAT_ALLOWLIST compartilha o mesmo ``_repo_rel``: as 4
        # entradas (score, temperature e as duas de confidence) evaporavam junto.
        _chdir_case(cwd_case, tmp_path, monkeypatch)
        models = str(_REPO_ROOT / "backend/app/models")
        assert gate.scan_models_float_columns(models) == []

    @pytest.mark.parametrize("cwd_case", _CWD_CASES)
    def test_scan_nao_e_inerte_no_mesmo_cwd(self, cwd_case, tmp_path, monkeypatch):
        # Não-inércia: o verde acima tem de vir da ALLOWLIST, não de o scan
        # ter parado de ler arquivo. Zerando a allowlist no MESMO cwd, o scan
        # acha exatamente a exceção documentada — e nada além dela.
        _chdir_case(cwd_case, tmp_path, monkeypatch)
        monkeypatch.setattr(gate, "LLM_SCHEMAS_FLOAT_ALLOWLIST", {})
        schemas = str(_REPO_ROOT / "pipeline/llm/schemas")
        offenders = gate.scan_llm_schemas_float_fields(schemas)
        assert [(Path(rel).name, field) for rel, _, field in offenders] == [
            ("parecer_planejador.py", "valor_estimado_brl")
        ]

    @pytest.mark.parametrize("cwd_case", _CWD_CASES)
    def test_models_scan_nao_e_inerte_no_mesmo_cwd(self, cwd_case, tmp_path, monkeypatch):
        # Mesma prova para o braço de models: sem a allowlist, o scan acha
        # EXATAMENTE as chaves declaradas nela. Pega os dois lados — verde por
        # rglob vazio (chave errada, dir errado) e entrada morta na allowlist.
        _chdir_case(cwd_case, tmp_path, monkeypatch)
        declaradas = set(gate.MODELS_FLOAT_ALLOWLIST)
        monkeypatch.setattr(gate, "MODELS_FLOAT_ALLOWLIST", {})
        models = str(_REPO_ROOT / "backend/app/models")
        achadas = {(rel, column) for rel, _, column in gate.scan_models_float_columns(models)}
        assert achadas == declaradas

    @pytest.mark.parametrize("cwd_case", _CWD_CASES)
    def test_repo_rel_devolve_chave_repo_relativa(self, cwd_case, tmp_path, monkeypatch):
        _chdir_case(cwd_case, tmp_path, monkeypatch)
        alvo = _REPO_ROOT / "pipeline/llm/schemas/parecer_planejador.py"
        assert gate._repo_rel(alvo) == "pipeline/llm/schemas/parecer_planejador.py"

    def test_forma_do_hook_dir_relativo_da_raiz(self, monkeypatch):
        # Forma exata do .pre-commit-config.yaml — o caminho que passava por
        # acidente continua passando por construção.
        monkeypatch.chdir(_REPO_ROOT)
        assert gate.scan_llm_schemas_float_fields("pipeline/llm/schemas") == []
        assert gate.scan_models_float_columns("backend/app/models") == []

    def test_path_relativo_fora_da_raiz_nao_casa_por_string(self, monkeypatch):
        # O fallback antigo devolvia a string crua: um arquivo em
        # `tests/pipeline/llm/schemas/` casaria a chave da allowlist sem ser
        # o arquivo dela. Resolver antes de ancorar faz a chave falhar fechada.
        monkeypatch.chdir(_REPO_ROOT / "tests")
        key = gate._repo_rel(Path("pipeline/llm/schemas/parecer_planejador.py"))
        assert key == "tests/pipeline/llm/schemas/parecer_planejador.py"


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

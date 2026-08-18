"""Golden de execução E5: tenant mínimo + E3→E4→E5 → assert + schema.

ADR-212 PR3b: E3/baseline são seeded no ``InMemoryArtifactStore`` (não em
disco). E4/E5 lêem/escrevem via store API.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.pipeline_golden_asserts import assert_qa_log_md

_REPO = Path(__file__).resolve().parents[1]
_E3_FIXTURE = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-3_reconciled.json"
)
_E3_MIXED = (
    _REPO
    / "tests"
    / "fixtures"
    / "pipeline_golden"
    / "e3"
    / "minimal-conta-com-despesa-3_reconciled.json"
)
_BASELINE_MIN = (
    _REPO
    / "tests"
    / "fixtures"
    / "pipeline_golden"
    / "e2"
    / "minimal-baseline-1.5_consolidated.json"
)
# ADR-274: itens em ano-base (2024) mas patrimonio_por_ano chaveado em
# exercício (2025) — reproduz o off-by-one que zerava imóveis no relatório.
_BASELINE_DIVERGENT = (
    _REPO
    / "tests"
    / "fixtures"
    / "pipeline_golden"
    / "e2"
    / "minimal-baseline-divergent-1.5_consolidated.json"
)
# A7.5: ``parametros_fiscais.json`` + ``taxas.json`` saíram de ``config/`` —
# fixtures locais cobrem tests legacy que precisam dos JSONs em disco.
_LEGACY_CONFIGS = _REPO / "tests" / "fixtures" / "legacy_configs"
_LEGACY_FISCAL = _LEGACY_CONFIGS / "parametros_fiscais.json"
_LEGACY_TAXAS = _LEGACY_CONFIGS / "taxas.json"

_GOALS_MIN = {
    "independencia_financeira": {
        "if_meta": 1_000_000.0,
        "trs_pct": 4.0,
    },
    # A12.alocacao-v2 PR10: alvo v2 (7 classes AUVP) — exercita o bloco
    # derived injetado pelo E5 (_enrich_alocacao_with_deviation, ADR-141).
    "alocacao_alvo": {
        "rf_pos_pct": 20,
        "rf_pre_pct": 10,
        "rf_ipca_pct": 10,
        "acoes_br_pct": 25,
        "acoes_int_pct": 15,
        "fiis_pct": 10,
        "caixa_pct": 10,
        "rebalanceamento_modo": "por_aporte",
    },
}

_FAMILY_E5 = {
    "titular": "david",
    "membros": {
        "david": {
            "nome_curto": "David",
            "data_nascimento": "1985-06-15",
        }
    },
}


def _write_e5_config(tmp_path: Path, *, expense_keywords: dict | None = None) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    # `_schema_to_validate` le de `CONFIG_DIR/schemas/`, e o CONFIG_DIR aqui e o
    # tmp. Sem esta copia, `schema_path.exists()` e False e `validate_dict` faz
    # SHORT-CIRCUIT para True: o assert de schema passa sem validar nada.
    # Medido em A40.l5 PR1 por mutacao — apertar o schema no repo nao derrubava
    # teste nenhum. Copiar os schemas reais faz o golden validar o contrato de
    # producao, que e a terceira perna do gate (schema x PRODUTOR).
    shutil.copytree(_REPO / "config" / "schemas", cfg / "schemas", dirs_exist_ok=True)
    cat = {
        "expense_keywords": expense_keywords or {},
        "income_keywords": {"renda": ["PIX"]},
        "internal_transfer_patterns": [],
        "pj_source_mapping": {},
        "clt_source_mapping": {},
    }
    (cfg / "categorization.json").write_text(
        json.dumps(cat, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cfg / "family_members.json").write_text(
        json.dumps(_FAMILY_E5, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # `{}` fazia `schema_validation.enabled` cair no default False, e
    # `_schema_to_validate` short-circuitava para True: o assert de schema
    # abaixo era VERDE VACUOSO — apertar o schema no repo nao derrubava teste
    # nenhum (medido por mutacao, A40.l5 PR1). Ligar a validacao aqui e o que
    # torna este golden a terceira perna do gate (schema x PRODUTOR).
    (cfg / "pipeline.json").write_text(
        json.dumps(
            {"schema_validation": {"enabled": True, "mode": "strict", "mode_overrides": {}}}
        ),
        encoding="utf-8",
    )
    (cfg / "goals.json").write_text(
        json.dumps(_GOALS_MIN, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.copy(_REPO / "config" / "scoring.json", cfg / "scoring.json")
    shutil.copy(_LEGACY_FISCAL, cfg / "parametros_fiscais.json")
    shutil.copy(_LEGACY_TAXAS, cfg / "taxas.json")


def _load_fixture_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _new_e5_ctx(root: Path, *, e3_fixture: Path, baseline: Path | None = None):
    """Cria WorkspaceContext com InMemoryArtifactStore seeded com E3 + baseline."""
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext

    store = InMemoryArtifactStore()
    e3_key = e3_fixture.stem.replace("-3_reconciled", "")
    store.seed("E3", e3_key, _load_fixture_json(e3_fixture))
    if baseline is not None:
        store.seed("E1.5c", "baseline_patrimonial", _load_fixture_json(baseline))
    return WorkspaceContext(root=root, artifact_store=store)


@pytest.fixture
def e5_tenant_minimal(tmp_path: Path) -> Path:
    _write_e5_config(tmp_path)
    return tmp_path


@pytest.fixture
def e5_tenant_mixed_cashflow(tmp_path: Path) -> Path:
    _write_e5_config(tmp_path, expense_keywords={"lazer": ["CINEMA"]})
    return tmp_path


@pytest.fixture
def e5_tenant_with_baseline(tmp_path: Path) -> Path:
    _write_e5_config(tmp_path)
    return tmp_path


def test_e5_execution_produces_analysis_json(e5_tenant_minimal: Path):
    """Roda E4 e E5 em tenant isolado; restaura globals dos scripts."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    ctx = _new_e5_ctx(e5_tenant_minimal, e3_fixture=_E3_FIXTURE)
    e4_mws(ctx)
    e5_mws(ctx)
    store = ctx.artifact_store

    payload = store.read("E5", "analise_financeira")
    assert payload is not None
    assert payload["score"]["valor"] >= 0
    assert payload["score"]["valor"] <= 10
    assert isinstance(payload["score"]["classificacao"], str)
    assert "bruto" in payload["patrimonio"] and "liquido" in payload["patrimonio"]
    assert "fluxo_caixa" in payload
    assert payload["goals"]["if_meta"] == 1_000_000.0

    # A12.alocacao-v2 PR10: E5 injeta o bloco derived de desvio atual-vs-alvo
    # (ADR-141 §Emenda item 4) — fecha o gap de cobertura end-to-end.
    alvo = payload["goals"]["alocacao_alvo"]
    assert "derived" in alvo, "E5 deve injetar goals.alocacao_alvo.derived"
    derived = alvo["derived"]
    assert derived["rf_comparacao"] == "agregada"
    assert derived["has_alvo"] is True
    assert isinstance(derived["comparaveis"], list)
    assert {"classe", "atual_pct", "alvo_pct", "desvio_pp", "severity"} <= set(
        derived["comparaveis"][0]
    )
    assert "caixa" in derived and "sinal_excesso" in derived["caixa"]

    # `jsonschema.validate(payload, schema)` cru NAO e o validador de producao:
    # ele nao tem o registry que resolve `$ref` cross-file por filename
    # (`_load_schema_resources`), entao mede um contrato mais fraco e diferente
    # do que o hook de escrita aplica. Medido em A40.l5 PR1: ao trocar
    # `protecao_patrimonial` por `$ref`, o cru quebrou com `Unresolvable`
    # enquanto `validate_dict` passava. Usar so o de producao.
    pytest.importorskip("jsonschema")
    from scripts.pipeline_common import validate_dict

    assert validate_dict(payload, "e5_analysis.schema.json") is True

    assert_qa_log_md(e5_tenant_minimal)


def test_e5_execution_mixed_receita_despesa(e5_tenant_mixed_cashflow: Path):
    """E5 com receitas e despesas não nulas no E4 (golden expandido)."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    ctx = _new_e5_ctx(e5_tenant_mixed_cashflow, e3_fixture=_E3_MIXED)
    e4_mws(ctx)
    e5_mws(ctx)
    store = ctx.artifact_store

    payload = store.read("E5", "analise_financeira")
    fc = payload["fluxo_caixa"]
    assert fc.get("receita_total", 0) > 0
    assert fc.get("despesa_total", 0) > 0

    pytest.importorskip("jsonschema")
    from scripts.pipeline_common import validate_dict

    assert validate_dict(payload, "e5_analysis.schema.json") is True

    assert_qa_log_md(e5_tenant_mixed_cashflow)


def test_e5_execution_with_baseline_patrimonial(e5_tenant_with_baseline: Path):
    """E5 lê baseline consolidado: patrimônio bruto/líquido refletem totais do IRPF sintético."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    ctx = _new_e5_ctx(e5_tenant_with_baseline, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_MIN)
    e4_mws(ctx)
    e5_mws(ctx)
    store = ctx.artifact_store

    payload = store.read("E5", "analise_financeira")
    assert payload["patrimonio"]["bruto"] == 500_000.0
    assert payload["patrimonio"]["liquido"] == 400_000.0
    assert payload["patrimonio"]["dividas"] == 100_000.0

    pytest.importorskip("jsonschema")
    from scripts.pipeline_common import validate_dict

    assert validate_dict(payload, "e5_analysis.schema.json") is True

    assert_qa_log_md(e5_tenant_with_baseline)


def test_e5_divergent_baseline_imoveis_not_zeroed(e5_tenant_with_baseline: Path):
    """ADR-274 end-to-end: baseline com itens em ano-base (2024) e resumo
    chaveado em exercício (2025) não pode zerar imóveis. Antes do fix, o
    resolver buscava ``valores_31_12['2025']`` (miss) → ``valor_31_12_ano_base``
    = 0 → classe 'Imóveis Investimento' = 0 (sintoma do relatório)."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    ctx = _new_e5_ctx(e5_tenant_with_baseline, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_DIVERGENT)
    e4_mws(ctx)
    e5_mws(ctx)
    payload = ctx.artifact_store.read("E5", "analise_financeira")

    classes = {c["categoria"]: c["valor"] for c in payload["investimentos"]["tabela_classes"]}
    assert classes.get("Imóveis Investimento", 0) == 350_000.0
    assert payload["patrimonio"]["bruto"] == 350_000.0


# O golden é o único lugar onde o schema REAL de produção encontra o payload
# REAL: `guarda_de_sinal` declarado à mão não prova que ele valida sob o
# registry que resolve $ref cross-file (A40.l67 · [[ADR-394]] §Emenda).
def test_e5_publica_veredito_da_guarda_de_sinal(e5_tenant_with_baseline: Path):
    """Corpus limpo: veredito inerte, cobertura completa e run sem needs_review."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    ctx = _new_e5_ctx(e5_tenant_with_baseline, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_MIN)
    e4_mws(ctx)
    result = e5_mws(ctx)
    payload = ctx.artifact_store.read("E5", "analise_financeira")

    guarda = payload["patrimonio"]["guarda_de_sinal"]
    assert guarda["modo"] == "enforce"
    assert guarda["cobertura_completa"] is True
    assert guarda["baldes_negativos"] == [] and guarda["reclassificados"] == []
    assert result["validation"] == {"valid": True, "errors": [], "review_reasons": []}

    pytest.importorskip("jsonschema")
    from scripts.pipeline_common import validate_dict

    assert validate_dict(payload, "e5_analysis.schema.json") is True

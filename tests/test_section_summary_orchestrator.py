"""Integration test do SectionSummaryOrchestrator (v2.9 · ADR-144)."""
# Cobre: toggle env (default OFF), wire-up LLM injetado, fallback path,
# dispatch sobre SUPPORTED_SECTION_IDS, snapshot_hash determinístico.

from __future__ import annotations

import os

import pytest

from backend.app.services.section_summary_orchestrator import (
    SUPPORTED_SECTION_IDS,
    compute_snapshot_hash,
    generate_all_section_summaries,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from pipeline.domain.services.section_summary_generator import (
    PromptTemplate,
    SectionSummaryGenerator,
    SectionSummaryGeneratorConfig,
)
from tests.fakes.llm import FakeLLMSuccess, make_fake_fallback


def _make_test_generator():
    templates = {sid: _make_template(sid) for sid in SUPPORTED_SECTION_IDS}
    return SectionSummaryGenerator(
        llm_client=FakeLLMSuccess(text="Resumo de teste."),
        cache=InMemoryLLMCache(),
        fallback=make_fake_fallback("fallback"),
        templates=templates,
        config=SectionSummaryGeneratorConfig(),
    )


def _make_template(section_id: str) -> PromptTemplate:
    return PromptTemplate(
        system_prompt=f"Editor financeiro. Seção {section_id}.",
        user_prompt_template=f"Seção {section_id}: {{section_data_json}}",
    )


def test_disabled_by_default_returns_empty_dict(monkeypatch: pytest.MonkeyPatch):
    """Toggle OFF (default) → orquestrador retorna {} sem chamar LLM."""
    monkeypatch.delenv("MATHOMS_LLM_SECTION_SUMMARIES", raising=False)
    result = generate_all_section_summaries(
        workspace_id=1,
        e5_data={"patrimonio": {"liquido": 1000}},
    )
    assert result == {}


def test_with_explicit_generator_runs_all_sections():
    """Generator injetado bypassa o toggle (uso por integration tests)."""
    gen = _make_test_generator()
    result = generate_all_section_summaries(
        workspace_id=1,
        e5_data={"patrimonio": {"liquido": 1000}, "score": {"valor": 8}},
        generator=gen,
    )
    # Cobre todas as 13 seções suportadas
    assert len(result) == len(SUPPORTED_SECTION_IDS)
    for section_id in SUPPORTED_SECTION_IDS:
        assert section_id in result
        assert result[section_id] == "Resumo de teste."


def test_compute_snapshot_hash_deterministic():
    """Hash determinístico — mesma entrada produz mesmo hash."""
    payload = {"a": 1, "b": [2, 3]}
    h1 = compute_snapshot_hash(payload)
    h2 = compute_snapshot_hash({"b": [2, 3], "a": 1})  # ordem diferente
    assert h1 == h2  # sort_keys=True
    assert len(h1) == 64  # SHA-256 hex


def test_compute_snapshot_hash_changes_with_data():
    """Mudança de dados → mudança de hash."""
    h1 = compute_snapshot_hash({"a": 1})
    h2 = compute_snapshot_hash({"a": 2})
    assert h1 != h2


def test_supported_section_ids_match_yaml_keys():
    """Sanity check: SUPPORTED_SECTION_IDS bate com keys do YAML."""
    from backend.app.services.section_summary_orchestrator import _resolve_yaml_path
    from pipeline.domain.services.section_summary_generator import (
        load_prompt_templates_from_yaml,
    )

    templates = load_prompt_templates_from_yaml(_resolve_yaml_path())
    yaml_keys = set(templates.keys())
    supported = set(SUPPORTED_SECTION_IDS)
    assert supported == yaml_keys, (
        f"Drift entre código e YAML — supported-yaml={supported - yaml_keys}, "
        f"yaml-supported={yaml_keys - supported}"
    )


def test_fallback_via_narrativas_summaries_legacy(monkeypatch: pytest.MonkeyPatch):
    """Quando LLM indisponível e env permite, fallback lê narrativas[summaries]."""
    from backend.app.services.section_summary_orchestrator import _default_fallback

    snapshot_data = {
        "patrimonio": {"liquido": 1000},
        "_narrativas": {"summaries": {"s1": "narrativa legada s1"}},
    }
    text = _default_fallback("S1", snapshot_data)
    assert text == "narrativa legada s1"


def test_fallback_returns_generic_text_when_no_legacy():
    """Sem narrativas[summaries], fallback retorna texto genérico por section_id."""
    from backend.app.services.section_summary_orchestrator import _default_fallback

    text = _default_fallback("S1", {})
    assert text is not None
    assert "Patrimônio" in text or "patrimonial" in text.lower()


def test_fallback_unknown_section_returns_none():
    from backend.app.services.section_summary_orchestrator import _default_fallback

    assert _default_fallback("UNKNOWN_SECTION", {}) is None


# A40.l4 (ADR-356 §D2): o teste acima usa `S1` — justamente o id onde
# `section_id.lower()` coincide com o destino correto. Com a entrega de narrativa
# ligada, o caminho passou a ser alcançável em 5 seções, e para a S2 o lowercase
# publicava o parágrafo de SCORE no topo do Fluxo de Caixa.
def test_fallback_nao_deriva_chave_por_lowercase():
    """`S2` não lê `summaries.s2` — o mapa é `summary_source` do layout."""
    from backend.app.services.section_summary_orchestrator import _default_fallback

    snapshot_data = {
        "_narrativas": {"summaries": {"s2": "Score financeiro de 5,6/10 (Regular)."}},
    }
    text = _default_fallback("S2", snapshot_data)
    assert text is not None
    assert "Score financeiro" not in text, text
    assert "Fluxo de caixa" in text, text


def test_fallback_usa_destino_declarado_no_layout():
    """A leitura segue `summary_source`; S9 → s9 (não coincidência de string)."""
    from backend.app.services.section_summary_orchestrator import _default_fallback

    snapshot_data = {"_narrativas": {"summaries": {"s9": "2 riscos prioritários: a, b."}}}
    assert _default_fallback("S9", snapshot_data) == "2 riscos prioritários: a, b."

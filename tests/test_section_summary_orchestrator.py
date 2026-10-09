"""Integration test do SectionSummaryOrchestrator (v2.9 · ADR-144)."""
# Cobre: toggle env (default OFF), wire-up LLM injetado, fallback path,
# dispatch sobre SUPPORTED_SECTION_IDS, snapshot_hash determinístico.

from __future__ import annotations

import hashlib
import json
import os

import pytest

from backend.app.services.section_summary_orchestrator import (
    _SECTION_KEYS,
    SUPPORTED_SECTION_IDS,
    _default_fallback,
    _slice_section_data,
    compute_snapshot_hash,
    generate_all_section_summaries,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from pipeline.domain.services.section_summary_generator import (
    PromptTemplate,
    SectionSummaryGenerator,
    SectionSummaryGeneratorConfig,
)
from tests.fakes.llm import (
    FakeLLMPromptRecorder,
    FakeLLMRaisingClient,
    FakeLLMSuccess,
    make_fake_fallback,
)


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

    fallback_context = {"summaries": {"s1": "narrativa legada s1"}}
    text = _default_fallback("S1", fallback_context)
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

    fallback_context = {"summaries": {"s2": "Score financeiro de 5,6/10 (Regular)."}}
    text = _default_fallback("S2", fallback_context)
    assert text is not None
    assert "Score financeiro" not in text, text
    assert "Fluxo de caixa" in text, text


def test_fallback_usa_destino_declarado_no_layout():
    """A leitura segue `summary_source`; S9 → s9 (não coincidência de string)."""
    from backend.app.services.section_summary_orchestrator import _default_fallback

    fallback_context = {"summaries": {"s9": "2 riscos prioritários: a, b."}}
    assert _default_fallback("S9", fallback_context) == "2 riscos prioritários: a, b."


# O payload da seção ia ao provider com `_narrativas` anexado — as narrativas
# do relatório inteiro, com R$ formatado — em todas as seções. O único leitor
# era o fallback determinístico. O prompt leva o slice declarado e só ele; o
# fallback recebe a narrativa por outro canal.
_SENTINELA = "SENTINELA-NARRATIVA-DE-OUTRA-SECAO"


def _e5_com_narrativas(texto_s1: str = _SENTINELA) -> dict:
    chaves_de_slice = {chave for chaves in _SECTION_KEYS.values() for chave in chaves}
    e5 = {chave: {"marcador": f"slice:{chave}"} for chave in sorted(chaves_de_slice)}
    e5["composicao_familiar"] = {"marcador": "fora-de-todo-slice"}
    e5["narrativas"] = {"summaries": {"s1": texto_s1, "s9": f"{_SENTINELA} s9"}}
    return e5


def _gerador(llm, *, cache=None, fallback=None) -> SectionSummaryGenerator:
    templates = {
        sid: PromptTemplate(system_prompt="Editor.", user_prompt_template="{section_data_json}")
        for sid in SUPPORTED_SECTION_IDS
    }
    return SectionSummaryGenerator(
        llm_client=llm,
        cache=cache or InMemoryLLMCache(),
        fallback=fallback or make_fake_fallback("fallback"),
        templates=templates,
        config=SectionSummaryGeneratorConfig(),
    )


def test_narrativas_nao_entram_no_prompt_de_nenhuma_secao():
    llm = FakeLLMPromptRecorder()
    generate_all_section_summaries(
        workspace_id=1, e5_data=_e5_com_narrativas(), generator=_gerador(llm)
    )
    assert [sid for sid, _ in llm.prompts] == list(SUPPORTED_SECTION_IDS)
    vazados = [sid for sid, prompt in llm.prompts if _SENTINELA in prompt]
    assert vazados == [], f"narrativa de outra seção no prompt de {vazados}"


def test_prompt_de_cada_secao_carrega_exatamente_o_slice_declarado():
    llm = FakeLLMPromptRecorder()
    generate_all_section_summaries(
        workspace_id=1, e5_data=_e5_com_narrativas(), generator=_gerador(llm)
    )
    for section_id, prompt in llm.prompts:
        assert set(json.loads(prompt)) == set(_SECTION_KEYS[section_id]), section_id


def test_fallback_ainda_le_a_narrativa_quando_o_llm_falha():
    gen = _gerador(
        FakeLLMRaisingClient(error=TimeoutError("request timed out")),
        fallback=_default_fallback,
    )
    e5 = _e5_com_narrativas(texto_s1="Narrativa determinística da S1.")
    result = generate_all_section_summaries(workspace_id=1, e5_data=e5, generator=gen)
    assert result["S1"] == "Narrativa determinística da S1."
    assert result["S9"] == f"{_SENTINELA} s9"


def test_mudar_so_a_narrativa_nao_invalida_o_cache_da_secao():
    """A chave hasheia o que o LLM lê (ADR-144 §2) — e a narrativa não vai ao prompt."""
    llm = FakeLLMPromptRecorder()
    cache = InMemoryLLMCache()
    for texto in ("Primeira redação da S1.", "Segunda redação da S1."):
        generate_all_section_summaries(
            workspace_id=1,
            e5_data=_e5_com_narrativas(texto_s1=texto),
            generator=_gerador(llm, cache=cache),
        )
    assert len(llm.prompts) == len(SUPPORTED_SECTION_IDS)


def test_hash_da_chave_cobre_os_mesmos_bytes_que_o_prompt_recebe():
    """Slice igual é input igual: a chave hasheia a serialização que vai ao prompt."""
    llm = FakeLLMPromptRecorder()
    e5 = _e5_com_narrativas()
    generate_all_section_summaries(workspace_id=1, e5_data=e5, generator=_gerador(llm))
    for section_id, prompt in llm.prompts:
        esperado = compute_snapshot_hash(_slice_section_data(e5, section_id))
        assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == esperado, section_id

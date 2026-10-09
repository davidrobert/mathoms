"""Integration test do SectionSummaryOrchestrator (v2.9 · ADR-144)."""
# Cobre: toggle env (default OFF), wire-up LLM injetado, falha deixando a
# seção ausente, dispatch sobre SUPPORTED_SECTION_IDS, snapshot_hash
# determinístico e payload do prompt = slice declarado.

from __future__ import annotations

import hashlib
import json
import os

import pytest

import backend.app.services.section_summary_orchestrator as orchestrator
from backend.app.services.section_summary_orchestrator import (
    _SECTION_KEYS,
    SUPPORTED_SECTION_IDS,
    _cita_valor_monetario,
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
from tests.fakes.llm import FakeLLMPromptRecorder, FakeLLMSuccess


def _make_test_generator():
    templates = {sid: _make_template(sid) for sid in SUPPORTED_SECTION_IDS}
    return SectionSummaryGenerator(
        llm_client=FakeLLMSuccess(text="Resumo de teste."),
        cache=InMemoryLLMCache(),
        cites_money=_cita_valor_monetario,
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
        e5_data=_e5_com_narrativas(),
        generator=gen,
    )
    # Cobre todas as seções suportadas (o fixture dá dado a todo slice)
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


# O payload da seção ia ao provider com `_narrativas` anexado — as narrativas
# do relatório inteiro, com R$ formatado — em todas as seções. O único leitor
# era o fallback do backend, que saiu (último teste). O prompt leva o slice
# declarado e só ele.
_SENTINELA = "SENTINELA-NARRATIVA-DE-OUTRA-SECAO"


def _e5_com_narrativas(texto_s1: str = _SENTINELA) -> dict:
    chaves_de_slice = {chave for chaves in _SECTION_KEYS.values() for chave in chaves}
    e5 = {chave: {"marcador": f"slice:{chave}"} for chave in sorted(chaves_de_slice)}
    e5["composicao_familiar"] = {"marcador": "fora-de-todo-slice"}
    e5["narrativas"] = {"summaries": {"s1": texto_s1, "s9": f"{_SENTINELA} s9"}}
    return e5


def _gerador(llm, *, cache=None) -> SectionSummaryGenerator:
    templates = {
        sid: PromptTemplate(system_prompt="Editor.", user_prompt_template="{section_data_json}")
        for sid in SUPPORTED_SECTION_IDS
    }
    return SectionSummaryGenerator(
        llm_client=llm,
        cache=cache or InMemoryLLMCache(),
        cites_money=_cita_valor_monetario,
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


def test_secao_sem_dado_nao_chama_o_llm():
    """T5 sem cônjuge: slice vazio daria frase genérica que vence as camadas 2 e 3."""
    llm = FakeLLMPromptRecorder()
    e5 = _e5_com_narrativas()
    del e5["cenarios_conjuge"]
    result = generate_all_section_summaries(workspace_id=1, e5_data=e5, generator=_gerador(llm))
    assert "T5" not in [sid for sid, _ in llm.prompts]
    assert "T5" not in result
    assert "S7" in result  # S7 ainda tem `ratios`


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


# ADR-356: camada 1 preenchida vence as camadas 2 e 3. O fallback do backend
# escrevia ali a cópia do E5.N, rotulada `llm` e sem o sufixo da §D10, ou um
# genérico que mascarava o `deriveSectionSummary`. Falha deixa a seção ausente.
def test_flag_ligada_sem_chave_de_api_nao_preenche_a_camada_1(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MATHOMS_LLM_SECTION_SUMMARIES", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(orchestrator, "_build_cache", InMemoryLLMCache)
    result = generate_all_section_summaries(workspace_id=1, e5_data=_e5_com_narrativas())
    assert result == {}


@pytest.mark.parametrize(
    "prosa, cita",
    [
        ("Patrimônio de R$ 1.234 concentrado em imóveis.", True),
        ("Sobram 720 mil reais no período.", True),
        ("Ativos de US$ 10 mil no exterior.", True),
        ("Juros reais acima da inflação sustentam a carteira.", False),
        ("Taxa de poupança de 23% no período.", False),
        ("A reserva cobre 8 meses do custo de vida.", False),
    ],
)
def test_detector_monetario_e_o_do_parecer(prosa: str, cita: bool):
    assert _cita_valor_monetario(prosa) is cita


def test_prosa_com_valor_monetario_nao_chega_a_section_summaries():
    llm = FakeLLMPromptRecorder(text="Patrimônio de R$ 1.234 concentrado em imóveis.")
    result = generate_all_section_summaries(
        workspace_id=1, e5_data=_e5_com_narrativas(), generator=_gerador(llm)
    )
    assert len(llm.prompts) == len(SUPPORTED_SECTION_IDS)
    assert result == {}

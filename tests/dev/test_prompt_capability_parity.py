"""O prompt do parecer não promete capacidade que o transporte não expõe (A40.l117)."""

# Bicondicional de propósito. Um gate que só perguntasse "o prompt cita `get_e5_section`?"
# vira monotônico: verde para sempre no minuto em que as strings somem, e cego ao caminho
# inverso — alguém liga tool no transporte e o modelo nunca fica sabendo. As duas pernas
# são alcançáveis por mudança plausível, que é o que separa gate de carimbo.
#
# Limite declarado: fecha os dois NOMES literais, não a classe. Prosa equivalente ("peça a
# seção completa") passa. A defesa contra a classe é a perna reversa + o inventário de
# superfícies por igualdade de conjunto — não finja cobertura que o regex não tem.

from __future__ import annotations

import dataclasses
import inspect

import pytest

from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_manifest import load_manifest, load_persona
from backend.app.services.parecer_orchestrator import _build_prompts
from pipeline.llm.litellm_client import LLMService
from pipeline.llm.prompts.parecer_planejador import (
    SYSTEM_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE,
)
from tests.test_parecer_distiller_exec_context import make_dogfood_like_e5

# Nomes que só fazem sentido se o modelo puder chamá-los.
TOOL_NAMES = ("get_e5_section", "get_e5_jsonpath")

# Parâmetros de `LLMService.call` que expõem tool-use ao modelo. Lido da ASSINATURA
# VIVA, nunca de constante espelho: teste que compara com a própria constante sobrevive
# à mutação dela.
TOOL_PARAMS = ("tools", "tool_choice", "toolkit")

# Produtores que compõem o prompt montado. Igualdade de conjunto, não allowlist: produtor
# novo sem entrada reprova pedindo declaração, porque allowlist que só cresce falha aberta.
SUPERFICIES = frozenset(
    {
        "system_template",  # pipeline/llm/prompts/parecer_planejador.py
        "persona",  # config/agents/planner_persona.md
        "user_template",  # idem, lado do usuário
        "section_bodies",  # parecer_distiller._render_section_body
        "eviction_marker",  # parecer_distiller._eviction_marker
        "hints",  # parecer_distiller._render_hints_block
        "citation_catalog",  # parecer_distiller._render_catalog_block
    }
)


def _exposed_tool_params() -> frozenset[str]:
    params = set(inspect.signature(LLMService.call).parameters)
    return frozenset(p for p in TOOL_PARAMS if p in params)


def _promised(text: str) -> frozenset[str]:
    return frozenset(name for name in TOOL_NAMES if name in text)


@pytest.fixture(scope="module")
def prompts_montados() -> tuple[str, str]:
    # Os DOIS regimes: um só deixaria o canal do `_eviction_marker` vazio, e caso não
    # exercido passa por vacuidade — o modo de falha que este arquivo existe para não repetir.
    e5 = make_dogfood_like_e5()
    manifest = load_manifest()
    persona_body, _ = load_persona()
    normal = _build_prompts(manifest=manifest, persona_body=persona_body, e5_data=e5)

    apertado = dataclasses.replace(manifest, max_exec_context_bytes=900)
    truncado = _build_prompts(manifest=apertado, persona_body=persona_body, e5_data=e5)
    return normal[0] + "\n" + truncado[0], normal[1] + "\n" + truncado[1]


def test_regime_truncado_e_exercido():
    """Precondição do canal `_eviction_marker`: sem isto o caso passa vazio."""
    apertado = dataclasses.replace(load_manifest(), max_exec_context_bytes=900)
    assert "seções removidas" in distill_exec_context(apertado, make_dogfood_like_e5()), (
        "o regime apertado não produziu marcador de eviction — o gate estaria medindo "
        "um canal vazio e daria verde por vacuidade"
    )


def _promete_sem_expor(system: str, user: str) -> bool:
    """O predicado do gate, isolado para que as mutações possam exercê-lo."""
    return bool((_promised(system) | _promised(user)) and not _exposed_tool_params())


def test_prompt_nao_promete_tool_que_o_transporte_nao_expoe(prompts_montados):
    system, user = prompts_montados
    promised = _promised(system) | _promised(user)
    exposed = _exposed_tool_params()
    assert not (promised and not exposed), (
        f"o prompt montado promete {sorted(promised)} e `LLMService.call` não expõe "
        f"nenhum de {list(TOOL_PARAMS)}: o modelo é single-shot e a instrução é "
        f"insatisfazível (A40.l117 · ADR-341 §Emenda 2026-09-01)"
    )


def test_transporte_com_tool_exige_contrato_model_facing(prompts_montados):
    """Perna reversa — é ela que dá ao gate um segundo estado alcançável."""
    system, user = prompts_montados
    exposed = _exposed_tool_params()
    assert not (exposed and not (_promised(system) | _promised(user))), (
        f"`LLMService.call` passou a expor {sorted(exposed)} e nenhuma superfície "
        f"model-facing declara as tools ao modelo: capacidade sem contrato"
    )


def test_inventario_de_superficies_e_declarado_por_igualdade():
    """Produtor novo em `distill_exec_context` sem entrada em SUPERFICIES reprova."""
    fonte = inspect.getsource(distill_exec_context)
    produtores = {
        "section_bodies": "_render_section_body",
        "hints": "_render_hints_block",
        "citation_catalog": "_render_catalog_block",
        "eviction_marker": "_fit_body_to_budget",
    }
    vistos = {chave for chave, fn in produtores.items() if fn in fonte}
    esperado = SUPERFICIES - {"system_template", "persona", "user_template"}
    assert vistos == esperado, (
        f"o conjunto de produtores do exec context mudou: {sorted(vistos)} != "
        f"{sorted(esperado)}. Declare a superfície nova em SUPERFICIES e confirme "
        f"que ela é varrida por `prompts_montados`."
    )


def test_templates_cobertos_pelo_prompt_montado():
    """As 3 superfícies fora do distiller entram no montado por construção."""
    assert "{persona_body}" in SYSTEM_PROMPT_TEMPLATE
    assert "{exec_context}" in USER_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# Não-inércia: cada canal reprova SOZINHO
# ---------------------------------------------------------------------------
# Sem estes quatro, o gate acima é indistinguível de um que só sabe ler o system
# prompt — e o canal que ele não vê é exatamente o que reintroduziria o defeito.
# Mutamos o PRODUTOR (binding no módulo que consome), nunca a string montada:
# mutar o payload provaria só que o regex funciona.


def _montar(manifest, persona_body, e5, *, cap: int | None = None) -> tuple[str, str]:
    m = dataclasses.replace(manifest, max_exec_context_bytes=cap) if cap else manifest
    return _build_prompts(manifest=m, persona_body=persona_body, e5_data=e5)


def test_mutacao_no_system_template_reprova(monkeypatch):
    import backend.app.services.parecer_orchestrator as orch

    monkeypatch.setattr(
        orch,
        "SYSTEM_PROMPT_TEMPLATE",
        SYSTEM_PROMPT_TEMPLATE + "\nChame get_e5_section quando faltar dado.\n",
    )
    system, user = _montar(load_manifest(), load_persona()[0], make_dogfood_like_e5())
    assert _promete_sem_expor(system, user), "canal `system_template` NÃO é coberto"


def test_mutacao_na_persona_reprova():
    persona = load_persona()[0] + "\n**R99.** Use `get_e5_jsonpath` se precisar.\n"
    system, user = _montar(load_manifest(), persona, make_dogfood_like_e5())
    assert _promete_sem_expor(system, user), "canal `persona` NÃO é coberto"


def test_mutacao_no_eviction_marker_reprova(monkeypatch):
    import backend.app.services.parecer_distiller as dist

    original = dist._eviction_marker
    monkeypatch.setattr(
        dist,
        "_eviction_marker",
        lambda evicted: original(evicted) + " Recupere via get_e5_section.",
    )
    # Só sob eviction — em cap normal este canal não emite nada e o teste passaria vazio.
    system, user = _montar(load_manifest(), load_persona()[0], make_dogfood_like_e5(), cap=900)
    assert _promete_sem_expor(system, user), "canal `eviction_marker` NÃO é coberto"


def test_mutacao_no_narrative_hint_reprova():
    manifest = load_manifest()
    sections = [dict(s) for s in manifest.sections]
    sections[0]["narrative_hints"] = [
        *(sections[0].get("narrative_hints") or []),
        "Se faltar, chame get_e5_section('patrimonio').",
    ]
    mutado = dataclasses.replace(manifest, sections=sections)
    system, user = _montar(mutado, load_persona()[0], make_dogfood_like_e5())
    assert _promete_sem_expor(system, user), "canal `narrative_hints` NÃO é coberto"


def test_perna_reversa_e_alcancavel(monkeypatch):
    """Se o transporte ganhar `tools` e o prompt calar, a outra perna acusa."""
    monkeypatch.setattr(
        "tests.dev.test_prompt_capability_parity._exposed_tool_params",
        lambda: frozenset({"tools"}),
    )
    system, user = _montar(load_manifest(), load_persona()[0], make_dogfood_like_e5())
    exposed = _exposed_tool_params()
    assert exposed and not (
        _promised(system) | _promised(user)
    ), "a perna reversa não é alcançável — o gate teria um só estado"

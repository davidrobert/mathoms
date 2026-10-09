"""A chave do cache do parecer compõe a proveniência carimbada no output (ADR-201 §Emenda 2026-10-09)."""

from __future__ import annotations

import hashlib

from backend.app.services import parecer_manifest
from backend.app.services.parecer_orchestrator import (
    ParecerGenerationResult,
    ParecerOrchestratorConfig,
    generate_parecer,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from tests.fakes.parecer import FakeLLMService, make_valid_parecer_output

_E5 = {"patrimonio": {"bruto": 1}}


def _persona_em(tmp_path, monkeypatch, nome: str, corpo: str) -> str:
    """Aponta o loader para uma persona em disco; devolve o sha256 que ele deve calcular."""
    arquivo = tmp_path / nome
    arquivo.write_text(corpo, encoding="utf-8")
    monkeypatch.setattr(parecer_manifest, "_PERSONA_PATH", str(arquivo))
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def _gerar(
    cache: InMemoryLLMCache, tier: str = "premium"
) -> tuple[ParecerGenerationResult, FakeLLMService]:
    llm = FakeLLMService(output=make_valid_parecer_output())
    result = generate_parecer(
        e5_data=_E5,
        config=ParecerOrchestratorConfig(workspace_id="ws-proveniencia", tier=tier),
        llm_service=llm,
        cache=cache,
    )
    return result, llm


class TestPersonaEditadaInvalidaOCache:
    """O corpo da persona abre o system prompt; o cache guardava o parecer da persona
    antiga por até 7 dias, e o hit carimbava o hash NOVO no ``PlannerReview``."""

    def test_corpo_novo_da_persona_e_cache_miss(self, tmp_path, monkeypatch):
        cache = InMemoryLLMCache()
        _persona_em(tmp_path, monkeypatch, "a.md", "# Persona A\n")
        _gerar(cache)
        hash_b = _persona_em(tmp_path, monkeypatch, "b.md", "# Persona B\n")

        result, llm = _gerar(cache)

        assert result.cache_hit is False, "serviu parecer gerado sob a persona antiga"
        assert len(llm.summary.calls) == 1
        assert result.output.metadata.persona_hash == hash_b

    def test_mesma_persona_continua_hit(self, tmp_path, monkeypatch):
        """Contraprova: sem ela, uma chave que nunca repete passaria o teste acima."""
        cache = InMemoryLLMCache()
        hash_a = _persona_em(tmp_path, monkeypatch, "a.md", "# Persona A\n")
        _gerar(cache)

        result, llm = _gerar(cache)

        assert result.cache_hit is True
        assert llm.summary.calls == []
        assert result.persona_hash == result.output.metadata.persona_hash == hash_a


class TestTierCompoeAChave:
    """``tier_at_generation`` é carimbado no output cacheado: hit cross-tier fazia o
    envelope (``config.tier``) divergir do ``output.metadata`` servido."""

    def test_tier_diferente_e_cache_miss(self):
        cache = InMemoryLLMCache()
        _gerar(cache, tier="premium")

        result, llm = _gerar(cache, tier="free")

        assert result.cache_hit is False
        assert len(llm.summary.calls) == 1
        assert result.tier_at_generation == result.output.metadata.tier_at_generation == "free"

"""Política de cache do parecer — o caminho de rejeição não cacheia (emenda ADR-199 · A40.l17)."""

from __future__ import annotations

from backend.app.services.parecer_orchestrator import (
    ParecerOrchestratorConfig,
    generate_parecer,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from tests.fakes.parecer import FailingLLM, FakeLLMService, make_valid_parecer_output


class TestNeedsReviewNaoEscreveCache:
    """O caminho de rejeição NÃO cacheia. Hoje isso vale só por topologia do
    call-graph (único ``_write_cache`` é pós-``finalize_output``); estes testes
    pinam o invariante para que a Decisão 3 revogada da lane não seja re-aberta
    por acidente. Cachear o placeholder o serviria de volta como ``status='Gerado'``
    — ver a emenda 2026-08-03 da ADR-199."""

    def _cfg(self, ws: str) -> ParecerOrchestratorConfig:
        return ParecerOrchestratorConfig(workspace_id=ws, tier="premium")

    def test_falha_de_llm_nao_cacheia(self):
        cache = InMemoryLLMCache()
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=self._cfg("ws-nr-llm"),
            llm_service=FailingLLM(),
            cache=cache,
        )
        assert result.status == "needs_review"
        assert cache._store == {}, "needs_review escreveu no cache"

    def test_sigilo_nao_cacheia(self):
        bad = make_valid_parecer_output().model_copy(
            update={
                "diagnostico_geral": (
                    "Família segue metodologia consagrada do mercado financeiro brasileiro "
                    "ainda com gaps. Aplicação direta de princípios Perini ajudaria."
                )
            }
        )
        cache = InMemoryLLMCache()
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=self._cfg("ws-nr-sigilo"),
            llm_service=FakeLLMService(output=bad),
            cache=cache,
        )
        assert result.status == "needs_review"
        assert cache._store == {}, "needs_review escreveu no cache"

    def test_llm_indisponivel_nao_cacheia(self, monkeypatch):
        """R2 — ``llm is None`` (sem ANTHROPIC_API_KEY): não há chamada nem cache."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cache = InMemoryLLMCache()
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=self._cfg("ws-nr-nokey"),
            llm_service=None,
            cache=cache,
        )
        assert result.status == "needs_review"
        assert cache._store == {}

    def test_sucesso_cacheia(self):
        """Contra-prova: o gate acima não é vacuamente verde — o sucesso escreve."""
        cache = InMemoryLLMCache()
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=self._cfg("ws-ok"),
            llm_service=FakeLLMService(output=make_valid_parecer_output()),
            cache=cache,
        )
        assert result.status == "Gerado"
        assert len(cache._store) == 1


class TestLeituraDeCacheEhFailOpen:
    """``_try_cache`` não pode derrubar o stage: ``LLMCacheBackend`` não tem
    ``delete`` e o TTL é 7 dias, então exceção na leitura = workspace travado
    até expirar. Simetria com ``_write_cache`` (ADR-144)."""

    def test_entrada_com_shape_alheio_vira_miss(self):
        class _PoisonedCache(InMemoryLLMCache):
            def get(self, key: str):
                return '{"nao":"e_um_parecer"}'

        fake = FakeLLMService(output=make_valid_parecer_output())
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=ParecerOrchestratorConfig(workspace_id="ws-poison", tier="premium"),
            llm_service=fake,
            cache=_PoisonedCache(),
        )
        assert result.status == "Gerado", "entrada envenenada deveria virar miss, não exceção"
        assert not result.cache_hit

    def test_backend_que_levanta_vira_miss(self):
        class _ExplodingCache(InMemoryLLMCache):
            def get(self, key: str):
                raise ConnectionError("redis down")

        fake = FakeLLMService(output=make_valid_parecer_output())
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=ParecerOrchestratorConfig(workspace_id="ws-redis", tier="premium"),
            llm_service=fake,
            cache=_ExplodingCache(),
        )
        assert result.status == "Gerado"
        assert not result.cache_hit

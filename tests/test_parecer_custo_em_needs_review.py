"""Custo/tokens sobrevivem ao caminho needs_review (A40.l17 · emenda ADR-199).

O run `2ded7aab` reportou `tokens {in:0,out:0}, cost_usd 0.0` no `output_summary`
enquanto o `llm_call_log` registrava 76.133/17.000 e US$ 0,4834: `_needs_review`
montava de `_base_result` (defaults 0) e nunca lia as métricas da chamada.
"""

from __future__ import annotations

from backend.app.services.parecer_orchestrator import (
    LLMCallMetrics,
    ParecerOrchestratorConfig,
    generate_parecer,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from tests.fakes.parecer import FailingLLM, FakeLLMService, make_valid_parecer_output

# Valores do FakeLLMCallResult em tests/fakes/parecer.py — pinados aqui de propósito:
# se o fake mudar, este teste tem de falhar em vez de seguir medindo outra coisa.
_FAKE_TOKENS_IN = 1234
_FAKE_TOKENS_OUT = 567
_FAKE_COST = 0.0123


def _cfg(ws: str) -> ParecerOrchestratorConfig:
    return ParecerOrchestratorConfig(workspace_id=ws, tier="premium")


def _sigilo_output():
    return make_valid_parecer_output().model_copy(
        update={
            "diagnostico_geral": (
                "Família segue metodologia consagrada do mercado financeiro brasileiro "
                "ainda com gaps. Aplicação direta de princípios Perini ajudaria."
            )
        }
    )


class TestCustoSobreviveAoNeedsReview:
    def test_sigilo_reporta_custo_da_chamada(self):
        """Rejeição pós-chamada: a API cobrou, então o custo tem de aparecer."""
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=_cfg("ws-cost-sigilo"),
            llm_service=FakeLLMService(output=_sigilo_output()),
            cache=InMemoryLLMCache(),
        )
        assert result.status == "needs_review"
        assert result.tokens_in == _FAKE_TOKENS_IN
        assert result.tokens_out == _FAKE_TOKENS_OUT
        assert result.cost_usd == _FAKE_COST
        assert result.cost_known is True

    def test_paridade_de_campos_com_o_sucesso(self):
        """Mesma chamada, mesmo custo — o desfecho não pode mudar a contabilidade."""
        ok = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=_cfg("ws-cost-ok"),
            llm_service=FakeLLMService(output=make_valid_parecer_output()),
            cache=InMemoryLLMCache(),
        )
        nr = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=_cfg("ws-cost-nr"),
            llm_service=FakeLLMService(output=_sigilo_output()),
            cache=InMemoryLLMCache(),
        )
        assert nr.status == "needs_review" and ok.status == "Gerado"
        assert (nr.tokens_in, nr.tokens_out, nr.cost_usd) == (
            ok.tokens_in,
            ok.tokens_out,
            ok.cost_usd,
        )


class TestZeroLegitimoContinuaZero:
    """Polaridade pinada: sem isto o fix drifta para "sempre não-zero"."""

    def test_llm_indisponivel_e_zero_conhecido(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=_cfg("ws-zero-nokey"),
            llm_service=None,
            cache=InMemoryLLMCache(),
        )
        assert result.status == "needs_review"
        assert (result.tokens_in, result.tokens_out, result.cost_usd) == (0, 0, 0.0)
        assert result.cost_known is True, "nenhuma tentativa: zero é fato, não lacuna"

    def test_cache_hit_nao_cobra(self):
        cache = InMemoryLLMCache()
        cfg = _cfg("ws-zero-hit")
        e5 = {"patrimonio": {"bruto": 1}}
        generate_parecer(
            e5_data=e5,
            config=cfg,
            llm_service=FakeLLMService(output=make_valid_parecer_output()),
            cache=cache,
        )
        hit = generate_parecer(
            e5_data=e5,
            config=cfg,
            llm_service=FakeLLMService(output=make_valid_parecer_output()),
            cache=cache,
        )
        assert hit.cache_hit
        assert (hit.tokens_in, hit.tokens_out, hit.cost_usd) == (0, 0, 0.0)
        assert hit.cost_known is True


class TestFalhaSemRegistroEhDesconhecido:
    """`LLMService.call` só faz `summary.calls.append` após `create()` retornar, então
    falha pós-cobrança (reask storm, timeout) não deixa entry. Reportar 0.0 como
    certo mentiria na classe mais cara — vira `cost_known=False`."""

    def test_falha_de_llm_marca_custo_desconhecido(self):
        result = generate_parecer(
            e5_data={"patrimonio": {"bruto": 1}},
            config=_cfg("ws-unknown"),
            llm_service=FailingLLM(),
            cache=InMemoryLLMCache(),
        )
        assert result.status == "needs_review"
        assert result.cost_usd == 0.0
        assert result.cost_known is False, "ausência de entry é desconhecido, não grátis"


class TestLLMCallMetrics:
    def test_sentinela_de_nenhuma_chamada_e_zero_conhecido(self):
        assert LLMCallMetrics() == LLMCallMetrics(0, 0, 0.0, True)

    def test_e_frozen(self):
        import dataclasses

        import pytest

        with pytest.raises(dataclasses.FrozenInstanceError):
            LLMCallMetrics().tokens_in = 9  # type: ignore[misc]

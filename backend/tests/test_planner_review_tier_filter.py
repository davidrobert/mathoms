"""Tier filter (ADR-208) — testa free teaser + premium passthrough + sigilo."""

from __future__ import annotations

import pytest

from backend.app.schemas.dto.planner_review.response import (
    ParecerPlanejadorContent,
)
from backend.app.services.planner_review_tier_filter import (
    FREE_TIER_LIMITS,
    PREMIUM_TIER_LIMITS,
    apply_tier_filter,
)

# --------------------------------------------------------------------------
# Fixtures — artifact dict no shape de pipeline_artifacts.content_json
# --------------------------------------------------------------------------


def _meta() -> dict:
    return {
        "persona_hash": "a" * 64,
        "manifest_version": "1.0",
        "schema_version": "1.0",
        "model_id": "anthropic/claude-sonnet-4-20250514",
        "tier_at_generation": "premium",
        "generated_at": "2026-05-13T16:00:00+00:00",
    }


def _ponto(titulo: str, ancora: str = "perini") -> dict:
    return {
        "titulo": titulo,
        "descricao": f"descricao de {titulo}",
        "ancora_metodologica": ancora,
        "tema_canonico": "Alocação",
        "section_id": "S3",
    }


def _risco(titulo: str, severidade: str) -> dict:
    return {
        "severidade": severidade,
        "titulo": titulo,
        "descricao": f"descricao de {titulo}",
        "ancora_metodologica": "perini",
        "tema_canonico": "Saúde de balanço",
        "evidencia": None,
        "evidencia_path": None,
        "section_id": "S1",
        "confianca": "alta",
    }


def _sugestao(prio: str, dedup: str = "f" * 64) -> dict:
    return {
        "prioridade": prio,
        "acao": "ajustar TRS para 4%",
        "impacto_qualitativo": "reduz risco da carteira",
        "ancora_metodologica": "convergencia",
        "tema_canonico": "Renda passiva",
        "confianca": "media",
        "section_id": "S7",
        "suggestion_dedup_key": dedup,
    }


def _metrica() -> dict:
    return {
        "nome": "TRS",
        "valor_atual": "0.5%",
        "target": "4%",
        "frequencia_revisao": "trimestral",
        "section_id": "S7",
        "ancora_metodologica": "perini",
        "tema_canonico": "Renda passiva",
    }


def _nota(titulo: str = "Cerbasi") -> dict:
    return {
        "titulo": titulo,
        "conteudo": "conteudo da nota metodologica para teste com tamanho minimo de 20 chars",
        "ancoras_metodologicas": ["cerbasi", "convergencia"],
        "temas_canonicos": ["Equilíbrio presente-futuro"],
    }


def _artifact() -> dict:
    return {
        "version": "1.0",
        "metadata": _meta(),
        "diagnostico_geral": "diagnostico de teste com tamanho minimo aceito pelo schema",
        "pontos_fortes": [_ponto(f"forte-{i}") for i in range(5)],
        "riscos": [
            _risco("R-baixa", "Baixa"),
            _risco("R-critica", "Crítica"),
            _risco("R-alta", "Alta"),
            _risco("R-media", "Média"),
        ],
        "sugestoes_execucao": [_sugestao("P0", "a" * 64), _sugestao("P1", "b" * 64)],
        "sugestoes_taticas": [_sugestao("P1", "c" * 64)],
        "sugestoes_estrategicas": [_sugestao("P2", "d" * 64), _sugestao("P2", "e" * 64)],
        "metricas": [_metrica() for _ in range(4)],
        "notas_metodologicas": [_nota(), _nota("Perini")],
    }


# --------------------------------------------------------------------------
# Premium tier — passa tudo, gated_counts zerados
# --------------------------------------------------------------------------


def test_premium_passes_all_items():
    content, total = apply_tier_filter(artifact=_artifact(), tier="premium")

    assert isinstance(content, ParecerPlanejadorContent)
    assert total == 0
    assert len(content.pontos_fortes) == 5
    assert len(content.riscos) == 4
    assert len(content.sugestoes_execucao) == 2
    assert len(content.metricas) == 4
    assert len(content.notas_metodologicas) == 2
    assert content.meta.tier_at_generation == "premium"
    assert content.meta.gated_counts.pontos_fortes == 0
    assert content.meta.gated_counts.riscos == 0


def test_premium_preserves_diagnostico():
    content, _ = apply_tier_filter(artifact=_artifact(), tier="premium")
    assert "diagnostico" in content.diagnostico_geral


# --------------------------------------------------------------------------
# Free tier — teaser de 3 pontos + 1 risco (pior severidade)
# --------------------------------------------------------------------------


def test_free_truncates_to_teaser_limits():
    content, total = apply_tier_filter(artifact=_artifact(), tier="free")

    assert len(content.pontos_fortes) == FREE_TIER_LIMITS.pontos_fortes == 3
    assert len(content.riscos) == FREE_TIER_LIMITS.riscos == 1
    assert content.sugestoes_execucao == []
    assert content.sugestoes_taticas == []
    assert content.sugestoes_estrategicas == []
    assert content.metricas == []
    assert content.notas_metodologicas == []
    # 2 + 3 + 2 + 1 + 2 + 4 + 2 = 16
    assert total == 16


def test_free_risco_is_worst_severity_first():
    """Free vê o RISCO mais grave (Crítica > Alta > Média > Baixa)."""
    content, _ = apply_tier_filter(artifact=_artifact(), tier="free")
    assert content.riscos[0].severidade == "Crítica"


def _gc_sum(gc) -> int:
    return (
        gc.pontos_fortes
        + gc.riscos
        + gc.sugestoes_execucao
        + gc.sugestoes_taticas
        + gc.sugestoes_estrategicas
        + gc.metricas
        + gc.notas_metodologicas
    )


def test_free_gated_counts_detail():
    content, total = apply_tier_filter(artifact=_artifact(), tier="free")
    gc = content.meta.gated_counts
    assert gc.pontos_fortes == 2  # 5 - 3
    assert gc.riscos == 3  # 4 - 1
    assert gc.sugestoes_execucao == 2
    assert gc.sugestoes_taticas == 1
    assert gc.sugestoes_estrategicas == 2
    assert gc.metricas == 4
    assert gc.notas_metodologicas == 2
    assert _gc_sum(gc) == total


def test_free_meta_tier_set():
    content, _ = apply_tier_filter(artifact=_artifact(), tier="free")
    assert content.meta.tier_at_generation == "free"


# --------------------------------------------------------------------------
# Sigilo §13 — DTO não expõe `ancora_metodologica`
# --------------------------------------------------------------------------


def test_dto_strips_ancora_metodologica_from_pontos():
    """Sigilo §13 (ADR-207): UI nunca recebe `ancora_metodologica`."""
    content, _ = apply_tier_filter(artifact=_artifact(), tier="premium")
    for p in content.pontos_fortes:
        assert "ancora_metodologica" not in p.model_dump()


def test_dto_strips_ancora_metodologica_from_riscos():
    content, _ = apply_tier_filter(artifact=_artifact(), tier="premium")
    for r in content.riscos:
        assert "ancora_metodologica" not in r.model_dump()


def test_dto_strips_ancora_metodologica_from_sugestoes():
    content, _ = apply_tier_filter(artifact=_artifact(), tier="premium")
    for s in content.sugestoes_execucao:
        assert "ancora_metodologica" not in s.model_dump()


def test_dto_maps_ancoras_to_temas_canonicos_in_notas():
    content, _ = apply_tier_filter(artifact=_artifact(), tier="premium")
    for n in content.notas_metodologicas:
        # Note DTO usa `temas_canonicos`, não `ancoras_metodologicas`.
        dump = n.model_dump()
        assert "ancoras_metodologicas" not in dump
        assert "temas_canonicos" in dump


# --------------------------------------------------------------------------
# Edge cases
# --------------------------------------------------------------------------


def test_empty_artifact_returns_empty_content():
    artifact = {
        "version": "1.0",
        "metadata": _meta(),
        "diagnostico_geral": "x" * 60,
    }
    content, total = apply_tier_filter(artifact=artifact, tier="premium")
    assert content.pontos_fortes == []
    assert content.riscos == []
    assert total == 0


def test_premium_keeps_suggestion_dedup_key():
    """`suggestion_dedup_key` é exposto p/ frontend chamar /accept idempotente."""
    content, _ = apply_tier_filter(artifact=_artifact(), tier="premium")
    assert content.sugestoes_execucao[0].suggestion_dedup_key == "a" * 64


def test_constants_are_sensible():
    """Sanity: FREE_TIER_LIMITS é estritamente mais restritivo que PREMIUM."""
    assert FREE_TIER_LIMITS.pontos_fortes is not None
    assert FREE_TIER_LIMITS.riscos is not None
    assert PREMIUM_TIER_LIMITS.pontos_fortes is None
    assert PREMIUM_TIER_LIMITS.riscos is None

"""Cap de geração do parecer — máx. 3 sugestões/horizonte (ADR-290 F3); prompt (regra 13) é best-effort, o truncamento determinístico em finalize_output é o invariante."""

from __future__ import annotations

from typing import Optional

from backend.app.services.parecer_finalization import (
    GENERATION_CAP_PER_HORIZON,
    _truncate_horizon,
    finalize_output,
)
from pipeline.llm.schemas.parecer_planejador import (
    ImpactoEstimado,
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
    Sugestao,
)


def _impacto(valor_brl: Optional[float] = None) -> Optional[ImpactoEstimado]:
    if valor_brl is None:
        return None
    return ImpactoEstimado(
        valor_estimado_brl=valor_brl, unidade="ano", caveat="estimativa sintetica de teste"
    )


def make_sugestao(
    acao: str, *, prioridade: str = "P1", valor_brl: Optional[float] = None
) -> Sugestao:
    impacto = _impacto(valor_brl)
    return Sugestao(
        prioridade=prioridade,
        acao=acao,
        impacto_qualitativo="impacto qualitativo sintetico de teste",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        confianca="alta" if impacto else "media",
        section_id="S1",
        suggestion_dedup_key="0" * 64,
        impacto_estimado=impacto,
    )


def test_horizonte_dentro_do_cap_intocado():
    sugs = [make_sugestao(f"acao numero {i}") for i in range(3)]
    assert _truncate_horizon(sugs) == sugs


def test_trunca_para_3_mantendo_maior_impacto_e_ordem_original():
    sugs = [
        make_sugestao("impacto baixo aqui", valor_brl=1_000.0),
        make_sugestao("impacto alto aqui!", valor_brl=90_000.0),
        make_sugestao("sem impacto nenhum"),
        make_sugestao("impacto medio aqui", valor_brl=50_000.0),
        make_sugestao("impacto medio menor", valor_brl=20_000.0),
    ]
    kept = _truncate_horizon(sugs)
    assert len(kept) == GENERATION_CAP_PER_HORIZON
    acoes = [s.acao for s in kept]
    assert acoes == ["impacto alto aqui!", "impacto medio aqui", "impacto medio menor"]


def test_p0_sem_valor_nunca_cortado_por_impacto_alto():
    """Proteção fiduciária: P0 (danger) sem valor monetário não é rebaixado."""
    sugs = [
        make_sugestao("p1 com valor altissimo", valor_brl=900_000.0),
        make_sugestao("p0 critico sem valor", prioridade="P0"),
        make_sugestao("p1 valor alto aqui", valor_brl=100_000.0),
        make_sugestao("p1 valor medio aqui", valor_brl=50_000.0),
    ]
    kept = _truncate_horizon(sugs)
    assert "p0 critico sem valor" in [s.acao for s in kept]
    assert len(kept) == GENERATION_CAP_PER_HORIZON


_PONTO = PontoForte(
    titulo="ponto forte",
    descricao="descricao sintetica",
    ancora_metodologica="convergencia",
)

_METADATA = Metadata(
    persona_hash="a" * 64,
    manifest_version="1.0",
    model_id="placeholder",
    tier_at_generation="premium",
    generated_at="2026-06-12T00:00:00+00:00",
)


def _make_output(sugs: list[Sugestao]) -> ParecerPlanejadorOutput:
    return ParecerPlanejadorOutput(
        version="1.0",
        metadata=_METADATA,
        diagnostico_geral="diagnostico minimo aceito pelo schema validator do output",
        pontos_fortes=[_PONTO] * 3,
        riscos=[],
        sugestoes_execucao=sugs,
        sugestoes_taticas=[],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
    )


def test_finalize_output_aplica_cap_e_dedup_keys():
    sugs = [make_sugestao(f"acao distinta numero {i}", valor_brl=float(i * 1000)) for i in range(5)]
    out = finalize_output(
        output=_make_output(sugs),
        workspace_id="ws-cap",
        tier="premium",
        model_id="m",
        persona_hash="b" * 64,
        manifest_version="1.4",
    )
    assert len(out.sugestoes_execucao) == GENERATION_CAP_PER_HORIZON
    keys = {s.suggestion_dedup_key for s in out.sugestoes_execucao}
    assert len(keys) == GENERATION_CAP_PER_HORIZON
    assert all(k != "0" * 64 for k in keys)

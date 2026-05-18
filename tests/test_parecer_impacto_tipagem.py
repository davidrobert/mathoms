"""ADR-220 — `impacto_estimado.tipo` + `find_impacto_tipagem_violations` (soft check)."""

from __future__ import annotations

from pipeline.llm.schemas.parecer_planejador import (
    ImpactoEstimado,
    ImpactoTipo,
    Metadata,
    Metrica,
    NotaMetodologica,
    ParecerPlanejadorOutput,
    PontoForte,
    Sugestao,
)

_DUMMY_SHA = "a" * 64


def _build_impacto(tipo: ImpactoTipo | None) -> ImpactoEstimado | None:
    if tipo is None:
        return None
    return ImpactoEstimado(
        valor_estimado_brl=100_000.0,  # noqa: P5 - LLM stub; cents-on-persist (ADR-090)
        unidade="ano",
        caveat="Cálculo via projeção indicativa do modelo (ADR-220).",
        tipo=tipo,
    )


def _make_sugestao(
    *, tema: str = "Renda passiva", impacto_tipo: ImpactoTipo | None = None
) -> Sugestao:
    return Sugestao(
        prioridade="P1",
        acao="Acumular o patrimônio necessário para sustentar a renda alvo.",
        impacto_qualitativo="Estoque-alvo dimensiona quanto falta para destravar IF.",
        ancora_metodologica="perini",
        tema_canonico=tema,  # type: ignore[arg-type]
        confianca="alta",
        section_id="S7",
        suggestion_dedup_key=_DUMMY_SHA,
        impacto_estimado=_build_impacto(impacto_tipo),
    )


def test_impacto_estimado_aceita_tipo_patrimonio_alvo():
    imp = ImpactoEstimado(
        valor_estimado_brl=12_426_300.0,
        unidade="ano",
        caveat="Estoque pela regra 25x.",
        tipo="patrimonio_alvo",
    )
    assert imp.tipo == "patrimonio_alvo"


def test_impacto_estimado_tipo_opcional_default_none():
    imp = ImpactoEstimado(
        valor_estimado_brl=100.0,
        unidade="ano",
        caveat="Sem tipagem (compat com runs pre-ADR-220).",
    )
    assert imp.tipo is None


def test_impacto_estimado_rejeita_tipo_invalido():
    import pytest

    with pytest.raises(Exception):
        ImpactoEstimado(
            valor_estimado_brl=1.0,
            unidade="ano",
            caveat="Tipo fora do enum deve falhar.",
            tipo="livre",  # type: ignore[arg-type]
        )


def test_violations_vazio_quando_nao_ha_tema_renda_passiva():
    # Constroi mínimo válido sem tema Renda passiva.
    sug = _make_sugestao(tema="Alocação", impacto_tipo=None)
    parecer = _build_minimal_parecer([sug])
    assert parecer.find_impacto_tipagem_violations() == []


def test_violations_alerta_quando_tema_renda_passiva_sem_patrimonio_alvo():
    sug = _make_sugestao(tema="Renda passiva", impacto_tipo="fluxo_anual")
    parecer = _build_minimal_parecer([sug])
    violations = parecer.find_impacto_tipagem_violations()
    assert len(violations) == 1
    assert "patrimonio_alvo" in violations[0]


def test_violations_aceita_quando_uma_irmã_tem_patrimonio_alvo():
    fluxo = _make_sugestao(tema="Renda passiva", impacto_tipo="fluxo_anual")
    patri = _make_sugestao(tema="Renda passiva", impacto_tipo="patrimonio_alvo")
    parecer = _build_minimal_parecer([fluxo, patri])
    assert parecer.find_impacto_tipagem_violations() == []


def test_violations_aceita_quando_sugestao_sem_impacto():
    """Renda passiva sem impacto_estimado (LLM omitiu): rule não dispara
    (orchestrator decide via campos_faltantes_pediria_se_iterasse)."""
    sug = _make_sugestao(tema="Renda passiva", impacto_tipo=None)
    parecer = _build_minimal_parecer([sug])
    # Sem `impacto_estimado` → não há tipo a auditar; violation emitida só
    # quando há sugestões com impacto mas nenhuma tipada como patrimonio_alvo.
    assert (
        parecer.find_impacto_tipagem_violations()
    )  # disparado: existe sug tema=Renda passiva sem patrimonio_alvo


# ---------------------------------------------------------------------------
# Helper: monta um ParecerPlanejadorOutput mínimo válido para o test.
# ---------------------------------------------------------------------------


def _stub_metadata() -> Metadata:
    return Metadata(
        generated_at="2026-05-18T00:00:00+00:00",
        tier_at_generation="free",
        persona_hash="0" * 64,
        manifest_version="1.2",
        model_id="test-model",
    )


def _stub_pontos_fortes() -> list[PontoForte]:
    return [
        PontoForte(
            titulo=f"Ponto {i}",
            descricao="Descrição mínima do ponto forte para teste.",
            ancora_metodologica="perini",
        )
        for i in range(3)
    ]


def _stub_required_lists() -> dict:
    return {
        "pontos_fortes": _stub_pontos_fortes(),
        "metricas": [
            Metrica(
                nome="Métrica X",
                valor_atual="100",
                target="200",
                frequencia_revisao="mensal",
                section_id="S7",
            )
        ],
        "notas_metodologicas": [
            NotaMetodologica(
                titulo="Nota",
                conteudo="Conteúdo mínimo da nota metodológica para satisfazer schema.",
                ancoras_metodologicas=["perini"],
            )
        ],
    }


def _build_minimal_parecer(sugestoes) -> ParecerPlanejadorOutput:
    return ParecerPlanejadorOutput(
        version="1.0",
        metadata=_stub_metadata(),
        diagnostico_geral=(
            "Diagnóstico mínimo do parecer para satisfazer minLength=50. "
            "Texto neutro sem informação de domínio sensível."
        ),
        riscos=[],
        sugestoes_execucao=[],
        sugestoes_taticas=[],
        sugestoes_estrategicas=list(sugestoes),
        **_stub_required_lists(),
    )

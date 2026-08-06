"""A40.l10 PR2 · [[ADR-365]] — elegibilidade e proveniência da premissa.

Contrato: só `elegibilidade == computavel` entra no ranking; o resto é
**declarado** com a classe de motivo (a 6ª classe do §Critério de done do
PLAN-report-trust proíbe retenção de conselho sem declaração). O campo novo
atravessa **três** construtores campo-a-campo em série — `PontoUrgenteItem.to_dict`,
`E5OutputInputs` e o emissor de `build_e5_output` — e o padrão "construtor
campo-a-campo perde campo novo" já mordeu este repo. Por isso as provas de
travessia são **derivadas de `dataclasses.fields()`**, nunca enumeradas à mão:
enumerar repetiria a mesma omissão duas vezes.
"""

from __future__ import annotations

import dataclasses
from typing import Any, get_args

from pipeline.domain.services.e5_serialization import (
    E5OutputInputs,
    build_default_tarefas,
    build_e5_output,
    partition_pontos_urgentes,
)
from pipeline.domain.services.narrativas import NarrativasContext, SummariesNarrator
from pipeline.domain.services.pontos_urgentes_analyzer import (
    Elegibilidade,
    OrigemPremissa,
    PontoUrgenteItem,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics


def _item(**kw: Any) -> PontoUrgenteItem:
    base = {
        "prioridade": "Alta",
        "acao": "Ação",
        "impacto": "Impacto",
        "prazo": "Imediato",
        "code": "regra_x",
    }
    return PontoUrgenteItem(**{**base, **kw})  # type: ignore[arg-type]


# ── Travessia do campo pelos construtores campo-a-campo ───────────────


def test_to_dict_nao_perde_campo_do_dataclass():
    campos = {f.name for f in dataclasses.fields(PontoUrgenteItem)}
    assert set(_item().to_dict()) == campos


def test_output_e5_carrega_todo_campo_do_item_retido():
    """Prova a cadeia inteira: dataclass → to_dict → E5OutputInputs → output."""
    retido = _item(elegibilidade="pendente_de_dado", dado_faltante="composição da família")
    out = build_e5_output(_output_inputs(retidos=[retido.to_dict()]))
    assert out["pontos_urgentes_retidos"], "o array não chegou ao output do E5"
    assert set(out["pontos_urgentes_retidos"][0]) == {
        f.name for f in dataclasses.fields(PontoUrgenteItem)
    }


def test_chave_de_retidos_existe_mesmo_vazia():
    """Ausência de chave e ausência de retenção são coisas diferentes: o leitor
    não pode ter de distinguir `None` de `[]`."""
    out = build_e5_output(_output_inputs(retidos=[]))
    assert out["pontos_urgentes_retidos"] == []


# ── Partição ──────────────────────────────────────────────────────────


def test_particao_manda_so_computavel_ao_ranking():
    itens = [
        _item(code="a", elegibilidade="computavel").to_dict(),
        _item(code="b", elegibilidade="degenerada").to_dict(),
        _item(code="c", elegibilidade="nao_verificavel").to_dict(),
        _item(code="d", elegibilidade="pendente_de_dado").to_dict(),
    ]
    ranq, ret = partition_pontos_urgentes(itens)
    assert [i["code"] for i in ranq] == ["a"]
    assert [i["code"] for i in ret] == ["b", "c", "d"]


def test_particao_nao_perde_item():
    """Todo item cai em exatamente um lado — retenção silenciosa é o defeito."""
    itens = [_item(code=f"c{i}", elegibilidade=e).to_dict() for i, e in enumerate(_VALORES_ELEG)]
    ranq, ret = partition_pontos_urgentes(itens)
    assert len(ranq) + len(ret) == len(itens)
    assert {i["code"] for i in ranq} | {i["code"] for i in ret} == {i["code"] for i in itens}


def test_item_sem_o_campo_e_tratado_como_computavel():
    """Artefato antigo em `pipeline_artifacts` não tem o campo e não é revalidado
    na leitura: ausência não pode virar retenção retroativa."""
    ranq, ret = partition_pontos_urgentes([{"acao": "Legado", "prioridade": "Alta"}])
    assert len(ranq) == 1 and not ret


def test_tarefas_projetam_so_o_ranking():
    """`tarefas` é alias com perda e não recebe item retido (ADR-365 §Consequências)."""
    ranq, _ = partition_pontos_urgentes(
        [
            _item(code="a").to_dict(),
            _item(code="b", elegibilidade="degenerada").to_dict(),
        ]
    )
    assert [t["t"] for t in build_default_tarefas(ranq)] == ["Ação"]


# ── Declaração narrada — o leitor que legitima o array ────────────────


def _s10(retidas: list[dict[str, str]]) -> str:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = {**_build_metrics(), "recomendacoes_retidas": retidas}
    return SummariesNarrator(ctx).narrate(metrics, _FAMILY_BASE, ["r"], ["d1"])["s10"]


def test_s10_declara_uma_frase_por_classe_de_motivo():
    s10 = _s10(
        [
            {
                "acao": "Contratar seguro de vida",
                "motivo": "a regra atual não distingue o seu caso",
            },
            {"acao": "Consolidar rentabilidade", "motivo": "falta rentabilidade da carteira"},
        ]
    )
    assert "2 recomendações não entraram na lista" in s10
    assert "Contratar seguro de vida (a regra atual não distingue o seu caso)" in s10
    assert "Consolidar rentabilidade (falta rentabilidade da carteira)" in s10


def test_s10_singular_com_uma_retida():
    s10 = _s10([{"acao": "Contratar seguro de vida", "motivo": "falta a composição da família"}])
    assert "1 recomendação não entrou na lista" in s10
    assert "1 recomendações" not in s10


def test_s10_sem_retidas_nao_menciona_retencao():
    assert "não entrou na lista" not in _s10([])
    assert "não entraram na lista" not in _s10([])


def test_vocabulario_do_enum_nunca_aparece_no_texto():
    """ADR-365 §D5: a copy nomeia o dado que falta, não o estado interno."""
    s10 = _s10([{"acao": "Contratar seguro de vida", "motivo": "falta a composição da família"}])
    for jargao in (*_VALORES_ELEG, *get_args(OrigemPremissa), "elegibilidade", "origem_premissa"):
        assert jargao not in s10, f"jargão de implementação vazou para a tela: {jargao}"


_VALORES_ELEG = get_args(Elegibilidade)


_BLOCOS_VAZIOS = (
    "patrimonio",
    "goals",
    "fluxo",
    "ratios",
    "score",
    "orcamento",
    "reserva",
    "endividamento",
    "previdencia",
    "investimentos_classes",
    "equilibrio_cerbasi",
    "consumo",
    "cenarios_conjuge",
)


def _output_inputs(*, retidos: list[dict[str, Any]]) -> E5OutputInputs:
    return E5OutputInputs(
        periodo_dados="2026-01 a 2026-06",
        data_analise="2026-08-06",
        pontos_fortes=[],
        pontos_urgentes=[],
        diagnostico=[],
        pontos_urgentes_retidos=retidos,
        **{nome: {} for nome in _BLOCOS_VAZIOS},
    )

"""Enforcement por-item no strict (ADR-295) — lógica pura, sem LLM."""

from __future__ import annotations

from backend.app.services.parecer_strict_enforcement import enforce_strict_per_item
from pipeline.llm.schemas.parecer_planejador import Ancora, Risco, Sugestao
from tests.test_parecer_planejador_golden import make_canned_output


def _risco(severidade: str, titulo: str = "Risco sintético de enforcement") -> Risco:
    return Risco(
        severidade=severidade,
        titulo=titulo,
        descricao="Descrição sintética do item para enforcement.",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        section_id="S1",
        confianca="alta",
        ancoras=[Ancora(path="$.reserva_emergencia.total_liquida", rotulo="reserva_emergencia")],
    )


def _all_canned_sugestoes() -> list[Sugestao]:
    c = make_canned_output()
    return c.sugestoes_execucao + c.sugestoes_taticas + c.sugestoes_estrategicas


def _sugestao(prioridade: str) -> Sugestao:
    """Clona uma sugestão canônica e troca só a prioridade (campos obrigatórios intactos)."""
    return _all_canned_sugestoes()[0].model_copy(update={"prioridade": prioridade})


def _output(riscos=None, **horizons):
    update = {}
    if riscos is not None:
        update["riscos"] = riscos
    update.update(horizons)
    return make_canned_output().model_copy(update=update)


def test_no_hard_violations_passa_intacto():
    out = _output(riscos=[_risco("Baixa")])
    d = enforce_strict_per_item(out, [])
    assert d.needs_review_reason is None and d.dropped == () and d.output is out


def test_missing_path_nao_e_hard():
    out = _output(riscos=[_risco("Baixa")])
    d = enforce_strict_per_item(out, ["risco:0:missing_path"])
    assert d.needs_review_reason is None and d.dropped == ()


def test_risco_alta_hard_vira_needs_review():
    out = _output(riscos=[_risco("Alta")])
    d = enforce_strict_per_item(out, ["risco:0:pairing_mismatch"])
    assert d.needs_review_reason == "evidencia unverified (severidade alta): risco:0"
    assert d.dropped == ()


def test_risco_critica_hard_vira_needs_review():
    out = _output(riscos=[_risco("Crítica")])
    d = enforce_strict_per_item(out, ["risco:0:whitelist_miss"])
    assert d.needs_review_reason is not None


def test_risco_baixa_hard_e_descartado():
    out = _output(riscos=[_risco("Baixa"), _risco("Média", "Mantido")])
    d = enforce_strict_per_item(out, ["risco:0:pairing_mismatch"])
    assert d.needs_review_reason is None
    assert d.dropped == (("risco", 0),)
    assert [r.titulo for r in d.output.riscos] == ["Mantido"]


def test_sugestao_p0_hard_vira_needs_review():
    out = _output(sugestoes_execucao=[_sugestao("P0")])
    d = enforce_strict_per_item(out, ["sugestoes_execucao:0:pairing_mismatch"])
    assert d.needs_review_reason is not None and d.dropped == ()


def test_sugestao_p2_hard_e_descartada():
    out = _output(sugestoes_taticas=[_sugestao("P2"), _sugestao("P1")])
    d = enforce_strict_per_item(out, ["sugestoes_taticas:0:resolve_null"])
    assert d.needs_review_reason is None
    assert len(d.output.sugestoes_taticas) == 1


def test_um_item_alto_entre_varios_bloqueia_tudo():
    out = _output(riscos=[_risco("Baixa"), _risco("Alta")])
    d = enforce_strict_per_item(out, ["risco:0:pairing_mismatch", "risco:1:pairing_mismatch"])
    assert d.needs_review_reason is not None and d.dropped == ()


def test_number_in_prose_baixa_severidade_e_descartado():
    """ADR-304: R$ digitado na prosa é hard — item ofensor cai, parecer segue."""
    out = _output(riscos=[_risco("Baixa"), _risco("Média", "Mantido")])
    d = enforce_strict_per_item(out, ["risco:0:number_in_prose"])
    assert d.needs_review_reason is None
    assert d.dropped == (("risco", 0),)
    assert [r.titulo for r in d.output.riscos] == ["Mantido"]


def test_number_in_prose_alta_vira_needs_review_com_motivo_proprio():
    out = _output(riscos=[_risco("Alta")])
    d = enforce_strict_per_item(out, ["risco:0:number_in_prose"])
    assert d.needs_review_reason == "valor monetário na prosa (severidade alta): risco:0"
    assert d.dropped == ()


def test_sugestao_p0_number_in_prose_vira_needs_review():
    out = _output(sugestoes_execucao=[_sugestao("P0")])
    d = enforce_strict_per_item(out, ["sugestoes_execucao:0:number_in_prose"])
    assert d.needs_review_reason is not None and d.dropped == ()


def test_item_com_citacao_errada_e_prosa_monetaria_cai_uma_vez():
    """Dedupe por (tipo, índice): items_dropped conta itens, não violações."""
    out = _output(riscos=[_risco("Baixa")])
    d = enforce_strict_per_item(out, ["risco:0:pairing_mismatch", "risco:0:number_in_prose"])
    assert d.needs_review_reason is None
    assert d.dropped == (("risco", 0),)
    assert d.output.riscos == []


def test_multiplos_baixos_descartados_juntos():
    out = _output(
        riscos=[_risco("Baixa"), _risco("Média")],
        sugestoes_execucao=[_sugestao("P2")],
    )
    d = enforce_strict_per_item(
        out,
        ["risco:0:pairing_mismatch", "risco:1:resolve_null", "sugestoes_execucao:0:whitelist_miss"],
    )
    assert d.needs_review_reason is None
    assert d.output.riscos == [] and d.output.sugestoes_execucao == []
    assert len(d.dropped) == 3

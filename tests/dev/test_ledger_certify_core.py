"""ledger-certify núcleo puro — vereditos + drift + sum-preserving (ADR-302/343)."""

from __future__ import annotations

from types import SimpleNamespace

from dev.ledger_certify_core import (
    DriftSummary,
    _drift,
    build_report,
    e3_group_verdict,
    e4_bucket_verdict,
    format_report,
)
from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    DEDUP_LEGITIMO,
    NAO_VERIFICAVEL,
    PERDA_SILENCIOSA,
    investment_double_count,
)
from dev.ledger_unit_verdicts import _NON_LEDGER_CHECKERS
from tests.dev._ledger_payloads import bucket_payload, e3_payload

_CROSS_GROUP_TITLE = "## Duplicação cross-grupo"


def e3_payload(
    n_tx: int, *, dups: int = 0, total: int | None = None, valores=None, remocoes=None
) -> dict:
    txns = [{"valor": v} for v in (valores if valores is not None else [1.0] * n_tx)]
    out = {
        "transacoes": txns,
        "transacoes_total": n_tx if total is None else total,
        "transacoes_duplicadas_removidas": dups,
    }
    if remocoes is not None:
        out["remocoes"] = remocoes
    return out


def _remocoes(*, cross_file: int = 0, collapse: int = 0) -> dict:
    """Partição de remoções na forma que `e3_load_report._remocoes` emite."""
    return {
        "undated_drop": {"count": 0, "valor_cents": 0},
        "anachronic": {"count": 0, "valor_cents": 0},
        "intra_statement_dedup": {"count": 0, "valor_cents": 0},
        "cross_file_dedup": {"count": cross_file, "valor_cents": 0},
        "cross_document_collapse": {"count": collapse, "valor_cents": 0},
    }


# ─────────── sum-preserving: o check que a conservação não vê (ADR-271) ───────────


def test_investment_double_count_falha_em_cenario_sum_preserving() -> None:
    """Total intacto, posição duplicada 2× — a soma fecha, o dedup não. É o modo
    de falha que a skill existe para caçar; a conservação agregada é cega a ele."""
    pos = {"tipo": "cdb", "instituicao": "itau", "descricao": "cdb pos"}
    investimentos = {"dados": [pos, dict(pos)], "total_geral": 100.0}
    collisions = investment_double_count(investimentos)
    assert collisions, "duplicata não detectada"
    assert e4_bucket_verdict("investimentos", investimentos, collisions)[0] == PERDA_SILENCIOSA


# ─────────────────────────── drift ───────────────────────────


def test_drift_particiona_matched_diff_only() -> None:
    fresh = {"a": e3_payload(5), "b": e3_payload(3), "c": e3_payload(2)}
    persisted = {"a": e3_payload(5), "b": e3_payload(4), "d": e3_payload(1)}
    d = _drift(fresh, persisted)
    assert d.matched == 1
    assert len(d.count_diff) == 1 and "b:" in d.count_diff[0]
    assert d.fresh_only == ["c"]
    assert d.persisted_only == ["d"]


# A42.l20 — o canal `remocoes` normaliza o count do drift. O harness re-deriva com
# `collapse_enforce` default `False`: o lado fresco MEDE o colapso e não remove, então
# declara `cross_document_collapse.count == 0` com as tx ainda em `transacoes_total`; o
# run pinado rodou com enforce e declara o mesmo colapso como remoção. Somar só
# `transacoes_duplicadas_removidas` (= canal `cross_file_dedup`) faz o par divergir pelo
# tamanho do colapso, e o relatório manda investigar keying/run-parcial — ambas falsas.


def test_drift_normaliza_pelo_canal_de_remocao_declarado() -> None:
    fresco = e3_payload(1000, dups=7, remocoes=_remocoes(cross_file=7, collapse=0))
    persistido = e3_payload(93, dups=7, total=93, remocoes=_remocoes(cross_file=7, collapse=907))
    d = _drift({"g": fresco}, {"g": persistido})
    assert d.count_diff == []
    assert d.matched == 1


def test_drift_ainda_acusa_divergencia_que_o_canal_nao_explica() -> None:
    """Não-inércia: normalizar não pode calar drift real (resíduo fora do canal)."""
    fresco = e3_payload(1000, dups=7, remocoes=_remocoes(cross_file=7, collapse=0))
    persistido = e3_payload(90, dups=7, total=90, remocoes=_remocoes(cross_file=7, collapse=907))
    d = _drift({"g": fresco}, {"g": persistido})
    assert len(d.count_diff) == 1 and "1007" in d.count_diff[0] and "1004" in d.count_diff[0]
    assert d.matched == 0


def test_drift_artefato_legado_sem_remocoes_mantem_formula_antiga() -> None:
    """Compat: sem `remocoes`, o count segue `total + transacoes_duplicadas_removidas`."""
    d = _drift({"g": e3_payload(5, dups=2)}, {"g": e3_payload(5, dups=2)})
    assert d.count_diff == [] and d.matched == 1
    d2 = _drift({"g": e3_payload(5, dups=2)}, {"g": e3_payload(5, dups=3)})
    assert len(d2.count_diff) == 1


# ─────────────────────────── build_report (síntese) ───────────────────────────


def _fake_result(
    n: int, with_key: int, transf: int = 0, valores: list[float] | None = None
) -> SimpleNamespace:
    vals = valores or [0.0] * n
    classified = [
        SimpleNamespace(natural_key=({"x": 1} if i < with_key else None), valor=vals[i])
        for i in range(n)
    ]
    return SimpleNamespace(
        classified=classified, cash_flow=SimpleNamespace(transferencias_count=transf)
    )


def _fake_e3_result() -> SimpleNamespace:
    return SimpleNamespace(
        statements_loaded=1, statements_reconciled=1, skipped_inputs=0, artifacts_written=1
    )


# Os quatro termos do destino em Σ|valor| ([[ADR-434]]): sem os dois `*_abs_cents` o
# veredito cai para `coberto` (fail-closed). Nenhuma row negativa nesta fixture ⇒
# abs == assinado e a ponte fecha em 0.
_SIGNALS_EIXO_VALOR = {
    "dedup_collapsed": "0",
    "dedup_collapsed_cents": "0",
    "transferencias_cents": "0",
    "despesas_abs_cents": "300",
    "receitas_abs_cents": "0",
    "despesas_negativas_cents": "0",
    "receitas_negativas_cents": "0",
}


def _conserving_e4(n_tx: int) -> dict:
    despesas = bucket_payload(3.0, {"a": 3.0}, {"a": [{"valor": 1.0}, {"valor": 2.0}]}, n_tx=n_tx)
    # O destino declara o eixo-VALOR ([[ADR-426]]); sem os dois cents o veredito
    # desta perna cai para `coberto` (ausência é não-medido, não "deu zero").
    despesas["_lineage"] = {"signals": {"tx_total": str(n_tx), **_SIGNALS_EIXO_VALOR}}
    return {
        "despesas": despesas,
        "receitas": bucket_payload(0.0, {}, {}, n_tx=0),
        "investimentos": {"dados": []},
    }


def _bloco(text: str, titulo: str) -> str:
    """Recorta um bloco ``## ...`` do relatório — o eixo de veredito é POR bloco."""
    assert titulo in text, f"bloco ausente: {titulo}"
    return titulo + text.split(titulo, 1)[1].split("\n## ", 1)[0]


def _report(e4: dict, *, valores: list[float], with_key: int, transf: int = 0, entregue=False):
    """``build_report`` sobre E3/E2 sintéticos coerentes com ``valores`` — o eixo do
    teste é o E4 passado. ``entregue=True`` põe o eixo E3 sobre o persistido, onde a
    âncora externa do LC5-03 **não é medível** (o E2 de hoje não descreve aquele run)."""
    fresh_e3 = {"g1": e3_payload(len(valores), valores=valores)}
    return build_report(
        "ws-uuid",
        "run-1",
        [{"transacoes": [{"valor": v} for v in valores]}],
        _fake_e3_result(),
        _fake_result(len(valores), with_key, transf=transf, valores=valores),
        e4,
        fresh_e3,
        persisted_e3=fresh_e3 if entregue else {},
    )


def test_build_report_synthetic_conserva() -> None:
    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1)
    assert [c.verdict for c in report.conservation] == [CONSERVADO, CONSERVADO]
    assert report.e3_groups[0].verdict == CONSERVADO
    assert report.natural_key["present"] == 1 and report.natural_key["total"] == 2
    bloco = _bloco(format_report(report), _CROSS_GROUP_TITLE)
    assert "cobertura=" in bloco and "partição do numerador" in bloco
    assert "massa não-varrida" in bloco and "histograma diagnóstico" in bloco
    assert "histograma por shape de whitelist" in bloco
    # DEDUP_LEGITIMO é veredito de grupo/balde: emprestá-lo ao rótulo de whitelist
    # contamina o eixo que o Passo 4 da skill manda varrer por token.
    assert DEDUP_LEGITIMO not in bloco
    assert "shape declarado explicado" in bloco


def test_drift_casa_o_grupo_quando_o_persistido_existe() -> None:
    """O eixo de drift precisa do persistido; a asserção morava no teste de conservação,
    que passou a rodar sobre a SOMBRA quando a âncora do LC5-03 entrou (A42.l3)."""
    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1, entregue=True)

    assert report.drift.matched == 1


def test_ancora_transfere_ao_entregue_quando_o_drift_e_zero() -> None:
    """Sem esta cláusula o eixo entregue perderia a nota máxima PARA SEMPRE — e é ele
    que a [[A42.l14]] tornou o sujeito da rubrica. Drift zero = mesma população."""
    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1, entregue=True)

    assert report.e3_subject == "entregue"
    assert report.e3_groups[0].verdict == CONSERVADO


def test_ancora_nao_transfere_ao_entregue_quando_ha_drift() -> None:
    """Com drift, a perna E2→E3 (computada sobre a sombra) não descreve o substrato
    entregue — transferi-la seria comparar através do tempo."""
    fresh = {"g1": e3_payload(2, valores=[1.0, 2.0])}
    persistido = {"g1": e3_payload(3, valores=[1.0, 2.0, 3.0])}
    report = build_report(
        "ws-uuid",
        "run-1",
        [{"transacoes": [{"valor": 1.0}, {"valor": 2.0}]}],
        _fake_e3_result(),
        _fake_result(2, 1, valores=[1.0, 2.0]),
        _conserving_e4(2),
        fresh,
        persistido,
    )

    assert report.e3_subject == "entregue" and report.drift.count_diff
    assert report.e3_groups[0].verdict == COBERTO_SEM_VALOR
    assert "COM drift vs a re-derivação" in report.e3_groups[0].detail


def test_perna_e2e3_declara_a_particao_da_populacao_e_o_residuo() -> None:
    """Item 8: as rows entre `semeado` e `count_in` existiam e nenhuma linha as
    declarava; e o gap era adjetivado ("sub-declaração") sem ser computado."""
    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1)
    bloco = _bloco(format_report(report), "## Conservação")

    assert "população E2: semeado 2 = reconciliável 2 + não-reconciliável 0" in bloco
    assert "identidade: 2 − 2 − 0 (excl. run-level) = resíduo **0**" in bloco


def _pernas(descricao: str, magnitude: float) -> list[dict]:
    """Duas pernas do MESMO evento com o shape do carrier ADR-354 (tipo_conta variante
    + titular assimétrico); ``magnitude`` é o float do wire E4 (ADR-090 §wire)."""
    row = {"data": "2026-03-10", "descricao": descricao, "valor": magnitude, "moeda": "BRL"}
    return [
        {**row, "tipo_conta": "extrato", "titular": ""},
        {**row, "tipo_conta": "extratoconta", "titular": "titular exemplo"},
    ]


_VALORES_CARRIER = [100.0, 100.0, 50.0, 50.0, 150.0, 150.0]


def _e4_com_carrier_cross_grupo() -> dict:
    """E4 cujos baldes fecham em cents E carregam 3 pares do carrier ADR-354 — em DOIS
    baldes e 3 categorias (a forma real do E4), duplicação sum-preserving."""
    despesas = bucket_payload(
        300.0,
        {"moradia": 200.0, "outros": 100.0},
        {"moradia": _pernas("aluguel", 100.0), "outros": _pernas("mercado", 50.0)},
        n_tx=4,
    )
    despesas["_lineage"] = {"signals": {"tx_total": "6", "dedup_collapsed": "0"}}
    return {
        "despesas": despesas,
        "receitas": bucket_payload(
            300.0, {"salario": 300.0}, {"salario": _pernas("salario", 150.0)}, 2
        ),
        "investimentos": {"dados": []},
    }


def _unidade(report, nome: str):
    """Veredito de balde por NOME — índice mudou com a ordem canônica (A42.l14)."""
    return next(b for b in report.e4_buckets if b.unit == nome)


def test_render_cross_grupo_com_cobertura_ok_e_numerador_positivo() -> None:
    """Os pares sum-preserving passam no veredito de balde e AINDA são reportados — é o
    modo de falha que a conservação por grupo aprova (razão de existir da A40.l1)."""
    report = _report(_e4_com_carrier_cross_grupo(), valores=_VALORES_CARRIER, with_key=6)
    # Por NOME: a lista segue `ARTIFACT_KEYS` (A42.l14), e o índice 0 afirmaria outro balde.
    assert _unidade(report, "despesas").verdict == CONSERVADO  # despesas fecha em cents
    assert len(report.cross_group.numerador) == 3
    assert report.cross_group.coverage["coverage_ok"] is True
    bloco = _bloco(format_report(report), _CROSS_GROUP_TITLE)
    assert "cobertura=OK" in bloco and "CEGA" not in bloco
    assert "carrier-shaped=3" in bloco and "coincidence-shaped=0" in bloco
    assert "[sombra · enforce omitido]" in bloco and "[off-git]" in bloco
    assert "[numerador KR-B]" not in bloco
    # O número IMPRESSO tem asserção própria (o do grão de dados está 3 linhas acima):
    # 3 ocorrências × 2 proveniências ⇒ Σ (P−1)·valor = 10000 + 5000 + 15000 cents.
    assert "não-explicada: 3 ocorrência(s)" in bloco
    assert "Σ excesso 30000 cents" in bloco
    # 3ª identidade: nenhum filtro silencioso entre o que o detector achou e o que
    # saiu particionado — sem ela, um piso de materialidade no numerador é invisível.
    assert "3ª identidade" in bloco and "⇒ fecha" in bloco


def test_format_report_so_uma_linha_kr_b_e_e_a_do_persistido() -> None:
    report = _report(_e4_com_carrier_cross_grupo(), valores=_VALORES_CARRIER, with_key=6)
    report.cross_group_entregue = report.cross_group
    report.entregue = {
        "run_id": "abcdef12-persist",
        "executor_revision": "deadbeef",
        "cortadas": 4,
        "retido_por_override": 0,
    }
    texto = format_report(report)
    assert texto.count("[numerador KR-B]") == 1
    assert "[numerador KR-B] · E3 persistido run abcdef12" in texto
    assert texto.count("[sombra · enforce omitido]") == 1
    assert "cortadas=4" in texto and "retido_por_override=0" in texto
    assert "executor_revision=deadbeef" in texto


def test_transferencias_count_do_result_chega_ao_bloco_cross_grupo() -> None:
    # RATCHET: a massa NÃO-VARRIDA (kind transferencia não vai a balde) é o contexto que
    # impede ler queda de numerador como progresso — e o fio result→summary→render não
    # tinha teste: hardcodar 0 no call-site de `cross_group_summary` passava verde.
    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1, transf=9)
    assert report.cross_group.nao_varrido == {"transferencias": 9}
    assert "transferencias=9" in _bloco(format_report(report), _CROSS_GROUP_TITLE)


def test_build_report_synthetic_detecta_drop_e3_para_e4() -> None:
    seeds = [{"transacoes": [{"valor": 1.0}, {"valor": 2.0}]}]
    fresh_e3 = {"g1": e3_payload(2, valores=[1.0, 2.0])}
    e4 = _conserving_e4(1)  # tx_total=1 mas E3 tem 2 survivors → dropou 1
    report = build_report(
        "ws-uuid", "run-1", seeds, _fake_e3_result(), _fake_result(1, 0), e4, fresh_e3, fresh_e3
    )
    assert report.conservation[1].verdict == PERDA_SILENCIOSA


def test_zero_write_ok_property() -> None:
    report = build_report(
        "ws",
        "r",
        [],
        _fake_e3_result(),
        _fake_result(0, 0),
        {"investimentos": {"dados": []}},
        {},
        {},
    )
    report.counts_before = {"pipeline_artifacts": 5}
    report.counts_after = {"pipeline_artifacts": 5}
    assert report.zero_write_ok
    report.counts_after = {"pipeline_artifacts": 6}
    assert not report.zero_write_ok


def _blast(sem_ancora_v2: int, sem_snapshot: int) -> dict:
    return {
        "ativos": 10,
        "ativos_com_snapshot": 10 - sem_snapshot,
        "titular_vazio": 2,
        "sem_snapshot": sem_snapshot,
        "sem_ancora_v2": sem_ancora_v2,
        "quarentenados": 0,
        "soft_deleted": 0,
    }


def test_blast_radius_deriva_a_identidade_em_vez_de_afirmar_em_prosa() -> None:
    # ADR-282: as_columns() escreve natural_key_hash e o snapshot juntos, logo os dois
    # contadores DEVEM coincidir. Prosa estática ("== por construção") diria o mesmo
    # texto com os números divergentes; a comparação derivada não.
    from dev.ledger_certify_core import _fmt_blast_radius

    fecha = "\n".join(_fmt_blast_radius(_blast(3, 3)))
    assert "sem_ancora_v2=3 == sem_snapshot=3" in fecha
    assert "contornou" not in fecha
    diverge = "\n".join(_fmt_blast_radius(_blast(5, 3)))
    assert "sem_ancora_v2=5 != (writer contornou as_columns) sem_snapshot=3" in diverge


def test_blast_radius_ausente_declara_nao_medido() -> None:
    from dev.ledger_certify_core import _fmt_blast_radius

    assert any("não medido" in linha for linha in _fmt_blast_radius({}))


def test_balde_ausente_no_sujeito_vira_linha_nao_verificavel() -> None:
    """D6: eixo sem insumo declara o motivo — omissão era indistinguível de conservado."""
    from dev.ledger_conservation import NAO_VERIFICAVEL

    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1)
    unidades = {b.unit: b for b in report.e4_buckets}
    assert unidades["patrimonio"].verdict == NAO_VERIFICAVEL
    assert unidades["patrimonio"].detail == "balde ausente no sujeito"


def test_os_sete_baldes_canonicos_sempre_geram_linha() -> None:
    # O fixture só traz despesas/receitas/investimentos: os outros 4 não geravam linha
    # NENHUMA antes — sumiam do relatório sem deixar rastro.
    report = _report(_conserving_e4(2), valores=[1.0, 2.0], with_key=1)
    bloco = _bloco(format_report(report), "## Eixo E4 (por balde)")
    assert all(k in bloco for k in ("seguros", "pontos_milhas", "fluxo_mensal_detalhado"))


def test_glosa_do_drift_nao_atribui_causa_a_rechaveacao() -> None:
    """ADR-421 M1: os 31 grupos eram sobra de OUTROS runs — a re-chaveação não estava nela."""
    from dev.ledger_certify_core import _fmt_drift

    d = DriftSummary(matched=0, count_diff=[], fresh_only=[], persisted_only=["g1"])
    texto = "\n".join(_fmt_drift(d))
    assert "keying antigo" not in texto
    assert "só no persistido do run (publicado e não reproduzido)" in texto


def test_a_p0_n1_chega_ao_relatorio_pelo_balde_patrimonio() -> None:
    """LC06: o consolidado do E1.5c viaja DENTRO do balde `patrimonio`, e o harness o
    tinha em mãos sem nunca lê-lo. Emissor sem leitor foi a lição da A40.l88 — este
    teste é o leitor."""
    e4 = _conserving_e4(2)
    e4["patrimonio"] = {
        "patrimonio_por_ano": {"2024": {"total_bens": 200.0}},
        "investimentos_consolidados": [
            {"investment_id": "i1", "proprietario": "A", "valores_31_12": {"2024": 100.0}},
            {"investment_id": "i1", "proprietario": "A", "valores_31_12": {"2024": 100.0}},
        ],
    }

    report = _report(e4, valores=[1.0, 2.0], with_key=1)
    bloco = _bloco(format_report(report), "## P0 nº 1")

    assert "`INV-1`" in bloco and PERDA_SILENCIOSA in bloco
    assert "julgável em 2/2 itens" in bloco

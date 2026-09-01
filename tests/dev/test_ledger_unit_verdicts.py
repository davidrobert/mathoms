"""Rubrica por unidade da ledger-certify — um grupo E3 ou um balde E4.

Espelha `dev/ledger_unit_verdicts.py`, extraído do núcleo em A42.l19. O teste seguiu o
módulo em A42.l3, quando `test_ledger_certify_core.py` cruzou as 500 linhas: o núcleo
guarda drift + montagem + render, aqui mora **que veredito uma unidade merece**.
"""

from __future__ import annotations

from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    NAO_VERIFICAVEL,
    PERDA_SILENCIOSA,
)
from dev.ledger_unit_verdicts import (
    _NON_LEDGER_CHECKERS,
    LedgerAnchor,
    e3_group_verdict,
    e4_bucket_verdict,
)

# Âncora externa FECHADA (resíduo 0 na perna E2→E3 do workspace). Sem ela o grupo
# teto-a em `coberto` — é o fail-closed do LC5-03, exercitado em teste próprio.
_FECHADA = LedgerAnchor(residuo=0)
from tests.dev._ledger_payloads import bucket_payload, e3_payload

# ─────────────────────────── e3_group_verdict ───────────────────────────


def test_e3_group_conservado() -> None:
    assert e3_group_verdict(e3_payload(5), _FECHADA)[0] == CONSERVADO


def test_e3_group_dups_coberto() -> None:
    assert e3_group_verdict(e3_payload(5, dups=2), _FECHADA)[0] == COBERTO_SEM_VALOR


def test_e3_group_zero_tx_nao_sobe_a_conservado() -> None:
    assert e3_group_verdict(e3_payload(0), _FECHADA)[0] == COBERTO_SEM_VALOR


def test_e3_group_inconsistente_nao_verificavel() -> None:
    assert (
        e3_group_verdict({"transacoes": [{"valor": 1}], "transacoes_total": 9}, _FECHADA)[0]
        == NAO_VERIFICAVEL
    )


def test_e3_group_sem_payload_nao_verificavel() -> None:
    assert e3_group_verdict(None)[0] == NAO_VERIFICAVEL
    assert e3_group_verdict({})[0] == NAO_VERIFICAVEL


def _with_ledger(g: dict, *, tx_carregadas: int, **remocoes: int) -> dict:
    g = dict(g)
    g["tx_carregadas"] = tx_carregadas
    g["remocoes"] = {k: {"count": v, "valor_cents": 0} for k, v in remocoes.items()}
    return g


def test_e3_group_ledger_fecha_upgrada_para_conservado() -> None:
    # ADR-347 — sem ledger, dups>0 seria COBERTO; com o ledger de contagem que
    # FECHA (7 == 5 survivors + 2 removidas), sobe a CONSERVADO (conservação provada).
    g = _with_ledger(e3_payload(5, dups=2), tx_carregadas=7, intra_statement_dedup=2)
    assert e3_group_verdict(g, _FECHADA)[0] == CONSERVADO


def test_e3_group_ledger_com_residuo_e_perda_silenciosa() -> None:
    # ADR-347 — o ledger é o detector de P0: resíduo não-declarado ⇒ perda.
    g = _with_ledger(e3_payload(5), tx_carregadas=10, intra_statement_dedup=1)
    assert e3_group_verdict(g, _FECHADA)[0] == PERDA_SILENCIOSA


# ── LC5-03: o fechamento interno é do PRODUTOR; quem promove é a âncora externa ──


def test_grupo_que_fecha_internamente_nao_sobe_sem_ancora() -> None:
    """97/97 grupos saíam `conservado` impressos ao lado de "E2→E3: count não fecha".
    Sem âncora medida, o teto do grupo é `coberto` — o default é fail-closed."""
    g = _with_ledger(e3_payload(5), tx_carregadas=7, undated_drop=2)

    verdict, detalhe = e3_group_verdict(g)

    assert verdict == COBERTO_SEM_VALOR
    assert "âncora externa não computada" in detalhe


def test_ancora_com_residuo_nao_zero_teta_o_grupo() -> None:
    """A contradição que o LC5-03 nomeia fica impossível: se a perna do workspace tem
    resíduo, nenhum grupo dela pode afirmar `conservado`."""
    g = _with_ledger(e3_payload(5), tx_carregadas=7, undated_drop=2)

    verdict, detalhe = e3_group_verdict(g, LedgerAnchor(residuo=13))

    assert verdict == COBERTO_SEM_VALOR
    assert "resíduo 13 na perna E2→E3" in detalhe


def test_ancora_nao_rebaixa_perda_do_proprio_grupo() -> None:
    """Defeito do grupo é do grupo: `perda` não vira `coberto` por falta de âncora."""
    g = _with_ledger(e3_payload(5), tx_carregadas=9, undated_drop=2)

    assert e3_group_verdict(g)[0] == PERDA_SILENCIOSA


def test_grupo_sem_ledger_tambem_depende_da_ancora() -> None:
    """Fecha a CLASSE: o ramo `dups=0 ⇒ valor provável` é auto-consistente igual, e
    tetá-lo só no ramo do ledger deixaria metade do defeito viva."""
    assert e3_group_verdict(e3_payload(5))[0] == COBERTO_SEM_VALOR
    assert e3_group_verdict(e3_payload(5), LedgerAnchor(residuo=0))[0] == CONSERVADO


# ─────────────────────────── e4_bucket_verdict ───────────────────────────


def test_e4_tx_bucket_conservado() -> None:
    b = bucket_payload(3.0, {"a": 1.0, "b": 2.0}, {"a": [{"valor": 1.0}], "b": [{"valor": 2.0}]})
    assert e4_bucket_verdict("despesas", b, [])[0] == CONSERVADO


def test_e4_tx_bucket_sum_mismatch_perda() -> None:
    b = bucket_payload(5.0, {"a": 1.0, "b": 2.0}, {"a": [{"valor": 1.0}], "b": [{"valor": 2.0}]})
    assert e4_bucket_verdict("despesas", b, [])[0] == PERDA_SILENCIOSA


def test_e4_tx_bucket_dados_mismatch_perda() -> None:
    b = bucket_payload(3.0, {"a": 1.0, "b": 2.0}, {"a": [{"valor": 1.0}], "b": [{"valor": 99.0}]})
    assert e4_bucket_verdict("despesas", b, [])[0] == PERDA_SILENCIOSA


def test_e4_investimentos_empty_coberto() -> None:
    assert e4_bucket_verdict("investimentos", {"dados": []}, [])[0] == COBERTO_SEM_VALOR


def test_e4_investimentos_ok() -> None:
    assert e4_bucket_verdict("investimentos", {"dados": [{"tipo": "x"}]}, [])[0] == CONSERVADO


# ── balde não-transacional: contêiner resolvido pela CHAVE (A42.l19) ──


def test_e4_non_ledger_bucket_coberto() -> None:
    """`patrimonio_por_ano` é o contêiner do balde `patrimonio` (formato A)."""
    verdict, detalhe = e4_bucket_verdict("patrimonio", {"patrimonio_por_ano": {"2024": {}}}, [])
    assert verdict == COBERTO_SEM_VALOR
    assert "1 itens em `patrimonio_por_ano`" in detalhe


def test_e4_non_ledger_conta_o_formato_b() -> None:
    verdict, detalhe = e4_bucket_verdict("patrimonio", {"declarations": [{}, {}]}, [])
    assert verdict == COBERTO_SEM_VALOR
    assert "2 itens em `declarations`" in detalhe


def test_e4_non_ledger_fluxo_conta_meses() -> None:
    """Antes caía no `[]` final e imprimia "0 itens" para um balde com N meses."""
    verdict, detalhe = e4_bucket_verdict(
        "fluxo_mensal_detalhado", {"meses_ordenados": ["2026-01", "2026-02"]}, []
    )
    assert verdict == COBERTO_SEM_VALOR
    assert "2 itens em `meses_ordenados`" in detalhe


def test_e4_non_ledger_shape_desconhecido_nao_verificavel() -> None:
    """`composicao` é campo do bloco `patrimonio` do E5, não do balde E4 — o guard
    o sondava e devolvia `coberto · 0 itens` sobre payload que não sabia ler."""
    verdict, detalhe = e4_bucket_verdict("patrimonio", {"composicao": [1, 2]}, [])
    assert verdict == NAO_VERIFICAVEL
    assert "shape não reconhecido" in detalhe


def test_e4_non_ledger_contentor_vazio_e_ausente_nao_se_confundem() -> None:
    """O `or` encadeado colapsava os dois casos no mesmo `[]`."""
    assert e4_bucket_verdict("pontos_milhas", {"dados": []}, [])[0] == COBERTO_SEM_VALOR
    assert e4_bucket_verdict("pontos_milhas", {}, [])[0] == NAO_VERIFICAVEL


def test_e4_balde_desconhecido_nao_verificavel() -> None:
    """Balde novo sem contêiner declarado falha fechado, não vira `coberto`."""
    assert e4_bucket_verdict("balde_novo", {"dados": [1]}, [])[0] == NAO_VERIFICAVEL


def test_balde_sem_checker_diz_que_o_registry_nao_o_declara() -> None:
    """A lacuna aparece como lacuna DO REGISTRY, e não como "shape não reconhecido":
    são causas diferentes e levam a consertos diferentes (A42.l3)."""
    _, detalhe = e4_bucket_verdict("balde_novo", {"dados": [1]}, [])
    assert "sem checker declarado no registry" in detalhe


def test_proveniencia_do_fluxo_nao_afirma_origem_e2_baseline() -> None:
    """A glosa única era **factualmente falsa** para `fluxo_mensal_detalhado`: ele sai
    do `CashFlowBuilder`, sobre a MESMA população classificada (LC05 · §r4)."""
    _, detalhe = e4_bucket_verdict("fluxo_mensal_detalhado", {"meses_ordenados": ["2026-01"]}, [])
    assert not detalhe.startswith("fluxo_mensal_detalhado: origem ")
    assert "MESMA população classificada" in detalhe


def test_cada_balde_nao_transacional_emite_proveniencia_propria() -> None:
    """Guard de CLASSE, medido na SAÍDA e não no registry: a primeira versão deste
    teste comparava as glosas do dict e sobrevivia à mutação que voltava a carimbar a
    frase única no veredito — o dado ficava distinto e o output, não."""
    emitidas = {
        key: e4_bucket_verdict(key, {c.containers[0]: [1]}, [])[1]
        for key, c in _NON_LEDGER_CHECKERS.items()
    }
    assert len(set(emitidas.values())) == len(_NON_LEDGER_CHECKERS)
    for key, c in _NON_LEDGER_CHECKERS.items():
        assert c.proveniencia in emitidas[key]


def test_e4_bucket_ausente_nao_verificavel() -> None:
    assert e4_bucket_verdict("despesas", None, [])[0] == NAO_VERIFICAVEL

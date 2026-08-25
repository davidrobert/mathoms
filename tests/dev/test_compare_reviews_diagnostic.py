"""A40.l81 / ADR-411 D5 — a perna que LÊ `review_reasons` no `compare_reviews`.

Módulo próprio porque o concern é distinto das 3 pernas da ADR-343 (conservação,
drift de valor, saúde de execução): esta pergunta se o canal de DIAGNÓSTICO
continua falando. Reusa os construtores de snapshot do módulo irmão.
"""

from __future__ import annotations

import copy

from dev.compare_reviews import compare_reviews
from tests.dev.test_compare_reviews import _RR, _report_data, _snap


def test_snapshot_projeta_review_reasons_sem_texto_livre() -> None:
    # `message`/`offending_value` carregam valor e nome — não entram. O que
    # entra é enum, nome de stage e caminho de chave.
    snap = _snap()
    assert snap["review_reasons"] == {
        "consolidate_baseline|imoveis_consolidados[].review_reasons"
        "|domain.property_identity_uncanonical": 2,
        "consolidate_baseline|validation.review_reasons|domain.baseline_divergence": 2,
    }


def test_tabela_que_esvazia_e_regressao_hard() -> None:
    """Prova de fecho da A40.l81 — o canal de diagnóstico não pode emudecer."""
    cur = _snap(reasons=[])
    hard, _soft, _notes = compare_reviews(_snap(), cur, _report_data(), _report_data())
    assert any("canal mudo" in h for h in hard)


def test_razao_que_cresce_sem_corpus_crescer_e_soft() -> None:
    crescida = copy.deepcopy(_RR)
    crescida[0]["occurrence_count"] = 9
    _hard, soft, _notes = compare_reviews(
        _snap(), _snap(reasons=crescida), _report_data(), _report_data()
    )
    assert any("review_reasons 4 -> 11" in s for s in soft)


def test_posicao_nova_aparece_no_soft() -> None:
    # Razão que muda de POSIÇÃO sem mudar de total é o drift que um mapa por
    # `code` esconderia — é por isso que a chave é `stage|locator|code`.
    movida = copy.deepcopy(_RR)
    movida[1]["locator"] = "veiculos_consolidados[].review_reasons"
    _hard, soft, _notes = compare_reviews(
        _snap(), _snap(reasons=movida), _report_data(), _report_data()
    )
    assert any("posição(ões) nova(s)" in s for s in soft)


def test_baseline_sem_a_chave_declara_cegueira_em_vez_de_fabricar_veredito() -> None:
    # Baseline em schema v2 não tem `review_reasons`. Lê-la como `{}` diria
    # "canal mudo" sobre um run que nunca a escreveu.
    antigo = _snap()
    del antigo["review_reasons"]
    hard, soft, _notes = compare_reviews(antigo, _snap(), _report_data(), _report_data())
    assert not any("canal mudo" in h for h in hard)
    assert any("CEGA" in s for s in soft)

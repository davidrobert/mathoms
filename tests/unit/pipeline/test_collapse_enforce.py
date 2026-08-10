"""`collapse()` — mutação e declaração no MESMO passo ([[A40.l2]] D2 · [[ADR-354]]).

Identidade de row é identidade de **objeto** dentro da chamada: o measure e o
agrupamento rodam sobre a mesma lista, no mesmo processo, então selecionar objetos
dispensa endereço serializado (e portanto dispensa `_hash_v3`). Os dois eixos que
importam aqui são **externos**: mutação × declaração, e determinismo sob permutação.
"""

from __future__ import annotations

import random
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402
from pipeline.domain.services.cross_document_collapser import (
    CrossDocumentCollapser,
    OverrideRetentionGuard,
)  # noqa: E402


def _tx(valor: str = "-100.00", desc: str = "compra mercado") -> Transaction:
    return Transaction(date=date(2026, 3, 30), description=desc, amount=Money.of(valor, "BRL"))


def _doc(n: int, arquivo: str, metodo: str = "native", valor: str = "-100.00") -> BankStatement:
    llm = metodo == "llm"
    return BankStatement(
        institution="banco exemplo",
        member_key=None if llm else "titular exemplo",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency="BRL",
        transactions=[_tx(valor) for _ in range(n)],
        account_type="extrato" if llm else "extratoconta",
        extraction_method=metodo,
        source_document=arquivo,
    )


def _par() -> list[BankStatement]:
    return [_doc(1, "marco.pdf"), _doc(1, "anual.pdf", "llm")]


def _colapsa(statements, guard: OverrideRetentionGuard | None = None):
    """`collapse()` afirmando ausência de override — o caso base destes testes."""
    return CrossDocumentCollapser(
        retention_guard=guard or OverrideRetentionGuard.sem_overrides()
    ).collapse(statements)


def _total_tx(stmts) -> int:
    return sum(len(s.transactions) for s in stmts)


# ── eixo externo 1: mutação × declaração ──


def test_rows_removidas_de_fato_igualam_o_declarado() -> None:
    """O eixo que substitui `alvo_enderecavel`: o que saiu == o que o measure declarou."""
    entrada = _par()

    saida, medicao, removals = _colapsa(entrada)
    candidatos = medicao.candidates

    declarado = sum(c.removable_rows for c in candidatos if c.collapsible)
    assert _total_tx(entrada) - _total_tx(saida) == declarado == 1
    assert sum(r.count for r in removals) == declarado


def test_declarado_bate_com_removido_em_corpus_HETEROGENEO() -> None:
    """O eixo (i) sobre formas que DIVERGEM — a fixture de 1+1 rows não o exercita."""
    # Foi assim que a D5 passou verde declarando 453 e removendo 593: `_targets` e
    # `rows_to_drop` derivavam o corte em cópias separadas e concordavam só no caso
    # simétrico. `keep_split` é a fonte única; este teste é o que trava a regressão.
    formas = [(1, 1), (1, 3), (2, 1), (3, 2), (1, 2), (2, 2), (4, 1)]
    entrada = []
    for i, (n_nat, n_llm) in enumerate(formas):
        entrada += [_doc(n_nat, f"nat{i}.pdf"), _doc(n_llm, f"llm{i}.pdf", "llm")]

    saida, medicao, removals = _colapsa(entrada)
    candidatos = medicao.candidates

    removidas = _total_tx(entrada) - _total_tx(saida)
    declarado = sum(c.removable_rows for c in candidatos if c.collapsible)
    assert removidas == declarado == sum(r.count for r in removals)
    # invariante da D5, no mesmo corpus heterogêneo
    nat = lambda s: sum(len(x.transactions) for x in s if x.extraction_method == "native")  # noqa: E731
    assert nat(entrada) == nat(saida)


def test_removal_declara_cents_ASSINADO_nao_magnitude() -> None:
    """`candidate.valor_cents` é magnitude (`abs`); o ledger grava assinado. Reusar a
    magnitude faria `_declared_dedup_cents` nunca fechar contra `val_in − val_out`."""
    _saida, medicao, removals = _colapsa(_par())
    candidatos = medicao.candidates

    assert candidatos[0].valor_cents == 10000  # magnitude, no candidato
    assert sum(r.count for r in removals) == 1
    assert sum(r.valor_cents for r in removals) == -10000  # assinado, no ledger


def test_removal_e_agregado_por_source_document() -> None:
    """O ledger é per-group ⇒ atribuição global não fecha. Sob a D5 só a perna LLM
    entra: os dois arquivos nativos sobrepostos ficam (escopo da [[A42.l5]])."""
    statements = [_doc(1, "a.pdf"), _doc(1, "b.pdf"), _doc(1, "llm.pdf", "llm")]

    _s, _c, removals = _colapsa(statements)

    assert {r.source for r in removals} == {"llm.pdf"}
    assert all(r.canal == "cross_document_collapse" for r in removals)


# ── eixo externo 2: determinismo ──


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_permutacao_de_statements_nao_muda_o_resultado(seed) -> None:
    """Ordem total de CONTEÚDO: shuffle da entrada não move a escolha."""
    base = [_doc(1, "a.pdf"), _doc(1, "b.pdf"), _doc(1, "c.pdf"), _doc(1, "llm.pdf", "llm")]
    embaralhado = list(base)
    random.Random(seed).shuffle(embaralhado)

    ref, _c1, r1 = _colapsa(base)
    alt, _c2, r2 = _colapsa(embaralhado)

    sobrevive = lambda s: sorted((x.source_document, len(x.transactions)) for x in s)  # noqa: E731
    assert sobrevive(ref) == sobrevive(alt)
    assert sorted((r.source, r.count) for r in r1) == sorted((r.source, r.count) for r in r2)


def test_collapse_e_idempotente() -> None:
    """Re-rodar sobre a saída não remove mais nada (não há mais chave cross-prov)."""
    saida1, _c, _r = _colapsa(_par())

    saida2, cand2, removals2 = _colapsa(saida1)

    assert _total_tx(saida2) == _total_tx(saida1)
    assert removals2 == ()
    assert [c for c in cand2.candidates if c.collapsible] == []


def test_nao_muta_os_statements_de_entrada() -> None:
    """Cópias via `replace`; o original preserva as rows."""
    entrada = _par()

    _colapsa(entrada)

    assert _total_tx(entrada) == 2


def test_replace_preserva_campo_que_construtor_campo_a_campo_perderia() -> None:
    """Regressão de ADR-226 PR2: `account_number_norm` sobrevive ao colapso."""
    # O statement checado tem de PERDER row sem esvaziar — só assim passa pelo
    # `replace`. Com 1 row ele sai pelo ramo `else s`, intacto, e a asserção passaria
    # mesmo com construtor campo-a-campo (a mutação M4 sobreviveu por isso).
    # Sob a D5 quem perde row parcialmente é a perna LLM: 1 nativa + 3 LLM ⇒ card=3,
    # keep_native=1, keep_llm=2 ⇒ o statement LLM perde 1 de 3 e passa pelo `replace`.
    nativa = _doc(1, "a.pdf")
    llm = _doc(3, "llm.pdf", "llm")
    llm.account_number_raw, llm.account_number_norm = "12345-6", "123456"

    saida, _c, _r = _colapsa([nativa, llm])

    sobrevivente = next(s for s in saida if s.source_document == "llm.pdf")
    assert len(sobrevivente.transactions) == 2  # perdeu 1 de 3 => passou pelo replace
    assert sobrevivente.account_number_norm == "123456"
    assert sobrevivente.account_number_raw == "12345-6"


def test_grupo_bloqueado_nao_remove_row() -> None:
    """Predicado reprovou ⇒ nenhuma row sai, e nenhum removal é declarado."""
    statements = [_doc(1, "a.pdf"), _doc(1, "b.pdf", valor="-100.00")]
    statements[1].institution = "outro banco"

    saida, medicao, removals = _colapsa(statements)

    assert medicao.candidates[0].blocked_reason == "banco_conflitante"
    assert (_total_tx(saida), removals) == (2, ())


# ── corpus PRÉ-poda (ADR-364 · PR3b2) ──


def test_corpus_do_collapse_contem_o_hash_da_row_REMOVIDA() -> None:
    """A propriedade load-bearing: o corpus não pode perder o que o colapso removeu."""
    # É onde os overrides em risco ancoram. Corpus derivado pós-poda faria o gate declarar
    # "nenhum override casa o corpus" exatamente no caso em que ele precisa avisar.
    from pipeline.domain.services.cross_document_collapser import _row_hash

    entrada = [_doc(1, "a.pdf"), _doc(1, "llm.pdf", "llm")]
    removida = [(s, tx) for s in entrada if s.source_document == "llm.pdf" for tx in s.transactions]
    hash_removido = _row_hash(removida[0][1], removida[0][0])

    _saida, medicao, removals = _colapsa(entrada)

    assert sum(r.count for r in removals) == 1, "fixture não removeu nada — teste vira vácuo"
    assert hash_removido in medicao.corpus_row_hashes


def test_corpus_e_o_mesmo_em_measure_e_em_collapse() -> None:
    """Os dois modos têm de enxergar o mesmo corpus — senão o gate muda com a flag."""
    entrada = [_doc(2, "a.pdf"), _doc(1, "llm.pdf", "llm"), _doc(1, "solo.pdf")]

    do_measure = CrossDocumentCollapser(
        retention_guard=OverrideRetentionGuard.sem_overrides()
    ).measure(entrada)
    _s, do_collapse, _r = _colapsa(entrada)

    assert do_measure.corpus_row_hashes == do_collapse.corpus_row_hashes
    assert do_measure.corpus_gate_digests == do_collapse.corpus_gate_digests


def test_survivor_hash_e_de_row_NATIVA_e_sobrevive_ao_colapso() -> None:
    """Alvo da re-ancoragem: apontar para a perna LLM mandaria o override para a row errada."""
    from pipeline.domain.services.cross_document_collapser import _row_hash

    entrada = [_doc(1, "a.pdf"), _doc(1, "llm.pdf", "llm")]
    nativa = [(s, tx) for s in entrada if s.source_document == "a.pdf" for tx in s.transactions]

    saida, medicao, _r = _colapsa(entrada)
    sobrevivente = medicao.candidates[0].survivor_hash

    assert sobrevivente == _row_hash(nativa[0][1], nativa[0][0])
    assert sobrevivente in {
        _row_hash(tx, s) for s in saida for tx in s.transactions
    }, "survivor_hash aponta para row que NÃO sobreviveu"


# ─────────────────────────────────────────────────────────────────────
# Retenção por override ([[ADR-364]] §Emenda 2026-08-09 · A40.l2 3d)
# ─────────────────────────────────────────────────────────────────────


def _guard_que_retem(
    *digests: str, origens: tuple[str, ...] = ("manual",)
) -> OverrideRetentionGuard:
    return OverrideRetentionGuard(
        denied_digests=frozenset(digests),
        overrides_ativos=len(digests),
        sem_snapshot=0,
        denied_por_source=tuple((o, len(digests)) for o in origens),
        lido=True,
        sources_por_digest=tuple((d, origens) for d in digests),
    )


def _digest_do_par() -> str:
    """O `gate_digest` da chave que o par nativo+LLM forma."""
    medida = CrossDocumentCollapser(retention_guard=OverrideRetentionGuard.sem_overrides()).measure(
        _par()
    )
    (candidato,) = medida.candidates
    return candidato.gate_digest


# É estritamente mais forte que "toda row removida tem seu override re-ancorado", e sai de uma
# subtração de conjunto em vez de um adjudicador semântico.
def test_chave_com_override_ativo_NAO_colapsa() -> None:
    """A propriedade central do 3d: nenhuma row com override desaparece."""
    entrada = _par()

    saida, medicao, removals = CrossDocumentCollapser(
        retention_guard=_guard_que_retem(_digest_do_par())
    ).collapse(entrada)

    assert _total_tx(saida) == _total_tx(entrada), "row com override foi removida"
    assert removals == ()
    (candidato,) = medicao.candidates
    assert candidato.retido_por_override is True
    assert candidato.collapsible is True, "o predicado continua dizendo que colapsaria"
    assert candidato.sera_colapsado is False, "mas neste run não colapsa"


def test_chave_sem_override_colapsa_normalmente() -> None:
    """Controle: a retenção é cirúrgica, não desliga o enforce."""
    entrada = _par()

    saida, medicao, removals = CrossDocumentCollapser(
        retention_guard=_guard_que_retem("digest-de-outra-chave")
    ).collapse(entrada)

    assert _total_tx(saida) == _total_tx(entrada) - 1
    assert sum(r.count for r in removals) == 1
    (candidato,) = medicao.candidates
    assert candidato.retido_por_override is False


def test_guard_nao_lido_degrada_para_measure_only() -> None:
    """ "Não consegui ler os overrides" NÃO pode significar "pode apagar tudo"."""
    entrada = _par()

    saida, medicao, removals = CrossDocumentCollapser(
        retention_guard=OverrideRetentionGuard.nao_lido()
    ).collapse(entrada)

    assert _total_tx(saida) == _total_tx(entrada), "guard não-lido removeu row"
    assert removals == ()
    assert medicao.candidates, "a medição tem de continuar acontecendo"


def test_override_sem_snapshot_degrada_o_RUN_inteiro() -> None:
    """`_override_gate_digest` devolve `None` sem as colunas da [[ADR-282]], e o read-path
    AINDA aplica esse override pelo hash v1 — tratá-lo como "não existe" faria a chave
    colapsar e a correção morrer. É condição de RUN porque não se sabe a qual chave pertence."""
    guard = OverrideRetentionGuard(
        denied_digests=frozenset(),
        overrides_ativos=1,
        sem_snapshot=1,
        denied_por_source=(),
        lido=True,
    )
    entrada = _par()

    saida, _, removals = CrossDocumentCollapser(retention_guard=guard).collapse(entrada)

    assert _total_tx(saida) == _total_tx(entrada)
    assert removals == ()
    assert guard.degradado is True


def test_sem_overrides_AFIRMA_ausencia_e_colapsa() -> None:
    """`sem_overrides()` é diferente de `nao_lido()`: um afirma, o outro admite ignorância."""
    entrada = _par()

    saida, _, removals = _colapsa(entrada)

    assert _total_tx(saida) == _total_tx(entrada) - 1
    assert sum(r.count for r in removals) == 1
    assert OverrideRetentionGuard.sem_overrides().degradado is False


def test_contadores_do_guard_publicam_o_DENOMINADOR() -> None:
    """Zero medido e zero não-medido não podem imprimir o mesmo caractere — foi o defeito
    que esta lane pagou quatro vezes."""
    lido = OverrideRetentionGuard.sem_overrides().to_trace_dict()
    nao_lido = OverrideRetentionGuard.nao_lido().to_trace_dict()

    assert lido["denied_digests"] == nao_lido["denied_digests"] == 0
    assert lido["lido"] is True and nao_lido["lido"] is False
    assert lido["degradado"] is False and nao_lido["degradado"] is True
    assert "overrides_ativos" in lido and "sem_snapshot" in lido


def test_paridade_de_corte_pega_declaracao_divergente_da_poda() -> None:
    """Invariante que substitui o assert morto `measure() ≡ collapse()`: compara
    `removable_rows` contra `len(drop)` — a grandeza que o bug do `keep_split` movia
    (declarava 453, removia 593, suíte verde). Prova de mutação: trocar `keep_native` por
    `survivor_cardinality` em `keep_split` derruba isto."""
    from pipeline.domain.services.cross_document_collapse_types import (
        CorteDivergente,
        exige_paridade_de_corte,
    )

    medida = CrossDocumentCollapser(retention_guard=OverrideRetentionGuard.sem_overrides()).measure(
        _par()
    )

    with pytest.raises(CorteDivergente):
        exige_paridade_de_corte(medida.candidates, 0)  # declara 1, poda removeu 0


# Sem este teste, zerar `retido_por_sources` no colapsador passa verde: os testes de contador
# constroem `CollapseCandidate` à mão, com a origem já preenchida, e nunca exercitam quem a
# produz. É a classe "teste nomeia o mecanismo sem exercitá-lo".
def test_o_COLAPSADOR_anexa_a_origem_ao_candidato_retido() -> None:
    """Mutação: `retido_por_sources=()` no `_candidate`. Fica vermelho aqui, só aqui."""
    _saida, medicao, _removals = CrossDocumentCollapser(
        retention_guard=_guard_que_retem(_digest_do_par(), origens=("manual", "rule"))
    ).collapse(_par())

    (candidato,) = medicao.candidates
    assert candidato.retido_por_override is True
    assert candidato.retido_por_sources == ("manual", "rule")


def test_candidato_NAO_retido_nao_carrega_origem() -> None:
    """Origem em candidato que colapsa faria o passo (1) contar chave que nunca foi retida."""
    _saida, medicao, _removals = CrossDocumentCollapser(
        retention_guard=_guard_que_retem("digest-de-outra-chave", origens=("rule",))
    ).collapse(_par())

    (candidato,) = medicao.candidates
    assert candidato.retido_por_override is False and candidato.retido_por_sources == ()

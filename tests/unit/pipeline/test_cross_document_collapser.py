"""Predicado do colapsador cross-documento ([[ADR-354]] §Emenda) — measure-only.

Cada teste fixa UMA cláusula do predicado. O que importa aqui não é "detecta o
defeito" (isso o detector da [[A40.l1]] já faz) e sim **não colapsar dado
legítimo**: um detector pode sobre-detectar rotulado ([[ADR-342]]), um mutador que
sobre-colapsa apaga transação real.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402
from pipeline.domain.services.cross_document_collapser import (  # noqa: E402
    CrossDocumentCollapseConfig,
    CrossDocumentCollapser,
)

_DIA = date(2026, 3, 30)


def _tx(valor: str = "-100.00", descricao: str = "compra mercado", dia: date = _DIA) -> Transaction:
    return Transaction(date=dia, description=descricao, amount=Money.of(valor, "BRL"))


def _stmt(
    *txs: Transaction,
    tipo_conta: str = "extratoconta",
    titular: str | None = "titular exemplo",
    banco: str = "banco exemplo",
    extraction_method: str | None = "native",
    saldo_final: str | None = "500.00",
) -> BankStatement:
    return BankStatement(
        institution=banco,
        member_key=titular,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency="BRL",
        transactions=list(txs),
        closing_balance=Money.of(saldo_final, "BRL") if saldo_final else None,
        account_type=tipo_conta,
        extraction_method=extraction_method,
    )


def _par_nativo_llm(**kw) -> list[BankStatement]:
    """A classe medida: perna nativa `extratoconta` + perna LLM `extrato` sem titular."""
    return [
        _stmt(_tx(), tipo_conta="extratoconta", extraction_method="native", **kw),
        _stmt(
            _tx(),
            tipo_conta="extrato",
            titular=None,
            extraction_method="llm",
            saldo_final=None,
            **kw,
        ),
    ]


def _measure(statements: list[BankStatement], config=None):
    return CrossDocumentCollapser(config).measure(statements)


def test_classe_medida_e_colapsavel_com_uma_row_removivel() -> None:
    (candidato,) = _measure(_par_nativo_llm())

    assert candidato.collapsible
    assert candidato.blocked_reason is None
    assert (candidato.n_rows, candidato.n_provenances) == (2, 2)
    assert candidato.survivor_cardinality == 1
    assert candidato.removable_rows == 1
    assert len(candidato.removable_hashes) == 1


def test_coincidencia_cross_conta_com_pernas_simetricas_nao_colapsa() -> None:
    """Sobre-detecção DECLARADA da [[A40.l1]]: mesma tarifa, mesmo dia, contas distintas."""
    statements = [
        _stmt(_tx(descricao="tarifa"), banco="banco a", titular="membro um"),
        _stmt(_tx(descricao="tarifa"), banco="banco b", titular="membro dois"),
    ]

    (candidato,) = _measure(statements)

    assert not candidato.collapsible
    assert candidato.blocked_reason == "banco_conflitante"
    assert candidato.removable_hashes == ()


def test_titular_conflitante_nao_colapsa_mesmo_com_tipo_conta_variante() -> None:
    """Carrier 2 sem a cláusula de unificabilidade colapsaria contas irmãs do mesmo banco."""
    statements = [
        _stmt(_tx(), tipo_conta="extratoconta", titular="membro um", extraction_method="native"),
        _stmt(_tx(), tipo_conta="extrato", titular="membro dois", extraction_method="llm"),
    ]

    (candidato,) = _measure(statements)

    assert candidato.blocked_reason == "titular_conflitante"


def test_tipo_conta_fora_da_allow_list_nao_colapsa() -> None:
    """Tarifa de mesmo valor no mesmo dia em conta E poupança — §Residual da [[A40.l1]]."""
    statements = [
        _stmt(_tx(), tipo_conta="extratoconta", titular=None, extraction_method="native"),
        _stmt(_tx(), tipo_conta="extratopoupanca", extraction_method="llm"),
    ]

    (candidato,) = _measure(statements)

    assert candidato.blocked_reason == "tipo_conta_fora_da_allow_list"


def test_repeticao_legitima_no_mesmo_dia_preserva_a_cardinalidade_multiset() -> None:
    """Chave day-exact não distingue 1 evento visto 2× de 2 eventos vistos 1× cada."""
    statements = [
        _stmt(_tx(), _tx(), tipo_conta="extratoconta", extraction_method="native"),
        _stmt(_tx(), _tx(), tipo_conta="extrato", titular=None, extraction_method="llm"),
    ]

    (candidato,) = _measure(statements)

    assert candidato.n_rows == 4
    assert candidato.survivor_cardinality == 2
    assert candidato.removable_rows == 2
    assert len(candidato.removable_hashes) == 2


def _par_com_cardinalidade(n_nativo: int, n_llm: int) -> list[BankStatement]:
    """Mesmo evento visto ``n_nativo`` vezes pela perna nativa e ``n_llm`` pela LLM."""
    return [
        _stmt(*[_tx() for _ in range(n_nativo)], extraction_method="native"),
        _stmt(
            *[_tx() for _ in range(n_llm)],
            tipo_conta="extrato",
            titular=None,
            extraction_method="llm",
        ),
    ]


@pytest.mark.parametrize("n_nativo,n_llm", [(1, 2), (2, 1), (3, 1), (1, 3), (2, 2)])
def test_aritmetica_multiset_sob_cardinalidade_assimetrica(n_nativo, n_llm) -> None:
    """Sobreviventes == cardinalidade multiset; o corte nunca excede a perna LLM."""
    # Não ocorre no corpus (100% das 261 é `2 rows, 2 provs`) — guarda para quando
    # ocorrer: se o corte pedisse mais que `llm_rows`, a lista sairia curta em silêncio.
    (candidato,) = _measure(_par_com_cardinalidade(n_nativo, n_llm))

    assert candidato.survivor_cardinality == max(n_nativo, n_llm)
    assert candidato.n_rows - candidato.removable_rows == candidato.survivor_cardinality
    assert candidato.removable_rows == min(n_nativo, n_llm)
    assert len(candidato.removable_hashes) == candidato.removable_rows


def test_par_nativo_mais_nativo_nao_colapsa() -> None:
    """Classe latente nativo↔nativo é escopo da [[A42.l5]], não desta lane."""
    statements = [
        _stmt(_tx(), tipo_conta="extratoconta", extraction_method="native"),
        _stmt(_tx(), tipo_conta="extrato", titular=None, extraction_method="native"),
    ]

    (candidato,) = _measure(statements)

    assert candidato.blocked_reason == "par_nao_e_nativo_mais_llm"


def test_metodo_de_extracao_indeterminado_nao_colapsa() -> None:
    """Fail-open: sem discriminador de perna, mantém o status quo sum-preserving."""
    statements = [
        _stmt(_tx(), tipo_conta="extratoconta", extraction_method=None),
        _stmt(_tx(), tipo_conta="extrato", titular=None, extraction_method="llm"),
    ]

    (candidato,) = _measure(statements)

    assert candidato.blocked_reason == "par_nao_e_nativo_mais_llm"


def test_descricao_vazia_nao_colapsa() -> None:
    statements = _par_nativo_llm()
    for stmt in statements:
        stmt.transactions = [_tx(descricao="")]

    (candidato,) = _measure(statements)

    assert candidato.blocked_reason == "descricao_vazia"


def test_direction_oposto_nunca_colide_transferencia_interna() -> None:
    """Débito na origem + crédito no destino: caso (b) do critério de aceite da [[A40.l1]]."""
    statements = [
        _stmt(_tx(valor="-100.00"), tipo_conta="extratoconta", extraction_method="native"),
        _stmt(_tx(valor="100.00"), tipo_conta="extrato", titular=None, extraction_method="llm"),
    ]

    assert _measure(statements) == ()


def test_moedas_distintas_nunca_colidem() -> None:
    nativa = _stmt(_tx(), tipo_conta="extratoconta", extraction_method="native")
    llm = _stmt(_tx(), tipo_conta="extrato", titular=None, extraction_method="llm")
    llm.currency = "USD"
    llm.transactions = [
        Transaction(date=_DIA, description="compra mercado", amount=Money.of("-100.00", "USD"))
    ]

    assert _measure([nativa, llm]) == ()


def test_proveniencia_unica_nao_gera_candidato() -> None:
    """Duas compras idênticas na MESMA conta: duplicata legítima, caso (c) da [[A40.l1]]."""
    assert _measure([_stmt(_tx(), _tx())]) == ()


def test_tres_proveniencias_nao_colapsa_sem_decisao_declarada() -> None:
    statements = [
        _stmt(_tx(), tipo_conta="extratoconta", extraction_method="native"),
        _stmt(_tx(), tipo_conta="extrato", titular=None, extraction_method="llm"),
        _stmt(_tx(), tipo_conta="extrato", titular="terceiro", extraction_method="llm"),
    ]

    (candidato,) = _measure(statements)

    assert candidato.n_provenances == 3
    assert candidato.blocked_reason == "proveniencias_diferente_de_duas"


def test_sobrevivente_e_a_perna_nativa() -> None:
    """O hash removível é o da perna LLM — a nativa nunca entra na lista."""
    from pipeline.domain.services.cross_document_collapser import _row_hash

    nativa, llm = _par_nativo_llm()
    (candidato,) = _measure([nativa, llm])

    assert candidato.removable_hashes == (_row_hash(llm.transactions[0], llm),)
    assert _row_hash(nativa.transactions[0], nativa) not in candidato.removable_hashes


@pytest.mark.parametrize(
    "membros",
    [
        ("extratocontaglobalusd", "extratocontaglobaleur"),
        ("extratoconta", "extratocontausd"),
        ("extratocontaglobal", "extratocontaglobalbrl"),
    ],
)
def test_deny_list_recusa_alias_group_separado_por_sufixo_de_moeda(membros) -> None:
    """Sufixo de moeda é identidade de conta (C6 Global USD/EUR, Wise BRL/USD)."""
    with pytest.raises(ValueError, match="sufixo de moeda"):
        CrossDocumentCollapseConfig(alias_groups=(frozenset(membros),))


def test_allow_list_do_dono_cobre_apenas_extrato_e_extratoconta() -> None:
    config = CrossDocumentCollapseConfig()

    assert config.is_variant_pair(frozenset({"extrato", "extratoconta"}))
    assert not config.is_variant_pair(frozenset({"extratoconta", "extratopoupanca"}))
    assert not config.is_variant_pair(frozenset({"extratocontaglobalusd", "extratocontaglobaleur"}))


def test_measure_e_puro_nao_muta_os_statements() -> None:
    statements = _par_nativo_llm()
    antes = [len(s.transactions) for s in statements]

    _measure(statements)

    assert [len(s.transactions) for s in statements] == antes
    assert statements[1].closing_balance is None


def _carriers_do_candidato(candidato) -> tuple[str, ...]:
    """Carriers da [[A40.l1]] derivados DO candidato — hardcodar tornaria a asserção vácua."""
    # As tags do candidato alimentam a MESMA `carrier_signatures` que a partição do
    # relatório e o validador de whitelist consomem. Conjunto de campo fixo aqui
    # sobreviveria a qualquer mudança de predicado — o furo que a l1 mediu na r3.
    from dev.ledger_cross_group import _tag_fields, carrier_signatures

    return carrier_signatures(_tag_fields(candidato.divergence), _tag_fields(candidato.parciais))


@pytest.mark.parametrize(
    "fixture",
    [
        "par_simples",
        "par_com_repeticao_legitima",
    ],
)
def test_todo_candidato_colapsavel_e_carrier_shaped_para_o_detector_da_l1(fixture) -> None:
    """Equivalência com a definição ÚNICA de carrier da [[A40.l1]]: o colapsador não pode
    colapsar nada que o detector classificaria como coincidência."""
    statements = (
        _par_nativo_llm()
        if fixture == "par_simples"
        else [
            _stmt(_tx(), _tx(), tipo_conta="extratoconta", extraction_method="native"),
            _stmt(_tx(), _tx(), tipo_conta="extrato", titular=None, extraction_method="llm"),
        ]
    )

    (candidato,) = _measure(statements)

    assert candidato.collapsible, "fixture deixou de ser colapsável"
    assert _carriers_do_candidato(candidato), (
        f"colapsável mas NÃO carrier-shaped (divergence={candidato.divergence!r} "
        f"parciais={candidato.parciais!r}) — o colapsador apagaria uma coincidência"
    )


def test_coincidencia_declarada_do_detector_nao_e_carrier_nem_colapsavel() -> None:
    """A sobre-detecção que a l1 declara aceitável é justamente a que não pode colapsar."""
    statements = [
        _stmt(_tx(descricao="tarifa"), banco="banco a", titular="membro um"),
        _stmt(_tx(descricao="tarifa"), banco="banco b", titular="membro dois"),
    ]

    (candidato,) = _measure(statements)

    assert not candidato.collapsible
    assert _carriers_do_candidato(candidato) == ()


def test_tags_de_carrier_saem_do_dado_e_nao_de_constante() -> None:
    """Sem esta, `divergence`/`parciais` poderiam ser string fixa e a equivalência
    acima passaria por construção."""
    (com_carrier,) = _measure(_par_nativo_llm())
    (sem_carrier,) = _measure(
        [
            _stmt(_tx(descricao="tarifa"), banco="banco a", titular="membro um"),
            _stmt(_tx(descricao="tarifa"), banco="banco b", titular="membro dois"),
        ]
    )

    assert com_carrier.divergence == "titular+tipo_conta"
    assert com_carrier.parciais == "titular"
    assert sem_carrier.divergence == "banco+titular"
    assert sem_carrier.parciais == ""


# ── Wiring no adapter: inerte por default, mede quando injetado ──


def _e2_payload(tipo: str, titular: str | None, *, llm: bool) -> dict:
    payload = {
        "banco": "banco exemplo",
        "tipo": tipo,
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-12-31",
        "documento_titular": titular,
        "transacoes": [{"data": _DIA.isoformat(), "descricao": "compra mercado", "valor": -100.0}],
    }
    if llm:
        payload["extraido_por"] = "llm"
    return payload


def _reconcile_par_cross_documento(collapser: CrossDocumentCollapser | None):
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.domain.services.e3_reconciler_adapter import E3ReconcilerAdapter
    from pipeline.domain.services.reconciliation_service import ReconciliationConfig

    store = InMemoryArtifactStore()
    store.seed("E2", "nativo", _e2_payload("extratoconta", "titular exemplo", llm=False))
    store.seed("E2-llm", "escalado", _e2_payload("extrato", None, llm=True))
    adapter = E3ReconcilerAdapter(ReconciliationConfig(), cross_document_collapser=collapser)
    return adapter.reconcile_via_store(store, input_stages=("E2", "E2-llm"))


def test_adapter_sem_colapsador_injetado_e_inerte() -> None:
    """`default None` — o stage roda idêntico a antes desta lane."""
    resultado = _reconcile_par_cross_documento(None)

    assert resultado.collapse_candidates == ()
    assert resultado.to_dict()["collapse_candidates"] == []


def test_adapter_com_colapsador_reporta_candidato_e_nao_remove_nada() -> None:
    """Measure-only: o candidato aparece no traço e as 2 tx continuam no artefato."""
    sem = _reconcile_par_cross_documento(None)
    com = _reconcile_par_cross_documento(CrossDocumentCollapser())

    (candidato,) = com.collapse_candidates
    assert candidato.collapsible
    assert candidato.removable_rows == 1
    assert com.to_dict()["collapse_candidates"][0]["removable_rows"] == 1
    # Measure-only: nada muda no que o stage escreve.
    assert com.artifacts_written == sem.artifacts_written
    assert com.statements_reconciled == sem.statements_reconciled


def test_extraction_method_vem_do_marcador_do_artefato_e2() -> None:
    """`extraido_por` tem um writer só; ausência ⇒ nativo (erra para sub-colapso)."""
    nativo = BankStatement.from_e2_dict(_e2_payload("extratoconta", "t", llm=False))
    escalado = BankStatement.from_e2_dict(_e2_payload("extrato", None, llm=True))

    assert nativo.extraction_method == "native"
    assert escalado.extraction_method == "llm"


def test_extraction_method_sobrevive_ao_reconcile() -> None:
    """`_reconciled_copy` reconstrói campo-a-campo — sem esta guarda o predicado do
    colapsador cai em `par_nao_e_nativo_mais_llm` para TODO par e a lane fica inerte."""
    from pipeline.domain.services.reconciliation_service import (
        ReconciliationConfig,
        ReconciliationService,
    )

    entrada = _par_nativo_llm()
    saida = ReconciliationService(ReconciliationConfig()).reconcile(entrada)

    assert sorted(s.extraction_method for s in saida) == ["llm", "native"]


def test_reconcile_preserva_todo_campo_de_identidade() -> None:
    """Era `xfail(strict)` até o fix de 2026-08-05 (ADR-226 PR2)."""
    from dataclasses import fields

    from pipeline.domain.services.reconciliation_service import (
        ReconciliationConfig,
        ReconciliationService,
    )

    entrada = BankStatement.from_e2_dict(
        {**_e2_payload("extratoconta", "titular exemplo", llm=False), "numero_conta": "1234-5"}
    )
    (saida,) = ReconciliationService(ReconciliationConfig()).reconcile([entrada])

    perdidos = [
        f.name
        for f in fields(BankStatement)
        if f.name != "transactions" and getattr(entrada, f.name) != getattr(saida, f.name)
    ]
    assert perdidos == []

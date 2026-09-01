"""5º canal do ledger + `intra` autoritativo ([[A40.l2]] D3 · [[ADR-347]] §Emenda).

A inferência por diferença (`tx_loaded − len(transactions)`) era o mecanismo que
convertia remoção não-declarada em ABSORÇÃO SILENCIOSA: colapso de 3 rows aparecia
como `intra_statement_dedup` count=3/cents=0 e o invariante fechava. Com `intra`
autoritativo, canal não-instrumentado produz resíduo ≠ 0 e o invariante quebra alto.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402
from pipeline.domain.services.cross_document_collapser import CollapseRemoval  # noqa: E402
from pipeline.domain.services.e3_load_report import (  # noqa: E402
    ConservacaoQuebrada,
    LoadStat,
    atribui_removals_por_grupo,
    build_artifact_ledger,
    consolidacao_cross_documento,
)
from pipeline.domain.services.reconciliation_service import DedupRemoval  # noqa: E402


def _stmt(n_tx: int, arquivo: str = "a.pdf") -> BankStatement:
    s = BankStatement(
        institution="banco exemplo",
        member_key="titular exemplo",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency="BRL",
        transactions=[
            Transaction(
                date=date(2026, 3, 30), description="compra", amount=Money.of("-10.00", "BRL")
            )
            for _ in range(n_tx)
        ],
        account_type="extratoconta",
    )
    s.source_document = arquivo
    return s


def _identidade(ledger: dict, transacoes_total: int) -> tuple[int, int]:
    """(lado esquerdo, lado direito) de tx_carregadas == total + Σ remocoes[*].count."""
    declarado = sum(r["count"] for r in ledger["remocoes"].values())
    return ledger["tx_carregadas"], transacoes_total + declarado


def test_canal_collapse_declarado_e_identidade_fecha() -> None:
    """carregadas=10 → 1 undated + 1 anachronic + 2 intra + 1 collapse + 5 kept."""
    stats = {"a.pdf": LoadStat(tx_carregadas=10, tx_loaded=8, anachronic=1, undated=1)}
    removals = [
        DedupRemoval("intra_statement_dedup", 2, -2000, 0, "a.pdf"),
        CollapseRemoval("cross_document_collapse", 1, -1000, 1, "a.pdf"),
    ]

    ledger = build_artifact_ledger([_stmt(5)], stats, 0, 0, removals)

    canais = ledger["remocoes"]
    assert canais["cross_document_collapse"] == {"count": 1, "valor_cents": -1000}
    assert canais["intra_statement_dedup"] == {"count": 2, "valor_cents": -2000}
    esquerda, direita = _identidade(ledger, transacoes_total=5)
    assert esquerda == direita == 10


def test_remocao_nao_declarada_quebra_a_identidade_alto() -> None:
    """O eixo anti-absorção: 1 row removida SEM canal declarado ⇒ resíduo visível.
    Sob a inferência antiga o invariante fechava com a remoção misatribuída ao intra."""
    stats = {"a.pdf": LoadStat(tx_carregadas=10, tx_loaded=8, anachronic=1, undated=1)}
    removals = [DedupRemoval("intra_statement_dedup", 2, -2000, 0, "a.pdf")]

    ledger = build_artifact_ledger([_stmt(5)], stats, 0, 0, removals)  # 8-2=6 ≠ 5 kept

    assert ledger["remocoes"]["intra_statement_dedup"]["count"] == 2  # fato, não diferença
    esquerda, direita = _identidade(ledger, transacoes_total=5)
    assert esquerda != direita  # 10 ≠ 9 — a row não-declarada aparece como resíduo


def test_mesmo_source_em_dois_removals_soma_nao_sobrescreve() -> None:
    """Bug do co-design: dict-comprehension keyed por source perdia entradas."""
    stats = {"a.pdf": LoadStat(tx_carregadas=6, tx_loaded=6, anachronic=0, undated=0)}
    removals = [
        DedupRemoval("intra_statement_dedup", 1, -1000, 0, "a.pdf"),
        DedupRemoval("intra_statement_dedup", 2, -2000, 0, "a.pdf"),
    ]

    ledger = build_artifact_ledger([_stmt(3)], stats, 0, 0, removals)

    assert ledger["remocoes"]["intra_statement_dedup"] == {"count": 3, "valor_cents": -3000}


def test_dois_statements_do_mesmo_arquivo_nao_recontam_o_canal() -> None:
    """A soma do canal é por SOURCE distinto do grupo, não por statement."""
    stats = {"a.pdf": LoadStat(tx_carregadas=4, tx_loaded=4, anachronic=0, undated=0)}
    removals = [DedupRemoval("intra_statement_dedup", 1, -1000, 0, "a.pdf")]

    ledger = build_artifact_ledger([_stmt(2), _stmt(1)], stats, 0, 0, removals)

    assert ledger["remocoes"]["intra_statement_dedup"]["count"] == 1


def test_sem_removals_mantem_inferencia_legada() -> None:
    """Compat: caller antigo (removals=None) infere intra por diferença, collapse=0."""
    stats = {"a.pdf": LoadStat(tx_carregadas=8, tx_loaded=8, anachronic=0, undated=0)}

    ledger = build_artifact_ledger([_stmt(5)], stats, 0, 0, None)

    assert ledger["remocoes"]["intra_statement_dedup"]["count"] == 3  # inferido
    assert ledger["remocoes"]["cross_document_collapse"]["count"] == 0
    esquerda, direita = _identidade(ledger, transacoes_total=5)
    assert esquerda == direita


def test_e2_to_e3_ve_a_particao_completa_no_count_out() -> None:
    """O4 do co-design: `transacoes_duplicadas_removidas` é só cross-file; canal novo
    em `remocoes` não entrava no count_out e o check de COUNT disparava antes."""
    from dev.ledger_conservation import CONSERVADO, e2_to_e3

    e2 = [{"tipo": "extratoconta", "transacoes": [{"valor": 0}] * 10}]
    remocoes = {
        "undated_drop": {"count": 1, "valor_cents": 0},
        "anachronic": {"count": 1, "valor_cents": 0},
        "intra_statement_dedup": {"count": 2, "valor_cents": 0},
        "cross_file_dedup": {"count": 0, "valor_cents": 0},
        "cross_document_collapse": {"count": 1, "valor_cents": 0},
    }
    e3 = [{"transacoes_total": 5, "transacoes": [], "remocoes": remocoes}]

    r = e2_to_e3(e2, e3, exclusoes_run=0)

    assert (r.count_in, r.count_out) == (10, 10)
    assert r.verdict == CONSERVADO


def test_e2_to_e3_artefato_antigo_mantem_fallback() -> None:
    """Artefato de 4 canais (ou sem remocoes) segue lido pelo campo legado."""
    from dev.ledger_conservation import e2_to_e3

    e2 = [{"tipo": "extratoconta", "transacoes": [{"valor": 0}] * 6}]
    e3 = [{"transacoes_total": 5, "transacoes": [], "transacoes_duplicadas_removidas": 1}]

    r = e2_to_e3(e2, e3, exclusoes_run=0)

    assert (r.count_in, r.count_out) == (6, 6)


def test_sobre_declaracao_nao_passa_como_conservado() -> None:
    """P0-4: a guarda era unilateral — só testava `count_out < count_in`, e
    sobre-declaração caía no default CONSERVADO. Com o 5º canal, a mesma row declarada
    em dois canais ficava invisível; e é este somatório que vira o contador da S2."""
    from dev.ledger_conservation import PERDA_SILENCIOSA, e2_to_e3

    e2 = [{"tipo": "extratoconta", "transacoes": [{"valor": 0}] * 100}]
    remocoes = {
        "intra_statement_dedup": {"count": 15, "valor_cents": 0},
        "cross_document_collapse": {"count": 15, "valor_cents": 0},  # a MESMA row 2x
    }
    e3 = [{"transacoes_total": 90, "transacoes": [], "remocoes": remocoes}]

    r = e2_to_e3(e2, e3, exclusoes_run=0)

    assert (r.count_in, r.count_out) == (100, 120)
    assert r.verdict == PERDA_SILENCIOSA
    assert "SOBRE-declaração" in r.detail


# ─────────────────────────────────────────────────────────────────────
# Dono único da remoção ([[ADR-347]] §Emenda 2026-08-10 · A40.l2 3c1c)
# ─────────────────────────────────────────────────────────────────────


def _stmt_periodo(arquivo: str, inicio: date, fim: date) -> BankStatement:
    return BankStatement(
        institution="banco exemplo",
        member_key="titular exemplo",
        period_start=inicio,
        period_end=fim,
        currency="BRL",
        transactions=[],
        account_type="extratoconta",
        source_document=arquivo,
    )


def _removal(mes: str, count: int, arquivo: str = "extrato-a.pdf") -> CollapseRemoval:
    return CollapseRemoval(
        "cross_document_collapse",
        count,
        -100 * count,
        cross_source_count=count,
        source=arquivo,
        meses=((mes, count),),
    )


def _grupos_multi_periodo() -> dict:
    """UM arquivo cobrindo DOIS períodos — `output_key` embute o período, então ele
    vira dois grupos que compartilham o mesmo `source_document`."""
    return {
        "itau_BRL_202601_202601": [
            _stmt_periodo("extrato-a.pdf", date(2026, 1, 1), date(2026, 1, 31))
        ],
        "itau_BRL_202602_202602": [
            _stmt_periodo("extrato-a.pdf", date(2026, 2, 1), date(2026, 2, 28))
        ],
    }


def test_arquivo_multi_periodo_nao_declara_a_mesma_remocao_duas_vezes():
    """O defeito medido: 1 source em 2 grupos publicava 6 onde havia 3, porque cada
    grupo reivindicava toda remoção do source que ele contém. O mês é quem decide."""
    grupos = _grupos_multi_periodo()
    removals = (_removal("2026-01", 2), _removal("2026-02", 1))

    atribuido = atribui_removals_por_grupo(grupos, removals)
    payloads = []
    for key, stmts in grupos.items():
        payload: dict = {}
        payload |= build_artifact_ledger(stmts, {}, 0, 0, atribuido[key])
        payloads.append(payload)

    assert consolidacao_cross_documento(payloads) == {
        "count": 3,
        "meses": [{"mes": "2026-01", "count": 2}, {"mes": "2026-02", "count": 1}],
    }


def test_cada_remocao_tem_exatamente_um_dono():
    grupos = _grupos_multi_periodo()
    removals = (_removal("2026-01", 2), _removal("2026-02", 1))

    atribuido = atribui_removals_por_grupo(grupos, removals)

    donos = [(key, r.meses[0][0]) for key, lista in atribuido.items() for r in lista]
    assert sorted(donos) == [
        ("itau_BRL_202601_202601", "2026-01"),
        ("itau_BRL_202602_202602", "2026-02"),
    ]


def test_mes_fora_de_todo_periodo_cai_no_fallback_e_nao_se_perde():
    """Fatura com período sentinel ou borda de período: o mês não casa nenhuma janela.
    O fato vai para o primeiro grupo em ordem canônica — determinístico e conservado."""
    grupos = _grupos_multi_periodo()
    removals = (_removal("2025-07", 4),)

    atribuido = atribui_removals_por_grupo(grupos, removals)

    total = sum(r.count for lista in atribuido.values() for r in lista)
    assert total == 4
    assert len(atribuido["itau_BRL_202601_202601"]) == 1


def test_fato_sem_dono_aborta_em_vez_de_publicar_menos():
    """Prova por mutação da guarda: source que não pertence a nenhum grupo faria a soma
    publicada ficar ABAIXO da declarada — perda silenciosa, que é o que a ADR-347
    existe para impedir. Aqui a guarda tem de falhar alto."""
    grupos = _grupos_multi_periodo()
    removals = (_removal("2026-01", 2, arquivo="arquivo-que-nenhum-grupo-tem.pdf"),)

    with pytest.raises(ConservacaoQuebrada) as exc:
        atribui_removals_por_grupo(grupos, removals)

    assert "declarado" in str(exc.value) and "atribuido" in str(exc.value)


def test_source_em_um_grupo_so_continua_atribuido_normalmente():
    """Controle: sem multi-período o comportamento não muda."""
    grupos = {
        "itau_BRL_202601_202601": [_stmt_periodo("a.pdf", date(2026, 1, 1), date(2026, 1, 31))],
        "c6_BRL_202601_202601": [_stmt_periodo("b.pdf", date(2026, 1, 1), date(2026, 1, 31))],
    }
    removals = (_removal("2026-01", 2, "a.pdf"), _removal("2026-01", 3, "b.pdf"))

    atribuido = atribui_removals_por_grupo(grupos, removals)

    assert sum(r.count for r in atribuido["itau_BRL_202601_202601"]) == 2
    assert sum(r.count for r in atribuido["c6_BRL_202601_202601"]) == 3


_ARQUIVO_ANUAL = "extrato-anual.pdf"


def _e2_periodo(inicio: str, fim: str, transacoes: list[dict]) -> dict:
    """E2 de UM arquivo cobrindo um período — o mesmo `arquivo_origem` nos dois."""
    return {
        "pipeline_stage": "E2",
        "banco": "itau",
        "tipo": "extrato",
        "moeda": "BRL",
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "arquivo_origem": _ARQUIVO_ANUAL,
        "transacoes": transacoes,
    }


# Parâmetro com nome NÃO-monetário de propósito: `valor: float` casa o gate P5 (ADR-090 —
# dinheiro nunca é float). A chave do dict segue `"valor"`, contrato do E2; o gate lê a anotação.
def _tx_e2(dia: str, desc: str, quantia_reais: int) -> dict:
    return {"data": dia, "descricao": desc, "valor": quantia_reais}


# Trava o CALL-SITE, não o helper. Os testes acima provam `atribui_removals_por_grupo`
# isolada — e passam verdes com o call-site voltando a passar a lista completa (medido por
# mutação: publicado 2, declarado 1). O defeito vive na fiação, então a asserção tem de ser
# sobre o artefato que o stage escreve.
def _store_com_arquivo_em_dois_periodos():
    from tests.unit.pipeline.test_e3_reconciler_adapter import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    dup = [_tx_e2("2026-01-05", "MERCADO", -100), _tx_e2("2026-01-05", "MERCADO", -100)]
    store.seed("E2-extratos", "anual_jan", _e2_periodo("2026-01-01", "2026-01-31", dup))
    fev = [_tx_e2("2026-02-10", "UBER", -30)]
    store.seed("E2-extratos", "anual_fev", _e2_periodo("2026-02-01", "2026-02-28", fev))
    return store


def _roda_stage_com_arquivo_em_dois_periodos():
    """`(declarado_run_level, publicado_nos_ledgers)` do canal `intra_statement_dedup`."""
    from pipeline.domain.services.e3_reconciler_adapter import E3ReconcilerAdapter
    from pipeline.domain.services.reconciliation_service import ReconciliationConfig

    store = _store_com_arquivo_em_dois_periodos()
    result = E3ReconcilerAdapter(ReconciliationConfig(tolerance_days=3)).reconcile_via_store(store)

    assert result["artifacts_written"] == 2, "fixture não produz 2 grupos — teste vira vácuo"
    return (
        sum(r.count for r in result.removals if r.canal == "intra_statement_dedup"),
        sum(
            store.read("E3", k)["remocoes"]["intra_statement_dedup"]["count"]
            for k in store.list_keys("E3")
        ),
    )


def test_o_STAGE_usa_a_atribuicao__nao_so_a_funcao_isolada():
    """Um arquivo em dois períodos, com duplicata interna: `output_key` embute o período,
    logo dois grupos compartilham `source_document` e antes do fix os dois declaravam a
    mesma `DedupRemoval`."""
    declarado, publicado = _roda_stage_com_arquivo_em_dois_periodos()

    assert declarado == 1, "fixture não produz remoção intra — teste vira vácuo"
    assert publicado == declarado, (
        f"a soma dos ledgers publicados ({publicado}) não reproduz o declarado ({declarado}) — "
        "o call-site voltou a passar a lista completa de removals"
    )


# Deferimento vencido do §3d ([[A40.l2]]): o gate AST proíbe `collapse_enforce=True` no stage
# de produção, e os goldens rodam em sombra — logo o caminho que REMOVE row só existia sob
# `collapse()` isolado. Aqui o enforce é injetado no adapter e o stage roda inteiro: é a única
# cobertura do que o flip vai executar.
def _e2_conta(banco: str, tipo: str, arquivo: str, metodo: str, txs: list[dict]) -> dict:
    payload = _e2_periodo("2026-01-01", "2026-01-31", txs)
    # `extraido_por` é a chave do contrato E2 (`document.py:185`), não `extraction_method`:
    # com o nome errado as duas pernas viram nativas e o predicado bloqueia em
    # `par_nao_e_nativo_mais_llm` — o teste passaria medindo a ausência do par.
    payload.update(
        {"banco": banco, "tipo": tipo, "arquivo_origem": arquivo, "extraido_por": metodo}
    )
    return payload


def _store_com_par_cross_documento():
    """Mesma transação por duas proveniências do mesmo banco: nativa + perna LLM."""
    from tests.unit.pipeline.test_e3_reconciler_adapter import InMemoryArtifactStore

    tx = [_tx_e2("2026-01-05", "MERCADO", -100)]
    store = InMemoryArtifactStore()
    store.seed("E2-extratos", "nativo", _e2_conta("itau", "extratoconta", "ext.pdf", "native", tx))
    store.seed("E2-llm", "llm", _e2_conta("itau", "extrato", "anual.pdf", "llm", list(tx)))
    return store


def _adapter_com_enforce(enforce: bool):
    """Adapter com colapsador injetado — o composition root que o stage monta em produção."""
    from pipeline.domain.services.cross_document_collapse_types import OverrideRetentionGuard
    from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser
    from pipeline.domain.services.e3_reconciler_adapter import E3ReconcilerAdapter
    from pipeline.domain.services.reconciliation_service import ReconciliationConfig

    return E3ReconcilerAdapter(
        ReconciliationConfig(tolerance_days=3),
        cross_document_collapser=CrossDocumentCollapser(
            retention_guard=OverrideRetentionGuard.sem_overrides()
        ),
        collapse_enforce=enforce,
    )


def _roda_stage_com_enforce(enforce: bool):
    """`(publicado_no_canal, declarado_no_canal, txs, canais_com_remocao)`."""
    from pipeline.domain.services.cross_document_collapse_types import CANAL_COLAPSO

    store = _store_com_par_cross_documento()
    result = _adapter_com_enforce(enforce).reconcile_via_store(store)
    publicado, txs, canais = _le_ledgers(store, CANAL_COLAPSO)
    declarado = sum(r.count for r in result.removals if r.canal == CANAL_COLAPSO)
    return publicado, declarado, txs, canais


def _le_ledgers(store, canal_alvo: str):
    """`(count do canal alvo, total de txs, canais com remoção)` somados nos artefatos E3."""
    chaves = store.list_keys("E3")
    ledgers = [store.read("E3", k) for k in chaves]
    return (
        sum((a["remocoes"].get(canal_alvo) or {}).get("count", 0) for a in ledgers),
        sum(len(a["transacoes"]) for a in ledgers),
        {canal for a in ledgers for canal, v in a["remocoes"].items() if v.get("count")},
    )


def test_enforce_remove_a_row_e_o_ledger_publicado_reproduz_o_declarado():
    """Mutação: `_apply` devolver os statements intactos. O ledger declara 1 e `txs` fica 2."""
    publicado, declarado, txs, canais = _roda_stage_com_enforce(True)

    assert declarado == 1, "fixture não produz corte cross-documento — teste vira vácuo"
    assert publicado == declarado, f"ledger publicado {publicado} ≠ declarado {declarado}"
    assert txs == 1, "a row duplicada sobreviveu ao enforce"
    assert canais == {"cross_document_collapse"}


# Medido ao escrever este teste, e vale registrar porque contraria a leitura ingênua do flip:
# com as duas pernas na MESMA conta, o `cross_file_dedup` já removia a duplicata. Ligar o
# enforce não muda o total de transações — muda quem DECLARA a remoção. O ganho medido da lane
# (261 ocorrências, +19% de receita) vem de pares que caem em contas distintas, onde o
# `cross_file_dedup` não alcança. Um teste que só olhasse `txs` leria "o enforce não faz nada".
def test_na_sombra_o_cross_file_dedup_ja_removia__muda_a_ATRIBUICAO_nao_o_total():
    """Controle negativo: sem ele, um enforce inerte passaria despercebido aqui."""
    publicado, declarado, txs, canais = _roda_stage_com_enforce(False)

    assert (publicado, declarado) == (0, 0), "a sombra declarou corte no canal do colapso"
    assert txs == 1 and canais == {"cross_file_dedup"}

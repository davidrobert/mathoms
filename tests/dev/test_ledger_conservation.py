"""ledger-certify — núcleo puro de conservação E2→E3→E4 (ADR-343/302)."""

from __future__ import annotations

from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    PERDA_SILENCIOSA,
    _tx_cents,
    e2_to_e3,
    e3_to_e4,
    investment_double_count,
)


def _e2(*valores: float) -> dict:
    return {"transacoes": [{"valor": v} for v in valores]}


def _e2_nao_reconciliavel(tipo_field: str, tipo: str, *valores: float) -> dict:
    """Artefato E2 que o reconciliador não reconcilia (posição/informe): carrega
    ``transacoes`` mas não deve entrar no denominador E2→E3 (LC-07)."""
    return {tipo_field: tipo, "transacoes": [{"valor": v} for v in valores]}


def _e3(survivors: list[float], dups: int = 0) -> dict:
    return {
        "transacoes_total": len(survivors),
        "transacoes_duplicadas_removidas": dups,
        "transacoes": [{"valor": v} for v in survivors],
    }


def _bucket(geral, cats: dict, n_tx: int, *, tx_total=None, collapsed=0) -> dict:
    b = {"total_geral": geral, "totais_por_categoria": cats, "total_transacoes": n_tx}
    if tx_total is not None:
        b["_lineage"] = {"signals": {"tx_total": str(tx_total), "dedup_collapsed": str(collapsed)}}
    return b


# ─────────────────────────── _tx_cents ───────────────────────────


def test_tx_cents_prefers_amount_over_valor() -> None:
    assert _tx_cents({"valor": 1.11, "amount": "2.22"}) == 222
    assert _tx_cents({"valor": 1.11, "amount": None}) == 111
    assert _tx_cents({"valor": 1.11}) == 111


# ─────────────────────────── E2 → E3 ───────────────────────────


def test_e2e3_conservado_sem_dups() -> None:
    r = e2_to_e3([_e2(100.0, 50.0)], [_e3([100.0, 50.0])])
    assert r.verdict == CONSERVADO
    assert r.count_in == 2 and r.count_out == 2 and r.value_in_cents == 15000


def test_e2e3_dups_vira_coberto_sem_valor() -> None:
    r = e2_to_e3([_e2(100.0, 100.0, 50.0)], [_e3([100.0, 50.0], dups=1)])
    assert r.verdict == COBERTO_SEM_VALOR  # count fecha (2+1==3), valor não-provável


def test_e2e3_tx_perdida_e_perda_silenciosa() -> None:
    # 3 entram, só 2 sobrevivem e 0 dups declaradas → 1 sumiu
    r = e2_to_e3([_e2(100.0, 50.0, 25.0)], [_e3([100.0, 50.0], dups=0)])
    assert r.verdict == PERDA_SILENCIOSA
    assert r.count_in == 3 and r.count_out == 2


def test_e2e3_valor_diverge_sem_dups_e_perda() -> None:
    r = e2_to_e3([_e2(100.0, 50.0)], [_e3([100.0, 49.0])])  # count ok, valor não
    assert r.verdict == PERDA_SILENCIOSA


def test_e2e3_reupload_sobreposto_vira_coberto() -> None:
    # Re-upload sobreposto: 5 tx entram (100,50 duplicados + 25 único), reconcile
    # colapsa p/ 3 survivors mas declara só 1 dup (sub-declaração do dedup). count
    # cai (5->4) COM dups>0 ⇒ coberto-sem-verificação, NÃO perda (LC-07).
    r = e2_to_e3([_e2(100.0, 50.0, 100.0, 50.0, 25.0)], [_e3([100.0, 50.0, 25.0], dups=1)])
    assert r.verdict == COBERTO_SEM_VALOR
    assert r.count_in == 5 and r.count_out == 4


def test_e2e3_denominador_exclui_posicao_skip() -> None:
    # Artefato de posição (tipo em SKIP_TYPES via should_skip) não entra no
    # denominador: sem o filtro daria perda (5->2); com o filtro, conserva (LC-07).
    e2 = [_e2(100.0, 50.0), _e2_nao_reconciliavel("tipo", "investimentosposicao", 10.0, 20.0, 30.0)]
    r = e2_to_e3(e2, [_e3([100.0, 50.0])])
    assert r.verdict == CONSERVADO
    assert r.count_in == 2 and r.value_in_cents == 15000


def test_e2e3_denominador_exclui_investment_report_doctype() -> None:
    # Doc-type de relatório LLM (investment_report) passa por should_skip mas não é
    # transacional — o filtro o exclui pelo tipo_documento (LC-07).
    e2 = [
        _e2(100.0, 50.0),
        _e2_nao_reconciliavel("tipo_documento", "investment_report", 10.0, 20.0),
    ]
    r = e2_to_e3(e2, [_e3([100.0, 50.0])])
    assert r.verdict == CONSERVADO
    assert r.count_in == 2


# ─────────────────────────── E3 → E4 ───────────────────────────


def test_e3e4_conservado() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=2, collapsed=0)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == CONSERVADO


def test_e3e4_classifier_dropou() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=1)  # E3=2 mas tx_total=1
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


def test_e3e4_destino_nao_fecha() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=3)  # 3 classificados, só 2 têm destino
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0, 10.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


def test_e3e4_balde_nao_fecha() -> None:
    despesas = _bucket(80.0, {"casa": 50.0}, 1, tx_total=2)  # Σ cat (50) != total (80)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


def test_e3e4_transferencia_conta_no_destino() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=3)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0, 30.0])], despesas, receitas, transferencias_count=1)
    assert r.verdict == CONSERVADO  # 1 receita + 1 despesa + 1 transferência = 3


def _e3_com_info_fiscal(survivors: list[float], info_fiscal: int) -> dict:
    """E3 com ``info_fiscal`` linhas ``info_fiscal_anual`` (o classificador as pula,
    ADR-242) além dos ``survivors`` normais. ``transacoes_total`` conta TODAS."""
    txns = [{"valor": v} for v in survivors]
    txns += [{"valor": 0.0, "categoria_sugerida": "info_fiscal_anual"} for _ in range(info_fiscal)]
    return {
        "transacoes_total": len(txns),
        "transacoes_duplicadas_removidas": 0,
        "transacoes": txns,
    }


def test_e3e4_info_fiscal_anual_e_canal_declarado_nao_perda() -> None:
    # F2: E3 carrega 3 survivors mas 1 é linha info_fiscal_anual que o classificador
    # pula de propósito (ADR-242) → tx_total=2. Sem declarar o canal o check acusava
    # falso PERDA_SILENCIOSA (P0); declarando via is_info_fiscal_anual, CONSERVADO.
    # Reproduz o gap=1/residual=0 verificado no corpus 5@5.com r3.
    e3 = _e3_com_info_fiscal([100.0, 80.0], info_fiscal=1)
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=2)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([e3], despesas, receitas, transferencias_count=0)
    assert r.verdict == CONSERVADO


def test_e3e4_info_fiscal_nao_mascara_perda_real() -> None:
    # Adversarial (anti-silêncio): o canal info_fiscal NÃO pode mascarar perda real.
    # E3=4 (3 normais + 1 info_fiscal), tx_total=2 → 1 normal sumiu ALÉM do info_fiscal.
    # survivors declarados = 4-1 = 3 != tx_total 2 → PERDA (o drop real não é silenciado).
    e3 = _e3_com_info_fiscal([100.0, 80.0, 30.0], info_fiscal=1)
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=2)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([e3], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


# ─────────────── dedup de investimento (sum-preserving fail) ───────────────


def test_investment_double_count_detecta_duplicata() -> None:
    inv = {
        "dados": [
            {
                "tipo": "CDB",
                "instituicao": "Banco X",
                "descricao": "CDB 2028",
                "valor_atual": 1000.0,
            },
            {
                "tipo": "cdb",
                "instituicao": "banco x",
                "descricao": "CDB 2028",
                "valor_atual": 1000.0,
            },
        ]
    }
    hits = investment_double_count(inv)
    assert len(hits) == 1  # normalização casa "CDB"/"cdb", "Banco X"/"banco x"


def test_investment_double_count_limpo_quando_unico() -> None:
    inv = {
        "dados": [
            {"tipo": "CDB", "instituicao": "Banco X", "descricao": "CDB 2028"},
            {"tipo": "CDB", "instituicao": "Banco Y", "descricao": "CDB 2030"},
        ]
    }
    assert investment_double_count(inv) == []


def test_investment_n_produtos_distintos_mesma_data_nao_alerta() -> None:
    # (a) LC-06: 4 LCA do mesmo tipo/instituição/membro/data_referencia, descrição
    # vazia, valores distintos → produtos reais de UM snapshot; somar é correto.
    inv = {
        "dados": [
            {
                "tipo": "lca",
                "instituicao": "btg",
                "membro": "fulano",
                "nome": "",
                "data_referencia": "2026-03",
                "valor_atual": v,
            }
            for v in (100.0, 200.0, 300.0, 400.0)
        ]
    }
    assert investment_double_count(inv) == []


def test_investment_mesma_posicao_dois_snapshots_alerta() -> None:
    # (b) LC-06: MESMA posição (mesmo tipo/inst/ticker) em 2 data_referencia — e com
    # membro divergente (o escape membro-vazio real) → snapshot stale cross-período.
    base = {"tipo": "outros", "instituicao": "binance", "nome": "btc"}
    a = {**base, "membro": "", "data_referencia": "2025-03", "valor_atual": 1000.0}
    b = {**base, "membro": "fulano", "data_referencia": "2025-12", "valor_atual": 1500.0}
    hits = investment_double_count({"dados": [a, b]})
    assert len(hits) == 1 and "cross-período" in hits[0]


def test_investment_le_campo_nome_nao_descricao() -> None:
    # Posição real do E4 usa ``nome`` (não ``descricao``): dois produtos distintos com
    # nomes diferentes e mesma data não devem colidir (regressão do bug de campo).
    base = {"tipo": "acao", "instituicao": "xp", "data_referencia": "2026-03"}
    a = {**base, "nome": "PETR4", "valor_atual": 500.0}
    b = {**base, "nome": "VALE3", "valor_atual": 700.0}
    assert investment_double_count({"dados": [a, b]}) == []


def test_investment_vencimento_distingue_renda_fixa() -> None:
    # Renda fixa sem nome mas com vencimentos distintos = produtos distintos: o
    # descritor nome@vencimento separa-os mesmo no mesmo snapshot (LC-06).
    base = {
        "tipo": "cdb",
        "instituicao": "btg",
        "data_referencia": "2026-03",
        "valor_atual": 1000.0,
    }
    inv = {
        "dados": [
            {**base, "vencimento": "2027-01"},
            {**base, "vencimento": "2029-05"},
        ]
    }
    assert investment_double_count(inv) == []

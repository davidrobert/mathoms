"""Sombra do colapso cross-documento em produção (ADR-364 · A40.l2 PR3a).

O que estes testes travam é a propriedade que torna a sombra *shipável*: ela mede sem
mudar nada. Um teste que só checasse "o colapsador foi instanciado" passaria igual se
`collapse_enforce` vazasse para True — e aí a sombra removeria dado em produção.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cross_document_collapse_types import (  # noqa: E402
    OverrideRetentionGuard,
    shadow_counts,
)
from pipeline.domain.services.cross_document_collapser import (  # noqa: E402
    CrossDocumentCollapser,
)
from tests.unit.pipeline.test_collapse_cardinality import _doc, _measure  # noqa: E402


def _duas_pernas():
    """Mesma chave em duas proveniências — o caso que a lane existe para medir."""
    return [_doc(1, "itau_extrato.json"), _doc(1, "itau_llm.json", metodo="llm")]


def test_measure_nao_muda_a_lista_de_statements():
    """A sombra não pode ter caminho de escrita — nem por acidente de aliasing."""
    stmts = _duas_pernas()
    antes = [(s.source_document, len(s.transactions)) for s in stmts]

    candidates = _measure(stmts)

    assert [(s.source_document, len(s.transactions)) for s in stmts] == antes
    assert any(c.collapsible for c in candidates), "fixture sem candidato não prova nada"


def test_shadow_counts_conta_so_o_colapsavel():
    counts = shadow_counts(_measure(_duas_pernas()))

    assert counts["candidatos"] == 1
    assert counts["colapsaveis"] == 1
    assert counts["rows_removiveis"] == 1
    # `valor_cents` é MAGNITUDE — o sinal vive em `direction`, como no instrumento da
    # A40.l1. Somar com sinal aqui faria débito e crédito se cancelarem no agregado.
    assert counts["cents_removiveis"] == 10_000


def test_shadow_counts_materializa_generator():
    """Regressão: consumir o iterador na comprehension reportaria ``candidatos=0``."""
    candidates = _measure(_duas_pernas())

    counts = shadow_counts(c for c in candidates)

    assert counts["candidatos"] == 1


def test_bloqueado_conta_como_candidato_mas_nao_como_colapsavel():
    """Partição: o agregado não pode confundir "vi" com "removeria"."""
    # Duas nativas de arquivos distintos: candidato de UMA proveniência, nada a remover
    # (D5 — row nativa nunca sai).
    counts = shadow_counts(_measure([_doc(1, "a.json"), _doc(1, "b.json")]))

    assert counts["colapsaveis"] == 0
    assert counts["rows_removiveis"] == 0


@pytest.mark.parametrize("campo", ["candidatos", "colapsaveis", "rows_removiveis"])
def test_sem_candidato_zera_sem_estourar(campo):
    assert shadow_counts(())[campo] == 0


# `dev/certify_ledger_local.py` entra no escopo: ele monta o mesmo adapter e estava fora do
# parse, então ligar o enforce lá era invisível. `ast.Attribute` entra porque chamada por
# módulo (`mod._e3_build_adapter(...)`) não é `ast.Name` e escapava do filtro.
_FONTES_DO_ADAPTER = (
    "scripts/reconcile_transactions.py",
    "dev/certify_ledger_local.py",
)


def _nome_chamado(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def _enforce_args_do_stage() -> list[ast.expr | None]:
    """Valor de ``collapse_enforce`` em cada chamada a ``_e3_build_adapter`` nas fontes."""
    raiz = Path(__file__).resolve().parents[3]
    return [
        next((kw.value for kw in node.keywords if kw.arg == "collapse_enforce"), None)
        for fonte in _FONTES_DO_ADAPTER
        for node in ast.walk(ast.parse((raiz / fonte).read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and _nome_chamado(node.func) == "_e3_build_adapter"
    ]


# MEDIDO 2026-08-10: trocar o DEFAULT da assinatura (`collapse_enforce=False` → `True`) deixava
# a suíte inteira verde — 6210 testes —, inclusive o gate abaixo. Ele aceita `arg is None`
# porque o call-site de produção omite o kwarg, e nada pinava a assinatura. Um refactor que
# mexesse no default ligaria remoção de dado financeiro em produção sem um único sinal.
def test_o_default_da_assinatura_e_False__o_gate_de_call_site_nao_alcanca_isso():
    """Mutação: `collapse_enforce=True` no `def`. Só este teste fica vermelho."""
    import inspect

    from scripts.reconcile_transactions import _e3_build_adapter

    assinatura = inspect.signature(_e3_build_adapter)

    assert assinatura.parameters["collapse_enforce"].default is False


def test_stage_de_producao_nunca_liga_o_enforce():
    """AST, não grep: o único caminho de produção monta o adapter em SOMBRA."""
    # Sem isto, `collapse_enforce=True` no call-site passa verde — nenhum teste de unidade
    # do colapsador exercita `main_with_store`, e a suíte segue passando enquanto produção
    # começa a remover dado financeiro.
    chamadas = _enforce_args_do_stage()

    assert chamadas, "call-site sumiu — o teste passaria por vacuidade"
    for arg in chamadas:
        assert arg is None or (
            isinstance(arg, ast.Constant) and arg.value is False
        ), "stage de produção passou collapse_enforce truthy — a sombra virou enforce"


def _measurement(statements):
    return CrossDocumentCollapser(retention_guard=OverrideRetentionGuard.sem_overrides()).measure(
        statements
    )


# `retido_por_override` só enxerga o dano materializado. O reservatório é o ANTECEDENTE: no
# corpus de dogfood são 441 rows de perna LLM sem gêmea nativa, que viram alvo no instante em
# que o extrato daquela conta for ingerido. Sem publicá-lo, o gate do flip mede 0 num corpus
# incompleto e conclui "vazio" — a terceira vez que esta lane cairia nisso.
@pytest.mark.parametrize(
    ("corpus", "esperado"),
    [
        (["llm"], 1),
        (["native"], 0),
        (["llm", "native"], 0),
    ],
    ids=["perna_llm_orfa_entra", "nativa_orfa_nunca_entra", "par_formado_sai_do_reservatorio"],
)
def test_reservatorio_conta_so_a_perna_llm_sem_gemea(corpus, esperado):
    """Mutação: contar toda chave de proveniência única — a nativa solitária, que jamais vira
    alvo (D5, row nativa nunca sai), inflaria o preditor e o gate leria fila onde não há."""
    stmts = [_doc(1, f"{m}.json", metodo=m) for m in corpus]

    assert _measurement(stmts).reservatorio_llm_sem_gemea == esperado


def test_par_formado_e_candidato__o_reservatorio_zerou_por_promocao_nao_por_cegueira():
    """Sem esta asserção o caso `par_formado` passaria verde num colapsador que não vê nada."""
    m = _measurement([_doc(1, "llm.json", metodo="llm"), _doc(1, "native.json")])

    assert len(m.candidates) == 1 and m.reservatorio_llm_sem_gemea == 0


# ─── Gate COMPORTAMENTAL: o que o AST não alcança ────────────────────────────────────────
#
# O AST prova o que está ESCRITO no call-site. Não prova o que o adapter FAZ. Quando o flip
# trocar a constante por uma leitura de flag (`collapse_enforce=_e3_collapse_enforce_enabled(...)`),
# a mutação plausível deixa de ser o call-site e passa a ser o interior do helper — `return True`,
# `isinstance` invertido — e o AST fica cego para ela por construção. Este teste roda a fiação
# real de produção sobre um par colapsável e mede o EFEITO no ledger.
class _CtxConfigs:
    """Configs mínimas que `_e3_build_adapter` carrega — nenhuma toca o colapso."""

    workspace_id = "ws-teste"
    pipeline_run_id = None

    def load_config(self, nome: str):
        return {} if nome != "pipeline.json" else {"reconciliation": {"tolerance_days": 3}}


def _colapsador_como_o_stage_monta():
    from pipeline.domain.services.cross_document_collapse_types import OverrideRetentionGuard
    from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser

    return CrossDocumentCollapser(retention_guard=OverrideRetentionGuard.sem_overrides())


def _roda_fiacao_de_producao() -> int:
    """`count` no canal do colapso depois de rodar o adapter que o STAGE monta."""
    from pipeline.domain.services.cross_document_collapse_types import CANAL_COLAPSO
    from scripts.reconcile_transactions import _e3_build_adapter
    from tests.unit.pipeline.test_collapse_ledger_channel import _store_com_par_cross_documento

    store = _store_com_par_cross_documento()
    # `collapse_enforce` OMITIDO, exatamente como o call-site de produção — é por isso que a
    # mutação do DEFAULT da assinatura cai aqui, e não no gate AST.
    adapter, _canon = _e3_build_adapter(
        _CtxConfigs(), cross_document_collapser=_colapsador_como_o_stage_monta()
    )
    adapter.reconcile_via_store(store)
    return sum(
        (store.read("E3", k)["remocoes"].get(CANAL_COLAPSO) or {}).get("count", 0)
        for k in store.list_keys("E3")
    )


# Controle de não-vacuidade: `test_collapse_ledger_channel.py::test_enforce_remove_a_row_...`
# prova que ESTA fixture produz corte quando o enforce é ligado. Sem esse par, o zero abaixo
# seria indistinguível de "a fixture não tem o que colapsar".
def test_a_fiacao_de_producao_nao_remove_nada_no_canal_do_colapso():
    """Mutação: default `True` na assinatura de `_e3_build_adapter` — o AST passa verde nela."""
    assert (
        _roda_fiacao_de_producao() == 0
    ), "a fiação de produção removeu row — a sombra virou enforce"

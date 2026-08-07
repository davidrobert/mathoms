"""Gate de pré-condição do enforce de colapso ([[A40.l2]] D1 · PR3b).

O teste central é `test_override_na_perna_llm_bloqueia`: ele mata a premissa que o
co-design refutou — "a perna LLM não carrega âncora v2, logo remover row dela não
órfana override". O subsistema de override tem hasher PRÓPRIO, sem o gate de
discriminantes do item E4, então row de titular vazio ANCORA. Gate construído sobre a
premissa velha nasceria cego na classe exata que o enforce apaga.

O PR3b tornou o predicado **cumulativo** (`medido` · `hits` · `sem_snapshot` ·
`tx_data_nao_iso` · vivacidade **universal**) e a adjudicação **por hash**. Cada cláusula
tem teste que fica vermelho quando ela é removida — sem isso o predicado é prosa.

⚠️ **A escapatória de absolvição (`natural_key_hash == survivor_hash`) é exercitada por
ZERO overrides no corpus dogfood** (medido 2026-08-07: 5 ativos, 4
`casou_corpus_fora_de_candidato`, 1 `casou_nada`, 0 em candidato). Ela é necessária para o
gate ser alcançável em princípio, mas o dogfood **não a prova** — as travas de absolvição
vêm de fixture sintética, aqui. "Gate verde no dogfood" não é evidência de que ela funciona.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops import collapse_precondition
from backend.app.services.internal_ops.collapse_precondition import _override_gate_digest
from backend.tests import factories
from pipeline.domain.services.cross_document_collapse_types import (
    CollapseCandidate,
    RemovalTarget,
)
from pipeline.domain.services.cross_document_collapser import gate_key_digest

pytestmark = pytest.mark.asyncio

_DATA, _CENTS, _MOEDA = "2026-03-30", 10000, "BRL"
_DESC_CRUA = "Compra  Mercado"
_SOBREVIVENTE = "h-sobrevivente"


def _candidato(
    *, colapsavel: bool = True, descricao: str = _DESC_CRUA, sobrevivente: str = _SOBREVIVENTE
) -> CollapseCandidate:
    digest = gate_key_digest(data_iso=_DATA, valor_cents=_CENTS, moeda=_MOEDA, descricao=descricao)
    return CollapseCandidate(
        key_digest="ffffffffffff",
        gate_digest=digest,
        survivor_hash=sobrevivente,
        mes=_DATA[:7],
        valor_cents=_CENTS,
        moeda=_MOEDA,
        direction="debit",
        n_rows=2,
        n_provenances=2,
        survivor_cardinality=1,
        removable_rows=1 if colapsavel else 0,
        removal_targets=(RemovalTarget("h", 1, 1),) if colapsavel else (),
        blocked_reason=None if colapsavel else "banco_conflitante",
    )


_SNAPSHOT = {
    "tx_data": _DATA,
    "tx_valor_cents": _CENTS,
    "tx_moeda": _MOEDA,
    "tx_direction": "debit",
    "tx_descricao": _DESC_CRUA,
}


def _override(db, ws_id: str, *, titular: str | None, natural_key: str | None = "nk", **kw):
    """Override com snapshot ADR-282. ``titular=None`` = perna LLM (hash degenerado)."""
    campos = {**_SNAPSHOT, "tx_titular": titular, **kw}
    # `(workspace_id, transaction_hash)` é unique — dois overrides no mesmo workspace exigem
    # hashes distintos, e o default derivado da descrição os separa sem que cada teste tenha
    # de inventar um. Este valor NÃO é lido pelo gate (o join é pelo snapshot).
    padrao = f"v1-legado-nao-usado-{campos.get('tx_descricao')}"
    row = TransactionOverride(
        workspace_id=ws_id,
        transaction_hash=campos.pop("transaction_hash", padrao),
        natural_key_hash=natural_key,
        original_category="outros",
        new_category="alimentacao",
        **campos,
    )
    db.add(row)
    db.flush()
    return row


# Modela o caso normal — a row de cada override existe no E3 deste run —, que é o que faz a
# vivacidade universal passar. Ela NÃO é provada por este helper: tem os dois testes próprios
# abaixo (`test_vivacidade_existencial_nao_basta` e
# `test_vivacidade_universal_passa_quando_todos_casam`), porque cláusula cuja única evidência
# é a fixture que a satisfaz é cláusula não testada.
def _corpus_de(*overrides) -> frozenset[str]:
    """Corpus vivo: o digest de cada override passado."""
    return frozenset(d for d in (_override_gate_digest(o) for o in overrides) if d)


async def test_override_na_perna_llm_bloqueia(db) -> None:
    """Titular VAZIO ancora igual — o hasher do override não tem o gate de discriminantes."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert not result.ok
    assert report.hits == 1
    assert "enforce bloqueado" in (result.error or "")


async def test_join_e_por_snapshot_nao_por_hash(db) -> None:
    """`transaction_hash` de versão v1 não impede o match — o join é pelo snapshot."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular="alguem", transaction_hash="hash-v1-incompativel")
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert not result.ok and report.hits == 1


async def test_ancora_indecidivel_bloqueia(db) -> None:
    """Sem `natural_key_hash` E sem snapshot ⇒ não dá para decidir ⇒ fail-closed."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="alguem", natural_key=None, tx_data=None)
        result, report = collapse_precondition.evaluate(
            s, ws.id, [_candidato()], {_candidato().gate_digest}
        )

    assert not result.ok
    assert report.hits_ancora_indecidivel == 1


async def test_quarentenado_e_inerte(db) -> None:
    """`orphaned_at` não-nulo ⇒ o read-path ignora ⇒ NUNCA bloqueia (só conta)."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None, orphaned_at=datetime.now(timezone.utc))
        result, report = collapse_precondition.evaluate(
            s, ws.id, [_candidato()], {_candidato().gate_digest}
        )

    assert result.ok
    assert (report.hits, report.quarentenados_atingidos) == (0, 1)


async def test_candidato_bloqueado_nao_e_alvo(db) -> None:
    """Predicado reprovou ⇒ a row não sai ⇒ o override não corre risco."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None)
        result, report = collapse_precondition.evaluate(
            s, ws.id, [_candidato(colapsavel=False)], _corpus_de(o)
        )

    assert result.ok and report.hits == 0


async def test_override_de_outra_transacao_nao_bloqueia(db) -> None:
    """Sem falso-positivo: descrição diferente ⇒ digest diferente ⇒ libera."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular="alguem", tx_descricao="Outra Compra Totalmente")
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert result.ok
    assert (report.overrides_ativos, report.hits) == (1, 0)


async def test_sem_candidato_colapsavel_libera(db) -> None:
    """Corpus sem colapso ⇒ gate vazio ⇒ liberado, com as contagens no details."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None)
        result, _report = collapse_precondition.evaluate(s, ws.id, [], _corpus_de(o))

    assert result.ok
    assert result.details["alvos_do_colapsador"] == 0
    assert result.details["overrides_ativos"] == 1


async def test_override_com_natural_key_mas_sem_snapshot_bloqueia(db) -> None:
    """P0: antes ele ESCAPAVA. `_override_gate_digest` devolvia `None`, `None in alvos`
    era `False`, e `_ancora_indecidivel` não o pegava porque exigia `natural_key_hash
    is None`. Workspace inteiro sem snapshot devolvia `hits=0 ⇒ liberado`."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        # `hash_version=2` é o que isola o P0: âncora v2 GENUÍNA, então
        # `_ancora_indecidivel` NÃO o pega — antes ele escapava por completo.
        _override(s, ws.id, titular=None, natural_key="nk-v2", hash_version=2, tx_data=None)
        result, report = collapse_precondition.evaluate(
            s, ws.id, [_candidato()], {_candidato().gate_digest}
        )

    assert not result.ok
    assert report.hits_ancora_indecidivel == 0  # escapava por aqui
    assert report.sem_snapshot == 1  # e agora é pego por aqui
    assert not report.liberado


async def test_hash_version_1_conta_como_sem_ancora_v2(db) -> None:
    """`natural_key_hash` preenchido em `hash_version=1` é v1 disfarçada — igualmente
    indecidível. O proxy `natural_key_hash is None` sozinho deixava passar."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None, natural_key="nk-v1", hash_version=1, tx_data=None)
        result, report = collapse_precondition.evaluate(
            s, ws.id, [_candidato()], {_candidato().gate_digest}
        )

    assert not result.ok
    assert report.hits_ancora_indecidivel == 1


# ─── PR3b: as cinco cláusulas do predicado, uma prova de mutação cada ────────────────────


async def test_run_sem_medicao_nao_libera(db) -> None:
    """Corpus vazio = flag de measure desligada. Antes do PR3b isto saía `liberado`."""
    # `alvos = ∅ ⇒ hits = 0 ⇒ liberado` autorizava o flip DESTRUTIVO num run que não mediu
    # nada. Remover a cláusula `medido` deixa este teste verde de novo.
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None, tx_data=None)
        result, report = collapse_precondition.evaluate(s, ws.id, [], frozenset())

    assert not result.ok
    assert not report.medido
    assert "nao_medido" in report.clausulas_reprovadas()


async def test_tx_data_fora_do_iso_bloqueia(db) -> None:
    """`tx_data` é `String(10)`: acomoda `DD/MM/YYYY` igual. Medir não bastava — impede."""
    # O override nunca casa nada (digest derivado de data não-ISO), então antes do PR3b ele
    # contava em `com_snapshot`, não entrava em `hits`, e o run saía `liberado`. Literalmente
    # "confunde medir com impedir".
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular="alguem", tx_data="30/03/2026")
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert report.tx_data_nao_iso == 1
    assert not result.ok
    assert "tx_data_nao_iso=1" in (result.error or "")


async def test_vivacidade_existencial_nao_basta(db) -> None:
    """Dois julgáveis, um casando: sob `> 0` o outro entraria em `hits == 0` como limpo."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        visto = _override(s, ws.id, titular="a", tx_descricao="Existe No Corpus")
        _cego = _override(s, ws.id, titular="b", tx_descricao="Nao Existe No Corpus")
        result, report = collapse_precondition.evaluate(s, ws.id, [], _corpus_de(visto))

    assert (report.snapshot_casa_corpus, report.com_snapshot) == (1, 2)
    assert report.snapshot_casa_corpus > 0, "sob a forma existencial este run passaria"
    assert not report.vivacidade_universal and not result.ok


async def test_vivacidade_universal_passa_quando_todos_casam(db) -> None:
    """Controle positivo — sem ele a cláusula poderia estar sempre reprovando."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        a = _override(s, ws.id, titular="a", tx_descricao="Um")
        b = _override(s, ws.id, titular="b", tx_descricao="Dois")
        result, report = collapse_precondition.evaluate(s, ws.id, [], _corpus_de(a, b))

    assert (report.snapshot_casa_corpus, report.com_snapshot) == (2, 2)
    assert report.vivacidade_universal and result.ok


# ─── PR3b: adjudicação por HASH (a escapatória) — só fixture sintética a exercita ────────


async def test_override_ancorado_no_sobrevivente_e_absolvido(db) -> None:
    """A escapatória que torna o gate ALCANÇÁVEL: quem já ancora a row que sobra não órfana."""
    # Sem ela o predicado é inalcançável por construção — o `gate_digest` é compartilhado
    # pelas duas pernas por definição de candidato, então re-ancorar não muda o digest e o
    # override seguiria `hit` para sempre. Remover `_absolvido` de `_atingido` ⇒ hits=1 ⇒ red.
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None, natural_key=_SOBREVIVENTE, hash_version=2)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert report.alvos_do_colapsador == 1, "sem alvo o teste não exercita a absolvição"
    assert (report.hits, report.absolvidos_por_sobrevivente) == (0, 1)
    assert result.ok


async def test_absolvicao_exige_ancora_v2_genuina(db) -> None:
    """`hash_version=1` com hash igual ao sobrevivente é coincidência em namespace misto."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None, natural_key=_SOBREVIVENTE, hash_version=1)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert (report.hits, report.absolvidos_por_sobrevivente) == (1, 0)
    assert not result.ok


async def test_survivor_hash_vazio_nao_absolve(db) -> None:
    """`survivor_hash=""` significa "não há sobrevivente eleito", não "todos estão salvos"."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None, natural_key="", hash_version=2)
        result, report = collapse_precondition.evaluate(
            s, ws.id, [_candidato(sobrevivente="")], _corpus_de(o)
        )

    assert (report.hits, report.absolvidos_por_sobrevivente) == (1, 0)
    assert not result.ok


async def test_absolvicao_nao_atravessa_digest(db) -> None:
    """Ancorar o sobrevivente de OUTRA chave não absolve — o hash é olhado por digest."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        o = _override(s, ws.id, titular=None, natural_key="h-de-outra-chave", hash_version=2)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()], _corpus_de(o))

    assert (report.hits, report.absolvidos_por_sobrevivente) == (1, 0)
    assert not result.ok


# ─── PR3b: fail-loud e argumento obrigatório ────────────────────────────────────────────


class _CandidatoRenomeado:
    """Candidato após um rename — exatamente o que `getattr(..., default)` engolia."""

    collapsible = True
    gate_digest = "qualquer"


async def test_alvos_falha_alto_quando_o_candidato_e_renomeado() -> None:
    """Fail-open aqui dava `alvos = ∅ ⇒ liberado=True` em silêncio (precedente ADR-359)."""
    with pytest.raises(AttributeError):
        collapse_precondition._alvos([_CandidatoRenomeado()])


async def test_evaluate_exige_corpus_digests(db) -> None:
    """Sem default: chamador que esquece o argumento certificava vivacidade vazia."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s, pytest.raises(TypeError):
        collapse_precondition.evaluate(s, ws.id, [_candidato()])


async def test_liberado_e_derivado_das_clausulas_reprovadas() -> None:
    """Fonte única: o predicado e a mensagem de erro não podem divergir."""
    from backend.app.services.internal_ops.collapse_precondition import PreconditionReport

    limpo = PreconditionReport(corpus_observado=1)
    sujo = PreconditionReport(corpus_observado=1, hits=2, tx_data_nao_iso=1)

    assert limpo.liberado and limpo.clausulas_reprovadas() == ()
    assert not sujo.liberado
    assert sujo.clausulas_reprovadas() == ("hits=2", "tx_data_nao_iso=1")

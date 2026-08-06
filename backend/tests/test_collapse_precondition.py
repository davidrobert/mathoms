"""Gate de pré-condição do enforce de colapso ([[A40.l2]] D1).

O teste central é `test_override_na_perna_llm_bloqueia`: ele mata a premissa que o
co-design refutou — "a perna LLM não carrega âncora v2, logo remover row dela não
órfana override". O subsistema de override tem hasher PRÓPRIO, sem o gate de
discriminantes do item E4, então row de titular vazio ANCORA. Gate construído sobre a
premissa velha nasceria cego na classe exata que o enforce apaga.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops import collapse_precondition
from backend.tests import factories
from pipeline.domain.services.cross_document_collapse_types import (
    CollapseCandidate,
    RemovalTarget,
)
from pipeline.domain.services.cross_document_collapser import gate_key_digest

pytestmark = pytest.mark.asyncio

_DATA, _CENTS, _MOEDA = "2026-03-30", 10000, "BRL"
_DESC_CRUA = "Compra  Mercado"


def _candidato(*, colapsavel: bool = True, descricao: str = _DESC_CRUA) -> CollapseCandidate:
    digest = gate_key_digest(data_iso=_DATA, valor_cents=_CENTS, moeda=_MOEDA, descricao=descricao)
    return CollapseCandidate(
        key_digest="ffffffffffff",
        gate_digest=digest,
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
    row = TransactionOverride(
        workspace_id=ws_id,
        transaction_hash=campos.pop("transaction_hash", "v1-legado-nao-usado"),
        natural_key_hash=natural_key,
        original_category="outros",
        new_category="alimentacao",
        **campos,
    )
    db.add(row)
    db.flush()
    return row


async def test_override_na_perna_llm_bloqueia(db) -> None:
    """Titular VAZIO ancora igual — o hasher do override não tem o gate de discriminantes."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert not result.ok
    assert report.hits == 1
    assert "enforce bloqueado" in (result.error or "")


async def test_join_e_por_snapshot_nao_por_hash(db) -> None:
    """`transaction_hash` de versão v1 não impede o match — o join é pelo snapshot."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="alguem", transaction_hash="hash-v1-incompativel")
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert not result.ok and report.hits == 1


async def test_ancora_indecidivel_bloqueia(db) -> None:
    """Sem `natural_key_hash` E sem snapshot ⇒ não dá para decidir ⇒ fail-closed."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="alguem", natural_key=None, tx_data=None)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert not result.ok
    assert report.hits_ancora_indecidivel == 1


async def test_quarentenado_e_inerte(db) -> None:
    """`orphaned_at` não-nulo ⇒ o read-path ignora ⇒ NUNCA bloqueia (só conta)."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None, orphaned_at=datetime.now(timezone.utc))
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert result.ok
    assert (report.hits, report.quarentenados_atingidos) == (0, 1)


async def test_candidato_bloqueado_nao_e_alvo(db) -> None:
    """Predicado reprovou ⇒ a row não sai ⇒ o override não corre risco."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None)
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato(colapsavel=False)])

    assert result.ok and report.hits == 0


async def test_override_de_outra_transacao_nao_bloqueia(db) -> None:
    """Sem falso-positivo: descrição diferente ⇒ digest diferente ⇒ libera."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="alguem", tx_descricao="Outra Compra Totalmente")
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert result.ok
    assert (report.overrides_ativos, report.hits) == (1, 0)


async def test_sem_candidato_colapsavel_libera(db) -> None:
    """Corpus sem colapso ⇒ gate vazio ⇒ liberado, com as contagens no details."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular=None)
        result, report = collapse_precondition.evaluate(s, ws.id, [])

    assert result.ok and report.liberado
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
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

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
        result, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert not result.ok
    assert report.hits_ancora_indecidivel == 1


async def test_vivacidade_do_join_distingue_corpus_limpo_de_cegueira(db) -> None:
    """`hits=0` só é segurança se o join CASA alguma coisa. Sem este número, gate cujo
    digest nunca resolve é indistinguível de corpus sem risco."""
    ws = await factories.make_workspace(db)
    await db.commit()
    vivo = gate_key_digest(data_iso=_DATA, valor_cents=_CENTS, moeda=_MOEDA, descricao=_DESC_CRUA)

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="alguem")
        _cego, rep_cego = collapse_precondition.evaluate(s, ws.id, [], corpus_digests=frozenset())
        _vivo, rep_vivo = collapse_precondition.evaluate(s, ws.id, [], corpus_digests={vivo})

    assert (rep_cego.hits, rep_vivo.hits) == (0, 0)  # ambos "liberados" por hits
    assert rep_cego.snapshot_casa_corpus == 0  # ...mas este separa os dois
    assert rep_vivo.snapshot_casa_corpus == 1


async def test_tx_data_fora_do_iso_e_contado(db) -> None:
    """`tx_data` é `String(10)`: acomoda `DD/MM/YYYY` igual. A forma é contada, não presumida."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="alguem", tx_data="30/03/2026")
        _r, report = collapse_precondition.evaluate(s, ws.id, [_candidato()])

    assert report.tx_data_nao_iso == 1

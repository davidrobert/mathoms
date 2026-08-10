"""Trava anti-destruição do colapso cross-documento ([[A40.l2]] §3d · [[ADR-364]]).

Papel declarado: prova de que o colapso **não é writer** do subsistema de override. NÃO é
prova de segurança do enforce — essa vem da retenção, medida em `test_collapse_enforce.py`.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops.collapse_precondition import from_active_overrides
from backend.tests import factories
from backend.tests.test_collapse_precondition import _CENTS, _MOEDA, _override
from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction
from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser

pytestmark = pytest.mark.asyncio


def _stmt(descricao: str, arquivo: str, metodo: str) -> BankStatement:
    llm = metodo == "llm"
    return BankStatement(
        institution="banco exemplo",
        member_key=None if llm else "titular exemplo",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        currency=_MOEDA,
        transactions=[
            Transaction(
                date=date(2026, 3, 30),
                description=descricao,
                amount=Money.of(f"-{_CENTS // 100}.00", _MOEDA),
            )
        ],
        account_type="extrato" if llm else "extratoconta",
        extraction_method=metodo,
        source_document=arquivo,
    )


def _statements_colapsaveis(descricao: str) -> list[BankStatement]:
    """Par LLM + nativa sobre a MESMA transação — o caso que o enforce remove."""
    return [_stmt(descricao, "llm.json", "llm"), _stmt(descricao, "extrato.json", "native")]


# O total não é redundância dos dois carimbos: `delete_override.py:87` é hard delete — a row
# some do banco sem que `orphaned_at` nem `deleted_at` mexam, e uma trava que olhasse só os
# carimbos leria destruição total como "nada mudou".
def _contadores_de_override(s, ws_id: str) -> dict[str, int]:
    """Os TRÊS: `orphaned_at`, `deleted_at` e o **total**."""
    base = s.query(TransactionOverride).filter(TransactionOverride.workspace_id == ws_id)
    return {
        "total": base.count(),
        "orfaos": base.filter(TransactionOverride.orphaned_at.isnot(None)).count(),
        "deletados": base.filter(TransactionOverride.deleted_at.isnot(None)).count(),
    }


def _colapsa_com_guard_do_banco(s, ws_id: str):
    """Roda o colapso real com o guard lido do DB; devolve `(guard, removals)`."""
    guard = from_active_overrides(s, ws_id)
    _stmts, _medicao, removals = CrossDocumentCollapser(retention_guard=guard).collapse(
        _statements_colapsaveis("Compra Livre")
    )
    s.expire_all()
    return guard, removals


async def test_colapso_nao_escreve_no_subsistema_de_override(db) -> None:
    """Papel declarado: prova de que o colapso **não é writer** — NÃO prova de segurança
    do enforce, que vem da retenção ([[ADR-364]] §Emenda)."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        _override(s, ws.id, titular="fulano", tx_descricao="Assinatura Protegida")
        s.commit()
        antes = _contadores_de_override(s, ws.id)

        guard, removals = _colapsa_com_guard_do_banco(s, ws.id)

        depois = _contadores_de_override(s, ws.id)

    assert removals, "fixture sem corte não prova que o colapso não escreve"
    assert guard.overrides_ativos == 1, "guard cego não exercita o caminho de leitura"
    assert depois == antes == {"total": 1, "orfaos": 0, "deletados": 0}


async def test_hard_delete_so_aparece_no_total__por_isso_ele_esta_na_trava(db) -> None:
    """Justifica o terceiro contador. Mutação: tirar `total` de `_contadores_de_override` —
    a trava acima passaria verde com o subsistema de override inteiro apagado."""
    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as s:
        row = _override(s, ws.id, titular="fulano")
        s.commit()
        antes = _contadores_de_override(s, ws.id)

        s.delete(row)
        s.commit()
        depois = _contadores_de_override(s, ws.id)

    assert (depois["orfaos"], depois["deletados"]) == (antes["orfaos"], antes["deletados"])
    assert depois["total"] == antes["total"] - 1 == 0

"""Pré-condição do enforce de colapso cross-documento ([[A40.l2]] D1 · [[ADR-354]]).

READ-ONLY. Responde uma pergunta: **algum override ativo ancora numa row que o
colapsador removeria?** Enquanto a resposta for sim, o enforce não pode ligar — a
remoção órfanaria a categorização manual do usuário.

O join **não é por igualdade de hash**. Duas razões medidas em 2026-08-05:

1. ``transaction_overrides.transaction_hash`` é **namespace de versão mista** (row
   pré-cutover carrega ``_hash_v1``, pós-cutover ``_hash_v2``), então interseção
   contra um conjunto v2 dá vazio **por incompatibilidade de versão**, não por corpus.
2. O subsistema de override tem **hasher próprio, sem** o gate ``_has_discriminants``
   do item E4 — logo row de perna LLM (titular vazio) **pode** ancorar override em v2,
   com hash degenerado. Gate construído sobre "a perna LLM não tem âncora v2" nasce
   cego na classe exata que o enforce apaga.

Em vez disso, o backend recompõe o ``gate_digest`` (direction-free, provenance-free)
das **colunas de snapshot da [[ADR-282]]** e cruza com o que o pipeline emite. Imune a
versão de hash, imune ao gate de discriminantes, sem PII cruzando o boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops.results import OpResult
from pipeline.domain.services.cross_document_collapser import gate_key_digest

_ACTION = "override.collapse_precondition"
# `tx_data` é `String(10)`, largura que acomoda `YYYY-MM-DD` E `DD/MM/YYYY` igualmente —
# o tipo não discrimina, então a forma é contada, não presumida.
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class PreconditionReport:
    """Contagens PII-free — vai para `AuditRecord.details` e para o `OpResult`."""

    overrides_ativos: int = 0
    alvos_do_colapsador: int = 0
    hits: int = 0
    hits_ancora_indecidivel: int = 0
    quarentenados_atingidos: int = 0
    # Ativos sem snapshot utilizável: o gate NÃO consegue julgá-los. Contá-los à parte
    # é o que separa "corpus limpo" de "não consegui olhar" — sem isso um workspace
    # cujos overrides não têm snapshot devolvia `hits=0 ⇒ liberado`.
    sem_snapshot: int = 0
    tx_data_nao_iso: int = 0
    # Vivacidade do join: dos que TÊM snapshot, quantos casam alguma row do E3. Se
    # esta fração é ~0, `hits=0` é vácuo — o join nunca casa, não há segurança.
    snapshot_casa_corpus: int = 0

    @property
    def liberado(self) -> bool:
        """``True`` ⇒ nenhum override ativo é atingido **e** todos foram julgáveis."""
        return self.hits == 0 and self.sem_snapshot == 0

    def as_details(self) -> dict:
        return {
            "overrides_ativos": self.overrides_ativos,
            "alvos_do_colapsador": self.alvos_do_colapsador,
            "hits": self.hits,
            "hits_ancora_indecidivel": self.hits_ancora_indecidivel,
            "quarentenados_atingidos": self.quarentenados_atingidos,
            "sem_snapshot": self.sem_snapshot,
            "tx_data_nao_iso": self.tx_data_nao_iso,
            "snapshot_casa_corpus": self.snapshot_casa_corpus,
            "liberado": self.liberado,
        }


def _override_gate_digest(override: TransactionOverride) -> str | None:
    """Digest do override pelas colunas de snapshot; ``None`` se o snapshot falta."""
    if not override.tx_data or override.tx_valor_cents is None:
        return None
    return gate_key_digest(
        data_iso=override.tx_data,
        valor_cents=override.tx_valor_cents,
        moeda=override.tx_moeda or "",
        descricao=override.tx_descricao,
    )


def _sem_ancora_v2(override: TransactionOverride) -> bool:
    """Sem âncora v2 utilizável — `hash_version=1` conta, mesmo com hash preenchido."""
    # `natural_key_hash is None` sozinho é proxy errado: row com hash preenchido em
    # `hash_version=1` é v1 disfarçada e igualmente indecidível.
    return override.natural_key_hash is None or (override.hash_version or 0) < 2


def _ancora_indecidivel(override: TransactionOverride) -> bool:
    """Sem âncora v2 E sem snapshot — não dá para decidir, então bloqueia."""
    # Fail-closed deliberado: a polaridade de um gate que BLOQUEIA é sobre-detectar.
    # Over-match é adjudicável à mão em poucas rows; under-match é override órfão em
    # produção, que apaga categorização manual sem sinal.
    return _sem_ancora_v2(override) and _override_gate_digest(override) is None


def _ativos(db: Session, workspace_id: str) -> list[TransactionOverride]:
    """Overrides que o read-path ainda resolve — quarentenado é inerte por `orphaned_at`."""
    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == workspace_id,
        TransactionOverride.orphaned_at.is_(None),
        TransactionOverride.deleted_at.is_(None),
    )
    return list(db.execute(stmt).scalars())


def _quarentenados_atingidos(db: Session, workspace_id: str, alvos: frozenset[str]) -> int:
    """Contagem informativa — quarentenado DEVE seguir inerte, nunca bloquear."""
    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == workspace_id,
        TransactionOverride.orphaned_at.is_not(None),
    )
    return sum(1 for o in db.execute(stmt).scalars() if _override_gate_digest(o) in alvos)


def _alvos(collapse_candidates) -> frozenset[str]:
    """Digests direction-free dos candidatos COLAPSÁVEIS (bloqueado não é alvo)."""
    return frozenset(
        c.gate_digest
        for c in collapse_candidates
        if getattr(c, "collapsible", False) and getattr(c, "gate_digest", "")
    )


def _build_report(
    db: Session, workspace_id: str, alvos: frozenset[str], corpus: frozenset[str]
) -> PreconditionReport:
    ativos = _ativos(db, workspace_id)
    indecidiveis = [o for o in ativos if _ancora_indecidivel(o)]
    casados = [o for o in ativos if _override_gate_digest(o) in alvos]
    com_snapshot = [o for o in ativos if _override_gate_digest(o) is not None]
    return PreconditionReport(
        overrides_ativos=len(ativos),
        alvos_do_colapsador=len(alvos),
        hits=len({o.id for o in casados} | {o.id for o in indecidiveis}),
        hits_ancora_indecidivel=len(indecidiveis),
        quarentenados_atingidos=_quarentenados_atingidos(db, workspace_id, alvos),
        sem_snapshot=len(ativos) - len(com_snapshot),
        tx_data_nao_iso=sum(1 for o in ativos if o.tx_data and not _ISO.fullmatch(o.tx_data)),
        snapshot_casa_corpus=sum(1 for o in com_snapshot if _override_gate_digest(o) in corpus),
    )


def evaluate(
    db: Session, workspace_id: str, collapse_candidates, corpus_digests=frozenset()
) -> tuple[OpResult, PreconditionReport]:
    """Avalia a pré-condição. Read-only: não escreve, não commita, não muta override."""
    # `corpus_digests` são os gate_digest de TODAS as rows do E3 (não só as
    # colapsáveis): medem a VIVACIDADE do join. Sem isso não há como distinguir
    # "nenhum override em risco" de "o join nunca casa".
    report = _build_report(db, workspace_id, _alvos(collapse_candidates), frozenset(corpus_digests))
    if report.liberado:
        return OpResult(ok=True, details=report.as_details()), report
    erro = (
        f"{report.hits} hit(s) + {report.sem_snapshot} sem snapshot julgável "
        "— enforce bloqueado (re-ancore, quarentene ou complete o snapshot)"
    )
    return OpResult(ok=False, error=erro, details=report.as_details()), report

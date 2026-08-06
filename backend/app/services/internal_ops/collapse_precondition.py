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

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops.results import OpResult
from pipeline.domain.services.cross_document_collapser import gate_key_digest

_ACTION = "override.collapse_precondition"


@dataclass(frozen=True)
class PreconditionReport:
    """Contagens PII-free — vai para `AuditRecord.details` e para o `OpResult`."""

    overrides_ativos: int = 0
    alvos_do_colapsador: int = 0
    hits: int = 0
    hits_ancora_indecidivel: int = 0
    quarentenados_atingidos: int = 0

    @property
    def liberado(self) -> bool:
        """``True`` ⇒ nenhum override ativo é atingido; o enforce pode ser flipado."""
        return self.hits == 0

    def as_details(self) -> dict:
        return {
            "overrides_ativos": self.overrides_ativos,
            "alvos_do_colapsador": self.alvos_do_colapsador,
            "hits": self.hits,
            "hits_ancora_indecidivel": self.hits_ancora_indecidivel,
            "quarentenados_atingidos": self.quarentenados_atingidos,
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


def _ancora_indecidivel(override: TransactionOverride) -> bool:
    """Override ativo sem âncora v2 E sem snapshot — não dá para decidir, então bloqueia."""
    # Fail-closed deliberado: a polaridade de um gate que BLOQUEIA é sobre-detectar.
    # Over-match é adjudicável à mão em poucas rows; under-match é override órfão em
    # produção, que apaga categorização manual sem sinal.
    return override.natural_key_hash is None and _override_gate_digest(override) is None


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


def _build_report(db: Session, workspace_id: str, alvos: frozenset[str]) -> PreconditionReport:
    ativos = _ativos(db, workspace_id)
    indecidiveis = [o for o in ativos if _ancora_indecidivel(o)]
    casados = [o for o in ativos if _override_gate_digest(o) in alvos]
    return PreconditionReport(
        overrides_ativos=len(ativos),
        alvos_do_colapsador=len(alvos),
        hits=len({o.id for o in casados} | {o.id for o in indecidiveis}),
        hits_ancora_indecidivel=len(indecidiveis),
        quarentenados_atingidos=_quarentenados_atingidos(db, workspace_id, alvos),
    )


def evaluate(
    db: Session, workspace_id: str, collapse_candidates
) -> tuple[OpResult, PreconditionReport]:
    """Avalia a pré-condição. Read-only: não escreve, não commita, não muta override."""
    report = _build_report(db, workspace_id, _alvos(collapse_candidates))
    if report.liberado:
        return OpResult(ok=True, details=report.as_details()), report
    erro = (
        f"{report.hits} override(s) ativo(s) ancoram em row que o colapso removeria "
        "— enforce bloqueado (re-ancore ou quarentene antes de flipar a flag)"
    )
    return OpResult(ok=False, error=erro, details=report.as_details()), report

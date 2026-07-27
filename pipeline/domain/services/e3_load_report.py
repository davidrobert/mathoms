"""DTOs de carga do E3 + ledger de conservação de contagem por artefato (ADR-347).

Extraído de ``e3_reconciler_adapter`` (SRP + limite de 500 linhas): ``EmptyInstitutionWarning``
(warning de load), ``LoadOutcome`` (estado acumulado no load), ``LoadStat`` (fatos por
statement carregado) e a função pura ``build_artifact_ledger`` (partição de remoções
por artefato, count-balanced). Importa só módulos-folha — sem ciclo com o adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.domain.models.document import BankStatement
from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.statement_preprocessor import (
    AnachronicTransactionWarning,
    PeriodDerivationWarning,
)


@dataclass(frozen=True)
class EmptyInstitutionWarning:
    """Extrato E2 sem banco determinável — pulado para não gerar key E3 ``_...``."""

    source: str

    def format(self) -> str:
        return f"empty-institution src={self.source} skipped=1 (needs_review)"

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272) para ReviewReason — banco vazio é campo obrigatório ausente."""
        return ReviewReason(
            code=ReviewReasonCode.extract_missing_required_field,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value="banco=''",
            expected="campo banco/institution nao-vazio no artefato E2",
            message="extrato sem banco determinavel; documento requer revisao",
        )


@dataclass(frozen=True)
class LoadStat:
    """Fatos de carga de UM statement (ADR-347), keyed por ``source_document``.
    ``tx_carregadas`` = âncora pós-period-norm, PRÉ-anachronic/undated."""

    tx_carregadas: int
    anachronic: int
    undated: int
    tx_loaded: int


@dataclass(frozen=True)
class StatementExclusion:
    """Statement inteiro excluído no load (ADR-347), por canal. O tx count entra no
    ledger de conservação **run-level** (workspace), não num artefato E3 (não há)."""

    canal: str
    count: int


@dataclass
class LoadOutcome:
    """Estado interno acumulado durante ``_load_with_outcome``."""

    statements: list[BankStatement] = field(default_factory=list)
    period_warnings: list[PeriodDerivationWarning] = field(default_factory=list)
    anachronic_warnings: list[AnachronicTransactionWarning] = field(default_factory=list)
    institution_warnings: list[EmptyInstitutionWarning] = field(default_factory=list)
    review_reasons: list[ReviewReason] = field(default_factory=list)
    skipped: int = 0
    # ADR-347 PR1b — fatos de carga por source, base do ledger de conservação.
    load_stats: dict[str, LoadStat] = field(default_factory=dict)
    # ADR-347 PR2 — statements excluídos no load (tx count por canal), ledger run-level.
    exclusions: list[StatementExclusion] = field(default_factory=list)

    def exclude(self, canal: str, count: int) -> None:
        """Registra exclusão de statement inteiro: incrementa ``skipped`` + ledger."""
        self.skipped += 1
        self.exclusions.append(StatementExclusion(canal, count))


def _remocoes(
    undated: int, anachronic: int, intra: int, cross: int, cross_cents: int, intra_cents: int
) -> dict:
    """Partição de remoções por canal (ADR-347). ``valor_cents``: intra + cross
    serializados; undated/anachronic ficam 0 — captura de valor é a montante do
    adapter (perda real), diferida ao PR2b (measure-then-emit)."""
    return {
        "undated_drop": {"count": undated, "valor_cents": 0},
        "anachronic": {"count": anachronic, "valor_cents": 0},
        "intra_statement_dedup": {"count": intra, "valor_cents": intra_cents},
        "cross_file_dedup": {"count": cross, "valor_cents": cross_cents},
    }


def _intra_cents_by_source(removals) -> dict[str, int]:
    """Valor do dedup intra por ``source_document`` (ADR-347 §Dec-6), extraído dos
    ``DedupRemoval`` (duck-typed: ``.canal``/``.source``/``.valor_cents``)."""
    return {
        r.source: r.valor_cents
        for r in (removals or ())
        if getattr(r, "canal", None) == "intra_statement_dedup" and getattr(r, "source", None)
    }


def _ledger_totals(reconciled_stmts, load_stats, by_source: dict[str, int]):
    """(tx_carregadas, anachronic, undated, intra_count, intra_cents) somados por statement."""
    carregadas = anachronic = undated = intra = intra_cents = 0
    for s in reconciled_stmts:
        st = load_stats.get(s.source_document or "")
        if st is None:
            continue
        carregadas += st.tx_carregadas
        anachronic += st.anachronic
        undated += st.undated
        intra += st.tx_loaded - len(s.transactions)
        intra_cents += by_source.get(s.source_document or "", 0)
    return carregadas, anachronic, undated, intra, intra_cents


def build_artifact_ledger(
    reconciled_stmts: list[BankStatement],
    load_stats: dict[str, LoadStat],
    cross_removed: int,
    cross_cents: int,
    removals=None,
) -> dict:
    """Ledger de conservação por artefato E3 (ADR-347): ``tx_carregadas ==
    transacoes_total + Σ remocoes[*].count`` (tol-zero). ``removals`` traz o valor do
    dedup intra por ``source_document`` (§Dec-6); ausente ⇒ 0 (compat forward-only)."""
    by_source = _intra_cents_by_source(removals)
    carregadas, anachronic, undated, intra, intra_cents = _ledger_totals(
        reconciled_stmts, load_stats, by_source
    )
    remocoes = _remocoes(undated, anachronic, intra, cross_removed, cross_cents, intra_cents)
    return {"tx_carregadas": carregadas, "remocoes": remocoes}


def attach_artifact_ledger(
    payload: dict, reconciled_stmts, load_stats, cross_removed, cross_cents, removals
) -> None:
    """Anexa (in-place) o ledger de conservação E3 (ADR-347) ao ``payload``."""
    payload |= build_artifact_ledger(
        reconciled_stmts, load_stats, cross_removed, cross_cents, removals
    )

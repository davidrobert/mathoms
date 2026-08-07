"""Container de saída do E3 — ``ReconciliationStoreResult``.

Extraído de ``e3_reconciler_adapter`` porque o adapter chegou ao teto de 500
linhas do CLAUDE.md e cada ledger novo (ADR-347, ADR-350, ADR-354) acrescenta um
campo aqui. Mesma decisão de forma que o split de ``ledger_conservation`` na
[[A40.l1]]: o container é responsabilidade própria (o que o stage devolve), o
adapter é outra (como ele produz).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.domain.review_reason import ReviewReason
from pipeline.domain.services.baseline_validator import BaselineDiffWarning
from pipeline.domain.services.cross_document_collapse_types import CollapseMeasurement
from pipeline.domain.services.cross_document_collapser import CollapseCandidate
from pipeline.domain.services.e3_load_report import (
    EmptyInstitutionWarning,
    StatementExclusion,
)
from pipeline.domain.services.fatura_payment_cross_checker import FaturaCrossResult
from pipeline.domain.services.reconciliation_service import DedupRemoval
from pipeline.domain.services.reconciliation_validators import (
    FaturaExcludedFromSaldoChain,
    SaldoChainMemberInferred,
    SaldoGapWarning,
    TemporalGapWarning,
)
from pipeline.domain.services.statement_preprocessor import (
    AnachronicTransactionWarning,
    PeriodDerivationWarning,
)


@dataclass(frozen=True)
class ReconciliationStoreResult:
    """Saída enriquecida de :meth:`E3ReconcilerAdapter.reconcile_via_store`.

    Contagens espelham os campos do dict legado do retorno; warnings são
    dataclasses estruturadas (não strings) — serialização para o formato
    legado fica no shell que consome este resultado.
    """

    statements_loaded: int
    statements_reconciled: int
    artifacts_written: int
    skipped_inputs: int
    period_warnings: tuple[PeriodDerivationWarning, ...] = ()
    anachronic_warnings: tuple[AnachronicTransactionWarning, ...] = ()
    saldo_warnings: tuple[SaldoGapWarning, ...] = ()
    # ADR-310 — sinal de auditoria: statements classificados como fatura que
    # ficaram fora da cadeia de continuidade de saldo.
    saldo_exclusions: tuple[FaturaExcludedFromSaldoChain, ...] = ()
    # Emenda ADR-310 (2026-07-08) — statements sem número coalescidos na cadeia
    # numerada da mesma conta (Tier 2); número ausente jamais some em silêncio.
    inferred_chain_members: tuple[SaldoChainMemberInferred, ...] = ()
    temporal_warnings: tuple[TemporalGapWarning, ...] = ()
    baseline_warnings: tuple[BaselineDiffWarning, ...] = ()
    institution_warnings: tuple[EmptyInstitutionWarning, ...] = ()
    review_reasons: tuple[ReviewReason, ...] = ()
    # ADR-347 PR1 — remoções de dedup por canal (ledger de conservação de contagem).
    removals: tuple[DedupRemoval, ...] = ()
    # ADR-347 PR2 — statements excluídos no load (tx count por canal), ledger run-level.
    exclusions: tuple[StatementExclusion, ...] = ()
    fatura_cross_results: tuple[FaturaCrossResult, ...] = ()  # ADR-350 PR1 measure-only
    # ADR-354 §Emenda PR1 measure-only — candidatos a colapso cross-documento.
    collapse_candidates: tuple[CollapseCandidate, ...] = ()
    # ADR-364 — corpus PRÉ-poda para o gate de override; ver `CollapseMeasurement`.
    collapse_measurement: CollapseMeasurement = field(default_factory=CollapseMeasurement)

    def to_dict(self) -> dict[str, Any]:
        """Forma plana — útil para asserts em testes e logs estruturados."""
        return {
            "statements_loaded": self.statements_loaded,
            "statements_reconciled": self.statements_reconciled,
            "artifacts_written": self.artifacts_written,
            "skipped_inputs": self.skipped_inputs,
            "period_warnings": [w.format() for w in self.period_warnings],
            "anachronic_warnings": [w.format() for w in self.anachronic_warnings],
            "saldo_warnings": [w.format() for w in self.saldo_warnings],
            "saldo_exclusions": [w.format() for w in self.saldo_exclusions],
            "inferred_chain_members": [w.format() for w in self.inferred_chain_members],
            "temporal_warnings": [w.format() for w in self.temporal_warnings],
            "baseline_warnings": [w.format() for w in self.baseline_warnings],
            "institution_warnings": [w.format() for w in self.institution_warnings],
            "review_reasons": [r.to_dict() for r in self.review_reasons],
            "exclusions": [{"canal": e.canal, "count": e.count} for e in self.exclusions],
            "fatura_cross_results": [r.to_trace_dict() for r in self.fatura_cross_results],
            "collapse_candidates": [c.to_trace_dict() for c in self.collapse_candidates],
        }

    # Acesso dict-like para retro-compat com os testes existentes que fazem
    # ``result["artifacts_written"]``.
    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        return d[key]

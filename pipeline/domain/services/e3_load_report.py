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


def _remocoes(undated: int, anachronic: int, intra: int, cross: int, cross_cents: int) -> dict:
    """Partição de remoções por canal (``valor_cents`` só p/ cross em PR1b — resto PR2)."""
    return {
        "undated_drop": {"count": undated, "valor_cents": 0},
        "anachronic": {"count": anachronic, "valor_cents": 0},
        "intra_statement_dedup": {"count": intra, "valor_cents": 0},
        "cross_file_dedup": {"count": cross, "valor_cents": cross_cents},
    }


def build_artifact_ledger(
    reconciled_stmts: list[BankStatement],
    load_stats: dict[str, LoadStat],
    cross_removed: int,
    cross_cents: int,
) -> dict:
    """Ledger de conservação por artefato E3 (ADR-347): fecha ``tx_carregadas ==
    transacoes_total + Σ remocoes[*].count`` (tol-zero)."""
    carregadas = anachronic = undated = intra = 0
    for s in reconciled_stmts:
        st = load_stats.get(s.source_document or "")
        if st is None:
            continue
        carregadas += st.tx_carregadas
        anachronic += st.anachronic
        undated += st.undated
        intra += st.tx_loaded - len(s.transactions)
    remocoes = _remocoes(undated, anachronic, intra, cross_removed, cross_cents)
    return {"tx_carregadas": carregadas, "remocoes": remocoes}

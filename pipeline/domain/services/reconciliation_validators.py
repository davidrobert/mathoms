"""Validadores de continuidade e gap temporal (Fase 6 foundation · ADR-089).

Extrai ``validate_saldo_and_gaps()`` de ``scripts/reconcile_transactions.py:478`` em
dois serviços independentes, cada um com config própria (R9/ISP).

- ``SaldoContinuityValidator``: detecta descontinuidades entre
  ``closing_balance`` de um extrato e ``opening_balance`` do próximo, para a
  mesma conta. "Mesma conta" (ADR-310) deriva da ``AccountKey`` canônica do
  ``AccountGrouper`` (banco + tipo normalizado + moeda) + discriminadores
  ``member_key``/``account_number_norm`` (ADR-226). Statements de fatura
  ficam fora da cadeia — passivo rotativo não tem "saldo que continua";
  cada exclusão emite sinal tipado (``FaturaExcludedFromSaldoChain``).
- ``TemporalGapDetector``: detecta gaps (em dias) entre ``period_end`` de um
  extrato e ``period_start`` do próximo, para a mesma conta (mesma chave
  canônica; faturas formam cadeia própria).

Ambos operam sobre ``list[BankStatement]`` de domínio — nunca ``Path`` ou
``dict``. Conversão ``E2-dict → BankStatement`` acontece no call-site (ver
``BankStatement.from_e2_dict``).

Warnings são dataclasses frozen com dados estruturados — não strings.
Serialização para o formato legado (mensagens string em ``qa_log.md``)
fica no shell de reconciliação, não aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money
from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.account_grouper import AccountGrouper
from pipeline.domain.services.continuity_chain import (
    ChainPartition,  # noqa: F401 — re-export (retro-compat de import)
    ContinuityAccountKey,
    FaturaExcludedFromSaldoChain,
    SaldoChainMemberInferred,
    partition_chains,
)
from pipeline.domain.services.continuity_chain import (
    sort_key as _sort_key,
)

# =============================================================================
# Config dataclasses (R9 — cada service recebe seu value object de config)
# =============================================================================


@dataclass(frozen=True)
class SaldoContinuityConfig:
    """Tolerância para diferença entre ``closing_balance(n)`` e
    ``opening_balance(n+1)``. Default ``R$ 0,01`` (arredondamento).

    Fonte no legado: ``pipeline.json → reconciliation.tolerances.saldo_diff``.
    """

    tolerance_amount: Decimal = Decimal("0.01")

    @classmethod
    def from_pipeline_config(cls, pipeline: dict) -> "SaldoContinuityConfig":
        tol = (
            (pipeline or {})
            .get("reconciliation", {})
            .get("tolerances", {})
            .get("saldo_diff", "0.01")
        )
        return cls(tolerance_amount=Decimal(str(tol)))


@dataclass(frozen=True)
class TemporalGapConfig:
    """Gap máximo aceitável (em dias) entre o fim de um extrato e o início do
    próximo. Default 4 dias (fim-de-semana + feriado).

    Fonte no legado: ``pipeline.json → reconciliation.tolerances.temporal_gap_days``.
    """

    tolerance_gap_days: int = 4

    @classmethod
    def from_pipeline_config(cls, pipeline: dict) -> "TemporalGapConfig":
        days = (
            (pipeline or {})
            .get("reconciliation", {})
            .get("tolerances", {})
            .get("temporal_gap_days", 4)
        )
        return cls(tolerance_gap_days=int(days))


# =============================================================================
# Ordenação estável de warnings entre cadeias (determinismo ADR-111)
# =============================================================================


def _saldo_warning_sort_key(w: "SaldoGapWarning") -> tuple:
    """Ordem estável entre cadeias (determinismo ADR-111): a coalescência muda
    a ordem de iteração dos grupos, mas o conjunto+ordem de warnings não pode
    depender da ordem de inserção dos statements."""
    return (w.account_key.describe(), w.previous_source or "", w.next_source or "")


def _temporal_warning_sort_key(w: "TemporalGapWarning") -> tuple:
    return (w.account_key.describe(), w.previous_source or "", w.next_source or "")


# =============================================================================
# Warnings estruturados (dataclasses, não strings)
# =============================================================================


@dataclass(frozen=True)
class SaldoGapWarning:
    """Descontinuidade de saldo entre dois extratos consecutivos."""

    account_key: ContinuityAccountKey
    previous_source: str | None
    next_source: str | None
    previous_closing: Money
    next_opening: Money
    gap: Money  # valor absoluto da diferença

    def format(self) -> str:
        """Mensagem humana compatível com o formato do legado."""
        return (
            f"Saldo gap {self.account_key.describe()}: "
            f"prev={self.previous_source or '?'} closing={self.previous_closing.to_float():.2f}, "
            f"next={self.next_source or '?'} opening={self.next_opening.to_float():.2f}, "
            f"gap={self.gap.to_float():.2f}"
        )

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272/ADR-308) — informativo; ``offending_value`` nunca
        carrega o valor do gap (Money é sensível), só conta + documentos."""
        return ReviewReason(
            code=ReviewReasonCode.domain_balance_gap,
            stage=stage,
            artifact_key=self.next_source or artifact_key,
            document_id=document_id,
            offending_value=(
                f"descontinuidade de saldo em {self.account_key.describe()} "
                f"entre {self.previous_source or '?'} e {self.next_source or '?'}"
            ),
            expected="closing_balance(n) == opening_balance(n+1) na mesma conta",
            message="saldo nao continua entre extratos consecutivos; conferir documento",
        )


@dataclass(frozen=True)
class TemporalGapWarning:
    """Gap de dias entre ``period_end`` e o próximo ``period_start``."""

    account_key: ContinuityAccountKey
    previous_source: str | None
    next_source: str | None
    days_gap: int
    previous_end: str  # ISO date
    next_start: str  # ISO date

    def format(self) -> str:
        return (
            f"Temporal gap {self.account_key.describe()}: {self.days_gap} days "
            f"between {self.previous_source or '?'} (fim={self.previous_end}) and "
            f"{self.next_source or '?'} (inicio={self.next_start})"
        )

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272/ADR-308) — informativo, não bloqueia o run."""
        return ReviewReason(
            code=ReviewReasonCode.domain_temporal_gap,
            stage=stage,
            artifact_key=self.next_source or artifact_key,
            document_id=document_id,
            offending_value=(
                f"{self.days_gap} dias sem extrato em {self.account_key.describe()} "
                f"({self.previous_end} → {self.next_start})"
            ),
            expected="serie de extratos contigua por conta",
            message="periodo sem extrato entre documentos consecutivos; possivel documento faltando",
        )


# =============================================================================
# SaldoContinuityValidator
# =============================================================================


@dataclass(frozen=True)
class SaldoContinuityResult:
    """Warnings + sinal de exclusão de faturas + sinal de coalescência (ADR-310)."""

    warnings: tuple[SaldoGapWarning, ...]
    excluded_faturas: tuple[FaturaExcludedFromSaldoChain, ...]
    inferred_members: tuple[SaldoChainMemberInferred, ...] = ()


class SaldoContinuityValidator:
    """Valida continuidade de saldos entre extratos consecutivos da mesma conta.

    Função pura — recebe ``list[BankStatement]``, retorna
    ``list[SaldoGapWarning]``. Ordena internamente por
    ``(period_start, period_end, source_document)`` dentro de cada conta
    (ADR-310), portanto a ordem de entrada é irrelevante.

    Statements de fatura ficam fora da cadeia (passivo rotativo não tem
    "saldo que continua"; ``saldo_inicial/final`` de fatura =
    ``saldo_anterior/atual``) — cada exclusão vira
    ``FaturaExcludedFromSaldoChain`` em :meth:`validate_with_exclusions`.

    Contas com apenas um extrato (ou saldo faltando em alguma das pontas)
    nunca geram warning.
    """

    def __init__(
        self,
        config: SaldoContinuityConfig | None = None,
        *,
        grouper: AccountGrouper | None = None,
    ):
        self._config = config or SaldoContinuityConfig()
        self._grouper = grouper or AccountGrouper()

    def validate(self, statements: Iterable[BankStatement]) -> list[SaldoGapWarning]:
        return list(self.validate_with_exclusions(statements).warnings)

    def validate_with_exclusions(
        self, statements: Iterable[BankStatement]
    ) -> SaldoContinuityResult:
        partition = partition_chains(self._grouper, statements, exclude_faturas=True)
        warnings: list[SaldoGapWarning] = []
        for key, group in partition.chains.items():
            warnings.extend(self._validate_group(key, sorted(group, key=_sort_key)))
        warnings.sort(key=_saldo_warning_sort_key)
        return SaldoContinuityResult(
            tuple(warnings), partition.excluded_faturas, partition.inferred_members
        )

    def _validate_group(
        self, key: ContinuityAccountKey, group: list[BankStatement]
    ) -> list[SaldoGapWarning]:
        out: list[SaldoGapWarning] = []
        for prev, curr in zip(group, group[1:]):
            if prev.closing_balance is None or curr.opening_balance is None:
                continue
            # Currencies must match — grouping já garante, mas guard.
            if prev.closing_balance.currency != curr.opening_balance.currency:
                continue
            diff = prev.closing_balance - curr.opening_balance
            # Abs em Money: usa Decimal para não voltar para float.
            abs_diff_amount = abs(diff.amount)
            if abs_diff_amount > self._config.tolerance_amount:
                out.append(
                    SaldoGapWarning(
                        account_key=key,
                        previous_source=prev.source_document,
                        next_source=curr.source_document,
                        previous_closing=prev.closing_balance,
                        next_opening=curr.opening_balance,
                        gap=Money(abs_diff_amount, prev.closing_balance.currency),
                    )
                )
        return out


# =============================================================================
# TemporalGapDetector
# =============================================================================


@dataclass(frozen=True)
class TemporalGapResult:
    """Warnings + sinal de coalescência de cadeia (emenda ADR-310)."""

    warnings: tuple[TemporalGapWarning, ...]
    inferred_members: tuple[SaldoChainMemberInferred, ...] = ()


class TemporalGapDetector:
    """Detecta gaps temporais entre períodos de extratos consecutivos.

    Função pura — mesma interface de ``SaldoContinuityValidator``. Ordena
    internamente por ``(period_start, period_end, source_document)``
    (ADR-310). Faturas permanecem na detecção — gap temporal numa série de
    faturas sinaliza fatura faltando — mas em cadeia própria, separada das
    contas do mesmo banco pela chave canônica.

    Overlaps (próximo ``period_start`` anterior ao ``period_end`` atual)
    geram ``days_gap`` negativo, que não é warning — passa batido.
    """

    def __init__(
        self,
        config: TemporalGapConfig | None = None,
        *,
        grouper: AccountGrouper | None = None,
    ):
        self._config = config or TemporalGapConfig()
        self._grouper = grouper or AccountGrouper()

    def detect(self, statements: Iterable[BankStatement]) -> list[TemporalGapWarning]:
        return list(self.detect_with_inferences(statements).warnings)

    def detect_with_inferences(self, statements: Iterable[BankStatement]) -> TemporalGapResult:
        partition = partition_chains(self._grouper, statements, exclude_faturas=False)
        warnings: list[TemporalGapWarning] = []
        for key, group in partition.chains.items():
            warnings.extend(self._detect_group(key, sorted(group, key=_sort_key)))
        warnings.sort(key=_temporal_warning_sort_key)
        return TemporalGapResult(tuple(warnings), partition.inferred_members)

    def _detect_group(
        self, key: ContinuityAccountKey, group: list[BankStatement]
    ) -> list[TemporalGapWarning]:
        out: list[TemporalGapWarning] = []
        for prev, curr in zip(group, group[1:]):
            days = (curr.period_start - prev.period_end).days
            if days > self._config.tolerance_gap_days:
                out.append(
                    TemporalGapWarning(
                        account_key=key,
                        previous_source=prev.source_document,
                        next_source=curr.source_document,
                        days_gap=days,
                        previous_end=prev.period_end.isoformat(),
                        next_start=curr.period_start.isoformat(),
                    )
                )
        return out

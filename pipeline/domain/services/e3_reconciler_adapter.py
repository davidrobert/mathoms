"""E3 reconciler adapter (Fase 6 foundation — Caminho B gradual).

Ponte entre o ``ArtifactStore`` e os domain services de reconciliação. Cobre o
caminho feliz (extratos simples por conta) **e** integra os pre-processadores e
validadores extraídos de ``scripts/e3_reconcile.py`` na Sessão A1:

- :class:`StatementPeriodNormalizer` (faturas sem período)
- :class:`AnachronicTransactionDropper` (>180d antes de ``periodo.inicio``)
- :class:`AccountGrouper` (skip + chave de conta com equivalences)
- :class:`SaldoContinuityValidator` (descontinuidade de saldo)
- :class:`TemporalGapDetector` (gap entre períodos)
- :class:`BaselineValidator` (saldos vs IRPF)
- :class:`BankCanonicalizer` (output filename estável, comparação sem
  falsos positivos de substring)

Lógica residual (``reconciliation.md`` summary, ``qa_log.md`` rewriting,
``cleanup_e3_directory``) vive em ``scripts/e3_reconcile.main_with_store``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from pipeline.artifact_store import ArtifactStore, stage_suffix
from pipeline.domain.models.bank import BankCanonicalizer
from pipeline.domain.models.document import BankStatement
from pipeline.domain.services.account_grouper import AccountGrouper
from pipeline.domain.services.baseline_validator import (
    BaselineAccountSaldo,
    BaselineDiffWarning,
    BaselineValidator,
)
from pipeline.domain.services.reconciliation_service import (
    ReconciliationConfig,
    ReconciliationService,
)
from pipeline.domain.services.reconciliation_validators import (
    SaldoContinuityValidator,
    SaldoGapWarning,
    TemporalGapDetector,
    TemporalGapWarning,
)
from pipeline.domain.services.statement_preprocessor import (
    AnachronicTransactionDropper,
    AnachronicTransactionWarning,
    PeriodDerivationWarning,
    StatementPeriodNormalizer,
)

# =============================================================================
# Result container
# =============================================================================


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
    temporal_warnings: tuple[TemporalGapWarning, ...] = ()
    baseline_warnings: tuple[BaselineDiffWarning, ...] = ()

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
            "temporal_warnings": [w.format() for w in self.temporal_warnings],
            "baseline_warnings": [w.format() for w in self.baseline_warnings],
        }

    # Acesso dict-like para retro-compat com os testes existentes que fazem
    # ``result["artifacts_written"]``.
    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        return d[key]


@dataclass
class _LoadOutcome:
    """Estado interno acumulado durante ``load_bank_statements``."""

    statements: list[BankStatement] = field(default_factory=list)
    period_warnings: list[PeriodDerivationWarning] = field(default_factory=list)
    anachronic_warnings: list[AnachronicTransactionWarning] = field(default_factory=list)
    skipped: int = 0


# =============================================================================
# Adapter
# =============================================================================


class E3ReconcilerAdapter:
    """Adaptador ``ArtifactStore`` → domain services → ``ArtifactStore``.

    Foundation do Caminho B para E3 (Fase 6). Cada dependência é injetável e
    tem default seguro — testes podem instanciar o adapter sem nenhum arg
    além de ``ReconciliationConfig`` e o adapter rodará sem
    pre-processamento/validação de baseline.

    Ordem de operações por extrato em ``load_bank_statements``:

        1. ``account_grouper.should_skip`` (descarta IRPF, investimentos, etc).
        2. ``period_normalizer.normalize`` (sintetiza ``periodo`` para faturas).
        3. ``anachronic_dropper.filter`` (remove tx >180d antes do início).
        4. ``BankStatement.from_e2_dict`` (conversão final).
    """

    INPUT_STAGES = ("E2-extratos", "E2-faturas", "E2-llm")
    BASELINE_STAGE = "E1.5c"
    BASELINE_KEY = "baseline_patrimonial"

    def __init__(
        self,
        config: ReconciliationConfig,
        *,
        canonicalizer: BankCanonicalizer | None = None,
        grouper: AccountGrouper | None = None,
        period_normalizer: StatementPeriodNormalizer | None = None,
        anachronic_dropper: AnachronicTransactionDropper | None = None,
        saldo_validator: SaldoContinuityValidator | None = None,
        temporal_detector: TemporalGapDetector | None = None,
        baseline_validator: BaselineValidator | None = None,
    ) -> None:
        self._config = config
        self._service = ReconciliationService(config)
        self._canonicalizer = canonicalizer or BankCanonicalizer.empty()
        self._grouper = grouper or AccountGrouper()
        self._period_normalizer = period_normalizer or StatementPeriodNormalizer()
        self._anachronic_dropper = anachronic_dropper or AnachronicTransactionDropper()
        self._saldo_validator = saldo_validator
        self._temporal_detector = temporal_detector
        self._baseline_validator = baseline_validator

    # -- Loading --

    def load_bank_statements(
        self, store: ArtifactStore, *, input_stages: Iterable[str] | None = None
    ) -> list[BankStatement]:
        """Lê E2 artifacts do ``store`` e converte para ``BankStatement``.

        Mantém a assinatura original (lista de statements). Para obter os
        warnings coletados durante o load, use
        :meth:`load_bank_statements_with_warnings`.
        """
        return self._load_with_outcome(store, input_stages).statements

    def load_bank_statements_with_warnings(
        self, store: ArtifactStore, *, input_stages: Iterable[str] | None = None
    ) -> tuple[
        list[BankStatement],
        list[PeriodDerivationWarning],
        list[AnachronicTransactionWarning],
        int,
    ]:
        """Versão estendida — retorna também warnings e contagem de skips."""
        outcome = self._load_with_outcome(store, input_stages)
        return (
            outcome.statements,
            outcome.period_warnings,
            outcome.anachronic_warnings,
            outcome.skipped,
        )

    def _load_with_outcome(
        self, store: ArtifactStore, input_stages: Iterable[str] | None
    ) -> _LoadOutcome:
        stages = tuple(input_stages) if input_stages else self.INPUT_STAGES
        outcome = _LoadOutcome()

        # Dedup por key: ``DiskArtifactStore`` mapeia E2-extratos / E2-faturas
        # / E2-llm para o mesmo diretório (`E2_extracts/`), então ``list_keys``
        # retorna as mesmas keys em todos os 3 stages. Sem dedup, o mesmo
        # arquivo seria carregado várias vezes. Para ``InMemoryArtifactStore``,
        # keys são por (stage, key) e não há overlap natural — o set
        # apenas evita duplicatas óbvias.
        seen_keys: set[str] = set()
        for stage in stages:
            for key in store.list_keys(stage):
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                data = store.read(stage, key)
                if not data:
                    continue
                if data.get("requires_llm_fallback"):
                    outcome.skipped += 1
                    continue

                # Skip de tipos não-reconciliáveis (IRPF, posições, etc.)
                if self._grouper.should_skip(data):
                    outcome.skipped += 1
                    continue

                # Normaliza/sintetiza periodo (faturas, strings YYYYMM, etc.)
                norm_result = self._period_normalizer.normalize(data, source_name=key)
                outcome.period_warnings.extend(norm_result.warnings)
                if norm_result.skip:
                    outcome.skipped += 1
                    continue
                normalized = norm_result.data

                # Drop anachronic transactions antes da conversão.
                anach_result = self._anachronic_dropper.filter(normalized, source_name=key)
                if anach_result.warning is not None:
                    outcome.anachronic_warnings.append(anach_result.warning)
                normalized = anach_result.data

                # Conversão final → BankStatement. Garante ``source_document``
                # populado com o filename legado (``key`` + sufixo do stage),
                # essencial para preservar `fontes` no formato compatível com
                # o output E3 legado através do merge cross-file.
                try:
                    stmt = BankStatement.from_e2_dict(normalized)
                except Exception:
                    outcome.skipped += 1
                    continue
                if not stmt.source_document:
                    try:
                        stmt.source_document = key + stage_suffix(stage)
                    except KeyError:
                        stmt.source_document = key
                outcome.statements.append(stmt)

        return outcome

    # -- Baseline --

    def load_baseline_accounts(self, store: ArtifactStore) -> list[BaselineAccountSaldo]:
        """Lê o baseline (E1.5c) do store e extrai contas para validação.

        Retorna lista vazia se baseline não está no store.
        """
        baseline = store.read(self.BASELINE_STAGE, self.BASELINE_KEY)
        if not baseline:
            return []
        return BaselineAccountSaldo.from_baseline_dict(baseline)

    # -- Reconciliation --

    def reconcile(self, statements: list[BankStatement]) -> list[BankStatement]:
        """Aplica ``ReconciliationService.reconcile`` — função pura."""
        return self._service.reconcile(statements)

    def group_key(self, stmt: BankStatement) -> tuple[str, str | None, str]:
        """Chave canônica de agregação: (instituição canônica, membro, moeda)."""
        return (
            self._canonicalizer.canonicalize(stmt.institution),
            stmt.member_key,
            stmt.currency.upper(),
        )

    def output_key(self, stmt: BankStatement) -> str:
        """Chave de artifact para o output E3.

        Formato: ``{banco_canonico}_{moeda}_{YYYYMM}_{YYYYMM}``.
        Usa ``BankCanonicalizer`` quando configurado, caindo na forma
        normalizada (lowercase + sem espaços/acentos) caso contrário.
        """
        canon = self._canonicalizer.canonicalize(stmt.institution)
        inicio = stmt.period_start.strftime("%Y%m")
        fim = stmt.period_end.strftime("%Y%m")
        return f"{canon}_{stmt.currency.upper()}_{inicio}_{fim}"

    def reconcile_via_store(
        self,
        store: ArtifactStore,
        *,
        output_stage: str = "E3",
        input_stages: Iterable[str] | None = None,
        output_key_fn=None,
        serialize_fn=None,
        pipeline_run_id: str | None = None,
    ) -> ReconciliationStoreResult:
        """Pipeline end-to-end: read → preprocess → reconcile → validate → write.

        Args:
            store: ``ArtifactStore`` para ler E2 e escrever E3.
            output_stage: stage de destino (default ``"E3"``).
            input_stages: stages de origem (default ``INPUT_STAGES``).
            output_key_fn: opcional ``(stmt: BankStatement) -> str`` —
                substitui ``self.output_key`` (default produz
                ``{banco_canon}_{moeda}_{YYYYMM}_{YYYYMM}``). Use
                ``generate_legacy_artifact_key`` para incluir ``tipo_conta``.
            serialize_fn: opcional ``(stmt, sources, dup_count) -> dict`` —
                substitui ``stmt.to_e2_dict()`` (default). Use
                ``serialize_to_e3_legacy_format`` para output aderente a
                ``e3_reconciled.schema.json``.

        Retorna :class:`ReconciliationStoreResult` (frozen dataclass com
        suporte a acesso ``result["chave"]`` para retro-compat).
        """
        outcome = self._load_with_outcome(store, input_stages)
        statements = outcome.statements
        reconciled = self.reconcile(statements)

        key_for = output_key_fn or self.output_key

        # Agrupa pelo output_key — vários statements com mesma conta+período
        # produzem um único artefato (merge). Preserva sources via
        # ``stmt.source_document``.
        grouped: dict[str, list[BankStatement]] = defaultdict(list)
        for stmt in reconciled:
            grouped[key_for(stmt)].append(stmt)

        from pipeline.live_progress import emit_item_progress

        written = 0
        merged_statements: list[BankStatement] = []
        items_total = len(grouped)
        for idx, (key, stmts) in enumerate(grouped.items()):
            emit_item_progress(
                pipeline_run_id,
                output_stage,
                current_item=key,
                items_done=idx,
                items_total=items_total,
                phase="preparing",
            )
            sources = [s.source_document for s in stmts if s.source_document]
            if len(stmts) == 1:
                merged_stmt = stmts[0]
                dup_removed = 0
            else:
                # Merge: concatena transactions, mantém metadados do primeiro.
                # Re-reconcilia as transações juntas para pegar duplicatas
                # cross-file dentro da mesma conta.
                base = stmts[0]
                all_tx = []
                for s in stmts:
                    all_tx.extend(s.transactions)
                before = len(all_tx)
                all_tx = self._service._dedup(all_tx)
                dup_removed = before - len(all_tx)
                merged_stmt = BankStatement(
                    institution=base.institution,
                    member_key=base.member_key,
                    period_start=min(s.period_start for s in stmts),
                    period_end=max(s.period_end for s in stmts),
                    currency=base.currency,
                    transactions=all_tx,
                    opening_balance=stmts[0].opening_balance,
                    closing_balance=stmts[-1].closing_balance,
                    source_document=None,
                    notes=[f"merged from {len(stmts)} source statements"],
                    account_type=base.account_type,
                )

            if serialize_fn is not None:
                payload = serialize_fn(merged_stmt, sources, dup_removed)
            else:
                payload = merged_stmt.to_e2_dict()
                if len(stmts) > 1:
                    payload["pipeline_stage"] = "E3"
            merged_statements.append(merged_stmt)
            emit_item_progress(
                pipeline_run_id,
                output_stage,
                current_item=key,
                items_done=idx,
                items_total=items_total,
                phase="persisting",
            )
            store.write(output_stage, key, payload)
            written += 1

        if items_total > 0:
            emit_item_progress(
                pipeline_run_id,
                output_stage,
                current_item=None,
                items_done=items_total,
                items_total=items_total,
                phase="finalizing",
            )

        # Validações — sempre rodam sobre os statements originais (pré-merge)
        # para preservar fidelidade temporal entre arquivos.
        saldo_warnings: tuple[SaldoGapWarning, ...] = ()
        if self._saldo_validator is not None:
            saldo_warnings = tuple(self._saldo_validator.validate(statements))

        temporal_warnings: tuple[TemporalGapWarning, ...] = ()
        if self._temporal_detector is not None:
            temporal_warnings = tuple(self._temporal_detector.detect(statements))

        baseline_warnings: tuple[BaselineDiffWarning, ...] = ()
        if self._baseline_validator is not None:
            baseline_accounts = self.load_baseline_accounts(store)
            if baseline_accounts:
                baseline_warnings = tuple(
                    self._baseline_validator.validate(merged_statements, baseline_accounts)
                )

        return ReconciliationStoreResult(
            statements_loaded=len(statements),
            statements_reconciled=len(reconciled),
            artifacts_written=written,
            skipped_inputs=outcome.skipped,
            period_warnings=tuple(outcome.period_warnings),
            anachronic_warnings=tuple(outcome.anachronic_warnings),
            saldo_warnings=saldo_warnings,
            temporal_warnings=temporal_warnings,
            baseline_warnings=baseline_warnings,
        )

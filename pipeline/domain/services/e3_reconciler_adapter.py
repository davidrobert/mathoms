"""E3 reconciler adapter (Fase 6 foundation — Caminho B gradual).

Ponte entre o ``ArtifactStore`` e os domain services de reconciliação. Cobre o
caminho feliz (extratos simples por conta) **e** integra os pre-processadores e
validadores extraídos de ``scripts/reconcile_transactions.py`` na Sessão A1:

- :class:`StatementPeriodNormalizer` (faturas sem período)
- :class:`AnachronicTransactionDropper` (>180d antes de ``periodo.inicio``)
- :class:`AccountGrouper` (skip + chave de conta com equivalences)
- :class:`SaldoContinuityValidator` (descontinuidade de saldo)
- :class:`TemporalGapDetector` (gap entre períodos)
- :class:`BaselineValidator` (saldos vs IRPF)
- :class:`BankCanonicalizer` (output filename estável, comparação sem
  falsos positivos de substring)

Lógica residual (``reconciliation.md`` summary, ``qa_log.md`` rewriting,
``cleanup_e3_directory``) vive em ``scripts/reconcile_transactions.main_with_store``.

``ReconciliationStoreResult`` mora em ``e3_reconciliation_result`` e é
re-exportado aqui — o import histórico deste módulo segue válido.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from pipeline.artifact_store import ArtifactStore, stage_suffix
from pipeline.domain.models.bank import BankCanonicalizer
from pipeline.domain.models.document import BankStatement
from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.account_grouper import AccountGrouper
from pipeline.domain.services.baseline_validator import (
    BaselineAccountSaldo,
    BaselineDiffWarning,
    BaselineValidator,
)
from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser
from pipeline.domain.services.e3_load_report import (
    EmptyInstitutionWarning,
    LoadOutcome,
    LoadStat,
    StatementExclusion,
    attach_artifact_ledger,
)
from pipeline.domain.services.e3_reconciliation_result import ReconciliationStoreResult
from pipeline.domain.services.e3_review_reasons import (
    project_e3_reasons as _project_reasons,
)
from pipeline.domain.services.e3_review_reasons import (
    store_document_id as _document_id_for,
)
from pipeline.domain.services.e3_statement_merge import merge_group_statements
from pipeline.domain.services.fatura_payment_cross_checker import (
    FaturaCrossResult,
    FaturaPaymentCrossChecker,
    attach_cross_checksum,
    index_by_key,
)
from pipeline.domain.services.reconciliation_service import (
    DedupRemoval,
    ReconciliationConfig,
    ReconciliationService,
)
from pipeline.domain.services.reconciliation_validators import (
    FaturaExcludedFromSaldoChain,
    SaldoChainMemberInferred,
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

    INPUT_STAGES = ("extract_statements", "extract_invoices", "extract_with_llm")
    BASELINE_STAGE = "consolidate_baseline"
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
        fatura_cross_checker: FaturaPaymentCrossChecker | None = None,
        cross_document_collapser: CrossDocumentCollapser | None = None,
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
        self._fatura_cross_checker = fatura_cross_checker
        self._cross_document_collapser = cross_document_collapser

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
    ) -> LoadOutcome:
        stages = tuple(input_stages) if input_stages else self.INPUT_STAGES
        outcome = LoadOutcome()

        # Dedup por key: os 3 INPUT_STAGES podem expor a mesma key; sem o set,
        # o mesmo artefato seria carregado várias vezes.
        seen_keys: set[str] = set()
        for stage in stages:
            for key in store.list_keys(stage):
                if key in seen_keys:
                    continue
                data = store.read(stage, key)
                if not data:
                    continue
                if data.get("requires_llm_fallback"):
                    # ADR-342: stub de escalação NÃO reivindica a key — senão o
                    # stub em extract_statements bloquearia o artefato full do
                    # extract_with_llm no dedup por prioridade de stage.
                    outcome.exclude("llm_stub", len(data.get("transacoes") or []))
                    continue
                seen_keys.add(key)

                # Skip de tipos não-reconciliáveis (IRPF, posições, etc.)
                if self._grouper.should_skip(data):
                    outcome.exclude("non_tx_type", len(data.get("transacoes") or []))
                    continue

                # Normaliza/sintetiza periodo (faturas, strings YYYYMM, etc.)
                doc_id = _document_id_for(store, stage, key)
                norm_result = self._period_normalizer.normalize(data, source_name=key)
                outcome.period_warnings.extend(norm_result.warnings)
                outcome.review_reasons.extend(_project_reasons(norm_result.warnings, key, doc_id))
                if norm_result.skip:
                    outcome.exclude("period_skip", len(data.get("transacoes") or []))
                    continue
                normalized = norm_result.data
                # ADR-347 PR1b — âncora de contagem: pós-period-norm, PRÉ-anachronic/undated.
                raw_count = len(normalized.get("transacoes") or [])

                # Drop anachronic transactions antes da conversão.
                anach_result = self._anachronic_dropper.filter(normalized, source_name=key)
                if anach_result.warning is not None:
                    outcome.anachronic_warnings.append(anach_result.warning)
                    outcome.review_reasons.extend(
                        _project_reasons([anach_result.warning], key, doc_id)
                    )
                normalized = anach_result.data

                # Conversão final → BankStatement. Garante ``source_document``
                # populado com o filename legado (``key`` + sufixo do stage),
                # essencial para preservar `fontes` no formato compatível com
                # o output E3 legado através do merge cross-file.
                try:
                    stmt = BankStatement.from_e2_dict(normalized)
                except Exception:
                    outcome.exclude("parse_error", len(normalized.get("transacoes") or []))
                    continue
                # A28.l8: banco vazio nunca vira key E3 "_extrato_..." silenciosa.
                if not (stmt.institution or "").strip():
                    warning = EmptyInstitutionWarning(source=key)
                    outcome.institution_warnings.append(warning)
                    outcome.review_reasons.extend(_project_reasons([warning], key, doc_id))
                    outcome.exclude("empty_institution", len(stmt.transactions))
                    continue
                if not stmt.source_document:
                    try:
                        stmt.source_document = key + stage_suffix(stage)
                    except KeyError:
                        stmt.source_document = key
                # ADR-347 PR1b — fatos de carga (ledger de conservação por artefato).
                anach_n = anach_result.warning.dropped_count if anach_result.warning else 0
                tx_loaded = len(stmt.transactions)
                outcome.load_stats[stmt.source_document] = LoadStat(
                    tx_carregadas=raw_count,
                    anachronic=anach_n,
                    undated=raw_count - anach_n - tx_loaded,
                    tx_loaded=tx_loaded,
                )
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
        output_stage: str = "reconcile_transactions",
        input_stages: Iterable[str] | None = None,
        output_key_fn=None,
        serialize_fn=None,
        pipeline_run_id: str | None = None,
    ) -> ReconciliationStoreResult:
        """Pipeline end-to-end: read → preprocess → reconcile → validate → write.
        ``output_key_fn``/``serialize_fn`` opcionais trocam key/payload pelo
        formato legado (ver ``generate_legacy_artifact_key`` /
        ``serialize_to_e3_legacy_format``). Retorna :class:`ReconciliationStoreResult`."""
        outcome = self._load_with_outcome(store, input_stages)
        statements = outcome.statements
        reconciled, removals = self._service.reconcile_with_report(statements)
        # ADR-350 PR1 measure-only — cross-check fatura↔pagamento (pré-merge, NÃO escala).
        fatura_cross = (
            self._fatura_cross_checker.check(statements) if self._fatura_cross_checker else ()
        )
        cross_by_key = index_by_key(fatura_cross)
        # ADR-354 §Emenda — mede pré-agrupamento: a chave de artefato carrega período
        # e `tipo_conta`, então as duas pernas do mesmo evento nunca se encontram
        # depois daqui. Measure-only: não remove row (enforce + re-ancoragem são PRs
        # próprios; remover row órfãna override ancorado no hash dela).
        collapse_candidates = (
            self._cross_document_collapser.measure(reconciled)
            if self._cross_document_collapser
            else ()
        )

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
                dup_removed = cents = 0
            else:
                # Merge: concatena transactions, mantém metadados do primeiro.
                # Re-reconcilia as transações juntas para pegar duplicatas
                # cross-file dentro da mesma conta.
                all_tx = []
                for s in stmts:
                    all_tx.extend(s.transactions)
                all_tx, dup_removed, cents, cross = self._service.dedup_report(all_tx)
                if dup_removed:
                    removals.append(DedupRemoval("cross_file_dedup", dup_removed, cents, cross))
                merged_stmt = merge_group_statements(stmts, all_tx)

            if serialize_fn is not None:
                payload = serialize_fn(merged_stmt, sources, dup_removed)
            else:
                payload = merged_stmt.to_e2_dict()
                if len(stmts) > 1:
                    payload["pipeline_stage"] = "E3"
            # ADR-347 PR1b — anexa o ledger de conservação (serializer-agnóstico).
            attach_artifact_ledger(payload, stmts, outcome.load_stats, dup_removed, cents, removals)
            attach_cross_checksum(payload, merged_stmt, cross_by_key)
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

        # Validações — sempre sobre os statements originais (pré-merge) para
        # preservar fidelidade temporal entre arquivos.
        saldo_warnings: tuple[SaldoGapWarning, ...] = ()
        saldo_exclusions: tuple[FaturaExcludedFromSaldoChain, ...] = ()
        inferred_members: tuple[SaldoChainMemberInferred, ...] = ()
        if self._saldo_validator is not None:
            saldo = self._saldo_validator.validate_with_exclusions(statements)
            saldo_warnings, saldo_exclusions, inferred_members = (
                saldo.warnings,
                saldo.excluded_faturas,
                saldo.inferred_members,
            )

        temporal_warnings: tuple[TemporalGapWarning, ...] = ()
        if self._temporal_detector is not None:
            # Coalescência (emenda ADR-310) só ocorre em non-fatura; ambos
            # validators emitem o mesmo sinal — saldo tem precedência, temporal
            # cobre quando o saldo não foi injetado.
            temporal = self._temporal_detector.detect_with_inferences(statements)
            temporal_warnings = temporal.warnings
            inferred_members = inferred_members or temporal.inferred_members

        baseline_warnings: tuple[BaselineDiffWarning, ...] = ()
        if self._baseline_validator is not None:
            accounts = self.load_baseline_accounts(store)
            if accounts:
                baseline_warnings = tuple(
                    self._baseline_validator.validate(merged_statements, accounts)
                )

        # ADR-308/A29.l2: warnings de reconciliação também projetam ReviewReason
        # (informativos — BLOCKING_CODES decide o gate de needs_review).
        cross_doc_reasons: list[ReviewReason] = []
        for warning_group in (saldo_warnings, temporal_warnings, baseline_warnings):
            cross_doc_reasons.extend(_project_reasons(warning_group, artifact_key=""))

        return ReconciliationStoreResult(
            statements_loaded=len(statements),
            statements_reconciled=len(reconciled),
            artifacts_written=written,
            skipped_inputs=outcome.skipped,
            period_warnings=tuple(outcome.period_warnings),
            anachronic_warnings=tuple(outcome.anachronic_warnings),
            saldo_warnings=saldo_warnings,
            saldo_exclusions=saldo_exclusions,
            inferred_chain_members=inferred_members,
            temporal_warnings=temporal_warnings,
            baseline_warnings=baseline_warnings,
            institution_warnings=tuple(outcome.institution_warnings),
            review_reasons=tuple(outcome.review_reasons) + tuple(cross_doc_reasons),
            removals=tuple(removals),
            exclusions=tuple(outcome.exclusions),
            fatura_cross_results=fatura_cross,
            collapse_candidates=collapse_candidates,
        )

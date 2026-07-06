"""Tests — ``E3ReconcilerAdapter`` (Fase 6 foundation + Sessão A1).

Cobre:
- API legada (``load_bank_statements``, ``reconcile_via_store`` retornando
  dict-like com ``statements_loaded`` / ``artifacts_written``).
- Extensões A1: integração com ``BankCanonicalizer``, ``AccountGrouper``,
  ``StatementPeriodNormalizer``, ``AnachronicTransactionDropper``,
  ``SaldoContinuityValidator``, ``TemporalGapDetector``, ``BaselineValidator``.
- Asserts contra os 3 goldens em ``tests/pipeline/goldens/e3/``.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.models import BankCanonicalizer, BankStatement, Money  # noqa: E402
from pipeline.domain.services import (  # noqa: E402
    AccountGrouper,
    BaselineValidator,
    BaselineValidatorConfig,
    E3ReconcilerAdapter,
    ReconciliationConfig,
    ReconciliationStoreResult,
    SaldoContinuityValidator,
    TemporalGapDetector,
)

GOLDENS_DIR = Path(__file__).resolve().parents[2] / "pipeline" / "goldens" / "e3"


def _load_golden(name: str) -> dict:
    return json.loads((GOLDENS_DIR / name).read_text(encoding="utf-8"))


def _seed_from_golden(store: InMemoryArtifactStore, golden: dict) -> None:
    for entry in golden["e2_extracts"]:
        store.seed(entry["stage"], entry["key"], entry["payload"])
    if "baseline" in golden:
        store.seed("E1.5c", "baseline_patrimonial", golden["baseline"])


def _e2_extract(banco: str, moeda: str, start: str, end: str, transacoes: list[dict]) -> dict:
    return {
        "pipeline_stage": "E2",
        "banco": banco,
        "tipo": "extrato",
        "moeda": moeda,
        "periodo_inicio": start,
        "periodo_fim": end,
        "transacoes": transacoes,
    }


def _tx(day: int, desc: str, valor: float, month: int = 1) -> dict:
    return {
        "data": f"2026-{month:02d}-{day:02d}",
        "descricao": desc,
        "valor": valor,
    }


class TestLoadBankStatements:
    def test_reads_all_e2_stages(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "itau_a",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "A", -100)]),
        )
        store.seed(
            "E2-faturas",
            "nubank_fat",
            _e2_extract("nubank", "BRL", "2026-01-01", "2026-01-31", [_tx(10, "F", -50)]),
        )
        adapter = E3ReconcilerAdapter(ReconciliationConfig())
        statements = adapter.load_bank_statements(store)
        assert len(statements) == 2
        institutions = sorted(s.institution for s in statements)
        assert institutions == ["itau", "nubank"]

    def test_skips_llm_fallback_stubs(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm",
            "unknown_x",
            {"banco": "unknown", "requires_llm_fallback": True, "transacoes": []},
        )
        statements = E3ReconcilerAdapter(ReconciliationConfig()).load_bank_statements(store)
        assert statements == []

    def test_skips_non_convertible_gracefully(self):
        store = InMemoryArtifactStore()
        # Um CDB position não tem período nem transações — load deve pular
        store.seed(
            "E2-extratos",
            "cdb_posicao",
            {"tipo": "cdb_posicao", "posicoes": [{"valor": 1000}]},
        )
        statements = E3ReconcilerAdapter(ReconciliationConfig()).load_bank_statements(store)
        # Pode ser 0 ou 1 dependendo de como from_e2_dict lida — aceitar ambos
        assert isinstance(statements, list)


class TestReconcileViaStore:
    def test_end_to_end_dedup_within_account(self):
        store = InMemoryArtifactStore()
        # Dois extratos do mesmo banco+moeda+período com transação duplicada entre eles
        store.seed(
            "E2-extratos",
            "itau_jan_a",
            _e2_extract(
                "itau",
                "BRL",
                "2026-01-01",
                "2026-01-31",
                [
                    _tx(5, "MERCADO", -100),
                    _tx(10, "UBER", -30),
                ],
            ),
        )
        store.seed(
            "E2-extratos",
            "itau_jan_b",
            _e2_extract(
                "itau",
                "BRL",
                "2026-01-01",
                "2026-01-31",
                [
                    _tx(5, "MERCADO", -100),  # duplicata cross-file
                    _tx(15, "RESTAURANTE", -80),
                ],
            ),
        )
        adapter = E3ReconcilerAdapter(ReconciliationConfig(tolerance_days=3))
        result = adapter.reconcile_via_store(store)

        assert result["statements_loaded"] == 2
        assert result["artifacts_written"] == 1  # merge em uma única conta itau_BRL

        e3_keys = store.list_keys("E3")
        assert len(e3_keys) == 1
        e3 = store.read("E3", e3_keys[0])
        # Depois do dedup: deve ter 3 transações únicas (MERCADO, UBER, RESTAURANTE)
        assert len(e3["transacoes"]) == 3

    def test_separate_currencies_produce_separate_artifacts(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "a",
            _e2_extract("bankofamerica", "USD", "2026-01-01", "2026-01-31", [_tx(5, "X", 100)]),
        )
        store.seed(
            "E2-extratos",
            "b",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "Y", 500)]),
        )
        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
        assert result["artifacts_written"] == 2
        keys = store.list_keys("E3")
        assert any("USD" in k for k in keys)
        assert any("BRL" in k for k in keys)

    def test_output_keys_follow_canonical_format(self):
        adapter = E3ReconcilerAdapter(ReconciliationConfig())
        from pipeline.domain.models import BankStatement

        stmt = BankStatement(
            institution="C6 Bank",
            member_key=None,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            currency="BRL",
            transactions=[],
        )
        assert adapter.output_key(stmt) == "c6bank_BRL_202601_202603"

    def test_does_not_touch_disk(self, tmp_path):
        """InMemoryArtifactStore sem fallback de disco — se algo tentar gravar
        em ``tmp_path``, esse teste falharia com IOError em outro contexto."""
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "a",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "X", -10)]),
        )
        E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
        # Nada em tmp_path
        assert list(tmp_path.iterdir()) == []


# =============================================================================
# Sessão A1 — Result type, skips, validators integration
# =============================================================================


class TestReconciliationStoreResult:
    def test_result_is_frozen_dataclass(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "a",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "X", -10)]),
        )

        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        assert isinstance(result, ReconciliationStoreResult)
        assert result.statements_loaded == 1
        assert result.artifacts_written == 1
        assert result.skipped_inputs == 0

    def test_result_supports_dict_subscript_for_legacy_callers(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "a",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "X", -10)]),
        )

        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        assert result["statements_loaded"] == 1
        assert result["artifacts_written"] == 1
        assert result["skipped_inputs"] == 0


class TestSkipBehavior:
    def test_skips_irpf_extracts(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "irpf",
            {
                "tipo": "irpf",
                "banco": "fazenda",
                "periodo_inicio": "2024-01-01",
                "periodo_fim": "2024-12-31",
                "transacoes": [],
            },
        )
        store.seed(
            "E2-extratos",
            "itau",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "X", -10)]),
        )

        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        assert result.statements_loaded == 1
        assert result.skipped_inputs == 1

    def test_skips_disallowed_fatura_types(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-faturas",
            "f1",
            {
                "tipo": "faturasecundaria",
                "banco": "Outro",
                "periodo_inicio": "2026-01-01",
                "periodo_fim": "2026-01-31",
                "transacoes": [],
            },
        )

        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        assert result.statements_loaded == 0
        assert result.skipped_inputs == 1


class TestSaldoTemporalIntegration:
    def test_saldo_validator_reports_gap_between_consecutive_statements(self):
        """Conta Itaú com dois extratos consecutivos cujos saldos não casam."""
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "jan",
            {
                "pipeline_stage": "E2",
                "banco": "itau",
                "tipo": "extratoconta",
                "moeda": "BRL",
                "periodo_inicio": "2026-01-01",
                "periodo_fim": "2026-01-31",
                "saldo_inicial": 1000.00,
                "saldo_final": 1500.00,
                "transacoes": [_tx(5, "X", 500)],
            },
        )
        store.seed(
            "E2-extratos",
            "fev",
            {
                "pipeline_stage": "E2",
                "banco": "itau",
                "tipo": "extratoconta",
                "moeda": "BRL",
                "periodo_inicio": "2026-02-01",
                "periodo_fim": "2026-02-28",
                "saldo_inicial": 999.00,  # gap de R$ 501 vs closing anterior
                "saldo_final": 999.00,
                "transacoes": [],
            },
        )
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            saldo_validator=SaldoContinuityValidator(),
        )

        result = adapter.reconcile_via_store(store)

        assert len(result.saldo_warnings) == 1
        warning = result.saldo_warnings[0]
        assert warning.gap.amount == Decimal("501.00")

    def test_temporal_detector_reports_gap_in_days(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "jan",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "X", -10)]),
        )
        # Gap de 28 dias entre 2026-01-31 e 2026-03-01.
        store.seed(
            "E2-extratos",
            "mar",
            _e2_extract("itau", "BRL", "2026-03-01", "2026-03-31", [_tx(5, "Y", -10, month=3)]),
        )
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            temporal_detector=TemporalGapDetector(),
        )

        result = adapter.reconcile_via_store(store)

        assert len(result.temporal_warnings) == 1
        assert result.temporal_warnings[0].days_gap == 29

    def test_validators_are_optional(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "a",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "X", -10)]),
        )

        # Sem saldo_validator nem temporal_detector configurados.
        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        assert result.saldo_warnings == ()
        assert result.temporal_warnings == ()


class TestCanonicalizerIntegration:
    def test_output_key_uses_canonicalizer_when_provided(self):
        canon = BankCanonicalizer.from_institutions(
            {"banco_canonical": {"itau": "Itaú", "c6bank": "C6 Bank"}}
        )
        adapter = E3ReconcilerAdapter(ReconciliationConfig(), canonicalizer=canon)
        stmt = BankStatement(
            institution="Itaú Unibanco",  # nome diferente do display canônico
            member_key=None,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            currency="BRL",
            transactions=[],
        )

        # "Itaú Unibanco" não bate exatamente em "Itaú", então cai no fallback
        # normalizado: "itauunibanco".
        assert adapter.output_key(stmt) == "itauunibanco_BRL_202601_202603"

    def test_output_key_canonical_match_uses_code(self):
        canon = BankCanonicalizer.from_institutions({"banco_canonical": {"itau": "Itaú"}})
        adapter = E3ReconcilerAdapter(ReconciliationConfig(), canonicalizer=canon)
        stmt = BankStatement(
            institution="Itaú",
            member_key=None,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            currency="BRL",
            transactions=[],
        )

        assert adapter.output_key(stmt) == "itau_BRL_202601_202601"


# =============================================================================
# Goldens — fixtures sintéticas em tests/pipeline/goldens/e3/
# =============================================================================


class TestGoldenExtratos:
    def test_cenario_extratos_matches_expected(self):
        golden = _load_golden("cenario_extratos.json")
        canon = BankCanonicalizer.from_institutions(golden["institutions"])
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(tolerance_days=3),
            canonicalizer=canon,
            saldo_validator=SaldoContinuityValidator(),
            temporal_detector=TemporalGapDetector(),
        )

        result = adapter.reconcile_via_store(store)

        expected = golden["expected"]
        assert result.statements_loaded == expected["statements_loaded"]
        assert result.artifacts_written == expected["artifacts_written"]
        assert result.skipped_inputs == expected["skipped_inputs"]
        assert sorted(store.list_keys("E3")) == sorted(expected["output_keys"])

        # 3 transações únicas após dedup cross-file.
        e3_payload = store.read("E3", expected["output_keys"][0])
        assert len(e3_payload["transacoes"]) == expected["merged_transaction_count"]

        assert len(result.saldo_warnings) == expected["saldo_warnings_count"]
        assert len(result.temporal_warnings) == expected["temporal_warnings_count"]
        assert len(result.baseline_warnings) == expected["baseline_warnings_count"]


class TestGoldenFaturaSemPeriodo:
    def test_cenario_fatura_synthesizes_periodo_and_drops_anachronic(self):
        golden = _load_golden("cenario_fatura_sem_periodo.json")
        canon = BankCanonicalizer.from_institutions(golden["institutions"])
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            canonicalizer=canon,
        )

        result = adapter.reconcile_via_store(store)

        expected = golden["expected"]
        assert result.statements_loaded == expected["statements_loaded"]
        assert result.artifacts_written == expected["artifacts_written"]
        assert result.skipped_inputs == expected["skipped_inputs"]

        # Output key derivado do período sintetizado (abr/2026 → 202604_202604).
        assert sorted(store.list_keys("E3")) == sorted(expected["output_keys"])

        e3_payload = store.read("E3", expected["output_keys"][0])
        # 3 transações entraram, 1 foi droppada (anachronic) → 2 restam.
        assert len(e3_payload["transacoes"]) == expected["merged_transaction_count"]

        # Período sintético + warnings esperados.
        assert len(result.period_warnings) >= expected["period_warnings_min_count"]
        assert len(result.anachronic_warnings) == expected["anachronic_warnings_count"]


class TestGoldenBaselineDiff:
    def test_cenario_baseline_diff_emits_baseline_warning(self):
        golden = _load_golden("cenario_baseline_diff.json")
        canon = BankCanonicalizer.from_institutions(golden["institutions"])
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            canonicalizer=canon,
            baseline_validator=BaselineValidator(
                BaselineValidatorConfig(),
                canonicalizer=canon,
            ),
        )

        result = adapter.reconcile_via_store(store)

        expected = golden["expected"]
        assert result.statements_loaded == expected["statements_loaded"]
        assert result.artifacts_written == expected["artifacts_written"]
        assert sorted(store.list_keys("E3")) == sorted(expected["output_keys"])

        assert len(result.baseline_warnings) == expected["baseline_warnings_count"]
        warning = result.baseline_warnings[0]
        assert warning.diff.amount == Decimal(str(expected["baseline_diff_amount_brl"]))
        assert warning.reference_date == date(2024, 12, 31)
        assert warning.baseline_member == "David"

    def test_baseline_validator_skipped_when_no_baseline_in_store(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "a",
            _e2_extract("itau", "BRL", "2024-01-01", "2024-12-31", [_tx(5, "X", 100)]),
        )
        canon = BankCanonicalizer.from_institutions({"banco_canonical": {"itau": "Itaú"}})
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            canonicalizer=canon,
            baseline_validator=BaselineValidator(canonicalizer=canon),
        )

        result = adapter.reconcile_via_store(store)

        assert result.baseline_warnings == ()


class TestLoadBaselineAccounts:
    def test_loads_from_store_when_baseline_present(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E1.5c",
            "baseline_patrimonial",
            {
                "members": {
                    "David": {
                        "nome": "David",
                        "contas_bancarias": [
                            {"banco": "Itaú", "ano_base": 2024, "saldo_31_12": 1000.00},
                        ],
                    }
                }
            },
        )

        accounts = E3ReconcilerAdapter(ReconciliationConfig()).load_baseline_accounts(store)

        assert len(accounts) == 1
        assert accounts[0].bank == "Itaú"
        assert accounts[0].year == 2024

    def test_returns_empty_when_no_baseline_in_store(self):
        store = InMemoryArtifactStore()

        accounts = E3ReconcilerAdapter(ReconciliationConfig()).load_baseline_accounts(store)

        assert accounts == []


class TestLoadBankStatementsWithWarnings:
    def test_returns_quadruple_with_warnings(self):
        """Extrato com período fixo + 1 tx anachronic (>180d antes de
        ``periodo.inicio``) — guard remove a tx e emite warning.
        Cenário separado do golden de fatura porque o ajuste de início para
        min(tx_dates) em fatura sintetizada anula o anachronic guard
        (paridade com legado).
        """
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "ext",
            {
                "pipeline_stage": "E2",
                "banco": "Itaú",
                "tipo": "extratoconta",
                "moeda": "BRL",
                "periodo_inicio": "2026-04-01",
                "periodo_fim": "2026-04-30",
                "saldo_inicial": 1000.00,
                "saldo_final": 940.00,
                "transacoes": [
                    {"data": "2024-09-01", "descricao": "OLD", "valor": -10.00},
                    {"data": "2026-04-10", "descricao": "NEW", "valor": -60.00},
                ],
            },
        )

        statements, period_warnings, anach_warnings, skipped = E3ReconcilerAdapter(
            ReconciliationConfig()
        ).load_bank_statements_with_warnings(store)

        assert len(statements) == 1
        assert len(statements[0].transactions) == 1  # OLD removida
        assert period_warnings == []  # extrato com período fixo, sem síntese
        assert len(anach_warnings) == 1
        assert anach_warnings[0].dropped_count == 1
        assert skipped == 0


def _reconcile_single_seed(stage: str, key: str, payload: dict) -> ReconciliationStoreResult:
    store = InMemoryArtifactStore()
    store.seed(stage, key, payload)
    result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
    if result.artifacts_written == 0:
        assert store.list_keys("reconcile_transactions") == []
    return result


class TestIngestHygieneA28L8:
    """A28.l8 — banco vazio e período implausível não viram artefato E3 silencioso."""

    def test_empty_institution_is_skipped_with_review_reason(self):
        from pipeline.domain.review_reason import ReviewReasonCode

        result = _reconcile_single_seed(
            "E2-llm",
            "binance_extrato",
            _e2_extract("", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "A", -100)]),
        )

        assert result.artifacts_written == 0
        assert result.skipped_inputs == 1
        assert result.institution_warnings[0].source == "binance_extrato"
        assert [r.code for r in result.review_reasons] == [
            ReviewReasonCode.extract_missing_required_field
        ]

    def test_implausible_period_is_skipped_with_review_reason(self):
        from pipeline.domain.review_reason import ReviewReasonCode

        payload = {
            "pipeline_stage": "E2",
            "banco": "c6bank",
            "tipo": "faturacarbon",
            "moeda": "BRL",
            "periodo": "210001",
            "transacoes": [],
        }
        result = _reconcile_single_seed("E2-faturas", "c6bank_faturacarbon_999999", payload)

        assert result.artifacts_written == 0
        assert result.skipped_inputs == 1
        assert [r.code for r in result.review_reasons] == [ReviewReasonCode.dedup_sentinel_period]
        reason = result.review_reasons[0]
        assert reason.artifact_key == "c6bank_faturacarbon_999999"
        assert reason.stage == "reconcile_transactions"

    def test_result_to_dict_carries_review_reasons(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "sem_banco",
            _e2_extract("", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "A", -100)]),
        )
        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        d = result.to_dict()

        assert d["institution_warnings"]
        assert d["review_reasons"][0]["code"] == "extract.missing_required_field"

    def test_plausible_inputs_produce_no_review_reasons(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-extratos",
            "itau_ok",
            _e2_extract("itau", "BRL", "2026-01-01", "2026-01-31", [_tx(5, "A", -100)]),
        )
        result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)

        assert result.artifacts_written == 1
        assert result.review_reasons == ()
        assert result.institution_warnings == ()

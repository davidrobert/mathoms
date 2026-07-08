"""Tests A32.l4 (ADR-310) — chave canônica de conta na continuidade de saldo.

Reproduz os casos do dossiê da sprint A32 (fixtures sintéticas, PII-zero):

- bradesco: ``extratopoupanca`` → ``extratoconta`` fundidos numa cadeia única
  geravam ``balance_gap`` falso;
- c6bank: ``faturacarbon`` → ``extratoconta`` → ``faturacarbon`` intercalados;
- santander: faturas com ``period_start`` colapsado por
  ``fatura_inicio_adjusted_to_tx`` encadeadas em ordem de hash.

Cobre também o teste negativo (objeção senior-cto): conta legítima
classificada como fatura por engano nunca some da validação sem sinal —
``FaturaExcludedFromSaldoChain`` registra cada exclusão.
"""

from __future__ import annotations

import itertools
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.models import BankStatement, Money  # noqa: E402
from pipeline.domain.services.account_grouper import (  # noqa: E402
    AccountGrouper,
    AccountGrouperConfig,
)
from pipeline.domain.services.e3_reconciler_adapter import E3ReconcilerAdapter  # noqa: E402
from pipeline.domain.services.reconciliation_service import ReconciliationConfig  # noqa: E402
from pipeline.domain.services.reconciliation_validators import (  # noqa: E402
    SaldoContinuityValidator,
    TemporalGapDetector,
)

_JAN = (date(2026, 1, 1), date(2026, 1, 31))
_FEV = (date(2026, 2, 1), date(2026, 2, 28))
_MAR = (date(2026, 3, 1), date(2026, 3, 31))


def _money_brl(value: str | None) -> Money | None:
    return Money.of(value, "BRL") if value is not None else None


def _stmt(period: tuple[date, date], opening=None, closing=None, **kw) -> BankStatement:
    """Statement sintético BRL; kw: inst, tipo, member, number, src."""
    return BankStatement(
        institution=kw.get("inst", "bradesco"),
        member_key=kw.get("member", "titular"),
        period_start=period[0],
        period_end=period[1],
        currency="BRL",
        transactions=[],
        opening_balance=_money_brl(opening),
        closing_balance=_money_brl(closing),
        source_document=kw.get("src"),
        account_type=kw.get("tipo", "extratoconta"),
        account_number_norm=kw.get("number"),
    )


# =============================================================================
# Caso bradesco — account_type distinto separa cadeias
# =============================================================================


class TestAccountTypeSeparatesChains:
    def test_poupanca_and_conta_do_not_compare(self):
        """extratopoupanca → extratoconta do mesmo banco: saldos díspares
        nunca geram gap — são contas diferentes (ADR-310)."""
        stmts = [
            _stmt(_JAN, "0", "5000", tipo="extratopoupanca", src="poupanca_jan.pdf"),
            _stmt(_FEV, "120", "300", tipo="extratoconta", src="conta_fev.pdf"),
        ]
        assert SaldoContinuityValidator().validate(stmts) == []

    def test_gap_within_same_account_type_still_fires(self):
        """Controle positivo: descontinuidade dentro da MESMA conta segue
        detectada — o fix não cega o validator."""
        stmts = [
            _stmt(_JAN, "0", "5000", src="jan.pdf"),
            _stmt(_FEV, "120", "300", src="fev.pdf"),
        ]
        warns = SaldoContinuityValidator().validate(stmts)
        assert len(warns) == 1
        assert warns[0].account_key.account_type == "extratoconta"
        assert warns[0].gap == Money.brl("4880.00")

    def test_account_number_norm_separates_chains(self):
        """Mesmo banco+tipo+moeda+membro com números de conta distintos
        (ADR-226) são cadeias separadas."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="111222"),
            _stmt(_FEV, "120", "300", number="333444"),
        ]
        assert SaldoContinuityValidator().validate(stmts) == []

    def test_members_still_separate_chains(self):
        stmts = [
            _stmt(_JAN, "0", "5000", member="titular"),
            _stmt(_FEV, "120", "300", member="conjuge"),
        ]
        assert SaldoContinuityValidator().validate(stmts) == []


# =============================================================================
# Caso c6bank — fatura fora da cadeia de saldo
# =============================================================================


class TestFaturaOutsideSaldoChain:
    def test_fatura_conta_fatura_interleaved_no_gap(self):
        """faturacarbon → extratoconta → faturacarbon do mesmo banco:
        zero balance_gap — fatura não participa da cadeia (ADR-310)."""
        stmts = [
            _stmt(_JAN, "800", "1200", inst="c6bank", tipo="faturacarbon", src="fat_jan.pdf"),
            _stmt(_FEV, "50", "70", inst="c6bank", tipo="extratoconta", src="conta_fev.pdf"),
            _stmt(_MAR, "900", "1500", inst="c6bank", tipo="faturacarbon", src="fat_mar.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert result.warnings == ()
        excluded_sources = sorted(e.source_document for e in result.excluded_faturas)
        assert excluded_sources == ["fat_jan.pdf", "fat_mar.pdf"]

    def test_exclusion_signal_carries_bank_and_type(self):
        stmts = [_stmt(_JAN, "800", "1200", inst="C6 Bank", tipo="faturacarbon", src="fat_jan.pdf")]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert len(result.excluded_faturas) == 1
        signal = result.excluded_faturas[0]
        assert signal.bank == "c6 bank"
        assert signal.account_type == "faturacarbon"
        assert "fat_jan.pdf" in signal.format()

    def test_misclassified_conta_never_disappears_silently(self):
        """Teste negativo (objeção senior-cto): conta legítima com tipo
        'fatura*' por engano sai da validação COM sinal auditável."""
        stmts = [
            _stmt(_JAN, "0", "5000", tipo="faturaqualquer", src="conta_misclassificada.pdf"),
            _stmt(_FEV, "120", "300", src="conta_fev.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert result.warnings == ()
        assert len(result.excluded_faturas) == 1
        assert result.excluded_faturas[0].source_document == "conta_misclassificada.pdf"

    def test_is_fatura_via_equivalences_shares_grouper_definition(self):
        """Equivalence do AccountGrouper decide is_fatura — a definição de
        'mesma conta' é uma só no domínio."""
        grouper = AccountGrouper(
            AccountGrouperConfig(account_type_equivalences={"cartaoxyz": "faturacarbon"})
        )
        stmts = [_stmt(_JAN, "800", "1200", tipo="cartaoxyz", src="cartao_jan.pdf")]
        result = SaldoContinuityValidator(grouper=grouper).validate_with_exclusions(stmts)
        assert result.warnings == ()
        assert result.excluded_faturas[0].account_type == "faturacarbon"

    def test_fatura_still_forms_own_chain_in_temporal_detector(self):
        """Fatura permanece na detecção temporal — em cadeia própria,
        separada da conta corrente do mesmo banco."""
        mar_late = (date(2026, 3, 10), date(2026, 3, 31))
        stmts = [
            _stmt(_JAN, inst="c6bank", tipo="faturacarbon", src="fat_jan.pdf"),
            _stmt(mar_late, inst="c6bank", tipo="faturacarbon", src="fat_mar.pdf"),
            _stmt(_FEV, inst="c6bank", tipo="extratoconta", src="conta_fev.pdf"),
        ]
        warns = TemporalGapDetector().detect(stmts)
        assert len(warns) == 1
        assert warns[0].account_key.is_fatura
        assert warns[0].previous_source == "fat_jan.pdf"
        assert warns[0].next_source == "fat_mar.pdf"


# =============================================================================
# Caso santander — desempate determinístico
# =============================================================================


class TestDeterministicOrdering:
    def test_collapsed_period_start_faturas_no_gap_any_order(self):
        """Faturas com início colapsado por fatura_inicio_adjusted_to_tx
        (mesmo period_start): nenhuma permutação gera gap ou warning."""
        collapsed_start = date(2025, 10, 15)
        faturas = [
            _stmt(
                (collapsed_start, date(2026, m, 10)),
                o,
                c,
                inst="santander",
                tipo="faturaunique",
                src=f"fatura_2026{m:02d}.pdf",
            )
            for m, o, c in ((1, "100", "200"), (2, "300", "400"), (3, "500", "600"))
        ]
        for perm in itertools.permutations(faturas):
            result = SaldoContinuityValidator().validate_with_exclusions(list(perm))
            assert result.warnings == ()
            assert len(result.excluded_faturas) == 3
            assert TemporalGapDetector().detect(list(perm)) == []

    def test_tie_on_period_start_resolved_by_period_end(self):
        """Empate de period_start: period_end decide, não ordem de inserção."""
        quinzena = (date(2026, 1, 1), date(2026, 1, 15))
        mes_cheio = (date(2026, 1, 1), date(2026, 1, 31))
        first = _stmt(quinzena, "0", "100", src="z_quinzena1.pdf")
        second = _stmt(mes_cheio, "999", "50", src="a_mes_cheio.pdf")
        for perm in itertools.permutations([first, second]):
            warns = SaldoContinuityValidator().validate(list(perm))
            assert len(warns) == 1
            # 'z' vem antes de 'a' porque period_end menor vence o desempate.
            assert warns[0].previous_source == "z_quinzena1.pdf"
            assert warns[0].next_source == "a_mes_cheio.pdf"

    def test_full_tie_resolved_by_source_document(self):
        """Empate total de período: source_document desempata — nunca hash."""
        a = _stmt(_JAN, "0", "100", src="a.pdf")
        b = _stmt(_JAN, "999", "50", src="b.pdf")
        for perm in itertools.permutations([a, b]):
            warns = SaldoContinuityValidator().validate(list(perm))
            assert len(warns) == 1
            assert warns[0].previous_source == "a.pdf"
            assert warns[0].next_source == "b.pdf"


# =============================================================================
# Integração — sinal de exclusão atravessa o adapter
# =============================================================================


def _fatura_payload() -> dict:
    return {
        "pipeline_stage": "E2",
        "banco": "c6bank",
        "tipo": "faturacarbon",
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-01-31",
        "saldo_inicial": 800.0,
        "saldo_final": 1200.0,
        "transacoes": [{"data": "2026-01-05", "descricao": "COMPRA X", "valor": -400.0}],
    }


class TestAdapterSurfacesExclusionSignal:
    def test_reconcile_via_store_exposes_saldo_exclusions(self):
        store = InMemoryArtifactStore()
        store.seed("E2-faturas", "c6bank_fatura_jan", _fatura_payload())
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            saldo_validator=SaldoContinuityValidator(),
        )

        result = adapter.reconcile_via_store(store)

        assert result.saldo_warnings == ()
        assert len(result.saldo_exclusions) == 1
        assert result.saldo_exclusions[0].account_type == "faturacarbon"
        assert result.to_dict()["saldo_exclusions"] == [result.saldo_exclusions[0].format()]


def _account_payload(*, key_period, opening, closing, number=None) -> dict:
    inicio, fim = key_period
    payload = {
        "pipeline_stage": "E2",
        "banco": "rico",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "periodo_inicio": inicio.isoformat(),
        "periodo_fim": fim.isoformat(),
        "saldo_inicial": opening,
        "saldo_final": closing,
        "transacoes": [],
    }
    if number is not None:
        payload["numero_conta"] = number
    return payload


class TestAdapterSurfacesInferredChainMembers:
    def test_reconcile_via_store_exposes_inferred_members(self):
        """Emenda ADR-310 (A35.l1): extrato sem número coalesce na cadeia
        numerada e o sinal atravessa o adapter."""
        jul = (date(2026, 7, 1), date(2026, 7, 31))
        store = InMemoryArtifactStore()
        store.seed(
            "extract_statements",
            "rico_jan",
            _account_payload(key_period=_JAN, opening=0.0, closing=5000.0, number="9988"),
        )
        store.seed(
            "extract_statements",
            "rico_jul",
            _account_payload(key_period=jul, opening=9000.0, closing=9500.0),
        )
        adapter = E3ReconcilerAdapter(
            ReconciliationConfig(),
            saldo_validator=SaldoContinuityValidator(),
            temporal_detector=TemporalGapDetector(),
        )

        result = adapter.reconcile_via_store(store)

        assert len(result.inferred_chain_members) == 1
        assert result.to_dict()["inferred_chain_members"] == [
            result.inferred_chain_members[0].format()
        ]
        assert len(result.temporal_warnings) == 1

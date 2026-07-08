"""Tests A35.l1 (emenda ADR-310 2026-07-08) — coalescência de cadeia de
continuidade quando o número de conta não é extraído.

`ContinuityAccountKey` inclui `account_number_norm` desde a A32.l4; quando um
extrato não tem número (parser não casou), ele vira "conta diferente" e o gap
genuíno entre ele e os extratos numerados da MESMA conta some (issue #860).
O fallback intra-run (Tier 2) coalesce os sem-número na cadeia numerada quando
há exatamente um número distinto no grupo `(banco, membro, tipo, moeda)`, com
sinal auditável `SaldoChainMemberInferred` — nunca em silêncio.

Fixtures sintéticas PII-zero (sem CPF/valores reais); espelham o caso rico
(#860) com números e valores fabricados.
"""

from __future__ import annotations

import itertools
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import BankStatement, Money  # noqa: E402
from pipeline.domain.services.reconciliation_validators import (  # noqa: E402
    SaldoChainMemberInferred,
    SaldoContinuityValidator,
    TemporalGapDetector,
)

_JAN = (date(2026, 1, 1), date(2026, 1, 31))
_FEV = (date(2026, 2, 1), date(2026, 2, 28))
_MAR = (date(2026, 3, 1), date(2026, 3, 31))
# Buraco abr–jun/2026: extrato de julho depois de janeiro, sem cobertura no meio.
_JUL = (date(2026, 7, 1), date(2026, 7, 31))


def _money_brl(value: str | None) -> Money | None:
    return Money.of(value, "BRL") if value is not None else None


def _stmt(period: tuple[date, date], opening=None, closing=None, **kw) -> BankStatement:
    return BankStatement(
        institution=kw.get("inst", "rico"),
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
# KR1 — detecção restaurada (o gap genuíno volta a aparecer)
# =============================================================================


class TestGenuineGapRestored:
    def test_accountless_coalesces_into_numbered_chain_temporal_gap(self):
        """Caso rico #860: extrato jan (com número) + jul (sem número) da mesma
        conta coalescem → o gap temporal abr–jun/2026 re-sinaliza."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        result = TemporalGapDetector().detect_with_inferences(stmts)
        assert len(result.warnings) == 1
        gap = result.warnings[0]
        assert gap.previous_source == "jan.pdf"
        assert gap.next_source == "jul.pdf"
        assert gap.days_gap > 30

    def test_accountless_coalesces_into_numbered_chain_balance_gap(self):
        """Mesma coalescência re-sinaliza a descontinuidade de saldo."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert len(result.warnings) == 1
        assert result.warnings[0].gap == Money.brl("4000.00")

    def test_without_fallback_gap_would_be_invisible(self):
        """Controle: contas SEPARADAS por número distinto não comparam (o
        comportamento que o #860 sofria antes do fallback é o esperado quando
        há dois números reais)."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_JUL, "9000", "9500", number="7766", src="jul.pdf"),
        ]
        assert TemporalGapDetector().detect(stmts) == []
        assert SaldoContinuityValidator().validate(stmts) == []


# =============================================================================
# KR2 — anti-regressão da A32.l4 (não-fusão indevida)
# =============================================================================


class TestNonFusionGuards:
    def test_two_distinct_numbers_plus_accountless_does_not_coalesce(self):
        """>= 2 números distintos no grupo → o sem-número NÃO coalesce
        (isola); ramo frágil deferido ao Tier 1 / SourceRef.kind."""
        stmts = [
            _stmt(_JAN, "0", "100", number="111", src="a.pdf"),
            _stmt(_FEV, "100", "200", number="222", src="b.pdf"),
            _stmt(_MAR, "5000", "6000", src="c.pdf"),  # sem número
        ]
        result = TemporalGapDetector().detect_with_inferences(stmts)
        assert result.inferred_members == ()
        saldo = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert saldo.inferred_members == ()

    def test_poupanca_accountless_never_matches_cc_accountless(self):
        """account_type canônico segura: poupança sem número nunca casa com
        conta corrente sem número (eixo estrito preservado)."""
        stmts = [
            _stmt(_JAN, "0", "5000", tipo="extratopoupanca", src="poupanca.pdf"),
            _stmt(_FEV, "120", "300", tipo="extratoconta", src="conta.pdf"),
        ]
        assert SaldoContinuityValidator().validate(stmts) == []
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert result.inferred_members == ()

    def test_all_none_still_group_together(self):
        """Todos sem número → agrupam entre si (comportamento A32 preservado):
        gap dispara e nenhuma coalescência é sinalizada."""
        stmts = [
            _stmt(_JAN, "0", "5000", src="a.pdf"),
            _stmt(_FEV, "120", "300", src="b.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert len(result.warnings) == 1
        assert result.inferred_members == ()

    def test_distinct_members_never_coalesce(self):
        """Membro distinto isola mesmo com um único número no banco."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", member="titular", src="a.pdf"),
            _stmt(_FEV, "120", "300", member="conjuge", src="b.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert result.inferred_members == ()

    def test_fatura_never_coalesces(self):
        """Fatura (sem account_number, tipo fatura*) fica fora da cadeia de
        saldo e nunca entra na coalescência (só `not is_fatura`)."""
        stmts = [
            _stmt(_JAN, "800", "1200", tipo="faturacarbon", src="fat.pdf"),
            _stmt(_FEV, "0", "5000", number="9988", src="conta.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert result.inferred_members == ()
        assert len(result.excluded_faturas) == 1


# =============================================================================
# KR3 — sinal sempre (nenhuma inferência silenciosa)
# =============================================================================


class TestInferenceSignalAlwaysEmitted:
    def test_coalescence_always_emits_signal(self):
        """Toda coalescência emite um SaldoChainMemberInferred por statement
        sem número — nunca some da observabilidade (espelha o teste negativo
        da l4 para FaturaExcludedFromSaldoChain)."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert len(result.inferred_members) == 1
        signal = result.inferred_members[0]
        assert isinstance(signal, SaldoChainMemberInferred)
        assert signal.source_document == "jul.pdf"

    def test_signal_omits_raw_account_number(self):
        """Dado sensível: a mensagem nunca carrega o número de conta cru."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        signal = SaldoContinuityValidator().validate_with_exclusions(stmts).inferred_members[0]
        assert "9988" not in signal.format()
        assert "rico/extratoconta/titular/BRL" in signal.format()

    def test_signal_present_in_both_validators(self):
        """Ambos os validators expõem o sinal (helper compartilhado)."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        saldo = SaldoContinuityValidator().validate_with_exclusions(stmts)
        temporal = TemporalGapDetector().detect_with_inferences(stmts)
        assert len(saldo.inferred_members) == 1
        assert len(temporal.inferred_members) == 1
        assert saldo.inferred_members[0].format() == temporal.inferred_members[0].format()

    def test_multiple_accountless_each_emit_signal(self):
        """Dois extratos sem número na mesma conta numerada → dois sinais."""
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_FEV, "5000", "5100", src="fev.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert len(result.inferred_members) == 2
        assert sorted(s.source_document for s in result.inferred_members) == ["fev.pdf", "jul.pdf"]


# =============================================================================
# Determinismo (ADR-111) — mesma entrada, qualquer ordem → mesma saída
# =============================================================================


class TestCoalescenceDeterminism:
    def test_same_warnings_and_signals_regardless_of_insertion_order(self):
        stmts = [
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
            _stmt(_FEV, "5000", "5100", src="fev.pdf"),
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),
        ]
        outputs = set()
        for perm in itertools.permutations(stmts):
            saldo = SaldoContinuityValidator().validate_with_exclusions(list(perm))
            temporal = TemporalGapDetector().detect_with_inferences(list(perm))
            outputs.add(
                (
                    tuple(w.format() for w in saldo.warnings),
                    tuple(s.format() for s in saldo.inferred_members),
                    tuple(w.format() for w in temporal.warnings),
                    tuple(s.format() for s in temporal.inferred_members),
                )
            )
        assert len(outputs) == 1

    def test_survivor_key_is_the_numbered_one(self):
        """Sobrevivente canônico fixo = a chave numerada (nunca a sem-número)."""
        stmts = [
            _stmt(_JUL, "9000", "9500", src="jul.pdf"),  # sem número, inserido primeiro
            _stmt(_JAN, "0", "5000", number="9988", src="jan.pdf"),
        ]
        result = SaldoContinuityValidator().validate_with_exclusions(stmts)
        assert len(result.warnings) == 1
        assert result.warnings[0].account_key.account_number == "9988"

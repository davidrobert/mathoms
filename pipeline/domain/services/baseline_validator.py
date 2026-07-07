"""Validador de saldos de conta vs. baseline IRPF (Fase 6 foundation · ADR-089).

Extrai ``validate_against_baseline()`` de ``scripts/reconcile_transactions.py:551`` em
um domain service independente.

Responsabilidade: para cada ``BankStatement`` cujo ``period_end`` coincide com
uma data-base do baseline (``YYYY-12-31``), comparar o ``closing_balance`` com
o saldo declarado em IRPF. Diferenças acima de ``tolerance_amount`` viram
``BaselineDiffWarning``.

Baseline é representado como ``list[BaselineAccountSaldo]`` — value object
extraído do raw dict do baseline patrimonial via ``from_baseline_dict``. O
schema de baseline é complexo (várias seções), mas o validator só precisa de
``(banco, ano, saldo, membro, tipo)``.

Comparação de nome de banco usa ``BankCanonicalizer`` (não substring — evita
fix 4.4).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from pipeline.domain.models.bank import BankCanonicalizer
from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money
from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.reconciliation_validators import AccountKey

# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class BaselineValidatorConfig:
    """Tolerância para diferença entre saldo IRPF e saldo do extrato em 31/12.

    Default ``R$ 1,00`` (legacy: ``pipeline.json → reconciliation.tolerances.baseline_irpf_diff``).
    """

    tolerance_amount: Decimal = Decimal("1.00")

    @classmethod
    def from_pipeline_config(cls, pipeline: dict) -> "BaselineValidatorConfig":
        tol = (
            (pipeline or {})
            .get("reconciliation", {})
            .get("tolerances", {})
            .get("baseline_irpf_diff", "1.00")
        )
        return cls(tolerance_amount=Decimal(str(tol)))


# =============================================================================
# Value objects
# =============================================================================


@dataclass(frozen=True)
class BaselineAccountSaldo:
    """Saldo declarado em IRPF para uma conta bancária em 31/12/``year``.

    Extraído do baseline_patrimonial consolidado (E1.5c). Aceita tanto o
    formato ``members: dict`` quanto ``members: list`` do schema legado.
    """

    bank: str  # forma livre; será canonicalizada no validator
    year: int
    saldo: Money
    member: str
    account_type: str = ""

    @property
    def reference_date(self) -> date:
        """Data-base do saldo (31/12 do ano)."""
        return date(self.year, 12, 31)

    @classmethod
    def from_baseline_dict(cls, baseline: dict) -> list["BaselineAccountSaldo"]:
        """Extrai todos os ``BaselineAccountSaldo`` de um dict do baseline.

        Aceita ``baseline["members"]`` ou ``baseline["membros"]``, ambos no
        formato ``dict[nome, data]`` ou ``list[data]`` (com ``data.nome``).
        Cada membro pode ter ``contas_bancarias: list[...]`` com:
            - ``banco`` ou ``banco_origem``
            - ``saldo_31_12`` ou ``saldo_31_12_ano_base``
            - ``ano_base``
            - ``tipo`` (opcional)

        Entradas inválidas (sem saldo ou sem banco) são silenciosamente
        ignoradas — consistente com o legado.
        """
        if not isinstance(baseline, dict):
            return []
        raw_members = baseline.get("members") or baseline.get("membros") or {}

        # Normaliza list-of-dict → dict[nome, dict].
        members: dict[str, dict]
        if isinstance(raw_members, list):
            members = {}
            for i, m in enumerate(raw_members):
                if isinstance(m, dict):
                    name = m.get("nome") or m.get("name") or f"member_{i}"
                    members[str(name)] = m
        elif isinstance(raw_members, dict):
            members = raw_members
        else:
            return []

        out: list["BaselineAccountSaldo"] = []
        for name, member_data in members.items():
            if not isinstance(member_data, dict):
                continue
            contas = member_data.get("contas_bancarias", [])
            if not isinstance(contas, list):
                continue
            for conta in contas:
                if not isinstance(conta, dict):
                    continue
                bank_raw = (conta.get("banco") or conta.get("banco_origem") or "").strip()
                saldo_raw = conta.get("saldo_31_12")
                if saldo_raw is None:
                    saldo_raw = conta.get("saldo_31_12_ano_base")
                ano_raw = conta.get("ano_base")
                if not bank_raw or saldo_raw is None or ano_raw is None:
                    continue
                try:
                    year = int(ano_raw)
                except (TypeError, ValueError):
                    continue
                # ``str(saldo_raw)`` preserva Decimal exato sem voltar para float.
                try:
                    saldo = Money.of(str(saldo_raw), "BRL")
                except Exception:
                    continue
                out.append(
                    cls(
                        bank=bank_raw,
                        year=year,
                        saldo=saldo,
                        member=str(name),
                        account_type=str(conta.get("tipo") or ""),
                    )
                )
        return out


@dataclass(frozen=True)
class BaselineDiffWarning:
    """Discrepância entre baseline IRPF e extrato em ``reference_date``."""

    account_key: AccountKey
    reference_date: date
    baseline_saldo: Money
    statement_closing: Money
    diff: Money  # valor absoluto
    baseline_member: str
    account_type: str = ""

    @property
    def percent_diff(self) -> Decimal:
        """Diferença como % do baseline (``inf`` se baseline == 0)."""
        bl = self.baseline_saldo.amount
        if bl == 0:
            return Decimal("Infinity")
        return (self.diff.amount / abs(bl)) * Decimal(100)

    def format(self) -> str:
        inst, member, currency = self.account_key
        who = f"{inst}/{member or '-'}/{currency}"
        pct = self.percent_diff
        pct_str = "inf" if pct.is_infinite() else f"{float(pct):.1f}%"
        return (
            f"Baseline diff {who} em {self.reference_date.isoformat()}: "
            f"IRPF={self.baseline_saldo.to_float():.2f} vs "
            f"extrato={self.statement_closing.to_float():.2f} "
            f"(diff={self.diff.to_float():.2f}, {pct_str}) "
            f"[membro: {self.baseline_member}]"
        )

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272/ADR-308) — informativo; ``offending_value`` só
        carrega % relativo (saldo/diff absolutos são Money, sensível)."""
        inst, member, currency = self.account_key
        pct = self.percent_diff
        pct_str = "inf" if pct.is_infinite() else f"{float(pct):.1f}%"
        return ReviewReason(
            code=ReviewReasonCode.domain_baseline_divergence,
            stage=stage,
            artifact_key=artifact_key or f"{inst}_{currency}_baseline_{self.reference_date.year}",
            document_id=document_id,
            offending_value=(
                f"saldo do extrato difere {pct_str} do IRPF em "
                f"{inst}/{member or '-'}/{currency} ({self.reference_date.isoformat()})"
            ),
            expected="closing_balance == saldo declarado no IRPF em 31/12",
            message="saldo do extrato diverge do baseline IRPF; conferir documento",
        )


# =============================================================================
# Service
# =============================================================================


class BaselineValidator:
    """Compara saldos de ``BankStatement`` contra declarações IRPF.

    Para cada ``(bank, year)`` no baseline, procura ``BankStatement`` que:
        - pertença ao mesmo banco canônico (via ``BankCanonicalizer``), e
        - tenha ``period_end`` == ``YYYY-12-31``.

    Diferenças acima da tolerância geram ``BaselineDiffWarning``.
    Extratos com ``closing_balance`` ausente são ignorados.
    """

    def __init__(
        self,
        config: BaselineValidatorConfig | None = None,
        canonicalizer: BankCanonicalizer | None = None,
    ):
        self._config = config or BaselineValidatorConfig()
        self._canon = canonicalizer or BankCanonicalizer.empty()

    def validate(
        self,
        statements: Iterable[BankStatement],
        baseline_accounts: Iterable[BaselineAccountSaldo],
    ) -> list[BaselineDiffWarning]:
        """Retorna lista de warnings (ordem estável: por banco, ano, membro)."""
        stmt_list = list(statements)
        baseline_list = list(baseline_accounts)

        if not baseline_list:
            return []

        warnings: list[BaselineDiffWarning] = []
        for bl in baseline_list:
            ref = bl.reference_date
            bl_canon = self._canon.canonicalize(bl.bank)
            for stmt in stmt_list:
                if stmt.closing_balance is None:
                    continue
                # Moedas devem bater.
                if stmt.closing_balance.currency != bl.saldo.currency:
                    continue
                # Banco canônico igual.
                if self._canon.canonicalize(stmt.institution) != bl_canon:
                    continue
                # ``period_end`` == data-base.
                if stmt.period_end != ref:
                    continue
                diff_amount = abs(stmt.closing_balance.amount - bl.saldo.amount)
                if diff_amount > self._config.tolerance_amount:
                    warnings.append(
                        BaselineDiffWarning(
                            account_key=(
                                stmt.institution.lower(),
                                stmt.member_key,
                                stmt.currency.upper(),
                            ),
                            reference_date=ref,
                            baseline_saldo=bl.saldo,
                            statement_closing=stmt.closing_balance,
                            diff=Money(diff_amount, bl.saldo.currency),
                            baseline_member=bl.member,
                            account_type=bl.account_type,
                        )
                    )
        return warnings

    def validate_grouped(
        self,
        statements: Iterable[BankStatement],
        baseline_accounts: Iterable[BaselineAccountSaldo],
    ) -> dict[AccountKey, list[BaselineDiffWarning]]:
        """Mesma validação, agrupada por ``AccountKey`` — formato próximo do
        legado ``validate_against_baseline() → dict[str, list[str]]``.
        """
        grouped: dict[AccountKey, list[BaselineDiffWarning]] = defaultdict(list)
        for w in self.validate(statements, baseline_accounts):
            grouped[w.account_key].append(w)
        return dict(grouped)

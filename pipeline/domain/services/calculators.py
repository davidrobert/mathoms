"""Calculadoras financeiras (Fase 8 — foundation).

Cada classe encapsula UMA responsabilidade extraída de ``e5_analyze.py``
(108KB, 30 globals). A decomposição completa é feita ao longo de sprints
dedicados (``financial_analyzer_v2``) — este módulo entrega a base:

- ``CashFlowAggregator``: fluxo de caixa mensal (receitas/despesas por mês).
- ``PatrimonioCalculator``: patrimônio líquido = ativos − passivos.
- ``EmergencyReserveCalculator``: reserva ≥ ``months`` × média de despesas.
- ``FinancialScoreCalculator``: score composto (implementação simples hoje).

Interfaces conservadoras — suficientes para testes unitários puros e para
o caminho B ao longo da Fase 8. Extensões posteriores são aditivas.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from pipeline.domain.models.document import BankStatement, BaselinePatrimonial
from pipeline.domain.models.transaction import Money, Transaction

# =============================================================================
# Config dataclasses (R9 — services não recebem StageConfig inteiro)
# =============================================================================


@dataclass(frozen=True)
class PatrimonioConfig:
    pass  # placeholder — params específicos entram conforme demanda


@dataclass(frozen=True)
class EmergencyReserveConfig:
    target_months: int = 6  # meses de despesas como meta de reserva


@dataclass(frozen=True)
class ScoreConfig:
    """Pesos do score (0-100). Default: soma = 100."""

    weight_patrimonio: int = 40
    weight_reserve: int = 30
    weight_positive_flow: int = 30


# =============================================================================
# Models de saída
# =============================================================================


@dataclass(frozen=True)
class MonthlyFlow:
    year_month: str  # "2026-01"
    income: Money
    expenses: Money

    @property
    def net(self) -> Money:
        return self.income - self.expenses


@dataclass(frozen=True)
class CashFlowReport:
    currency: str
    months: tuple[MonthlyFlow, ...]

    def to_dict(self) -> dict:
        return {
            "currency": self.currency,
            "months": [
                {
                    "ym": m.year_month,
                    "income": m.income.to_float(),
                    "expenses": m.expenses.to_float(),
                    "net": m.net.to_float(),
                }
                for m in self.months
            ],
        }


@dataclass(frozen=True)
class PatrimonioReport:
    total: Money
    assets: Money
    liabilities: Money
    by_member: dict[str, Money]

    def to_dict(self) -> dict:
        return {
            "total": self.total.to_float(),
            "assets": self.assets.to_float(),
            "liabilities": self.liabilities.to_float(),
            "by_member": {k: v.to_float() for k, v in self.by_member.items()},
        }


@dataclass(frozen=True)
class EmergencyReserveReport:
    current_balance: Money
    monthly_avg_expenses: Money
    target: Money
    months_of_coverage: Decimal
    target_months: int

    def to_dict(self) -> dict:
        return {
            "current_balance": self.current_balance.to_float(),
            "monthly_avg_expenses": self.monthly_avg_expenses.to_float(),
            "target": self.target.to_float(),
            "months_of_coverage": float(self.months_of_coverage),
            "target_months": self.target_months,
        }


# =============================================================================
# Calculadoras
# =============================================================================


class CashFlowAggregator:
    """Agrega fluxo de caixa mensal a partir de statements."""

    def aggregate(self, statements: Iterable[BankStatement]) -> CashFlowReport:
        stmts = list(statements)
        if not stmts:
            return CashFlowReport(currency="BRL", months=())

        currency = stmts[0].currency
        # Invariante: mesma moeda para agregação
        for s in stmts:
            if s.currency != currency:
                raise ValueError(
                    f"CashFlowAggregator requer mesma moeda; encontrei "
                    f"'{s.currency}' vs '{currency}'"
                )

        buckets: dict[str, dict[str, Money]] = {}
        zero = Money.zero(currency)
        for s in stmts:
            for t in s.transactions:
                if t.is_transfer:
                    continue
                ym = f"{t.date.year:04d}-{t.date.month:02d}"
                b = buckets.setdefault(ym, {"income": zero, "expenses": zero})
                if zero < t.amount:
                    b["income"] = b["income"] + t.amount
                elif t.amount < zero:
                    b["expenses"] = b["expenses"] + (-t.amount)
        months = tuple(
            MonthlyFlow(year_month=ym, income=v["income"], expenses=v["expenses"])
            for ym, v in sorted(buckets.items())
        )
        return CashFlowReport(currency=currency, months=months)


class PatrimonioCalculator:
    """Patrimônio líquido = ativos − passivos.

    **Foundation**: hoje assume que o ``BaselinePatrimonial`` é a fonte de
    ativos; passivos (cartão, financiamentos) serão incorporados quando E1.5
    evoluir para expor essa separação. Por hora ``liabilities`` é sempre zero
    se o baseline não informar.
    """

    def calculate(
        self,
        statements: Iterable[BankStatement],
        baseline: BaselinePatrimonial | None,
    ) -> PatrimonioReport:
        if baseline is None:
            return PatrimonioReport(
                total=Money.zero("BRL"),
                assets=Money.zero("BRL"),
                liabilities=Money.zero("BRL"),
                by_member={},
            )
        # Baseline já agrega ativos por membro. Flows dos statements compõem
        # a variação patrimonial — aqui só consumimos o baseline.
        assets = baseline.total_brl
        liabilities = Money.zero("BRL")
        total = assets - liabilities
        return PatrimonioReport(
            total=total,
            assets=assets,
            liabilities=liabilities,
            by_member=dict(baseline.members),
        )


class EmergencyReserveCalculator:
    """Reserva de emergência: saldo × meses de cobertura."""

    def __init__(self, config: EmergencyReserveConfig = EmergencyReserveConfig()) -> None:
        self._config = config

    def calculate(self, statements: Iterable[BankStatement]) -> EmergencyReserveReport:
        stmts = list(statements)
        if not stmts:
            return EmergencyReserveReport(
                current_balance=Money.zero("BRL"),
                monthly_avg_expenses=Money.zero("BRL"),
                target=Money.zero("BRL"),
                months_of_coverage=Decimal(0),
                target_months=self._config.target_months,
            )
        currency = stmts[0].currency
        aggregator = CashFlowAggregator()
        report = aggregator.aggregate(stmts)
        # Saldo corrente: soma das closing_balances (ou aproximação)
        current = Money.zero(currency)
        for s in stmts:
            if s.closing_balance is not None:
                current = current + s.closing_balance
            else:
                current = current + s.net_flow  # fallback
        n_months = len(report.months) or 1
        expense_total = Money.zero(currency)
        for m in report.months:
            expense_total = expense_total + m.expenses
        avg = (
            Money(expense_total.amount / Decimal(n_months), currency)
            if n_months > 0
            else Money.zero(currency)
        )
        target = avg * self._config.target_months
        months_of_coverage = current.amount / avg.amount if avg.amount != Decimal(0) else Decimal(0)
        return EmergencyReserveReport(
            current_balance=current,
            monthly_avg_expenses=avg,
            target=target,
            months_of_coverage=months_of_coverage,
            target_months=self._config.target_months,
        )


class FinancialScoreCalculator:
    """Score composto 0-100 (implementação conservadora).

    Componentes:
    - Patrimônio > 0 → peso cheio.
    - Reserva ≥ target → peso cheio; senão, proporcional.
    - Fluxo médio positivo → peso cheio; negativo → zero.
    """

    def __init__(self, config: ScoreConfig = ScoreConfig()) -> None:
        self._config = config

    def calculate(
        self,
        patrimonio: PatrimonioReport,
        reserve: EmergencyReserveReport,
        cash_flow: CashFlowReport,
    ) -> int:
        score = 0
        if Money.zero("BRL") < patrimonio.total:
            score += self._config.weight_patrimonio
        if reserve.target.amount > Decimal(0):
            ratio = min(Decimal(1), reserve.current_balance.amount / reserve.target.amount)
            score += int(self._config.weight_reserve * ratio)
        # fluxo médio positivo?
        if cash_flow.months:
            net_sum = Money.zero(cash_flow.currency)
            for m in cash_flow.months:
                net_sum = net_sum + m.net
            if Money.zero(cash_flow.currency) < net_sum:
                score += self._config.weight_positive_flow
        return max(0, min(100, score))
